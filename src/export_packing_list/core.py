import re

from rest_framework import serializers
from plugin import InvenTreePlugin
from plugin.mixins import DataExportMixin

from . import PLUGIN_VERSION


class BuildOrderExporterOptionsSerializer(serializers.Serializer):
    """Custom export options for the Build exporter plugin."""

    export_extra_headers = serializers.BooleanField(
        default=False,
        label="Extra Data",
        help_text="Include all data from standard allocation export in addition to packing list",
    )


class ExportPackingList(InvenTreePlugin, DataExportMixin):
    """ExportPackingList - custom InvenTree plugin."""

    # Plugin metadata
    TITLE = "Export Packing List"
    NAME = "ExportPackingList"
    SLUG = "export-packing-list"
    DESCRIPTION = "Plugin designed to add additional exported data for InvenTree BOs"
    VERSION = PLUGIN_VERSION
    MIN_VERSION = '0.15.0'

    # Additional project information
    AUTHOR = "Hannah Hepburn"
    LICENSE = "MIT"

    ExportOptionsSerializer = BuildOrderExporterOptionsSerializer

    # Only display export option when downloading from 'allocated stock' tab
    def supports_export(self, model_class: type, user, *args, **kwargs) -> bool:
        from build.models import BuildItem

        return issubclass(model_class, BuildItem)
    
    # Override to generate a custom filename upon exporting
    def generate_filename(self, model_class, export_format: str) -> str:
        build_name = model_class.__name__

        return f"{build_name}-packinglist.{export_format}"
    
    def get_export_formats(self):
        return ['csv', 'xlsx']
    
    def update_headers(self, headers, context, **kwargs):
        """Update headers for the packing list export."""
        export_extra_headers = context.get("export_extra_headers", True)

        # Remove data from the headers
        if not export_extra_headers:
            headers.clear()

        headers["required_quantity"] = "Required Qty"
        headers["package_part_name"] = "Package Part Name"
        headers["part_name"] = "BOM MPN"
        headers["parameter_value"] = "Value"
        headers["PF"] = "Press Fit"
        headers["stock_location"] = "Location"
        headers["part_category"] = "Category"
        headers["stock_item_quantity"] = "Available Qty"
        headers["unit_price"] = "Unit Price"
        headers["batch_code"] = "PV IPN"
        headers["box"] = "Box"
        headers["stock_item_packaging"] = "Condition/Packaging"
        headers["notes"] = "Notes"
        headers["part_description"] = "Part Description"

        return headers

    def prefetch_queryset(self, queryset):
        # Perform pre-fetch on the provided queryset.
        queryset = queryset.prefetch_related(
            "build_line__build",
            "build_line__bom_item",
            "stock_item",  # Join the stock item table
            "stock_item__part",  # Join the part table
            "stock_item__part__category",
            "stock_item__part__category__parent",
            "stock_item__supplier_part",
            "stock_item__location",
        )

        return queryset

    def export_data(
        self, queryset, serializer_class, headers, context, output, **kwargs
    ):
        # Export build data from the queryset.
        self.serializer_class = serializer_class

        # Pre-fetch related data to reduce database queries
        queryset = self.prefetch_queryset(queryset)

        # first_item = queryset.first()
        # if first_item and first_item.build and first_item.build.part:
        #     self.generate_filename(first_item.build.part.name)

        self.build_data = []

        # Run through each item in the queryset
        for build_item in queryset:
            self.process_build_row(build_item, **kwargs)

        # Apply multi-condition sorting
        self.build_data.sort(key=self._get_sort_key)

        return self.build_data

    def get_parameter_value(self, build_item, category):
        part = build_item.stock_item.part
        if not part:
            return "", ""

        part_data = part.report_context()
        parameters = part_data['parameters']

        # Initialize default values
        value_str = ""
        is_pf = ""

        # 1. Handle component values based on Category
        if category == 'Capacitors' and 'Capacitance' in parameters:
            value_str = parameters['Capacitance']
        elif category == 'Resistors' and 'Resistance' in parameters:
            value_str = parameters['Resistance']
        elif category == 'Inductors' and 'Inductance' in parameters:
            value_str = parameters['Inductance']

        # 2. Handle Press Fit parameter (can apply to Connectors or any other category)
        if 'Press Fit' in parameters:
            is_pf = parameters['Press Fit']

        return value_str, is_pf

    def _parse_numeric_value(self, val_str: str) -> float:
        """Helper function to turn component SI strings (e.g. '10k', '100nF') into float numbers for sorting."""
        if not val_str:
            return 0.0

        multipliers = {
            "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6,
            "m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9,
        }

        # Use regex to isolate different parameter values
        match = re.search(r"([0-9.]+)\s*([pnumµkMG])?", str(val_str))
        if match:
            number = float(match.group(1))
            unit = match.group(2)
            return float(number * multipliers.get(unit, 1.0))
        return 0.0

    def _get_sort_key(self, row: dict) -> tuple:
        """Returns a comparison tuple based on specified priority sorting rules."""
        loc = (row.get("stock_location") or "").lower()
        pf = (row.get("PF") or "").lower()
        parent_cat = (row.get("parent_category") or "").lower()
        cat = (row.get("part_category") or "").lower()
        pkg = (row.get("stock_item_packaging") or "").lower()
        part_name = (row.get("part_name") or "").lower()
        parameter_val = (row.get("parameter_value") or 0.0)

        if (pf == "true" or pf == "True"):
            pf = 0
        else:
            pf = 1

        is_passive_component = parent_cat == "Passives"

        if is_passive_component:
            # Type 0: Passive group branch
            parsed_val = self._parse_numeric_value(parameter_val)
            return (loc, pf, 0, cat, pkg, parsed_val, "")
        else:
            # Type 1: Standard part branch
            return (loc, pf, 1, "", "", 0.0, part_name)
        
    def process_build_row(self, build_item, **kwargs) -> list:
        """Process a single Build allocation row.

        Arguments:
            build_item: The BuildItem object to process
        """

        # serialize row data for export
        row = self.serializer_class(build_item, exporting=True).data

        try:
            # pre-processing steps to pull unit price, part category, part params, and BOM part name
            stock_item = build_item.stock_item
            price = stock_item.purchase_price
            category = stock_item.part.category if stock_item and stock_item.part else None
            category_name = category.name if category else ""
            parent_category_name = category.parent.name if category and category.parent else ""

            parameter_value, press_fit_status = self.get_parameter_value(build_item, category.name)
            bom_part_name = build_item.bom_item.sub_part.name.removesuffix("-PV")

            # There are setup and overages that may be applied to builds, deviating build required quantity from BOM quantity
            # To get true net required quantity for production, multiply BOM quantity with build quantity
            req_quantity = build_item.build.quantity * build_item.bom_item.quantity
            row["required_quantity"] = req_quantity

            # in instances where a stock item doesn't have an associated supplier part (i.e. no SKU)
            if build_item.stock_item.supplier_part:
                row["package_part_name"] = build_item.stock_item.supplier_part.SKU
            else:
                row["package_part_name"] = bom_part_name

            row["part_name"] = bom_part_name
            row["parameter_value"] = parameter_value
            row["PF"] = press_fit_status
            row["stock_location"] = stock_item.location.name if stock_item and stock_item.location else ""
            row["part_category"] = category_name
            row["parent_category"] = parent_category_name  # Used for sorting internal logic
            row["stock_item_quantity"] = stock_item.quantity
            row["unit_price"] = price
            row["batch_code"] = stock_item.batch
            row["box"] = ""
            row["stock_item_packaging"] = stock_item.packaging or ""

            # For passives: unit price above $1
            # All other parts: unit price above $10

            if price and hasattr(price, "amount"):
                unit_price = price.amount
                if(unit_price > 10):
                    row["notes"] = "EXPENSIVE PART"
                elif(unit_price > 1 and category.parent.name == "Passives"):
                    row["notes"] = "PASSIVE EXPENSIVE PART"
            else:
                row["notes"] = ""
                
            row["part_description"] = build_item.build_line.bom_item.sub_part.description
        except ValueError as e:
            row["part_name"] = "ERROR - could not pull data"
            row["parameter_value"] = str(e)
            row["parent_category"] = ""
        
        self.build_data.append(row)