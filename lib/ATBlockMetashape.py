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

from pyLibPhotogrammetry.defs import  defs_project
from pyLibPhotogrammetry.defs import defs_metashape_markers as defs_msm

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
# from pyLibQtTools import Tools
# from pyLibGDAL import defs_gdal
# from pyLibGDAL.GDALTools import GDALTools

from pyLibPhotogrammetry.lib.ATBlock import ATBlock
from pyLibPhotogrammetry.lib.SensorMetashape import SensorMetashape
from pyLibPhotogrammetry.lib.CameraMetashape import CameraMetashape
from pyLibPhotogrammetry.lib.ObjectPointMetashape import ObjectPointMetashape
from pyLibPhotogrammetry.lib.ImagePoint import ImagePoint

class ATBlockMetashape(ATBlock):
    def __init__(self,
                 file_path,
                 project):
        super().__init__(file_path, project)
        self.transform_scale = None
        self.transform = None
        self.transform_inv = None
        self.crs_geo2d_id = None
        self.crs_ecef_id = None
        self.crs_geo3d_id = None
        self.camera_crs_geo2d_id = None
        self.camera_crs_ecef_id = None
        self.camera_crs_geo3d_id = None
        self.gcps_crs_geo2d_id = None
        self.gcps_crs_ecef_id = None
        self.gcps_crs_geo3d_id = None
        self.cameras_group_by_id = {} # dictionary: id, label, type, cameras

    def from_sensors_to_object(self,
                               image_measured_coordinates_by_camera_id,
                               crs_id,
                               compute_backward_camera_coordinates,
                               use_distortion, use_ppa):
        str_error = ''
        position = []
        std_position = []
        image_position_backward_error_by_camera_id = {}
        number_of_image_points = len(image_measured_coordinates_by_camera_id)
        number_of_equations = 2 * number_of_image_points
        A = np.zeros((number_of_equations, 3))
        b = np.zeros((number_of_equations, 1))
        use_weights = True
        use_simplified_weights = True
        number_of_stds = 0
        for camera_id in image_measured_coordinates_by_camera_id:
            if use_weights and len(image_measured_coordinates_by_camera_id[camera_id]) >=4:
                number_of_stds = number_of_stds + 1
        if number_of_stds != number_of_image_points:
            use_weights = False
        MVC = None
        P = None
        if use_weights:
            MVC = np.zeros((number_of_equations, number_of_equations))
            P = np.zeros((number_of_equations, number_of_equations))
            for i in range(number_of_equations):
                MVC[i, i] = 1.0
                P[i, i] = 1.0
        n_img = 0
        for camera_id in image_measured_coordinates_by_camera_id:
            camera = self.camera_by_id[camera_id]
            column_m = image_measured_coordinates_by_camera_id[camera_id][0]
            row_m = image_measured_coordinates_by_camera_id[camera_id][1]
            sqrt_weight = 1.
            std_column = std_row = None
            if use_weights:
                std_column = image_measured_coordinates_by_camera_id[camera_id][2]
                std_row = image_measured_coordinates_by_camera_id[camera_id][3]
                sqrt_weight = 1. / np.sqrt(std_column ** 2. + std_row ** 2.)
            camera_pc_chunk = camera.get_pc_chunk()
            str_error, dx, dy, dz = camera.from_sensor_to_chunk_coordinates_direction(column_m, row_m,
                                                                                      use_distortion, use_ppa)
            if str_error:
                str_error = ('For camera: {}, error:\n{}'.format(camera.label, str_error))
                return str_error, position, std_position, image_position_backward_error_by_camera_id
            ca = (dx - camera_pc_chunk[0]) / (dz - camera_pc_chunk[2])
            cb = (dy - camera_pc_chunk[1]) / (dz - camera_pc_chunk[2])
            A[n_img * 2, 0] = 1.0 * sqrt_weight
            A[n_img * 2, 1] = 0.0 * sqrt_weight
            A[n_img * 2, 2] = -1.0 * ca * sqrt_weight
            A[n_img * 2 + 1, 0] = 0.0 * sqrt_weight
            A[n_img * 2 + 1, 1] = 1.0 * sqrt_weight
            A[n_img * 2 + 1, 2] = -1.0 * cb * sqrt_weight
            b[n_img * 2] = (camera_pc_chunk[0] - ca * camera_pc_chunk[2]) * sqrt_weight
            b[n_img * 2 + 1] = (camera_pc_chunk[1] - cb * camera_pc_chunk[2]) * sqrt_weight
            if use_weights and not use_simplified_weights and number_of_image_points >= 4:
                MVC_Obs = np.zeros((2, 2))
                MVC_Obs[0, 0] = std_column ** 2.
                MVC_Obs[1, 1] = std_row ** 2.
                J_1 = np.zeros((3, 2))
                inc_column = 0.5
                inc_row = 0.5
                str_error, ic_dx, ic_dy, ic_dz = camera.from_sensor_to_chunk_coordinates_direction(column_m + inc_column,
                                                                                                   row_m,
                                                                                                   use_distortion, use_ppa)
                if str_error:
                    str_error = ('For camera: {}, error:\n{}'.format(camera.label, str_error))
                    return str_error, position, std_position, image_position_backward_error_by_camera_id
                str_error, ir_dx, ir_dy, ir_dz = camera.from_sensor_to_chunk_coordinates_direction(column_m,
                                                                                                   row_m + inc_row,
                                                                                                   use_distortion, use_ppa)
                if str_error:
                    str_error = ('For camera: {}, error:\n{}'.format(camera.label, str_error))
                    return str_error, position, std_position, image_position_backward_error_by_camera_id
                J_1[0, 0] = ic_dx - dx
                J_1[0, 1] = ir_dx - dx
                J_1[1, 0] = ic_dy - dy
                J_1[1, 1] = ir_dy - dy
                J_1[2, 0] = ic_dx - dz
                J_1[2, 1] = ir_dz - dz
                aux_1 = np.matmul(MVC_Obs, J_1.transpose())
                matrix_var_first_calculation =np.matmul(J_1 * aux_1)
                length_vector = np.sqrt(ic_dx ** 2 + ic_dy ** 2 + ic_dz ** 2)
                inc_vector_inc_column = np.sqrt((ic_dx - dx) ** 2 + (ic_dy - dy) ** 2 + (ic_dz - dz) ** 2)
                inc_vector_inc_row = np.sqrt((ir_dx - dx) ** 2 + (ir_dy - dy) ** 2 + (ir_dz - dz) ** 2)
                inc_vector = (inc_vector_inc_column + inc_vector_inc_row) / 2.
                ca_incX = (dx + inc_vector - camera_pc_chunk[0]) / (dz - camera_pc_chunk[2])
                cb_incX = (dy - camera_pc_chunk[1]) / (dz - camera_pc_chunk[2])
                ca_incY = (dx - camera_pc_chunk[0]) / (dz - camera_pc_chunk[2])
                cb_incY = (dy + inc_vector - camera_pc_chunk[1]) / (dz - camera_pc_chunk[2])
                ca_incZ = (dx - camera_pc_chunk[0]) / (dz + inc_vector - camera_pc_chunk[2])
                cb_incZ = (dy - camera_pc_chunk[1]) / (dz + inc_vector - camera_pc_chunk[2])
                J_2 = np.zeros((2, 3))
                J_2[0,0]=(ca_incX-ca)/inc_vector
                J_2[0,1]=(ca_incY-ca)/inc_vector
                J_2[0,2]=(ca_incZ-ca)/inc_vector
                J_2[1,0]=(cb_incX-cb)/inc_vector
                J_2[1,1]=(cb_incY-cb)/inc_vector
                J_2[1,2]=(cb_incZ-cb)/inc_vector
                aux_2 = np.matmul(matrix_var_first_calculation, J_2.transpose())
                matrix_var_second_calculation =np.matmul(J_2 * aux_2)
                J_3 = np.zeros((2, 2))
                incCa = np.sqrt(ca_incX ** 2. + ca_incY ** 2. + ca_incZ ** 2.)
                incCb = np.sqrt(cb_incX ** 2. + cb_incY ** 2. + cb_incZ ** 2.)
                incC = (incCa + incCb) / 2.
                J_3[0, 0] = (camera_pc_chunk[0] - (ca + incC) * camera_pc_chunk[2] - b(n_img * 2)) / incC
                J_3[0, 1] = 0.
                J_3[1, 0] = 0.
                J_3[1, 1] = (camera_pc_chunk[1] - (cb + incC) * camera_pc_chunk[2] - b(n_img * 2 + 1)) / incC
                aux_3 = np.matmul(matrix_var_second_calculation, J_3.transpose())
                matrix_var_b =np.matmul(J_3 * aux_3)
                MVC[n_img * 2, n_img * 2] = matrix_var_b(0, 0)
                MVC[n_img * 2, n_img * 2 + 1] = matrix_var_b(0, 1)
                MVC[n_img * 2 + 1, n_img * 2] = matrix_var_b(1, 0)
                MVC[n_img * 2 + 1, n_img * 2 + 1] = matrix_var_b(1, 1)
            n_img = n_img + 1
        var = 1.
        var_pri = 1.
        numerical_rank_A = np.linalg.matrix_rank(A)
        degrees_of_freedom = number_of_equations - 3
        x = None
        Qxx = None
        if  use_weights and not use_simplified_weights:
            LChol_MVC = np.linalg.cholesky(MVC)
            inv_LChol_Qll = np.linalg.inv(LChol_MVC)
            P = var_pri * np.matmul(inv_LChol_Qll.transpose(), inv_LChol_Qll)
            # for i in range(number_of_equations):
            #     valueMVC = MVC(i, i)
            #     valueP = P(i, i)
            aux_1 = np.matmul(P, A)
            N = np.matmul(A.transpose(), aux_1)
            Lchol_N = np.linalg.cholesky(N)
            inv_LChol_N = np.linalg.inv(Lchol_N)
            Qxx = np.matmul(inv_LChol_N.transpose(), inv_LChol_N)
            aux_2 = np.matmul(P, b)
            AtPb = np.matmul(A.transpose(), aux_2)
            x = np.matmul(Qxx, AtPb)
            V = np.subtract(np.matmul(A, x), b)
            Vrel = np.matmul(inv_LChol_Qll, V)
            var_pos = np.matmul(Vrel.transpose(), Vrel) / degrees_of_freedom
            var_pos = var_pos.item(0)
        else:
            N = np.matmul(A.transpose(), A)
            Lchol_N = np.linalg.cholesky(N)
            inv_LChol_N = np.linalg.inv(Lchol_N)
            Qxx = np.matmul(inv_LChol_N.transpose(), inv_LChol_N)
            Atb = np.matmul(A.transpose(), b)
            x = np.matmul(Qxx, Atb)
            V = np.subtract(np.matmul(A, x), b)
            var_pos = np.matmul(V.transpose(), V) / degrees_of_freedom
            var_pos = var_pos.item(0)
        chunk_coor = np.zeros(4)
        chunk_coor[0] = x[0]
        chunk_coor[1] = x[1]
        chunk_coor[2] = x[2]
        chunk_coor[3] = 1
        ecef_coordinates = np.dot(self.transform, chunk_coor)
        pc_crs = [[ecef_coordinates[0], ecef_coordinates[1], ecef_coordinates[2]]]
        str_error = self.project.crs_tools.operation(self.crs_ecef_id, crs_id, pc_crs)
        if str_error:
            str_error = ('Error in ECEF to Geo3D operation:\n{}'.format(str_error))
            return str_error, position, std_position, image_position_backward_error_by_camera_id
        position = [pc_crs[0][0], pc_crs[0][1], pc_crs[0][2]]
        stdComputedFc = np.sqrt(var_pos * Qxx[0, 0])
        stdComputedSc = np.sqrt(var_pos * Qxx[1, 1])
        stdComputedTc = np.sqrt(var_pos * Qxx[2, 2])
        stdComputedFc = stdComputedFc * self.transform_scale
        stdComputedSc = stdComputedSc * self.transform_scale
        stdComputedTc = stdComputedTc * self.transform_scale
        std_position = [stdComputedFc, stdComputedSc, stdComputedTc]
        if not compute_backward_camera_coordinates:
            return str_error, position, std_position, image_position_backward_error_by_camera_id
        for camera_id in image_measured_coordinates_by_camera_id:
            camera = self.camera_by_id[camera_id]
            column_m = image_measured_coordinates_by_camera_id[camera_id][0]
            row_m = image_measured_coordinates_by_camera_id[camera_id][1]
            str_error, within, withinAfterUndistortion, position_image, position_undistorted_image \
                = camera.from_chunk_to_sensor(chunk_coor)
            if str_error:
                return str_error
            error_column = column_m - position_image[0]
            error_row = row_m - position_image[1]
            if not use_distortion:
                error_column = column_m - position_undistorted_image[0]
                error_row = row_m - position_undistorted_image[1]
            error_camera_coordinates = [error_column, error_row]
            image_position_backward_error_by_camera_id[camera_id] = error_camera_coordinates
        return str_error, position, std_position, image_position_backward_error_by_camera_id

    def set_from_metashape_xml(self,
                               xml_element):
        str_error = ''
        label = xml_element[defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL]
        if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_ENABLED in xml_element:
            str_error = ('Not exists attribute: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_ENABLED, self.file_path))
            return str_error
        str_enabled = xml_element[defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_ENABLED]
        enabled = False
        if str_enabled.casefold() == 'true':
            enabled = True
        if not enabled:
            str_error = ('Chunk: {} is disabled in metashape markers XML file:\n{}'.
                         format(label, self.file_path))
            return str_error
        if label in self.project.at_block_by_label:
            str_error = ('Exists chunk: {} in project importing metashape markers XML file:\n{}'.
                         format(label, self.file_path))
            return str_error
        self.label = label

        # transform
        if not defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_TAG in xml_element:
            str_error = ('Not exists element: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_TAG, self.file_path))
            return str_error
        transform_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_ROTATION_TAG in transform_element:
            str_error = ('Not exists element: {} in transform in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_ROTATION_TAG, self.file_path))
            return str_error
        if not defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_TRANSLATION_TAG in transform_element:
            str_error = ('Not exists element: {} in transform in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_TRANSLATION_TAG, self.file_path))
            return str_error
        if not defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_SCALE_TAG in transform_element:
            str_error = ('Not exists element: {} in transform in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_SCALE_TAG, self.file_path))
            return str_error
        transform_rotation_element = transform_element[defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_ROTATION_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_TEXT in transform_rotation_element:
            str_error = ('Not exists: {} in transform rotation in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TEXT, self.file_path))
            return str_error
        transform_rotation_element_text = transform_rotation_element[defs_msm.METASHAPE_MARKERS_XML_TEXT]
        try:
            transform_rotation_values = [float(x) for x in transform_rotation_element_text.split()]
        except:
            str_error = ('Not float values in: {} in transform rotation in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TEXT, self.file_path))
            return str_error
        if len(transform_rotation_values) != 9:
            str_error = ('Not 9 float values in: {} in transform rotation in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TEXT, self.file_path))
            return str_error
        transform_translation_element = transform_element[defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_TRANSLATION_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_TEXT in transform_translation_element:
            str_error = ('Not exists: {} in transform translation in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TEXT, self.file_path))
            return str_error
        transform_translation_element_text = transform_translation_element[defs_msm.METASHAPE_MARKERS_XML_TEXT]
        try:
            transform_translation_values = [float(x) for x in transform_translation_element_text.split()]
        except:
            str_error = ('Not float values in: {} in transform translation in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TEXT, self.file_path))
            return str_error
        if len(transform_translation_values) != 3:
            str_error = ('Not 3 float values in: {} in transform translation in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TEXT, self.file_path))
            return str_error
        transform_scale_element = transform_element[defs_msm.METASHAPE_MARKERS_XML_TRANSFORM_SCALE_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_TEXT in transform_scale_element:
            str_error = ('Not exists: {} in transform scale in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TEXT, self.file_path))
            return str_error
        transform_sale_element_text = transform_scale_element[defs_msm.METASHAPE_MARKERS_XML_TEXT]
        try:
            transform_scale_values = [float(x) for x in transform_sale_element_text.split()]
        except:
            str_error = ('Not float values in: {} in transform scale in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TEXT, self.file_path))
            return str_error
        if len(transform_scale_values) != 1:
            str_error = ('Not 1 float values in: {} in transform scale in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_TEXT, self.file_path))
            return str_error
        self.transform_scale = transform_scale_values[0]
        self.transform = np.zeros((4, 4))
        for row in range(0, 3):
            for col in range(0, 3):
                pos = row * 3 + col
                self.transform[row, col] = transform_rotation_values[pos] * self.transform_scale
            self.transform[row, 3] = transform_translation_values[row]
        self.transform[3, 3] = 1.
        # self.transform_inv_bad = np.linalg.inv(self.transform)
        u, s, v = np.linalg.svd(self.transform)
        self.transform_inv = np.dot(v.transpose(),np.dot(np.diag(s**-1),u.transpose()))

        # reference
        if not defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG in xml_element:
            str_error = ('Not exists element: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG, self.file_path))
            return str_error
        reference_wkt = xml_element[defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG]
        str_error, crs_id, crs_epsg_code, vertical_crs_epsg_code = self.project.crs_tools.get_crs_from_wkt(reference_wkt)
        # reference_wkt_cmp = "COMPD_CS[\"ETRS89 / UTM zone 30N + Alicante height\",PROJCS[\"ETRS89 / UTM zone 30N\",GEOGCS[\"ETRS89\",DATUM[\"European Terrestrial Reference System 1989 ensemble\",SPHEROID[\"GRS 1980\",6378137,298.257222101,AUTHORITY[\"EPSG\",\"7019\"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY[\"EPSG\",\"6258\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.01745329251994328,AUTHORITY[\"EPSG\",\"9102\"]],AUTHORITY[\"EPSG\",\"4258\"]],PROJECTION[\"Transverse_Mercator\",AUTHORITY[\"EPSG\",\"9807\"]],PARAMETER[\"latitude_of_origin\",0],PARAMETER[\"central_meridian\",-3],PARAMETER[\"scale_factor\",0.9996],PARAMETER[\"false_easting\",500000],PARAMETER[\"false_northing\",0],UNIT[\"metre\",1,AUTHORITY[\"EPSG\",\"9001\"]],AUTHORITY[\"EPSG\",\"25830\"]],VERT_CS[\"Alicante height\",VERT_DATUM[\"Alicante\",2005,AUTHORITY[\"EPSG\",\"5180\"]],UNIT[\"metre\",1,AUTHORITY[\"EPSG\",\"9001\"]],AUTHORITY[\"EPSG\",\"5782\"]]]"
        # reference_wkt_bad = "COMPD_KK[\"ETRS89 / UTM zone 30N + Alicante height\",PROJCS[\"ETRS89 / UTM zone 30N\",GEOGCS[\"ETRS89\",DATUM[\"European Terrestrial Reference System 1989 ensemble\",SPHEROID[\"GRS 1980\",6378137,298.257222101,AUTHORITY[\"EPSG\",\"7019\"]],TOWGS84[0,0,0,0,0,0,0],AUTHORITY[\"EPSG\",\"6258\"]],PRIMEM[\"Greenwich\",0,AUTHORITY[\"EPSG\",\"8901\"]],UNIT[\"degree\",0.01745329251994328,AUTHORITY[\"EPSG\",\"9102\"]],AUTHORITY[\"EPSG\",\"4258\"]],PROJECTION[\"Transverse_Mercator\",AUTHORITY[\"EPSG\",\"9807\"]],PARAMETER[\"latitude_of_origin\",0],PARAMETER[\"central_meridian\",-3],PARAMETER[\"scale_factor\",0.9996],PARAMETER[\"false_easting\",500000],PARAMETER[\"false_northing\",0],UNIT[\"metre\",1,AUTHORITY[\"EPSG\",\"9001\"]],AUTHORITY[\"EPSG\",\"25830\"]],VERT_CS[\"Alicante height\",VERT_DATUM[\"Alicante\",2005,AUTHORITY[\"EPSG\",\"5180\"]],UNIT[\"metre\",1,AUTHORITY[\"EPSG\",\"9001\"]],AUTHORITY[\"EPSG\",\"5782\"]]]"
        # str_error, crs_id_cmp, crs_epsg_code_cmp, vertical_crs_epsg_code_cmp = self.project.crs_tools.get_crs_from_wkt(reference_wkt_cmp)
        # str_error, crs_id_bad, crs_epsg_code_bad, vertical_crs_epsg_code_bad = self.project.crs_tools.get_crs_from_wkt(reference_wkt_bad)
        if str_error:
            str_error = ('Reading element: {} in chunk in metashape markers XML file:\n{}\nError:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG, self.file_path, str_error))
            return str_error
        if not crs_id:
            str_error = ('Reading element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                         format(defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG, self.file_path))
            return str_error
        crs_geo2d_id = self.project.crs_tools.get_crs_geo2d_for_crs(crs_id)
        if not crs_geo2d_id:
            str_error = (
                'Getting CRS geographic 2D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                format(defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG, self.file_path))
        crs_ecef_ids = self.project.crs_tools.get_crs_ecef_ids_for_crs_geo2d_id(crs_geo2d_id)
        if not crs_ecef_ids:
            str_error = (
                'Getting CRS ECEF from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                format(defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG, self.file_path))
        crs_ecef_id = crs_ecef_ids[0]
        crs_geo3d_ids = self.project.crs_tools.get_crs_geo3d_ids_for_crs_geo2d_id(crs_geo2d_id)
        if not crs_geo3d_ids:
            str_error = (
                'Getting CRS geographic 3D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                format(defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG, self.file_path))
        crs_geo3d_id = crs_geo3d_ids[0]
        self.crs_id = crs_id
        self.crs_geo2d_id = crs_geo2d_id
        self.crs_ecef_id = crs_ecef_id
        self.crs_geo3d_id = crs_geo3d_id

        # camera_reference
        if defs_msm.METASHAPE_MARKERS_XML_CAMERAS_REFERENCE_TAG in xml_element:
            camera_reference_wkt = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERAS_REFERENCE_TAG]
            str_error, camera_crs_id, camera_crs_epsg_code, camera_vertical_crs_epsg_code = self.project.crs_tools.get_crs_from_wkt(
                camera_reference_wkt)
            if str_error:
                str_error = ('Reading element: {} in chunk in metashape markers XML file:\n{}\nError:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_REFERENCE_TAG, self.file_path, str_error))
                return str_error
            if not crs_id:
                str_error = ('Reading element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_REFERENCE_TAG, self.file_path))
                return str_error
            camera_crs_geo2d_id = self.project.crs_tools.get_crs_geo2d_for_crs(camera_crs_id)
            if not camera_crs_geo2d_id:
                str_error = (
                    'Getting CRS geographic 2D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_REFERENCE_TAG, self.file_path))
            camera_crs_ecef_ids = self.project.crs_tools.get_crs_ecef_ids_for_crs_geo2d_id(camera_crs_geo2d_id)
            if not crs_ecef_ids:
                str_error = (
                    'Getting CRS ECEF from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_REFERENCE_TAG, self.file_path))
            camera_crs_ecef_id = camera_crs_ecef_ids[0]
            camera_crs_geo3d_ids = self.project.crs_tools.get_crs_geo3d_ids_for_crs_geo2d_id(camera_crs_geo2d_id)
            if not crs_geo3d_ids:
                str_error = (
                    'Getting CRS geographic 3D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_REFERENCE_TAG, self.file_path))
            camera_crs_geo3d_id = camera_crs_geo3d_ids[0]
            self.camera_crs_id = camera_crs_id
            self.camera_crs_geo2d_id = camera_crs_geo2d_id
            self.camera_crs_ecef_id = camera_crs_ecef_id
            self.camera_crs_geo3d_id = camera_crs_geo3d_id
        else:
            self.camera_crs_id = self.crs_id
            self.camera_crs_geo2d_id = self.crs_geo2d_id
            self.camera_crs_ecef_id = self.crs_ecef_id
            self.camera_crs_geo3d_id = self.crs_geo3d_id

        # gcps_reference
        if defs_msm.METASHAPE_MARKERS_XML_MARKERS_REFERENCE_TAG in xml_element:
            gcps_reference_wkt = xml_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_REFERENCE_TAG]
            str_error, gcps_crs_id, gcps_crs_epsg_code, gcps_vertical_crs_epsg_code = self.project.crs_tools.get_crs_from_wkt(
                gcps_reference_wkt)
            if str_error:
                str_error = ('Reading element: {} in chunk in metashape markers XML file:\n{}\nError:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_REFERENCE_TAG, self.file_path, str_error))
                return str_error
            if not crs_id:
                str_error = ('Reading element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                             format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_REFERENCE_TAG, self.file_path))
                return str_error
            gcps_crs_geo2d_id = self.project.crs_tools.get_crs_geo2d_for_crs(gcps_crs_id)
            if not gcps_crs_geo2d_id:
                str_error = (
                    'Getting CRS geographic 2D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_REFERENCE_TAG, self.file_path))
            gcps_crs_ecef_ids = self.project.crs_tools.get_crs_ecef_ids_for_crs_geo2d_id(gcps_crs_geo2d_id)
            if not crs_ecef_ids:
                str_error = (
                    'Getting CRS ECEF from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_REFERENCE_TAG, self.file_path))
            gcps_crs_ecef_id = gcps_crs_ecef_ids[0]
            gcps_crs_geo3d_ids = self.project.crs_tools.get_crs_geo3d_ids_for_crs_geo2d_id(gcps_crs_geo2d_id)
            if not crs_geo3d_ids:
                str_error = (
                    'Getting CRS geographic 3D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_REFERENCE_TAG, self.file_path))
            gcps_crs_geo3d_id = gcps_crs_geo3d_ids[0]
            self.gcps_crs_id = gcps_crs_id
            self.gcps_crs_geo2d_id = gcps_crs_geo2d_id
            self.gcps_crs_ecef_id = gcps_crs_ecef_id
            self.gcps_crs_geo3d_id = gcps_crs_geo3d_id
        else:
            self.gcps_crs_id = self.crs_id
            self.gcps_crs_geo2d_id = self.crs_geo2d_id
            self.gcps_crs_ecef_id = self.crs_ecef_id
            self.gcps_crs_geo3d_id = self.crs_geo3d_id

        # METASHAPE_MARKERS_XML_SENSORS_TAG
        if not defs_msm.METASHAPE_MARKERS_XML_SENSORS_TAG in xml_element:
            str_error = ('Not exists element: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSORS_TAG, self.file_path))
            return str_error
        sensors_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSORS_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_TAG in sensors_element:
            str_error = ('Not exists element: {} in: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_TAG,
                                defs_msm.METASHAPE_MARKERS_XML_SENSORS_TAG, self.file_path))
            return str_error
        sensors_content = sensors_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_TAG]
        sensors_list = []
        if isinstance(sensors_content, dict):
            sensors_list.append(sensors_content)
        else:
            sensors_list = sensors_content
        is_multi_band = False
        for i in range(len(sensors_list)):
            sensor_element = sensors_list[i]
            sensor = SensorMetashape(self)
            str_error = sensor.set_from_metashape_xml(sensor_element)
            if str_error:
                str_error = ('Loading sensor position: {}\nError:\n{}'.format(str(i+1), str_error))
                return str_error
            self.sensor_by_id[sensor.id] = sensor
            if sensor.master_id != defs_msm.METASHAPE_MARKERS_XML_SENSOR_NO_MASTER_ID:
                if not is_multi_band:
                    is_multi_band = True
        if is_multi_band:
            for sensor_id in self.sensor_by_id:
                sensor = self.sensor_by_id[sensor_id]
                band_name = sensor.band_names[0]
                self.sensor_id_by_band[band_name] = sensor.id

        # METASHAPE_MARKERS_XML_CAMERAS_TAG
        if not defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG in xml_element:
            str_error = ('Not exists element: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG, self.file_path))
            return str_error
        cameras_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG]
        if defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_TAG in cameras_element:
            cameras_group_element = cameras_element[defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_TAG]
            # id
            if not defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_ID in cameras_group_element:
                str_error = ('Not exists attribute: {} in element: {} in element: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_ID,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG, self.file_path))
                return str_error
            str_cameras_group_id = cameras_group_element[defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_ID]
            cameras_group_id = None
            try:
                cameras_group_id = int(str_cameras_group_id)
            except ValueError:
                str_error = ('Attribute: {} in camera in metashape markers XML file:\n{}\n must be an integer: {}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_ID, self.file_path, str_cameras_group_id))
                return str_error
            if cameras_group_id in self.cameras_group_by_id:
                str_error = ('Exists previous cameras group id: {} in metashape markers XML file:\n{}'.
                             format(str(cameras_group_id), self.file_path, ))
                return str_error
            # label
            if not defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_LABEL in cameras_group_element:
                str_error = ('Not exists attribute: {} in element: {} in element: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_LABEL,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG, self.file_path))
                return str_error
            cameras_group_label = cameras_group_element[defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_LABEL]
            # type
            if not defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_TYPE in cameras_group_element:
                str_error = ('Not exists attribute: {} in element: {} in element: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_TYPE,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG, self.file_path))
                return str_error
            cameras_group_type = cameras_group_element[defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_TYPE]
            if not defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_CAMERA_TAG in cameras_group_element:
                str_error = ('Not exists element: {} in element: {} in element: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_CAMERA_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG, self.file_path))
                return str_error
            cameras_group_camera_list_element = cameras_group_element[defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_CAMERA_TAG]
            if not isinstance(cameras_group_camera_list_element, list):
                str_error = ('Element: {} in element: {} in element: {} in metashape markers XML file:\n{}\nmust be a list'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_CAMERA_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG, self.file_path))
                return str_error
            cameras_group_camera_by_id = {}
            for i in range(len(cameras_group_camera_list_element)):
                camera_element = cameras_group_camera_list_element[i]
                camera = CameraMetashape(self)
                str_error = camera.set_from_metashape_xml(camera_element)
                if str_error:
                    str_error = ('Loading camera position: {}\nError:\n{}'.format(str(i + 1), str_error))
                    return str_error
                cameras_group_camera_by_id[camera.id] = camera
            self.cameras_group_by_id[cameras_group_id] = {}  # dictionary: label, type, cameras
            self.cameras_group_by_id[cameras_group_id][defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_LABEL] = cameras_group_label
            self.cameras_group_by_id[cameras_group_id][defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_TYPE] = cameras_group_type
            self.cameras_group_by_id[cameras_group_id][defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_CAMERA_TAG] = cameras_group_camera_by_id
        if not defs_msm.METASHAPE_MARKERS_XML_CAMERAS_CAMERA_TAG in cameras_element:
            str_error = ('Not exists element: {} in element: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_CAMERA_TAG,
                                defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG, self.file_path))
            return str_error
        camera_list_element = cameras_element[defs_msm.METASHAPE_MARKERS_XML_CAMERAS_CAMERA_TAG]
        if not isinstance(camera_list_element, list):
            str_error = ('Element: {} in element: {} in chunk in metashape markers XML file:\n{}\nmust be a list.'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_CAMERA_TAG,
                                defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG, self.file_path))
            return str_error
        for i in range(len(camera_list_element)):
            camera_element = camera_list_element[i]
            camera = CameraMetashape(self)
            str_error = camera.set_from_metashape_xml(camera_element)
            if str_error:
                str_error = ('Loading camera position: {}\nError:\n{}'.format(str(i+1), str_error))
                return str_error
            self.camera_by_id[camera.id] = camera
        for camera_id in self.cameras_group_by_id:
            camera = self.camera_by_id[camera_id]
            if camera.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
                if not camera.master_id in self.cameras_id_by_multi_camera_master_id:
                    self.cameras_id_by_multi_camera_master_id[camera.master_id] = []
                self.cameras_id_by_multi_camera_master_id[camera.master_id].append(camera_id)
        # METASHAPE_MARKERS_XML_MARKERS_TAG
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_TAG in xml_element:
            return str_error
        markers_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_TAG in markers_element:
            str_error = ('Not exists element: {} in element: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_TAG,
                                defs_msm.METASHAPE_MARKERS_XML_MARKERS_TAG, self.file_path))
            return str_error
        markers_list_element = []
        markers_element_content = markers_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_TAG]
        if not isinstance(markers_element_content, list):
            markers_list_element.append(markers_element_content)
            # str_error = ('Element: {} in element: {} in chunk in metashape markers XML file:\n{}\nmust be a list.'.
            #              format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_TAG,
            #                     defs_msm.METASHAPE_MARKERS_XML_MARKERS_TAG, self.file_path))
            # return str_error
        else:
            markers_list_element = markers_element_content
        for i in range(len(markers_list_element)):
            marker_element = markers_list_element[i]
            gcp = ObjectPointMetashape(self)
            str_error = gcp.set_from_metashape_xml(marker_element)
            if str_error:
                str_error = ('Loading marker position: {}\nError:\n{}'.format(str(i+1), str_error))
                return str_error
            self.gcps_by_id[gcp.id] = gcp
        # METASHAPE_MARKERS_XML_FRAMES_TAG
        if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG in xml_element:
            return str_error
        frames_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG in frames_element:
            return str_error
        frame_element = frames_element[defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_ATTRIBUTE_ID in frame_element:
            str_error = ('Not exists attribute: {} in element: {} in element: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_ATTRIBUTE_ID,
                                defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path))
            return str_error
        str_id = frame_element[defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_ATTRIBUTE_ID]
        frame_id = None
        try:
            frame_id = int(str_id)
        except ValueError:
            str_error = ('Attribute: {} in element: {} in element: {} in metashape markers XML file:\n{}\nmust be an integer: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_ATTRIBUTE_ID,
                                defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path, str_id))
            return str_error
        if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG in frame_element:
            return str_error
        frame_markers_element = frame_element[defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG]
        frame_markers_list = []
        if not isinstance(frame_markers_element, list):
            frame_markers_list.append(frame_markers_element)
        else:
            frame_markers_list = frame_markers_element
        for i in range(len(frame_markers_list)):
            frame_marker_element_content = frame_markers_list[i]
            if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG in frame_marker_element_content:
                str_error = ('In position: {} not exists element: {} in element: {} in element: {} in element: {} in in metashape markers XML file:\n{}'.
                             format(str(i+1), defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path))
                return str_error
            frame_marker_elements = frame_marker_element_content[defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG]
            frame_marker_list = []
            if not isinstance(frame_marker_elements, list):
                frame_marker_list.append(frame_marker_elements)
            else:
                frame_marker_list = frame_marker_elements
            for im in range(len(frame_marker_list)):
                frame_marker_element = frame_marker_list[im]
                if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_ATTRIBUTE_ID in frame_marker_element:
                    str_error = ('In position: {} in position: {} not exists attribute: {} in element: {} in element: '
                                 '{} in element: {} in element: {} in in metashape markers XML file:\n{}'.
                                 format(str(im + 1), str(i+1),
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_ATTRIBUTE_ID,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path))
                    return str_error
                str_gcp_id = frame_marker_element[defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_ATTRIBUTE_ID]
                gcp_id = None
                try:
                    gcp_id = int(str_gcp_id)
                except ValueError:
                    str_error = ('In position: {} in position: {} attribute: {} in element: {} in element: {} '
                                 'in element: {} in in metashape markers XML file:\n{}\nmust be an integer: {}'.
                                 format(str(im + 1), str(i+1),
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_ATTRIBUTE_ID,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path, str_gcp_id))
                    return str_error
                # only GCPs
                if not gcp_id in self.gcps_by_id:
                    continue
                gcp = self.gcps_by_id[gcp_id]
                if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_TAG in frame_marker_element:
                    continue
                    # str_error = ('In position: {} not exists element: {} in element: {} in element: {} in element: {} in element: {} in in metashape markers XML file:\n{}'.
                    #              format(str(i+1), defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_TAG,
                    #                     defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG,
                    #                     defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                    #                     defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                    #                     defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path))
                    # return str_error
                locations_element = frame_marker_element[defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_TAG]
                location_list = []
                if not isinstance(locations_element, list): # solo una med
                    location_list.append(locations_element)
                else:
                    location_list = locations_element
                for j in range(len(location_list)):
                    location_element = location_list[j]
                    if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_CAMERA in location_element:
                        str_error = ('In position: {} in position: {} not exists attribute: {} in element: {} in element: {} in element: {} '
                                     'in element: {} in element: {} in in metashape markers XML file:\n{}'.
                                 format(str(im + 1), str(j+1), defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_CAMERA,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path))
                        return str_error
                    str_camera_id = location_element[defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_CAMERA]
                    camera_id = None
                    try:
                        camera_id = int(str_camera_id)
                    except ValueError:
                        str_error = ('In position: {} in position: {} not exists attribute: {} in element: {} in element: {} in element: {} in element: {}'
                                     ' in element: {} in in metashape markers XML file:\n{}\nmust be an integer: {}'.
                                 format(str(im + 1), str(j+1), defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_CAMERA,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path, str_camera_id))
                        return str_error
                    if not camera_id in self.camera_by_id:
                        continue
                    camera = self.camera_by_id[camera_id]
                    if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_PINNED in location_element:
                        str_error = ('In position: {} in position: {} not exists attribute: {} in element: {} in element: {} in element: {} '
                                     'in element: {} in element: {} in in metashape markers XML file:\n{}'.
                                 format(str(im + 1), str(j+1), defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_PINNED,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path))
                        return str_error
                    str_pinned = location_element[defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_PINNED]
                    pinned = False
                    if str_pinned.casefold() == 'true'.casefold():
                        pinned = True
                    if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_COLUMN in location_element:
                        str_error = ('In position: {} in position: {} not exists attribute: {} in element: {} in element: {} in element: {} '
                                     'in element: {} in element: {} in in metashape markers XML file:\n{}'.
                                 format(str(im + 1), str(j+1), defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_COLUMN,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path))
                        return str_error
                    str_column = location_element[defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_COLUMN]
                    column = None
                    try:
                        column = float(str_column)
                    except ValueError:
                        str_error = ('In position: {} in position: {} not exists attribute: {} in element: {} in element: {} in element: {} in element: {}'
                                     ' in element: {} in in metashape markers XML file:\n{}\nmust be a float: {}'.
                                 format(str(im + 1), str(j+1), defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_COLUMN,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path, str_column))
                        return str_error
                    if not defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_ROW in location_element:
                        str_error = ('In position: {} in position: {} not exists attribute: {} in element: {} in element: {} in element: {} '
                                     'in element: {} in element: {} in in metashape markers XML file:\n{}'.
                                 format(str(im + 1), str(j+1), defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_ROW,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path))
                        return str_error
                    str_row = location_element[defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_ROW]
                    row = None
                    try:
                        row = float(str_row)
                    except ValueError:
                        str_error = ('In position: {} in position: {} not exists attribute: {} in element: {} in element: {} in element: {} in element: {}'
                                     ' in element: {} in in metashape markers XML file:\n{}\nmust be a float: {}'.
                                 format(str(im + 1), str(j+1), defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_ATTRIBUTE_COLUMN,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_LOCATION_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_MARKER_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path, str_row))
                        return str_error
                    image_point = ImagePoint(camera, gcp)
                    measured_values = [column, row]
                    image_point.set_measured_values(measured_values)
                    image_point.set_pinned(pinned)
                    image_point.set_frame_id(frame_id)
                    if not gcp_id in self.image_points_by_gcp_id:
                        self.image_points_by_gcp_id[gcp_id] = []
                    self.image_points_by_gcp_id[gcp_id].append(image_point)
        return str_error




