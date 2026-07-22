# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import numpy as np
# from numpy.core.records import ndarray

from pyLibPhotogrammetry.core.Camera import Camera

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

    def from_enu_to_sensor(self,
                           position_enu):
        str_error = ''
        within = False
        withinAfterUndistortion = False
        position_image = None
        position_undistorted_image = None
        if not isinstance(self.sensor_id, int):
            str_error = ('Not exists sensor in camera: {} in block: {} in graphos file:\n{}'.
                         format(self.label, self.at_block.label, self.at_block.file_path))
            return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image
        if not self.sensor_id in self.at_block.sensor_by_id:
            str_error = ('Not exists sensor id: {} in camera: {} in block: {} in graphos file:\n{}'.
                         format(str(self.sensor_id), self.label, self.at_block.label, self.at_block.file_path))
            return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image
        sensor = self.at_block.sensor_by_id[self.sensor_id]
        pc_enu = self.get_pc_enu()
        x = position_enu[0] - pc_enu[0]
        y = position_enu[1] - pc_enu[1]
        z = position_enu[2] - pc_enu[2]
        str_error, within, withinAfterUndistortion, position_image, position_undistorted_image \
            = sensor.from_camera_to_sensor(x, y, z, self.enu_rot)
        return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image

    def get_pc_ecef(self):
        # if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
        #     master_camera = self.at_block.camera_by_id[self.master_id]
        #     pc_ecef = master_camera.get_pc_ecef()
        #     return pc_ecef
        pc_ecef = self.pc_ecef
        return pc_ecef
        # return self.pc_ecef

    def get_pc_enu(self):
        # if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
        #     master_camera = self.at_block.camera_by_id[self.master_id]
        #     pc_chunk = master_camera.get_pc_chunk()
        #     return pc_chunk
        pc_enu = self.pc_enu
        return pc_enu
        # return self.pc_enu

    def get_pc_geo3d(self):
        # if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
        #     master_camera = self.at_block.camera_by_id[self.master_id]
        #     pc_geo3d = master_camera.get_pc_geo3d()
        #     return pc_geo3d
        pc_geo3d = self.pc_geo3d
        return pc_geo3d
        # return self.pc_geo3d

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

    def is_usefull(self):
        is_usefull = True
        sensor = self.at_block.sensor_by_id[self.sensor_id]
        if not sensor:
            is_usefull = False
            return is_usefull
        # if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
        #     master_camera = self.at_block.camera_by_id[self.master_id]
        #     pc_geo3d = master_camera.get_pc_geo3d()
        #     if not pc_geo3d:
        #         is_usefull = False
        #         return is_usefull
        # else:
        #     pc_geo3d = self.get_pc_geo3d()
        #     if not isinstance(pc_geo3d, ndarray):
        #         is_usefull = False
        #         return is_usefull
        pc_geo3d = self.get_pc_geo3d()
        if not isinstance(pc_geo3d, np.ndarray):
            is_usefull = False
            return is_usefull
        return is_usefull
