# ExportPackingList

Plugin designed to add additional exported data for InvenTree BOs

## How to Use

When stock has been allocated to a project, you may navigate to the 'allocations' tab in a build order and download the packing list using this exporter.
Press 'download' as you would usually when downloading a CSV for table data. Choose 'ExportPackingList' instead of 'InvenTreeExporter'. You may toggle on the option to include all data typically associated with the allocations CSV, or leave the option untoggled for the raw formatted packing list.

### InvenTree Plugin Manager

1. Install this plugin in the webinterface with the packagename 'inventree-export-packing-list'

1. Enable the plugin in the plugin settings. You need to be signed in as a superuser for this.
**The server will restart if you enable the plugin**

### Command Line 

To install manually via the command line, run the following command:

```bash
pip install inventree-export-packing-list
```

### InvenTree Plugin Installer

1. Navigate to **Admin Center > Plugins**.
2. Press **Install Plugin** to open the Plugin Installation wizard.
- Package Name: **inventree-export-packing-list**
- Source URL: **git+https://github.com/HMHepburn/inventree-packing-list-export-plugin**
- Version: Leave this blank
3. Toggle **Confirm plugin installation**
4. Press **Install**

## Verification

To verify the plugin is working:
1. Navigate to **Settings > Plugin Management**.
2. Confirm **Export Packing List** is visible and the toggle is **ON**.
3. Navigate to a **Build Order** -> **Allocated Stock**.
4. Click **Export Data**. "Export Packing List" should appear in the "Exporter" dropdown.

## Troubleshooting
If the plugin is not visible:
- Ensure `INVENTREE_PLUGINS_ENABLED=True` is set in your environment.
- Check the InvenTree server logs for "Error loading plugin" messages.
