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
        self.pc_chunk = None
        self.pc_ecef = None
        self.pc_geo3d = None
