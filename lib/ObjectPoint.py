# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math
import numpy as np

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from pyLibPhotogrammetry.defs import defs_project
from pyLibPhotogrammetry.defs import defs_metashape_markers as defs_msm

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools

class ObjectPoint:
    def __init__(self,
                 at_block):
        self.at_block = at_block
        self.crs_tools = self.at_block.project.crs_tools
        self.id = None
        self.label = None
        self.enabled = False
        self.position_crs_source = None # only for GCPs, markers_crs, rest in CRSs project, all array[4]
        self.position = None # self.at_block.crs_id
        self.position_ecef = None
        self.position_geo3d = None

    def set_from_at_position_in_at_block_crs(self,
                                             point_coordinates):
        str_error = ''
        if not isinstance(point_coordinates, list):
            str_error = ('Point object space coordinates must be a list of three values')
            return str_error
        if len(point_coordinates) != 3:
            str_error = ('Point object space coordinates must be a list of three values')
            return str_error
        fc = point_coordinates[0]
        sc = point_coordinates[1]
        tc = point_coordinates[2]
        position = [[fc, sc, tc]]
        self.position = np.array(position[0])
        if self.at_block.crs_id != self.at_block.crs_ecef_id:
            position_ecef = [self.position.tolist()]
            str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_ecef_id, position_ecef)
            if str_error:
                str_error = ('Error in CRSs operation:\n{}'.format(str_error))
                return str_error
            self.position_ecef = np.array(position_ecef[0])
        else:
            self.position_ecef = np.array(self.position.tolist())
        if self.at_block.crs_id != self.at_block.crs_geo3d_id:
            position_geo3d = [self.position.tolist()]
            str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_geo3d_id, position_geo3d)
            if str_error:
                str_error = ('Error in CRSs operation:\n{}'.format(str_error))
                return str_error
            self.position_geo3d = np.array(position_geo3d[0])
        else:
            self.position_geo3d = np.array(self.position.tolist())
        if self.at_block.project.is_metashape_model:
            position_ecef = np.append(self.position_ecef, 1.0)
            self.position_chunk = np.matmul(self.at_block.transform_inv, position_ecef)
        else:
            self.position_chunk = None # to do
        return str_error



