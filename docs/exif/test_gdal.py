# Reading EXIF Metadata with GDAL
# GDAL provides tools to access EXIF metadata from raster files, such as GeoTIFFs or JPEGs. Here's how you can read EXIF metadata using GDAL in Python:
# Example Code:
# Python
from osgeo import gdal
gdal.UseExceptions()

# image_path = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\exif\\DSC05742.JPG"
image_path = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\docs\\exif\\IMG_0207_4.tif"

# Open the raster file
dataset = gdal.Open(image_path)

str_error = ''
# Retrieve EXIF metadata
# exif_metadata = dataset.GetMetadata("EXIF")
try:
    exif_metadata = dataset.GetMetadata("EXIF")
except Exception as e:
    str_error = 'GDAL Error: ' + e.args[0]
if not str_error:
    # Print the EXIF metadata
    if exif_metadata:
        for key, value in exif_metadata.items():
            print(f"{key}: {value}")
    else:
        print("No EXIF metadata found.")
yo = 1

# Key Points:

# GetMetadata("EXIF"): This retrieves EXIF metadata as a dictionary.
# Supported Formats: Ensure the file format supports EXIF metadata (e.g., GeoTIFF, JPEG).
# Dependencies: GDAL must be compiled with support for the relevant file format.

# This approach is useful for extracting geotagging information, timestamps, and other metadata embedded in images.
