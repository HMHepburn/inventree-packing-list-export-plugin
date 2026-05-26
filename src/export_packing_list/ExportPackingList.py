import rest_framework.serializers as serializers
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

    def get_export_formats(self):
        return ['csv', 'xlsx']
    
    def update_headers(self, headers, context, **kwargs):
        """Update headers for the packing list export."""

        export_extra_headers = context.get("export_extra_headers", True)

        # Remove data from the headers
        if not export_extra_headers:
            headers.clear()

        # Append a 'required quantity' field
        headers["required_quantity"] = "Required Qty"

        # Append a 'package_part_name' field
        headers["package_part_name"] = "Package Part Name"

        # Append a 'part_name' field
        headers["part_name"] = "BOM MPN"

        # # *** For part name - might need to remove the '-PV' at the end of the part strings, but we can leave this for now

        # Append a 'parameter_value' field
        headers["parameter_value"] = "Value"

        # Append a 'PF' field
        headers["PF"] = "Press Fit"

        # Append a 'stock_location' field
        headers["stock_location"] = "Location"

        # Append a 'part_category' field
        headers["part_category"] = "Category"

        # Append a 'stock_item_quantity' field
        headers["stock_item_quantity"] = "Available Qty"

        # Append a 'unit_price' field
        headers["unit_price"] = "Unit Price"

        # Append a 'batch_code' field
        headers["batch_code"] = "PV IPN"

        # Append a box field - to be filled in manually by person kitting.
        headers["box"] = "Box"

        # Append a 'stock_item_packaging' field
        headers["stock_item_packaging"] = "Condition/Packaging"

        # Append a 'notes' field - Notes could be conditional depending on item price*
        headers["notes"] = "Notes"

        # Append a 'part_description' field
        headers["part_description"] = "Part Description"

        return headers

    def prefetch_queryset(self, queryset):
        # Perform pre-fetch on the provided queryset.
        queryset = queryset.prefetch_related(
            "build_line__build",
            "build_line__bom_item",
            "stock_item",  # Join the stock item table
            "stock_item__part",  # Join the part table
            "stock_item__supplier_part",  # Join the supplier part table
        )

        return queryset

    def export_data(
        self, queryset, serializer_class, headers, context, output, **kwargs
    ):
        # Export build data from the queryset.
        self.serializer_class = serializer_class

        # Pre-fetch related data to reduce database queries
        queryset = self.prefetch_queryset(queryset)

        self.build_data = []

        # Run through each item in the queryset
        for build_item in queryset:
            self.process_build_row(build_item, **kwargs)

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

    def process_build_row(self, build_item, **kwargs) -> list:
        """Process a single Build allocation row.

        Arguments:
            build_item: The BuildItem object to process
        """

        # serialize row data for export
        row = self.serializer_class(build_item, exporting=True).data

        # pre-processing steps for unit price, part category, part params, and BOM part name
        price = build_item.stock_item.purchase_price
        category = build_item.stock_item.part.category
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
        row["stock_location"] = build_item.stock_item.location.name if build_item.stock_item.location else ""
        row["part_category"] = category.name
        row["stock_item_quantity"] = build_item.stock_item.quantity
        row["unit_price"] = price
        row["batch_code"] = build_item.stock_item.batch
        row["box"] = ""
        row["stock_item_packaging"] = build_item.stock_item.packaging

        # For passives: unit price above $1
        # All other parts: unit price above $10

        if price and hasattr(price, 'amount'):
            unit_price = price.amount
            if(unit_price > 10):
                row["notes"] = "EXPENSIVE PART"
            elif(unit_price > 1 and category.parent.name == 'Passives'):
                row["notes"] = "PASSIVE EXPENSIVE PART"
        else:
            row["notes"] = ""
            
        row["part_description"] = build_item.build_line.bom_item.sub_part.description

        self.build_data.append(row)