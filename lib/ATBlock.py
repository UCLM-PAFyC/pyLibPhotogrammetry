# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from pyLibPhotogrammetry.defs import defs_project

# from pyLibCRSs import CRSsDefines as defs_crs
# from pyLibCRSs.CRSsTools import CRSsTools
# from pyLibQtTools import Tools
# from pyLibGDAL import defs_gdal
# from pyLibGDAL.GDALTools import GDALTools

class ATBlock:
    def __init__(self,
                 file_path,
                 project):
        self.label = None
        self.file_path = file_path
        self.project = project
        self.crs_id = None # from markers.xml
        self.camera_crs_id = None # from markers.xml
        self.gcps_crs_id = None # from markers.xml
        self.sensor_by_id = {}
        self.sensor_id_by_band = {}
        self.camera_by_id = {}
        self.cameras_id_by_multi_camera_master_id = {}
        self.gcps_by_id = {}
        self.image_points_by_gcp_id = {}

    def get_camera_from_camera_id(self,
                                  camera_id):
        if camera_id in self.camera_by_id:
            return self.camera_by_id[camera_id]
        return None

    def get_camera_from_image_file_path(self,
                                        image_file_path):
        image_file_path = os.path.normpath(image_file_path)
        for camera_id in self.camera_by_id:
            camera = self.camera_by_id[camera_id]
            if camera.image_file_path:
                camera_image_file_path = os.path.normpath(camera.image_file_path)
                if image_file_path.casefold() == camera_image_file_path.casefold():
                    return camera
        return None





