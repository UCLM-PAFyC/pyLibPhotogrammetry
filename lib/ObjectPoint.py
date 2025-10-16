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
from pyLibPhotogrammetry.defs import defs_metashape_markers as defs_msm

class ObjectPoint:
    def __init__(self,
                 at_block):
        self.at_block = at_block
        self.crs_tools = self.at_block.project.crs_tools
        self.id = None
        self.label = None
        self.enabled = False
        self.position_crs_source = None # markers_crs, rest in CRSs project, all array[4]
        self.position = None # self.at_block.crs_id
        self.position_ecef = None
        self.position_geo3d = None

