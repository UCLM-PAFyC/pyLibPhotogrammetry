# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import numpy as np
import math

from osgeo import gdal, osr, ogr
gdal.UseExceptions()

from ..defs import  defs_project
from ..defs import defs_metashape_markers as defs_msm
from ..defs import defs_processes
from pyLibGDAL import RasterDEM
from ..core.ATBlock import ATBlock
from ..core.SensorMetashape import SensorMetashape
from ..core.CameraMetashape import CameraMetashape
from ..core.ObjectPointMetashape import ObjectPointMetashape
from ..core.ImagePoint import ImagePoint

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
        self.sensors_to_object_outliers_camera_ids_before_lsa = []
        self.sensors_to_object_outliers_camera_ids = []

    def add_object_point_from_object_space(self,
                                           point_coordinates,
                                           crs_id,
                                           use_dem):
        str_error = ''
        point_id = None
        raster_dem = None
        raster_dem_crs_id = None
        fc = point_coordinates[0]
        sc = point_coordinates[1]
        tc = None
        dem_height = None
        # always get dem height
        dem_file_path = self.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM]
        if not dem_file_path in self.project.raster_dem_by_file_path:
            raster_dem = RasterDEM(defs_project.RASTER_DEM_PRECISION_CODE)
            dem_crs_id = self.project.digitizing_parameters[
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM_CRS]
            if dem_crs_id:  # can be empty for use internal of the DEM
                str_error = raster_dem.set_crs_id_by_user(dem_crs_id)
                if str_error:
                    str_error = ('Adding object point, setting CRS to raster DEM from file: {}\nError:\n{}'
                                 .format(dem_file_path, str_error))
                    return str_error, point_id
            str_error = raster_dem.set_from_file(dem_file_path)
            if str_error:
                str_error = ('Adding object point, setting raster DEM from file: {}\nError:\n{}'
                             .format(dem_file_path, str_error))
                return str_error, point_id
            raster_dem.set_check_domain(False)  # get solution for out points
            self.project.raster_dem_by_file_path[dem_file_path] = raster_dem
        else:
            raster_dem = self.project.raster_dem_by_file_path[dem_file_path]
        str_error = raster_dem.load()
        if str_error:
            str_error = ('Adding object point, loading in memory raster DEM from file: {}\nError:\n{}'
                         .format(dem_file_path, str_error))
            return str_error, point_id
        raster_dem_crs_id = raster_dem.get_crs_id()
        if raster_dem_crs_id.casefold() != crs_id.casefold():
            pto = [[fc, sc, 0.]]
            str_error = self.project.crs_tools.operation(crs_id, raster_dem_crs_id, pto)
            if str_error:
                str_error += ('Adding object point from object space')
                str_error += ('\nFrom AT Block CRS: {} to CRS: {}\nfor point: [{:.3f}, {:.3f}]\nerror:\n{}'.
                              format(crs_id, raster_dem_crs_id, fc, sc, str_error))
                return str_error, point_id
            fc = pto[0][0]
            sc = pto[0][1]
        str_error, dem_height, point_out_edge, is_no_data = raster_dem.get_elevation(fc, sc)
        if str_error:
            str_error += ('Adding object point from object space')
            str_error += ('\nGetting height from dem:\n{}\nfor point: ({:3.f}, {:.3f})\nerror:\n:{}'.
                          format(dem_file_path, fc, sc, str_error))
            return str_error, point_id
        crs_id = raster_dem_crs_id
        tc = dem_height
        # if use_dem:
        #     tc = dem_height
        # else:
        #     tc = point_coordinates[2]
        self.project.point_id = self.project.point_id + 1
        point_id = self.project.point_id
        if point_id in self.project.object_point_by_id:
            str_error = ('Adding object point, exists previous object point: {}'
                         .format(str(point_id)))
            return str_error, None
        object_point = ObjectPointMetashape(self)
        str_error = object_point.set_id(point_id,
                            self.project.digitizing_parameters[
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_SAVE_REPORT]
                            )
        if str_error:
            str_error = ('Adding object point, error:\n{}'
                         .format(str_error))
            return str_error, None
        str_error = object_point.set_position([fc, sc, tc], crs_id, True)
        if str_error:
            str_error = ('Adding object point, error:\n{}'
                         .format(str_error))
            return str_error, None
        if dem_height is None:
            dem_height = tc
        object_point.set_dem_height(dem_height)
        self.project.object_point_by_id[point_id] = object_point
        self.project.object_point_id_last = point_id
        return str_error, point_id

    def from_sensors_to_object(self,
                               image_measured_coordinates_by_camera_id,
                               crs_id,
                               compute_backward_camera_coordinates,
                               use_distortion,
                               use_ppa,
                               image_space_distance_tolerance_outlier_detection = None):
        # if image_space_distance_tolerance_outlier_detection:
        # - Outlier detection before LSA
        str_error = ''
        position = []
        std_position = []
        image_position_backward_error_by_camera_id = {}
        outliers_camera_ids_before_lsa = []
        outliers_camera_ids = []
        self.sensors_to_object_outliers_camera_ids = []
        # outliers detection
        if image_space_distance_tolerance_outlier_detection is not None:
            cameras_ids = list(image_measured_coordinates_by_camera_id.keys())
            outlier_detected = True
            aux_compute_backward_camera_coordinates = False
            while outlier_detected is True:
                number_of_right_solutions_by_camera_id = {}
                number_of_wrong_solutions_by_camera_id = {}
                for camera_id in image_measured_coordinates_by_camera_id:
                    if camera_id in outliers_camera_ids_before_lsa:
                        continue
                    number_of_right_solutions_by_camera_id[camera_id] = 0
                    number_of_wrong_solutions_by_camera_id[camera_id] = 0
                for i in range(len(cameras_ids) - 1):
                    first_camera_id = cameras_ids[i]
                    if first_camera_id in outliers_camera_ids_before_lsa:
                        continue
                    for j in range(i + 1, len(cameras_ids)):
                        second_camera_id = cameras_ids[j]
                        if second_camera_id in outliers_camera_ids_before_lsa:
                            continue
                        aux_image_measured_coordinates_by_camera_id = {}
                        aux_image_measured_coordinates_by_camera_id[first_camera_id] \
                            = image_measured_coordinates_by_camera_id[first_camera_id]
                        aux_image_measured_coordinates_by_camera_id[second_camera_id] \
                            = image_measured_coordinates_by_camera_id[second_camera_id]
                        str_error, aux_position, aux_std_position, aux_image_position_backward_error_by_camera_id \
                            = self.from_sensors_to_object(aux_image_measured_coordinates_by_camera_id,
                                                          crs_id,
                                                          aux_compute_backward_camera_coordinates,
                                                          use_distortion,
                                                          use_ppa)
                        if str_error:
                            continue
                        chunk_coor = np.zeros(4)
                        chunk_coor[0] = aux_position[3]
                        chunk_coor[1] = aux_position[4]
                        chunk_coor[2] = aux_position[5]
                        chunk_coor[3] = 1
                        for camera_id in image_measured_coordinates_by_camera_id:
                            if camera_id in outliers_camera_ids_before_lsa:
                                continue
                            if camera_id == first_camera_id or camera_id == second_camera_id:
                                continue
                            camera = self.camera_by_id[camera_id]
                            column_m = image_measured_coordinates_by_camera_id[camera_id][0]
                            row_m = image_measured_coordinates_by_camera_id[camera_id][1]
                            str_error, within, withinAfterUndistortion, position_image, position_undistorted_image \
                                = camera.from_chunk_to_sensor(chunk_coor)
                            if str_error:
                                self.sensors_to_object_outliers_camera_ids_before_lsa = outliers_camera_ids_before_lsa
                                self.sensors_to_object_outliers_camera_ids = outliers_camera_ids_before_lsa
                                return str_error
                            error_column = column_m - position_image[0]
                            error_row = row_m - position_image[1]
                            if not use_distortion:
                                error_column = column_m - position_undistorted_image[0]
                                error_row = row_m - position_undistorted_image[1]
                            image_space_error = np.sqrt(error_column ** 2. + error_row ** 2.)
                            if image_space_error <= image_space_distance_tolerance_outlier_detection:
                                number_of_right_solutions_by_camera_id[camera_id] \
                                = number_of_right_solutions_by_camera_id[camera_id] + 1
                            else:
                                number_of_wrong_solutions_by_camera_id[camera_id] \
                                = number_of_wrong_solutions_by_camera_id[camera_id] + 1
                camera_id_max_wrong_solutions = None
                max_wrong_solutions = 0
                for camera_id in number_of_wrong_solutions_by_camera_id:
                    if number_of_wrong_solutions_by_camera_id[camera_id] > max_wrong_solutions:
                        camera_id_max_wrong_solutions = camera_id
                        max_wrong_solutions = number_of_wrong_solutions_by_camera_id[camera_id]
                if max_wrong_solutions >= (len(cameras_ids) - len(outliers_camera_ids_before_lsa) - 1):
                    if not camera_id_max_wrong_solutions in outliers_camera_ids_before_lsa:
                        outliers_camera_ids_before_lsa.append(camera_id_max_wrong_solutions)
                else:
                    outlier_detected = False
                if (len(cameras_ids) - len(outliers_camera_ids_before_lsa)) < 3:
                    self.sensors_to_object_outliers_camera_ids_before_lsa = outliers_camera_ids_before_lsa
                    self.sensors_to_object_outliers_camera_ids = outliers_camera_ids_before_lsa
                    str_error = ('There is no solution for tolerance value')
                    return str_error, position, std_position, image_position_backward_error_by_camera_id
        number_of_image_points = len(image_measured_coordinates_by_camera_id) - len(outliers_camera_ids_before_lsa)
        number_of_equations = 2 * number_of_image_points
        A = np.zeros((number_of_equations, 3))
        b = np.zeros((number_of_equations, 1))
        use_weights = True
        use_simplified_weights = True
        number_of_stds = 0
        for camera_id in image_measured_coordinates_by_camera_id:
            if camera_id in outliers_camera_ids_before_lsa:
                continue
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
            if camera_id in outliers_camera_ids_before_lsa:
                continue
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
                self.sensors_to_object_outliers_camera_ids_before_lsa = outliers_camera_ids_before_lsa
                self.sensors_to_object_outliers_camera_ids = outliers_camera_ids_before_lsa
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
                    self.sensors_to_object_outliers_camera_ids_before_lsa = outliers_camera_ids_before_lsa
                    self.sensors_to_object_outliers_camera_ids = outliers_camera_ids_before_lsa
                    str_error = ('For camera: {}, error:\n{}'.format(camera.label, str_error))
                    return str_error, position, std_position, image_position_backward_error_by_camera_id
                str_error, ir_dx, ir_dy, ir_dz = camera.from_sensor_to_chunk_coordinates_direction(column_m,
                                                                                                   row_m + inc_row,
                                                                                                   use_distortion, use_ppa)
                if str_error:
                    self.sensors_to_object_outliers_camera_ids_before_lsa = outliers_camera_ids_before_lsa
                    self.sensors_to_object_outliers_camera_ids = outliers_camera_ids_before_lsa
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
        chunk_coor[0] = x[0][0]
        chunk_coor[1] = x[1][0]
        chunk_coor[2] = x[2][0]
        chunk_coor[3] = 1
        ecef_coordinates = np.dot(self.transform, chunk_coor)
        pc_crs = [[ecef_coordinates[0], ecef_coordinates[1], ecef_coordinates[2]]]
        str_error = self.project.crs_tools.operation(self.crs_ecef_id, crs_id, pc_crs)
        if str_error:
            self.sensors_to_object_outliers_camera_ids_before_lsa = outliers_camera_ids_before_lsa
            self.sensors_to_object_outliers_camera_ids = outliers_camera_ids_before_lsa
            str_error = ('Error in ECEF to Geo3D operation:\n{}'.format(str_error))
            return str_error, position, std_position, image_position_backward_error_by_camera_id
        position = [pc_crs[0][0], pc_crs[0][1], pc_crs[0][2],
                    chunk_coor[0], chunk_coor[1], chunk_coor[2], chunk_coor[3]]
        stdComputedFc = np.sqrt(var_pos * Qxx[0, 0])
        stdComputedSc = np.sqrt(var_pos * Qxx[1, 1])
        stdComputedTc = np.sqrt(var_pos * Qxx[2, 2])
        stdComputedFc = stdComputedFc * self.transform_scale
        stdComputedSc = stdComputedSc * self.transform_scale
        stdComputedTc = stdComputedTc * self.transform_scale
        std_position = [stdComputedFc, stdComputedSc, stdComputedTc]
        if not compute_backward_camera_coordinates:
            self.sensors_to_object_outliers_camera_ids_before_lsa = outliers_camera_ids_before_lsa
            self.sensors_to_object_outliers_camera_ids = outliers_camera_ids_before_lsa
            return str_error, position, std_position, image_position_backward_error_by_camera_id
        outliers_camera_ids = outliers_camera_ids_before_lsa
        for camera_id in image_measured_coordinates_by_camera_id:
            camera = self.camera_by_id[camera_id]
            column_m = image_measured_coordinates_by_camera_id[camera_id][0]
            row_m = image_measured_coordinates_by_camera_id[camera_id][1]
            str_error, within, withinAfterUndistortion, position_image, position_undistorted_image \
                = camera.from_chunk_to_sensor(chunk_coor)
            if str_error:
                self.sensors_to_object_outliers_camera_ids_before_lsa = outliers_camera_ids_before_lsa
                self.sensors_to_object_outliers_camera_ids = outliers_camera_ids_before_lsa
                return str_error
            error_column = column_m - position_image[0]
            error_row = row_m - position_image[1]
            if not use_distortion:
                error_column = column_m - position_undistorted_image[0]
                error_row = row_m - position_undistorted_image[1]
            error_camera_coordinates = [error_column, error_row]
            image_position_backward_error_by_camera_id[camera_id] = error_camera_coordinates
            if image_space_distance_tolerance_outlier_detection is not None:
                if np.sqrt(error_column ** 2. + error_row ** 2.) < image_space_distance_tolerance_outlier_detection:
                    if camera_id in outliers_camera_ids_before_lsa:
                        outliers_camera_ids_before_lsa.remove(camera_id)
                else:
                    if not camera_id in outliers_camera_ids:
                        outliers_camera_ids.append(camera_id)
        self.sensors_to_object_outliers_camera_ids_before_lsa = outliers_camera_ids_before_lsa
        self.sensors_to_object_outliers_camera_ids = outliers_camera_ids
        return str_error, position, std_position, image_position_backward_error_by_camera_id

    def set_from_xml(self,
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
        if crs_geo2d_id is None:
            str_error = (
                'Getting CRS geographic 2D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                format(defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG, self.file_path))
            return str_error
        crs_ecef_ids = self.project.crs_tools.get_crs_ecef_ids_for_crs_geo2d_id(crs_geo2d_id)
        if crs_ecef_ids is None:
            str_error = (
                'Getting CRS ECEF from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                format(defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG, self.file_path))
            return str_error
        crs_ecef_id = crs_ecef_ids[0]
        crs_geo3d_ids = self.project.crs_tools.get_crs_geo3d_ids_for_crs_geo2d_id(crs_geo2d_id)
        if crs_geo3d_ids is None:
            str_error = (
                'Getting CRS geographic 3D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                format(defs_msm.METASHAPE_MARKERS_XML_REFERENCE_TAG, self.file_path))
            return str_error
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
            if camera_crs_geo2d_id is None:
                str_error = (
                    'Getting CRS geographic 2D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_REFERENCE_TAG, self.file_path))
                return str_error
            camera_crs_ecef_ids = self.project.crs_tools.get_crs_ecef_ids_for_crs_geo2d_id(camera_crs_geo2d_id)
            if camera_crs_ecef_ids is None:
                str_error = (
                    'Getting CRS ECEF from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_REFERENCE_TAG, self.file_path))
                return str_error
            camera_crs_ecef_id = camera_crs_ecef_ids[0]
            camera_crs_geo3d_ids = self.project.crs_tools.get_crs_geo3d_ids_for_crs_geo2d_id(camera_crs_geo2d_id)
            if camera_crs_geo3d_ids is None:
                str_error = (
                    'Getting CRS geographic 3D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_REFERENCE_TAG, self.file_path))
                return str_error
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
            if gcps_crs_geo2d_id is None:
                str_error = (
                    'Getting CRS geographic 2D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_REFERENCE_TAG, self.file_path))
                return str_error
            gcps_crs_ecef_ids = self.project.crs_tools.get_crs_ecef_ids_for_crs_geo2d_id(gcps_crs_geo2d_id)
            if gcps_crs_ecef_ids is None:
                str_error = (
                    'Getting CRS ECEF from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_REFERENCE_TAG, self.file_path))
                return str_error
            gcps_crs_ecef_id = gcps_crs_ecef_ids[0]
            gcps_crs_geo3d_ids = self.project.crs_tools.get_crs_geo3d_ids_for_crs_geo2d_id(gcps_crs_geo2d_id)
            if gcps_crs_geo3d_ids is None:
                str_error = (
                    'Getting CRS geographic 3D from element: {} in chunk in metashape markers XML file:\n{}\nCRS is not valid'.
                    format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_REFERENCE_TAG, self.file_path))
                return str_error
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
            str_error = sensor.set_from_xml(sensor_element)
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
            cameras_group_element = cameras_element[defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_TAG] # ¿a list?
            cameras_group_element_list = []
            if not isinstance(cameras_group_element, list):
                cameras_group_element_list.append(cameras_group_element)
            else:
                cameras_group_element_list = cameras_group_element
            for i in range(len(cameras_group_element_list)):
                cameras_group_element = cameras_group_element_list[i]
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
                    str_error = camera.set_from_xml(camera_element)
                    if str_error:
                        str_error = ('Loading camera position: {}\nError:\n{}'.format(str(i + 1), str_error))
                        return str_error
                    cameras_group_camera_by_id[camera.id] = camera
                self.cameras_group_by_id[cameras_group_id] = {}  # dictionary: label, type, cameras
                self.cameras_group_by_id[cameras_group_id][defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_LABEL] = cameras_group_label
                self.cameras_group_by_id[cameras_group_id][defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_ATTRIBUTE_TYPE] = cameras_group_type
                self.cameras_group_by_id[cameras_group_id][defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_CAMERA_TAG] = cameras_group_camera_by_id
        # if not defs_msm.METASHAPE_MARKERS_XML_CAMERAS_CAMERA_TAG in cameras_element:
        #     str_error = ('Not exists element: {} in element: {} in chunk in metashape markers XML file:\n{}'.
        #                  format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_CAMERA_TAG,
        #                         defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG, self.file_path))
        #     return str_error
        if defs_msm.METASHAPE_MARKERS_XML_CAMERAS_CAMERA_TAG in cameras_element:
            camera_list_element = cameras_element[defs_msm.METASHAPE_MARKERS_XML_CAMERAS_CAMERA_TAG]
            if not isinstance(camera_list_element, list):
                str_error = ('Element: {} in element: {} in chunk in metashape markers XML file:\n{}\nmust be a list.'.
                             format(defs_msm.METASHAPE_MARKERS_XML_CAMERAS_CAMERA_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_CAMERAS_TAG, self.file_path))
                return str_error
            for i in range(len(camera_list_element)):
                camera_element = camera_list_element[i]
                camera = CameraMetashape(self)
                str_error = camera.set_from_xml(camera_element)
                if str_error:
                    str_error = ('Loading camera position: {}\nError:\n{}'.format(str(i+1), str_error))
                    return str_error
                self.camera_by_id[camera.id] = camera
            for camera_id in self.cameras_group_by_id: # works if only exists one cameras group? view next ...
                camera = self.camera_by_id[camera_id]
                if camera.master_id != defs_msm.METASHAPE_MARKERS_XML_CAMERA_NO_MASTER_ID:
                    if not camera.master_id in self.cameras_id_by_multi_camera_master_id:
                        self.cameras_id_by_multi_camera_master_id[camera.master_id] = []
                    self.cameras_id_by_multi_camera_master_id[camera.master_id].append(camera_id)
        # new for spherical example
        for cameras_group_id in self.cameras_group_by_id:
            cameras_group_camera_by_id = self.cameras_group_by_id[cameras_group_id][defs_msm.METASHAPE_MARKERS_XML_CAMERAS_GROUP_CAMERA_TAG]
            for camera_id in cameras_group_camera_by_id:
                if not camera_id in self.camera_by_id:
                    self.camera_by_id[camera_id] = cameras_group_camera_by_id[camera_id]

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
            str_error = gcp.set_from_xml(marker_element)
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
            str_error = ('Not : {} in element: {} in metashape markers XML file:\n{}\n'.
                         format(defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_MARKERS_TAG,
                                defs_msm.METASHAPE_MARKERS_XML_FRAMES_FRAME_TAG,
                                defs_msm.METASHAPE_MARKERS_XML_FRAMES_TAG, self.file_path))
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

    def set_projected_images_from_object_point(self,
                                               object_point,
                                               ignore_hided_points_in_images,
                                               ignored_images):
        str_error = ''
        content = ''
        if not self.exists_footprints():
            str_error = ('Images footprints are not loaded')
            return str_error, content
        # if not self.exists_footprints_undistorted():
        #     str_error = ('Images undistorted footprints are not loaded')
        #     return str_error
        only_enabled_images = self.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_ENABLED_IMAGES]
        ignored_sensor_percentage = self.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IGNORED_SENSOR_PERCENTAGE]
        raster_dem = None
        dem_file_path = None
        if ignore_hided_points_in_images:
            dem_file_path = self.project.digitizing_parameters[
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM]
            if not dem_file_path in self.project.raster_dem_by_file_path:
                raster_dem = RasterDEM(defs_project.RASTER_DEM_PRECISION_CODE)
                dem_crs_id = self.project.digitizing_parameters[
                    defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM_CRS]
                if dem_crs_id: # can be empty for use internal of the DEM
                    str_error = raster_dem.set_crs_id_by_user(dem_crs_id)
                    if str_error:
                        str_error = ('Setting CRS to raster DEM from file: {}\nError:\n{}'
                                     .format(dem_file_path, str_error))
                        return str_error, content
                str_error = raster_dem.set_from_file(dem_file_path)
                if str_error:
                    str_error = ('Setting raster DEM from file: {}\nError:\n{}'
                                 .format(dem_file_path, str_error))
                    return str_error, content
                raster_dem.set_check_domain(False) # get solution for out points
                self.project.raster_dem_by_file_path[dem_file_path] = raster_dem
            else:
                raster_dem = self.project.raster_dem_by_file_path[dem_file_path]
            str_error = raster_dem.load()
            if str_error:
                str_error = ('Loading in memory raster DEM from file: {}\nError:\n{}'
                             .format(dem_file_path, str_error))
                return str_error, content
            raster_dem_crs_id = raster_dem.get_crs_id()
        if only_enabled_images:
            str_error = self.project.update_enabled_images_from_db()
            if str_error:
                str_error = ('Updating enabled images from file: {}\nError:\n{}'
                             .format(self.file_path, str_error))
                return str_error, content
        ogr_point = ogr.Geometry(ogr.wkbPoint)
        ogr_point.AddPoint(object_point.position[0], object_point.position[1])
        cameras_to_process = []
        for camera_id in self.camera_by_id:
            if camera_id in ignored_images:
                continue
            camera = self.camera_by_id[camera_id]
            camera_enabled = camera.get_enabled()  # multisensor ...
            if camera_enabled:
                if camera.is_usefull():
                    cameras_to_process.append(camera)
        for i in range(len(cameras_to_process)):
            camera = cameras_to_process[i]
            camera_id = camera.id
            camera_footprint_geometry = camera.footprint_geometry
            if not camera_footprint_geometry.Contains(ogr_point):
                continue
            if camera.gsd is None:
                camera_footprint_area = camera_footprint_geometry.GetArea()
                str_error = camera.set_gsd_from_footprint_area(camera_footprint_area)
                if str_error:
                    str_error = ("Getting GSD for image: {}\nError:\n{}".format(camera.label, str_error))
                    return str_error, content
            distance2dTolerance = 2. * camera.gsd
            distanceTcTolerance = 3. * camera.gsd
            str_error, within, withinAfterUndistortion, position_image, position_undistorted_image \
                = camera.from_chunk_to_sensor(object_point.position_chunk)
            if str_error:
                str_error = ("Getting position in image: {}\nError:\n{}".format(camera.label, str_error))
                return str_error, content
            column = position_image[0]
            row = position_image[1]
            sensor = self.sensor_by_id[camera.sensor_id]
            columns = sensor.width
            rows = sensor.height
            number_of_columns_to_ignore = math.floor(float(columns * ignored_sensor_percentage / 100.))
            number_of_rows_to_ignore = math.floor(float(rows * ignored_sensor_percentage / 100.))
            min_column = number_of_columns_to_ignore
            max_column = columns - number_of_columns_to_ignore
            min_row = number_of_rows_to_ignore
            max_row = rows - number_of_rows_to_ignore
            inside_valid_area = True
            if column < min_column or column > max_column or row < min_row or row > max_row:
                inside_valid_area = False
            content += "\n  - Image.................: " + camera.label
            content += ("\n    Coordinates ..........: ({:.3f}, {:.3f})".format(column, row))
            content += ("\n    Coordinates (Undist) .: ({:.3f}, {:.3f})".format(position_undistorted_image[0],
                                                                             position_undistorted_image[1]))
            if inside_valid_area:
                content += "\n    Inside valid area"
            else:
                content += "\n    Outside valid area"
                continue
            if ignore_hided_points_in_images:
                is_visible = True
                str_error, pto_dem = camera.from_sensor_to_dem(column, row, raster_dem)
                if str_error:
                    str_error = ("In image: {}\nprojecting point: ({:.3f}, {:.3f})\nover DEM:\n{}Error:\n{}".
                                 format(camera.label, column, row, dem_file_path, str_error))
                    return str_error, content
                distance2d = math.sqrt((pto_dem[0] - object_point.position[0]) ** 2.
                                       + (pto_dem[1] - object_point.position[1]) ** 2.)
                distanceTc = pto_dem[2] - object_point.position[2]
                if distance2d > distance2dTolerance and distanceTc > distanceTcTolerance:
                    is_visible = False
                    content += "\n    Hyde by DSM"
                    continue
            projected_values = [column, row]
            projected_undistorted_values = position_undistorted_image
            object_point.add_image_projected_value(camera, projected_values, projected_undistorted_values)
        return str_error, content




