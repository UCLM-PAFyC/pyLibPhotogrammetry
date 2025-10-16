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
from pyLibPhotogrammetry.defs import defs_images as defs_img

from pyLibPhotogrammetry.lib.CameraMetashape import CameraMetashape
from pyLibPhotogrammetry.lib.ObjectPointMetashape import ObjectPointMetashape

class ImagePoint:
    def __init__(self,
                 camera,
                 marker):
        self.camera = camera
        self.marker = marker
        self.frame_id = None
        self.pinned = False
        self.crs_tools = self.marker.crs_tools
        self.values = {} # [type] = (column, row, stdColumn, stdRow, diffColumn, diffRow, diff2d)
        self.undistorted_values = {} # [type] = (column, row, stdColumn, stdRow, diffColumn, diffRow, diff2d)

    def set_frame_id(self, frame_id):
        self.frame_id = frame_id

    def set_measured_values(self, measured_values):
        self.values[defs_img.IMAGE_POINT_MEASURED] = measured_values

    def set_measured_undistorted_values(self, measured_undistorted_values):
        self.undistorted_values[defs_img.IMAGE_POINT_MEASURED] = measured_undistorted_values

    def set_pinned(self, pinned):
        self.pinned = pinned
