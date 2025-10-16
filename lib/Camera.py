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

class Camera:
    def __init__(self,
                 at_block):
        self.fid = None # db
        self.id = None
        self.label = None
        self.sensor_id = None
        self.master_id = defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID
        self.at_block = at_block
        self.enabled = True
        self.crs_tools = self.at_block.project.crs_tools
        self.image_file_path = None
        self.pc = None # self.at_block.crs_id
        self.exists_orientation = False
        self.enabled = False
        self.undistort_image_file_path = None
        self.string_id = None
        self.date = None
        self.utc = None
        self.sun_azimuth = None
        self.sun_elevation = None
        self.sun_glint = None
        self.sun_hotspot = None
        self.exif = None
        self.content = None
        self.footprint_geometry = None
        self.undistorted_footprint_geometry = None

    def get_enabled(self):
        if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
            master_camera = self.at_block.camera_by_id[self.master_id]
            enabled = master_camera.get_enabled()
            return enabled
        return self.enabled

    def get_pc(self):
        if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
            master_camera = self.at_block.camera_by_id[self.master_id]
            pc = master_camera.get_pc()
            return pc
        return self.pc



