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
