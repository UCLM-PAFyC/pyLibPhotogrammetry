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
from pyLibPhotogrammetry.defs import defs_metashape_markers as defs_msm

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
# from pyLibQtTools import Tools
# from pyLibGDAL import defs_gdal
# from pyLibGDAL.GDALTools import GDALTools

from pyLibPhotogrammetry.lib.Camera import Camera
from pyLibPhotogrammetry.lib.CalibrationMetashape import CalibrationMetashape

from osgeo import ogr

class CameraMetashape(Camera):
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

    def compute_footprint(self,
                          raster_dem,
                          number_of_points_by_side):
        str_error = None
        footprint_wkt = "POLYGON(("
        undistorted_footprint_wkt = "POLYGON(("
        str_error, at_block_crs_is_geographic = self.crs_tools.is_geographic(self.at_block.crs_id)
        if str_error:
            str_error = ('For AT Block: {}, getting is geographic CRS: {}\nError:\n{}'
                         .format(self.at_block.label, self.at_block.crs_id, str_error))
            return str_error, footprint_wkt, undistorted_footprint_wkt
        pc_at_block_crs = self.get_pc() # self.at_block.crs_id
        sensor = self.at_block.sensor_by_id[self.sensor_id]
        columns = sensor.width
        rows = sensor.height
        columns_inc = int(float(columns)/float(number_of_points_by_side-1))
        rows_inc = int(float(rows)/float(number_of_points_by_side-1))
        pixels_rows = []
        pixels_columns = []
        # upper row
        pixel_cont = 0
        pixel_row = 0
        pixel_column = 0
        pixels_rows.append(pixel_row)
        pixels_columns.append(pixel_column)
        pixel_cont = pixel_cont + 1
        while (pixel_cont < (number_of_points_by_side - 1)):
            pixel_column += columns_inc
            pixels_rows.append(pixel_row)
            pixels_columns.append(pixel_column)
            pixel_cont = pixel_cont + 1
        pixel_column = columns - 1
        pixels_rows.append(pixel_row)
        pixels_columns.append(pixel_column)
        # right column
        pixel_cont = 1
        pixel_row = 0
        pixel_column = columns - 1
        while (pixel_cont < (number_of_points_by_side - 1)):
            pixel_row += rows_inc
            pixels_rows.append(pixel_row)
            pixels_columns.append(pixel_column)
            pixel_cont = pixel_cont + 1
        pixel_row = rows - 1
        pixels_rows.append(pixel_row)
        pixels_columns.append(pixel_column)
        # lower row
        pixel_cont = 1
        pixel_row = rows - 1
        pixel_column = columns - 1
        while (pixel_cont < (number_of_points_by_side - 1)):
            pixel_column -= columns_inc
            pixels_rows.append(pixel_row)
            pixels_columns.append(pixel_column)
            pixel_cont = pixel_cont + 1
        pixel_column = 0
        pixels_rows.append(pixel_row)
        pixels_columns.append(pixel_column)
        # left column
        pixel_cont = 1
        pixel_row = rows - 1
        pixel_column = 0
        while (pixel_cont < (number_of_points_by_side - 1)):
            pixel_row -= rows_inc
            pixels_rows.append(pixel_row)
            pixels_columns.append(pixel_column)
            pixel_cont = pixel_cont + 1
        # distorted footprint
        use_distortion = True
        use_ppa = True
        first_pto_int = None
        for i in range(len(pixels_columns)):
            pixel_column = pixels_columns[i]
            pixel_row = pixels_rows[i]
            str_error, dx, dy, dz = self.from_sensor_to_chunk_coordinates_direction(pixel_column, pixel_row,
                                                                                    use_distortion, use_ppa)
            if str_error:
                str_error = ('Getting direction for pixel: [{}, {}]\nerror:\n{}'.
                             format(str(pixel_column), str(pixel_row), str_error))
                return str_error, footprint_wkt, undistorted_footprint_wkt
            pto_direction_chunk = np.zeros(4)
            pto_direction_chunk[0] = dx
            pto_direction_chunk[1] = dy
            pto_direction_chunk[2] = dz
            pto_direction_chunk[3] = 1
            pto_direction_ecef = np.matmul(self.at_block.transform, pto_direction_chunk)
            pto_direction_at_block_crs_aux = [[pto_direction_ecef[0], pto_direction_ecef[1], pto_direction_ecef[2]]]
            str_error = self.crs_tools.operation(self.at_block.crs_ecef_id, self.at_block.crs_id, pto_direction_at_block_crs_aux)
            if str_error:
                str_error = ('From AT Block ECEF CRS: {} to CRS: {}\nfor pixel: [{}, {}]\nerror:\n{}'.
                             format(self.at_block.crs_ecef_id, self.at_block.crs_id,
                                    str(pixel_column), str(pixel_row), str_error))
                return str_error, footprint_wkt, undistorted_footprint_wkt
            pto_direction_at_block_crs = [pto_direction_at_block_crs_aux[0][0],
                                          pto_direction_at_block_crs_aux[0][1],
                                          pto_direction_at_block_crs_aux[0][2]]
            # if i == 10:
            #     yo = 1
            str_error, pto_int = raster_dem.get_vector_dem_intersection(self.at_block.crs_id,
                                                                        pc_at_block_crs,
                                                                        pto_direction_at_block_crs)
            if str_error:
                str_error = ('Getting DEM intersection for pixel: [{}, {}]\nerror:\n{}'.
                             format(str(pixel_column), str(pixel_row), str_error))
                return str_error, footprint_wkt, undistorted_footprint_wkt
            # if np.abs(pto_int[0] - 379807.724199996) < 0.01 and np.abs(pto_int[1] - 4064344.753596645) < 0.01:
            #     yo = 1
            if i == 0:
                first_pto_int = pto_int
            if at_block_crs_is_geographic:
                footprint_wkt += ('{:.9f}'.format(pto_int[0]))
                footprint_wkt += (' {:.9f}'.format(pto_int[1]))
                # footprint_wkt += (' {:.4f}'.format(pto_int[2]))
            else:
                footprint_wkt += ('{:.4f}'.format(pto_int[0]))
                footprint_wkt += (' {:.4f}'.format(pto_int[1]))
                # footprint_wkt += (' {:.4f}'.format(pto_int[2]))
            footprint_wkt += ','
        if at_block_crs_is_geographic:
            footprint_wkt += ('{:.9f}'.format(first_pto_int[0]))
            footprint_wkt += (' {:.9f}'.format(first_pto_int[1]))
            # footprint_wkt += (' {:.4f}'.format(first_pto_int[2]))
        else:
            footprint_wkt += ('{:.4f}'.format(first_pto_int[0]))
            footprint_wkt += (' {:.4f}'.format(first_pto_int[1]))
            # footprint_wkt += (' {:.4f}'.format(first_pto_int[2]))
        footprint_wkt += '))'
        # undistorted footprint
        use_distortion = False
        use_ppa = True
        first_pto_int = None
        for i in range(len(pixels_columns)):
            pixel_column = pixels_columns[i]
            pixel_row = pixels_rows[i]
            str_error, dx, dy, dz = self.from_sensor_to_chunk_coordinates_direction(pixel_column, pixel_row,
                                                                                    use_distortion, use_ppa)
            if str_error:
                str_error = ('Getting direction for pixel: [{}, {}]\nerror:\n{}'.
                             format(str(pixel_column), str(pixel_row), str_error))
                return str_error, footprint_wkt, undistorted_footprint_wkt
            pto_direction_chunk = np.zeros(4)
            pto_direction_chunk[0] = dx
            pto_direction_chunk[1] = dy
            pto_direction_chunk[2] = dz
            pto_direction_chunk[3] = 1
            pto_direction_ecef = np.matmul(self.at_block.transform, pto_direction_chunk)
            pto_direction_at_block_crs_aux = [[pto_direction_ecef[0], pto_direction_ecef[1], pto_direction_ecef[2]]]
            str_error = self.crs_tools.operation(self.at_block.crs_ecef_id, self.at_block.crs_id, pto_direction_at_block_crs_aux)
            if str_error:
                str_error = ('From AT Block ECEF CRS: {} to CRS: {}\nfor pixel: [{}, {}]\nerror:\n{}'.
                             format(self.at_block.crs_ecef_id, self.at_block.crs_id,
                                    str(pixel_column), str(pixel_row), str_error))
                return str_error, footprint_wkt, undistorted_footprint_wkt
            pto_direction_at_block_crs = [pto_direction_at_block_crs_aux[0][0],
                                          pto_direction_at_block_crs_aux[0][1],
                                          pto_direction_at_block_crs_aux[0][2]]
            str_error, pto_int = raster_dem.get_vector_dem_intersection(self.at_block.crs_id,
                                                                        pc_at_block_crs,
                                                                        pto_direction_at_block_crs)
            if str_error:
                str_error = ('Getting DEM intersection for pixel: [{}, {}]\nerror:\n{}'.
                             format(str(pixel_column), str(pixel_row), str_error))
                return str_error, footprint_wkt, undistorted_footprint_wkt
            if i == 0:
                first_pto_int = pto_int
            if at_block_crs_is_geographic:
                undistorted_footprint_wkt += ('{:.9f}'.format(pto_int[0]))
                undistorted_footprint_wkt += (' {:.9f}'.format(pto_int[1]))
                # undistorted_footprint_wkt += (' {:.4f}'.format(pto_int[2]))
            else:
                undistorted_footprint_wkt += ('{:.4f}'.format(pto_int[0]))
                undistorted_footprint_wkt += (' {:.4f}'.format(pto_int[1]))
                # undistorted_footprint_wkt += (' {:.4f}'.format(pto_int[2]))
            undistorted_footprint_wkt += ','
        if at_block_crs_is_geographic:
            undistorted_footprint_wkt += ('{:.9f}'.format(first_pto_int[0]))
            undistorted_footprint_wkt += (' {:.9f}'.format(first_pto_int[1]))
            # undistorted_footprint_wkt += (' {:.4f}'.format(first_pto_int[2]))
        else:
            undistorted_footprint_wkt += ('{:.4f}'.format(first_pto_int[0]))
            undistorted_footprint_wkt += (' {:.4f}'.format(first_pto_int[1]))
            # undistorted_footprint_wkt += (' {:.4f}'.format(first_pto_int[2]))
        undistorted_footprint_wkt += '))'
        return str_error, footprint_wkt, undistorted_footprint_wkt

    def from_chunk_to_sensor(self,
                             position_chunk):
        str_error = ''
        within = False
        withinAfterUndistortion = False
        position_image = None
        position_undistorted_image = None
        if not isinstance(self.sensor_id, int):
            str_error = ('Not exists sensor in camera: {} in block: {} in metashape markers XML file:\n{}'.
                         format(self.label, self.at_block.label, self.at_block.file_path))
            return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image
        if not self.sensor_id in self.at_block.sensor_by_id:
            str_error = ('Not exists sensor id: {} in camera: {} in block: {} in metashape markers XML file:\n{}'.
                         format(str(self.sensor_id), self.label, self.at_block.label, self.at_block.file_path))
            return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image
        sensor = self.at_block.sensor_by_id[self.sensor_id]
        pc_chunk = self.get_pc_chunk()
        transform_inv = self.get_transform_inv()
        position_chunk_from_cp = position_chunk - pc_chunk
        position_camera = np.dot(transform_inv, position_chunk_from_cp)
        str_error, within, withinAfterUndistortion, position_image, position_undistorted_image \
            = sensor.from_camera_to_sensor(position_camera)
        if str_error:
            str_error = ('For operation with sensor: {} in camera: {} in block: {} in metashape markers XML file:\n{}\nError:\n{}'.
                         format(sensor.label, self.label, self.at_block.label, self.at_block.file_path, str_error))
            return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image
        return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image

    def from_sensor_to_chunk_coordinates_direction(self,
                                                   column,
                                                   row,
                                                   use_distortion,
                                                   use_ppa):
        str_error = ''
        dx = dy = dz = None
        x_cam = y_cam = z_cam = None
        sensor = self.at_block.sensor_by_id[self.sensor_id]
        str_error, x_cam, y_cam, z_cam = sensor.from_sensor_to_camera_coordinates_direction(column, row,
                                                                                            use_distortion, use_ppa)
        if str_error:
            return str_error, dx, dy, dz
        camera_coor = np.zeros(4)
        camera_coor[0] = x_cam
        camera_coor[1] = y_cam
        camera_coor[2] = z_cam
        camera_coor[3] = 1
        transform = self.get_transform()
        # chunk_coordinates = self.transform * camera_coor
        chunk_coordinates = np.dot(transform, camera_coor)
        dx = chunk_coordinates[0]
        dy = chunk_coordinates[1]
        dz = chunk_coordinates[2]
        return str_error, dx, dy, dz

    def get_pc_chunk(self):
        if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
            master_camera = self.at_block.camera_by_id[self.master_id]
            pc_chunk = master_camera.get_pc_chunk()
            return pc_chunk
        return self.pc_chunk

    def get_pc_ecef(self):
        if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
            master_camera = self.at_block.camera_by_id[self.master_id]
            pc_ecef = master_camera.get_pc_ecef()
            return pc_ecef
        return self.pc_ecef

    def get_pc_geo3d(self):
        if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
            master_camera = self.at_block.camera_by_id[self.master_id]
            pc_geo3d = master_camera.get_pc_geo3d()
            return pc_geo3d
        return self.pc_geo3d

    def get_transform(self):
        if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
            master_camera = self.at_block.camera_by_id[self.master_id]
            transform = master_camera.get_transform()
            return transform
        return self.transform

    def get_transform_inv(self):
        if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
            master_camera = self.at_block.camera_by_id[self.master_id]
            transform_inv = master_camera.get_transform_inv()
            return transform_inv
        return self.transform_inv

    def is_usefull(self):
        is_usefull = True
        sensor = self.at_block.sensor_by_id[self.sensor_id]
        if not sensor:
            is_usefull = False
            return is_usefull
        if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
            master_camera = self.at_block.camera_by_id[self.master_id]
            pc_geo3d = master_camera.get_pc_geo3d()
            if not pc_geo3d:
                is_usefull = False
                return is_usefull
        else:
            pc_geo3d = self.get_pc_geo3d()
            if not isinstance(pc_geo3d, ndarray):
                is_usefull = False
                return is_usefull
        return is_usefull

    def set_from_metashape_xml(self,
                               xml_element):
        str_error = ''
        #id
        if not defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_ID in xml_element:
            str_error = ('Not exists attribute: {} in camera in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_ID, self.at_block.file_path))
            return str_error
        str_id = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_ID]
        try:
            self.id = int(str_id)
        except ValueError:
            str_error = ('Attribute: {} in camera in metashape markers XML file:\n{}\n must be an integer: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_ID, self.at_block.file_path, str_id))
            return str_error
        if self.id in self.at_block.camera_by_id:
            str_error = ('Exists previous camera id: {} in camera in metashape markers XML file:\n{}'.
                         format(str(self.id), self.file_path,))
            return str_error
        # label
        if not defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_LABEL in xml_element:
            str_error = ('Not exists attribute: {} in camera in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_LABEL, self.at_block.file_path))
            return str_error
        label = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_LABEL]
        # if label == "IMG_0022_1" or label == "IMG_0194_1":
        #     yo = 1
        self.label = label
        #sensor_id
        if not defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_SENSOR_ID in xml_element:
            str_error = ('Not exists attribute: {} in camera in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_SENSOR_ID, self.at_block.file_path))
            return str_error
        str_sensor_id = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_SENSOR_ID]
        try:
            self.sensor_id = int(str_sensor_id)
        except ValueError:
            str_error = ('Attribute: {} in camera in metashape markers XML file:\n{}\n must be an integer: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_SENSOR_ID, self.at_block.file_path, str_id))
            return str_error
        if not self.sensor_id in self.at_block.sensor_by_id:
            str_error = ('Not exists sensor id: {} in camera: {} in metashape markers XML file:\n{}'.
                         format(str(self.sensor_id), self.label, self.at_block.file_path,))
            return str_error
        # enabled
        self.enabled = True # attribute enabled is optional
        if defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_ENABLED in xml_element:
            str_enabled = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_ENABLED]
            if str_enabled.casefold() == 'false':
                self.enabled = False
        if defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_MASTER_ID in xml_element:
            str_master_id = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_MASTER_ID]
            try:
                self.master_id = int(str_master_id)
            except ValueError:
                str_error = ('Attribute: {} in camera: {} in metashape markers XML file:\n{}\n must be an integer: {}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_ATTRIBUTE_MASTER_ID, self.label, self.at_block.file_path, str_id))
                return str_error
        # if self.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
        # transform
        if defs_msm.METASHAPE_MARKERS_XML_CAMERA_TRANSFORM_TAG in xml_element:
            transform_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_TRANSFORM_TAG]
            try:
                transform_values = [float(x) for x in transform_element.split()]
            except:
                str_error = ('Not float values in: {} in camera: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_TRANSFORM_TAG, self.label, self.at_block.file_path))
                return str_error
            if len(transform_values) != 16:
                str_error = ('Not 16 float values in: {} in camera: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_TEXT, self.label, self.at_block.file_path))
                return str_error
            self.transform = np.zeros((4, 4))
            for row in range(0, 4):
                for col in range(0, 4):
                    pos = row * 4 + col
                    self.transform[row, col] = transform_values[pos]
            u, s, v = np.linalg.svd(self.transform)
            self.transform_inv = np.dot(v.transpose(), np.dot(np.diag(s ** -1), u.transpose()))
            self.exists_transform = True
            self.exists_orientation = True
        # rotation_covariance
        if defs_msm.METASHAPE_MARKERS_XML_CAMERA_ROTATION_COVARIANCE_TAG in xml_element:
            rotation_covariance_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_ROTATION_COVARIANCE_TAG]
            try:
                rotation_covariance_values = [float(x) for x in rotation_covariance_element.split()]
            except:
                str_error = ('Not float values in: {} in camera: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_ROTATION_COVARIANCE_TAG, self.label, self.at_block.file_path))
                return str_error
            if len(rotation_covariance_values) != 9:
                str_error = ('Not 9 float values in: {} in camera: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_ROTATION_COVARIANCE_TAG, self.label, self.at_block.file_path))
                return str_error
            self.rotation_covariance = rotation_covariance_values
        # location_covariance
        if defs_msm.METASHAPE_MARKERS_XML_CAMERA_LOCATION_COVARIANCE_TAG in xml_element:
            location_covariance_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_LOCATION_COVARIANCE_TAG]
            try:
                location_covariance_values = [float(x) for x in location_covariance_element.split()]
            except:
                str_error = ('Not float values in: {} in camera: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_LOCATION_COVARIANCE_TAG, self.label, self.at_block.file_path))
                return str_error
            if len(location_covariance_values) != 9:
                str_error = ('Not 9 float values in: {} in camera: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_LOCATION_COVARIANCE_TAG, self.label, self.at_block.file_path))
                return str_error
            self.location_covariance = location_covariance_values
        # reference
        if defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_TAG in xml_element:
            reference_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_TAG]
            # x
            if not defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_FIRST_COORDINATE in reference_element:
                str_error = ('Not exists attribute: {} in element: {} in camera: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_FIRST_COORDINATE,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_TAG, self.label, self.at_block.file_path))
                return str_error
            str_reference_x = reference_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_FIRST_COORDINATE]
            try:
                reference_x = float(str_reference_x)
            except ValueError:
                str_error = ('Attribute: {} in element: {} in camera: {} in metashape markers XML file:\n{}\nmust be a float'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_FIRST_COORDINATE,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_TAG, self.label, self.at_block.file_path))
                return str_error
            # y
            if not defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_SECOND_COORDINATE in reference_element:
                str_error = ('Not exists attribute: {} in element: {} in camera: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_SECOND_COORDINATE,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_TAG, self.label, self.at_block.file_path))
                return str_error
            str_reference_y = reference_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_SECOND_COORDINATE]
            try:
                reference_y = float(str_reference_y)
            except ValueError:
                str_error = ('Attribute: {} in element: {} in camera: {} in metashape markers XML file:\n{}\nmust be a float'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_SECOND_COORDINATE,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_TAG, self.label, self.at_block.file_path))
                return str_error
            # z
            if not defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_THIRD_COORDINATE in reference_element:
                str_error = ('Not exists attribute: {} in element: {} in camera: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_THIRD_COORDINATE,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_TAG, self.label, self.at_block.file_path))
                return str_error
            str_reference_z = reference_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_THIRD_COORDINATE]
            try:
                reference_z = float(str_reference_z)
            except ValueError:
                str_error = ('Attribute: {} in element: {} in camera: {} in metashape markers XML file:\n{}\nmust be a float'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_THIRD_COORDINATE,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_TAG, self.label, self.at_block.file_path))
                return str_error
            # enabled
            if not defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_ENABLED in reference_element:
                str_error = ('Not exists attribute: {} in element: {} in camera: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_ENABLED,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_TAG, self.label, self.at_block.file_path))
                return str_error
            self.reference = [reference_x, reference_y, reference_z]
            str_enabled = reference_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_ENABLED]
            self.reference_enabled = True
            if str_enabled.casefold() == 'false':
                self.reference_enabled = False
        # if self.id == 235:
        #     yo = 1
        if self.exists_transform:
            # pc_local = np.zeros((4, 1))
            # pc_local[3][0] = 1
            pc_local = np.zeros(4)
            pc_local[3] = 1
            # self.pc_chunk = np.matmul(self.transform, pc_local)
            self.pc_chunk = np.dot(self.transform, pc_local)
            self.pc_ecef = np.matmul(self.at_block.transform, self.pc_chunk)
            pc_geo3d = [[self.pc_ecef[0], self.pc_ecef[1], self.pc_ecef[2]]]
            str_error = self.crs_tools.operation(self.at_block.crs_ecef_id, self.at_block.crs_geo3d_id, pc_geo3d)
            if str_error:
                str_error = ('In camera: {} in metashape markers XML file:\n{}\nError in ECEF to Geo3D operation:\n{}'.
                             format(self.label, self.at_block.file_path, str_error))
                return str_error
            self.pc_geo3d = np.array(pc_geo3d[0])
            self.pc = self.pc_geo3d
            str_error, crs_is_geographic = self.crs_tools.is_geographic(self.at_block.crs_id)
            if str_error:
                str_error = ('In camera: {} in metashape markers XML file:\n{}\nError getting is geographic chunk CRS:\n{}'.
                             format(self.label, self.at_block.file_path, str_error))
                return str_error
            if not crs_is_geographic:
                str_error = self.crs_tools.operation(self.at_block.crs_geo3d_id, self.at_block.crs_id, pc_geo3d)
                if str_error:
                    str_error = ('In camera: {} in metashape markers XML file:\n{}\nError in ECEF to Geo3D operation:\n{}'.
                                 format(self.label, self.at_block.file_path, str_error))
                    return str_error
                self.pc = np.array(pc_geo3d[0])
        return str_error







