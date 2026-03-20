# ExportPackingList

Plugin designed to add additional exported data for InvenTree BOs

### InvenTree Plugin Manager

1. Install this plugin in the webinterface with the packagename 'inventree-export-packing-list'

1. Enable the plugin in the plugin settings. You need to be signed in as a superuser for this.
**The server will restart if you enable the plugin**

### Command Line 

To install manually via the command line, run the following command:

```bash
pip install inventree-export-packing-list
```
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