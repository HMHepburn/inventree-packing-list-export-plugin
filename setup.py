from setuptools import setup, find_packages

setup(
    name="inventree-export-packing-list",  # Name on GitHub/Pip
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # Add any dependencies your plugin needs here, e.g., 'reportlab'
    ],
    entry_points={
        "inventree_plugins": [
            "ExportPackingList = export_packing_list.ExportPackingList:ExportPackingList"
        ]
    },
    author="Hannah",
    description="An InvenTree plugin to export custom packing lists",
    platforms="any",
)
