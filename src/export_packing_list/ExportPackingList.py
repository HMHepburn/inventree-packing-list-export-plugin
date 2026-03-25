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

        # Append part parameter columns - use when we've implemented part params for value
        # if self.export_parameter_data and len(self.parameters) > 0:
        #     for key, value in self.parameters.items():
        #         headers[f'parameter_{key}'] = value

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

        # Append a 'stock_item_packaging' field
        headers["stock_item_packaging"] = "Condition/Packaging"

        # Append a 'notes' field - Notes could be conditional depending on item price*
        headers["notes"] = "Notes"

        # Append a 'part_description' field
        headers["part_description"] = "Part Description"

        return headers

        # Attributes:
        #         build: Link to a Build object
        #         build_line: Link to a BuildLine object (this is a "line item" within a build)
        #         stock_item: Link to a StockItem object
        #         quantity: Number of units allocated
        #         install_into: Destination stock item (or None)

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

    def process_build_row(self, build_item, **kwargs) -> list:
        """Process a single Build allocation row.

        Arguments:
            build_item: The BuildItem object to process
        """
        # Add this row to the output dataset
        row = self.serializer_class(build_item, exporting=True).data
        price = build_item.stock_item.purchase_price

        row["required_quantity"] = build_item.build_line.quantity

        # in instances where a stock item doesn't have an associated supplier part
        if build_item.stock_item.supplier_part:
            row["package_part_name"] = build_item.stock_item.supplier_part.SKU
        else:
            row["package_part_name"] = ""

        row["part_name"] = build_item.bom_item.sub_part.name
        # row['value'] = build_item.build_line.bom_item.part
        row["value"] = ""
        row["stock_location"] = build_item.stock_item.location.name if build_item.stock_item.location else ""
        row["part_category"] = build_item.build_line.bom_item.sub_part.category.name
        row["stock_item_quantity"] = build_item.stock_item.quantity
        row["unit_price"] = price
        row["batch_code"] = build_item.stock_item.batch
        row["stock_item_packaging"] = build_item.stock_item.packaging

        if price and hasattr(price, 'amount'):
            row["notes"] = "EXPENSIVE PART"
        else:
            row["notes"] = ""
            
        row["part_description"] = build_item.build_line.bom_item.sub_part.description

        self.build_data.append(row)

    # def get_parameter_data(self, build_item: BuildItem) -> dict:
    #     """Return parameter data for a BomItem."""
    #     parameter_data = {}

    #     for parameter in build_item.sub_part.parameters.all():
    #         template = parameter.template
    #         if template.pk not in self.parameters:
    #             self.parameters[template.pk] = template.name

    #         parameter_data.update({f'parameter_{template.pk}': parameter.data})

    #     return parameter_data
