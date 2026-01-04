# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(os.path.realpath(__file__))
# sys.path.append(os.path.join(current_path, '..'))
# sys.path.insert(0, '..')

processes_path = os.path.normpath(os.path.dirname(current_path) + '/processes')
GDAL_PATH = "gdal"
CGAL_PATH = "cgal"
LIB_PATH = "lib" # library processes
processes_providers = []
processes_providers.append(GDAL_PATH)
processes_providers.append(CGAL_PATH)
processes_providers.append(LIB_PATH)


PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_NAME = "Ground Control Points Accuracy Analysis"
PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_PARAMETER_OUTPUT_FILE_LABEL = "Results report file"

PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_NAME = "Get Image Footprints"
PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM = "Raster layer DEM"
PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM_CRS = "DEM CRS"
PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_NOP = "Number of points by footprint side"
PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_ENABLED_IMAGES = "Process only enabled images"
