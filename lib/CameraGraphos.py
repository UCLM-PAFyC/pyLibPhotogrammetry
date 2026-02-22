# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math
import numpy as np
from numpy.core.records import ndarray

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from pyLibPhotogrammetry.defs import defs_project
from pyLibPhotogrammetry.defs import defs_graphos as defs_gr

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
# from pyLibQtTools import Tools
# from pyLibGDAL import defs_gdal
# from pyLibGDAL.GDALTools import GDALTools

from pyLibPhotogrammetry.lib.Camera import Camera
from pyLibPhotogrammetry.lib.CalibrationGraphos import CalibrationGraphos

from osgeo import ogr

class CameraGraphos(Camera):
    def __init__(self,
                 at_block):
        super().__init__(at_block)
        self.transform = None
        self.transform_inv  = None
        self.exists_transform = False
        self.rotation_covariance = None
        self.location_covariance = None
        self.reference = None
        self.reference_enabled = True
        self.pc_enu = None
        self.pc_ecef = None
        self.pc_geo3d = None
        self.enu_rot = None

    def initialize(self, id, sensor_id, label, enu_x, enu_y, enu_z, enu_rot):
        str_error = ''
        self.id = id
        self.sensor_id = sensor_id
        self.label = label
        self.pc_enu = np.zeros(4)
        self.pc_enu[0] = enu_x
        self.pc_enu[1] = enu_y
        self.pc_enu[2] = enu_z
        self.pc_enu[3] = 1
        pc_geo3d = [[self.pc_enu[0], self.pc_enu[1], self.pc_enu[2]]]
        str_error = self.crs_tools.operation(self.at_block.crs_enu_id, self.at_block.crs_geo3d_id, pc_geo3d)
        if str_error:
            str_error = ('In camera: {} \nError in ENU to Geo3D operation:\n{}'.
                         format(self.label, str_error))
            return str_error
        self.pc_geo3d = np.array(pc_geo3d[0])
        # self.pc = self.pc_geo3d
        pc_ecef = [[self.pc_geo3d[0], self.pc_geo3d[1], self.pc_geo3d[2]]]
        str_error = self.crs_tools.operation(self.at_block.crs_geo3d_id, self.at_block.crs_ecef_id, pc_ecef)
        if str_error:
            str_error = ('In camera: {} \nError in Geo3D to ECEF operation:\n{}'.
                         format(self.label, str_error))
            return str_error
        self.pc_ecef = np.array(pc_ecef[0])
        # self.pc_geo3d = np.array(pc_geo3d[0])
        self.pc = self.pc_geo3d
        str_error, crs_is_geographic = self.crs_tools.is_geographic(self.at_block.crs_id)
        if str_error:
            str_error = ('In camera: {} \nError getting is geographic chunk CRS:\n{}'.
                         format(self.label, str_error))
            return str_error
        if not crs_is_geographic:
            str_error = self.crs_tools.operation(self.at_block.crs_geo3d_id, self.at_block.crs_id, pc_geo3d)
            if str_error:
                str_error = ('In camera: {} \nError in ECEF to Geo3D operation:\n{}'.
                             format(self.label, str_error))
                return str_error
            self.pc = np.array(pc_geo3d[0])
        self.enu_rot = enu_rot
        self.enabled = True
        return str_error
