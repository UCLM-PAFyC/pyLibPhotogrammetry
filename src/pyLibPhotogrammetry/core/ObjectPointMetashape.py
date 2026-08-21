# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import numpy as np
import math

from ..defs import defs_metashape_markers as defs_msm
from ..core.ObjectPoint import ObjectPoint
from ..defs import  defs_project
from ..defs import defs_processes

class ObjectPointMetashape(ObjectPoint):
    def __init__(self,
                 at_block):
        super().__init__(at_block)
        self.position_chunk = None

    def set_from_xml(self,
                     xml_element):
        str_error = ''
        #id
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_ID in xml_element:
            str_error = ('Not exists attribute: {} in marker in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_ID, self.file_path))
            return str_error
        str_id = xml_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_ID]
        try:
            self.id = int(str_id)
        except ValueError:
            str_error = ('Attribute: {} in marker in metashape markers XML file:\n{}\n must be an integer: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_ID, self.file_path, str_id))
            return str_error
        if self.id in self.at_block.gcps_by_id:
            str_error = ('Exists previous marker id: {} in marker in metashape markers XML file:\n{}'.
                         format(str(self.id), self.file_path,))
            return str_error
        # label
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_LABEL in xml_element:
            str_error = ('Not exists attribute: {} in marker in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_LABEL, self.file_path))
            return str_error
        label = xml_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_LABEL]
        self.label = label
        # reference
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG in xml_element:
            str_error = ('Not exists attribute: {} in marker: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        reference_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG]
        # x
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_FIRST_COORDINATE in reference_element:
            str_error = ('Not exists attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_FIRST_COORDINATE,
                                defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        str_reference_x = reference_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_FIRST_COORDINATE]
        try:
            reference_x = float(str_reference_x)
        except ValueError:
            str_error = (
                'Attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}\nmust be a float'.
                format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_FIRST_COORDINATE,
                       defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        # y
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_SECOND_COORDINATE in reference_element:
            str_error = ('Not exists attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_SECOND_COORDINATE,
                                defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        str_reference_y = reference_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_SECOND_COORDINATE]
        try:
            reference_y = float(str_reference_y)
        except ValueError:
            str_error = (
                'Attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}\nmust be a float'.
                format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_SECOND_COORDINATE,
                       defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        # z
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_THIRD_COORDINATE in reference_element:
            str_error = ('Not exists attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_THIRD_COORDINATE,
                                defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        str_reference_z = reference_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_THIRD_COORDINATE]
        try:
            reference_z = float(str_reference_z)
        except ValueError:
            str_error = (
                'Attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}\nmust be a float'.
                format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_THIRD_COORDINATE,
                       defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        # enabled
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_ENABLED in reference_element:
            str_error = ('Not exists attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_ENABLED,
                                defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        position_crs_source = [reference_x, reference_y, reference_z]
        str_enabled = reference_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_ENABLED]
        self.enabled = True
        if str_enabled.casefold() == 'false':
            self.enabled = False
        self.position_crs_source = np.array(position_crs_source)
        if self.at_block.crs_id != self.at_block.gcps_crs_id:
            position = [[reference_x, reference_y, reference_z]]
            str_error = self.crs_tools.operation(self.at_block.gcps_crs_id, self.at_block.crs_id, position)
            if str_error:
                str_error = ('In GCP: {} in metashape markers XML file:\n{}\nError in CRSs operation:\n{}'.
                             format(self.label, self.file_path, str_error))
                return str_error
            self.position = np.array(position[0])
        else:
            self.position = np.array([reference_x, reference_y, reference_z])
        if self.at_block.crs_id != self.at_block.crs_ecef_id:
            position_ecef = [self.position.tolist()]
            str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_ecef_id, position_ecef)
            if str_error:
                str_error = ('In GCP: {} in metashape markers XML file:\n{}\nError in CRSs operation:\n{}'.
                             format(self.label, self.file_path, str_error))
                return str_error
            self.position_ecef = np.array(position_ecef[0])
        else:
            self.position_ecef = np.array(self.position.tolist())
        if self.at_block.crs_id != self.at_block.crs_geo3d_id:
            position_geo3d = [self.position.tolist()]
            str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_geo3d_id, position_geo3d)
            if str_error:
                str_error = ('In GCP: {} in metashape markers XML file:\n{}\nError in CRSs operation:\n{}'.
                             format(self.label, self.file_path, str_error))
                return str_error
            self.position_geo3d = np.array(position_geo3d[0])
        else:
            self.position_geo3d = np.array(self.position.tolist())
        position_ecef = np.append(self.position_ecef, 1.0)
        self.position_chunk = np.matmul(self.at_block.transform_inv, position_ecef)
        return str_error

    def set_position(self, point_coordinates, crs_id, write_report = False):
        str_error = ''
        if not isinstance(point_coordinates, list):
            str_error = ('Coordinates must be a list with two or three values')
            return str_error
        if len(point_coordinates) < 2:
            str_error = ('Coordinates must be a list with two or three values')
            return str_error
        if write_report and self.report_file is None:
            str_error = self.open_report_file(self.id)
            if str_error:
                return str_error
        if crs_id.casefold() != self.at_block.crs_id.casefold():
            position = [[point_coordinates[0], point_coordinates[1], point_coordinates[2]]]
            str_error = self.crs_tools.operation(crs_id, self.crs_id, position)
            if str_error:
                str_error += ('\nFrom AT Block CRS: {} to CRS: {}\nfor point: [{:.3f}, {:.3f}, {:.3f}]\nerror:\n{}'.
                              format(crs_id, self.at_block.crs_id,
                                     point_coordinates[0], point_coordinates[1], point_coordinates[2], str_error))
                return str_error
            self.position = np.array(position[0])
        else:
            self.position = np.array([point_coordinates[0], point_coordinates[1], point_coordinates[2]])
        if self.at_block.crs_id != self.at_block.crs_ecef_id:
            position_ecef = [self.position.tolist()]
            str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_ecef_id, position_ecef)
            if str_error:
                str_error = ('In GCP: {} in metashape markers XML file:\n{}\nError in CRSs operation:\n{}'.
                             format(self.label, self.file_path, str_error))
                return str_error
            self.position_ecef = np.array(position_ecef[0])
        else:
            self.position_ecef = np.array(self.position.tolist())
        if self.at_block.crs_id != self.at_block.crs_geo3d_id:
            position_geo3d = [self.position.tolist()]
            str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_geo3d_id, position_geo3d)
            if str_error:
                str_error = ('In GCP: {} in metashape markers XML file:\n{}\nError in CRSs operation:\n{}'.
                             format(self.label, self.file_path, str_error))
                return str_error
            self.position_geo3d = np.array(position_geo3d[0])
        else:
            self.position_geo3d = np.array(self.position.tolist())
        position_ecef = np.append(self.position_ecef, 1.0)
        self.position_chunk = np.matmul(self.at_block.transform_inv, position_ecef)
        content = "\n- ObjectPoint.set_position"
        content += "\n  - Id ...................: " + str(self.id)
        content += "\n  - CRS id ...............: " + self.at_block.crs_id
        content += ("\n  - Coordinates ..........: ({:.4f}, {:.4f}, {:.4f})".format(self.position[0],
                                                                                    self.position[1],
                                                                                    self.position[2]))
        content += ("\n  - GEO3D Coordinates ....: ({:.9f}, {:.9f}, {:.4f})".format(self.position_geo3d[0],
                                                                                    self.position_geo3d[1],
                                                                                    self.position_geo3d[2]))
        content += ("\n  - ECEF Coordinates .....: ({:.4f}, {:.4f}, {:.4f})".format(self.position_ecef[0],
                                                                                    self.position_ecef[1],
                                                                                    self.position_ecef[2]))
        content += ("\n  - Chunk Coordinates.....: ({:.4f}, {:.4f}, {:.4f})".format(self.position_chunk[0],
                                                                                    self.position_chunk[1],
                                                                                    self.position_chunk[2]))
        self.report_text += content
        self.report_text_last_step = content
        if write_report and self.report_file is not None:
            self.report_file.write(self.report_text_last_step)
            self.report_file.flush()
        return str_error

    def set_projected_images(self,
                             ignore_hided_points_in_images,
                             ignored_images,
                             write_report = False):
        str_error = ''
        content = "\n- ObjectPoint.set_projected_images"
        self.report_text += content
        self.report_text_last_step = content
        str_error, content = (
            self.at_block.set_projected_images_from_object_point(self,
                                                                 ignore_hided_points_in_images, ignored_images))
        if str_error:
            return str_error
        self.report_text += content
        self.report_text_last_step += content
        if write_report and self.report_file is not None:
            self.report_file.write(self.report_text_last_step)
            self.report_file.flush()
        return str_error

    def update_from_measured_images(self,
                                    ignore_hided_points_in_images,
                                    use_dem,
                                    point_outside_dem,
                                    measured_images,
                                    ignored_images):
        str_error = ''
        if not self.at_block.exists_footprints():
            str_error = ('Images footprints are not loaded')
            return str_error
        str_error, at_block_crs_is_geographic = self.at_block.project.crs_tools.is_geographic(self.at_block.crs_id)
        if str_error:
            str_error = ('For AT Block: {}, getting is geographic CRS: {}\nError:\n{}'
                         .format(self.at_block.label, self.at_block.crs_id, str_error))
            return str_error
        crs2d_precision = 4
        if at_block_crs_is_geographic:
            crs2d_precision = 9
        # 1. get parameters
        only_enabled_images = self.at_block.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_ENABLED_IMAGES]
        ignored_sensor_percentage = self.at_block.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IGNORED_SENSOR_PERCENTAGE]
        raster_dem = None
        dem_file_path = None
        if ignore_hided_points_in_images or use_dem:
            dem_file_path = self.at_block.project.digitizing_parameters[
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM]
            if not dem_file_path in self.at_block.project.raster_dem_by_file_path:
                raster_dem = RasterDEM(defs_project.RASTER_DEM_PRECISION_CODE)
                dem_crs_id = self.at_block.project.digitizing_parameters[
                    defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM_CRS]
                if dem_crs_id: # can be empty for use internal of the DEM
                    str_error = raster_dem.set_crs_id_by_user(dem_crs_id)
                    if str_error:
                        str_error = ('Setting CRS to raster DEM from file: {}\nError:\n{}'
                                     .format(dem_file_path, str_error))
                        return str_error
                str_error = raster_dem.set_from_file(dem_file_path)
                if str_error:
                    str_error = ('Setting raster DEM from file: {}\nError:\n{}'
                                 .format(dem_file_path, str_error))
                    return str_error
                raster_dem.set_check_domain(False) # get solution for out points
                self.at_block.project.raster_dem_by_file_path[dem_file_path] = raster_dem
            else:
                raster_dem = self.at_block.project.raster_dem_by_file_path[dem_file_path]
            str_error = raster_dem.load()
            if str_error:
                str_error = ('Loading in memory raster DEM from file: {}\nError:\n{}'
                             .format(dem_file_path, str_error))
                return str_error
            raster_dem_crs_id = raster_dem.get_crs_id()
        if only_enabled_images:
            str_error = self.at_block.project.update_enabled_images_from_db()
            if str_error:
                str_error = ('Updating enabled images from file: {}\nError:\n{}'
                             .format(self.file_path, str_error))
                return str_error
        minimum_overlap_percentage = self.at_block.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MINIMUM_OVERLAP_PERCENTAGE]
        images_meaurements_accuracy = self.at_block.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MEASUREMENTS_ACCURACY]

        # 2. get valid measurements (enabled, no ignored, not near sensor limits)
        #    and project in dem
        #    check exists valid measurement
        updated_object_point_position = False
        content = "\n- ObjectPoint.update_from_measured_images"
        image_id_to_process_by_image_label = {}
        measured_by_image_id = {}
        undistorted_measured_by_image_id = {}
        measured_backward_errors_by_image_id = {}
        projected_dem_by_image_id = {}
        outliers_images_ids = []
        camera_by_id = {}
        for image_label in measured_images:
            column = measured_images[image_label][0]
            row = measured_images[image_label][1]
            content += "\n  - Image.................: " + image_label
            content += ("\n    Coordinates ..........: ({:.3f}, {:.3f})".format(column, row))
            camera = self.at_block.get_camera_from_image_label(image_label)
            if camera is None:
                content += "\n    Not exists image"
                continue
            image_id = camera.id
            if image_id in ignored_images:
                content += "\n    Ignored image"
                continue
            camera_enabled = camera.get_enabled()  # multisensor ...
            if not camera_enabled:
                content += "\n    Disabled image"
                continue
            sensor = self.at_block.sensor_by_id[camera.sensor_id]
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
                content += "\n    Outside valid sensor area"
                continue
            str_error, column_nd, row_nd = sensor.get_undistorted(column, row)
            if str_error:
                content += ("\n    Error getting undistorted coordinates: {}".format(str_error))
                continue
            content += ("\n    Coordinates (Undist) .: ({:.3f}, {:.3f})".format(column_nd, row_nd))
            if use_dem:
                str_error, pto_dem = camera.from_sensor_to_dem(column, row, raster_dem)
                if str_error:
                    content += ("\n    Error projecting to dem: {}".format(str_error))
                    continue
                content += ("\n    Proj. to DEM coor ....: ({:.3f}, {:.3f}, {:.3f})".
                            format(pto_dem[0], pto_dem[1], pto_dem[2]))
            image_id_to_process_by_image_label[image_label] = [image_id]
            measured_by_image_id[image_id] = [column, row,
                                              images_meaurements_accuracy, images_meaurements_accuracy]
            undistorted_measured_by_image_id[image_id] = [column_nd, row_nd,
                                              images_meaurements_accuracy, images_meaurements_accuracy]
            measured_backward_errors_by_image_id[image_id] = [None, None]
            projected_dem_by_image_id[image_id] = pto_dem
            camera_by_id[image_id] = camera
        if len(measured_by_image_id) == 0:
            content += ("\n- Error: There are no valid measurements")
            self.report_text += content
            self.report_text_last_step = content
            if self.report_file is not None:
                self.report_file.write(self.report_text_last_step)
                self.report_file.flush()
            str_error = ('There are no valid measurements')
            return str_error
        # 3. Update object position
        # image_id_to_process_by_image_label = []
        # measured_by_image_id = {}
        # undistorted_measured_by_image_id = {}
        # measured_backward_errors_by_image_id = {}
        # projected_dem_by_image_id = {}
        fc = None
        sc = None
        tc = None
        if len(measured_by_image_id) == 1:
            if len(projected_dem_by_image_id) == 1:
                first_key = next(iter(projected_dem_by_image_id))
                fc = projected_dem_by_image_id[first_key][0]
                sc = projected_dem_by_image_id[first_key][1]
                tc = projected_dem_by_image_id[first_key][2]
                updated_object_point_position = True
        else:
            measured_by_image_id_original = measured_by_image_id
            iteration = True
            n_iteration = 0
            # to do, check with all measurements outliers
            while iteration: # stop if no outliers or only two image points
                image_space_tolerance = None
                if len(measured_by_image_id) > 2:
                    image_space_tolerance = images_meaurements_accuracy * 3.
                compute_backward_camera_coordinates = True
                use_distortion = True
                use_ppa = True
                image_measured_coordinates_by_camera_id = measured_by_image_id
                str_error, position, std_position, image_position_backward_error_by_camera_id \
                    = self.at_block.from_sensors_to_object(image_measured_coordinates_by_camera_id,
                                                           self.at_block.project.crs_id,
                                                           compute_backward_camera_coordinates,
                                                           use_distortion, use_ppa,
                                                           image_space_tolerance)
                if str_error:
                    content += ("\n- Error: computing position from images measurements:\n{}".format(str_error))
                    self.report_text += content
                    self.report_text_last_step = content
                    if self.report_file is not None:
                        self.report_file.write(self.report_text_last_step)
                        self.report_file.flush()
                    str_error = ('Error computing position from images measurements:\n{}'.format(str_error))
                    return str_error
                outliers_images_ids_before_lsa = self.at_block.sensors_to_object_outliers_camera_ids_before_lsa
                outliers_images_ids = self.at_block.sensors_to_object_outliers_camera_ids
                outliers_images_ids_lsa = []
                for i in range(len(outliers_images_ids_lsa)):
                    if not outliers_images_ids_lsa[i] in outliers_images_ids_before_lsa:
                        outliers_images_ids_lsa.append(outliers_images_ids_lsa[i])
                content += "\n  - Computing object position from images measurements"
                if n_iteration == 0:
                    content += ": First computation"
                else:
                    content += ": iteration number " + str(n_iteration)
                content += "\n    - Computed coordinates ......: ("
                if crs2d_precision == 9:
                    content += ("{:.9f}".format(position[0]))
                    content += (", {:.9f}".format(position[1]))
                else:
                    content += (" {:.4f}".format(position[0]))
                    content += (", {:.4f}".format(position[1]))
                content += (", {:.4f}".format(position[2]))
                content += "\n    - Std computed coordinates ..: "
                if crs2d_precision == 9:
                    content += ("{:.9f}".format(std_position[0]))
                    content += (", {:.9f}".format(std_position[1]))
                else:
                    content += ("{:.4f}".format(std_position[0]))
                    content += (", {:.4f}".format(std_position[1]))
                content += (", {:.4f}".format(std_position[2]))
                content += "\n     ColumnM      RowM   ColumnC      RowC  ErrorC  ErrorR Error2d  Image"
                exists_outliers_lsa = False
                for camera_id in image_position_backward_error_by_camera_id:
                    measured = image_measured_coordinates_by_camera_id[camera_id]
                    error_computed = image_position_backward_error_by_camera_id[camera_id]
                    error_c = error_computed[0]
                    error_r = error_computed[1]
                    error_2d = np.sqrt(error_c ** 2 + error_r ** 2)
                    camera = self.at_block.camera_by_id[camera_id]
                    content += '\n{:12.2f}'.format(measured[0])
                    content += '{:10.2f}'.format(measured[1])
                    content += '{:10.2f}'.format(measured[0] - error_c)
                    content += '{:10.2f}'.format(measured[1] - error_r)
                    content += '{:8.2f}'.format(error_c)
                    content += '{:8.2f}'.format(error_r)
                    content += '{:8.2f}'.format(error_2d)
                    content += '  {:s}'.format(camera.label)
                    detected_outlier_lsa = False
                    if camera_id in outliers_images_ids:
                        if not camera_id in outliers_images_ids_lsa:
                            content += ' **** outlier detected before LSA'
                        else:
                            content += ' **** outlier detected in LSA'
                            detected_outlier_lsa = True
                            if not exists_outliers_lsa:
                                exists_outliers_lsa = True
                            measured_by_image_id.pop(camera_id)
                if not exists_outliers_lsa:
                    iteration = False
                elif len(measured_by_image_id) == 2:
                    iteration = False
                fc = position[0]
                sc = position[1]
                tc = position[2]
                n_iteration += 1
            updated_object_point_position = True
        if not updated_object_point_position:
            return str_error
        # 4. remove existing locations
        self.remove_image_points()
        # 5. Update position
        str_error = self.set_position([fc, sc, tc], self.at_block.crs_id)
        content += self.report_text_last_step
        if str_error:
            content += ("\n- Error: setting position after computing position from images measurements:\n{}".format(str_error))
            self.report_text += content
            self.report_text_last_step = content
            if self.report_file is not None:
                self.report_file.write(self.report_text_last_step)
                self.report_file.flush()
            str_error = ('Error setting position after computing position from images measurements:\n{}'.format(str_error))
            return str_error
        # 6. Set projected images
        str_error = self.set_projected_images(ignore_hided_points_in_images, ignored_images)
        content += self.report_text_last_step
        if str_error:
            content += ("\n- Error: setting projected images after computing position from images measurements:\n{}".format(str_error))
            self.report_text += content
            self.report_text_last_step = content
            if self.report_file is not None:
                self.report_file.write(self.report_text_last_step)
                self.report_file.flush()
            str_error = ('Error setting projected images after computing position from images measurements:\n{}'.format(str_error))
            return str_error
        # 7. Set measured images
        for camera_id in measured_by_image_id:
            camera = camera_by_id[camera_id]
            measured_values = [measured_by_image_id[camera_id][0], measured_by_image_id[camera_id][1]]
            measured_undistorted_values = [undistorted_measured_by_image_id[camera_id][0],
                                           undistorted_measured_by_image_id[camera_id][1]]
            self.add_image_measured_value(camera, measured_values, measured_undistorted_values)
        # 8. Matching needs exists stereopairs homographies
        if not self.at_block.project.exists_stereopairs_homographies:
            self.report_text += content
            self.report_text_last_step = content
            if self.report_file is not None:
                self.report_file.write(self.report_text_last_step)
                self.report_file.flush()
            return str_error
        # 9. set memory data for matching
        maximum_ram_user = self.at_block.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RAM_MAXIMUM_SIZE]
        str_error = self.at_block.project.set_epipolar_memory_data_for_match_object_point(fc, sc)
        if str_error:
            content += ("\n- Error: setting epipolar memory data:\n{}".format(str_error))
            self.report_text += content
            self.report_text_last_step = content
            if self.report_file is not None:
                self.report_file.write(self.report_text_last_step)
                self.report_file.flush()
            str_error = ('Error: setting epipolar memory data:\n{}'.format(str_error))
            return str_error

        # images_matches_accuracy = self.at_block.project.digitizing_parameters[
        #     defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MATCHES_ACCURACY]
        # match_correlation_threshold_percentage = self.at_block.project.digitizing_parameters[
        #     defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_CORRELATION_THRESHOLD_PERCENTAGE]
        # match_windows_size = self.at_block.project.digitizing_parameters[
        #     defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_WINDOW_SIZE]

        # 8. Iterate over projected values for find matched solutions
        str_error, projected_images = self.get_projected_images()
        if str_error:
            content += ("\n- Error: getting projected images after computing position from images measurements:\n{}".format(str_error))
            self.report_text += content
            self.report_text_last_step = content
            if self.report_file is not None:
                self.report_file.write(self.report_text_last_step)
                self.report_file.flush()
            str_error = ('Error getting projected images after computing position from images measurements:\n{}'.format(str_error))
            return str_error
        str_error, undistorted_projected_images = self.get_undistorted_projected_images()
        if str_error:
            content += ("\n- Error: getting undistorted projected images after computing position from images measurements:\n{}".format(str_error))
            self.report_text += content
            self.report_text_last_step = content
            if self.report_file is not None:
                self.report_file.write(self.report_text_last_step)
                self.report_file.flush()
            str_error = ('Error getting undistorted projected images after computing position from images measurements:\n{}'.format(str_error))
            return str_error
        # Preparo vectores para matching con multiproceso
        measuredImagesId = [] # QVector<int> measuredImagesId;
        undistortedMeasuredColumns = [] # QVector<double> undistortedMeasuredColumns;
        undistortedMeasuredRows = [] # QVector<double> undistortedMeasuredRows;
        projectedImagesId = [] # QVector<int> projectedImagesDbId;
        undistortedMatchedColumns = [] # QVector<QVector<double> > undistortedMatchedColumns;
        undistortedMatchedRows = [] # QVector<QVector<double> > undistortedMatchedRows;
        matchedFinds = [] # QVector<bool> matchedFinds;
        qualitiesValues = [] # QVector<QVector<double> > qualitiesValues;
        measuredCamerasPc = [] # QVector<QVector<double> > measuredCamerasPc;
        matchedCamerasPc = [] # QVector<QVector<double> > matchedCamerasPc;
        matchedNames = [] # QVector<QVector<QString> > ;
        focal_in_pixels = None
        exists_several_sensors_in_at_block = False
        for projected_image_id in projectedImagesId:
            if projected_image_id in measured_by_image_id:
                continue
            if not projected_image_id in undistorted_projected_images:
                continue
            projected_camera = self.at_block.get_camera_from_camera_id(projected_image_id)
            if projected_camera is None:
                continue
            projected_camera_label = projected_camera.label
            # con los valores proyectados como aproximados para los matcheados
            undistorted_matched_column = undistorted_projected_images[projected_image_id][0]
            undistorted_matched_row = undistorted_projected_images[projected_image_id][1]
            if undistorted_matched_column is None or undistorted_matched_row is None:
                continue
            matched_camera_pc = projected_camera.get_pc()
            if matched_camera_pc is None:
                continue
            projected_sensor_id = projected_camera.sensor_id
            if projected_sensor_id is None:
                continue
            if not projected_sensor_id in self.at_block.sensor_by_id:
                continue
            projected_sensor = self.at_block.sensor_by_id[projected_sensor_id]
            if projected_sensor is None:
                continue
            str_error, projected_camera_focal_in_pixels = projected_sensor.get_focal()
            if str_error:
                continue
            if projected_camera_focal_in_pixels is None:
                continue
            if focal_in_pixels is None:
                focal_in_pixels = projected_camera_focal_in_pixels
            elif abs(projected_camera_focal_in_pixels - focal_in_pixels) > 0.5:
                exists_several_sensors_in_at_block = True
            for measured_image_id in measured_by_image_id:
                measured_camera = self.at_block.get_camera_from_camera_id(measured_image_id)
                if measured_camera is None:
                    continue
                measured_camera_label = measured_camera.label
                if not measured_image_id in undistorted_measured_by_image_id:
                    continue
                undistorted_measured_column = undistorted_measured_by_image_id[measured_image_id][0]
                undistorted_measured_row = undistorted_measured_by_image_id[measured_image_id][1]
                if undistorted_measured_column is None or undistorted_measured_row is None:
                    continue
                measured_camera_pc = measured_camera.get_pc()
                if measured_camera_pc is None:
                    continue
                measured_sensor_id = measured_camera.sensor_id
                if measured_sensor_id is None:
                    continue
                if not measured_sensor_id in self.at_block.sensor_by_id:
                    continue
                measured_sensor = self.at_block.sensor_by_id[measured_sensor_id]
                if measured_sensor is None:
                    continue
                str_error, measured_camera_focal_in_pixels = measured_sensor.get_focal()
                if str_error:
                    continue
                if measured_camera_focal_in_pixels is None:
                    continue
                if focal_in_pixels is None:
                    focal_in_pixels = measured_camera_focal_in_pixels
                elif abs(measured_camera_focal_in_pixels - focal_in_pixels) > 0.5:
                    exists_several_sensors_in_at_block = True
                matchedFind = False
                qualityValues = []
                measuredImagesId.append(measured_image_id)
                undistortedMeasuredColumns.append(undistorted_measured_column)
                undistortedMeasuredRows.append(undistorted_measured_row)
                projectedImagesDbId.append(projected_image_id)
                undistortedMatchedColumnsValues = []
                undistortedMatchedRowsValues = []
                undistortedMatchedColumnsValues.append(undistorted_matched_column)
                undistortedMatchedColumns.append(undistortedMatchedColumnsValues)
                undistortedMatchedRowsValues.append(undistorted_measured_row)
                undistortedMatchedRows.append(undistortedMatchedRowsValues)
                matchedFinds.append(matchedFind)
                qualitiesValues.append(qualityValues)
                measuredCamerasPc.append(measured_camera_pc)
                matchedCamerasPc.append(matched_camera_pc)
                matchedNamesValues = []
                matchedNames.append(matchedNamesValues)
        if exists_several_sensors_in_at_block:
            content += ("\n- Error: getting values for matching, exists several sensors width different focals")
            self.report_text += content
            self.report_text_last_step = content
            if self.report_file is not None:
                self.report_file.write(self.report_text_last_step)
                self.report_file.flush()
            str_error = ("\n- Error: getting values for matching, exists several sensors width different focals")
            return str_error
        for projected_image_id in projectedImagesId:
            if projected_image_id in measured_by_image_id:
                continue
            if not projected_image_id in undistorted_projected_images:
                continue
            projected_camera = self.at_block.get_camera_from_camera_id(projected_image_id)
            if projected_camera is None:
                continue
            projected_camera_label = projected_camera.label
            # con los valores proyectados como aproximados para los matcheados
            undistorted_matched_column = undistorted_projected_images[projected_image_id][0]
            undistorted_matched_row = undistorted_projected_images[projected_image_id][1]
            if undistorted_matched_column is None or undistorted_matched_row is None:
                continue
            content += ("\n  - Finding match img ...: {}".format(projected_camera_label))
            content += ("\n    Proj. Und. coor .....: ({:.2f},{:.2f})".format(undistorted_matched_column,
                                                                              undistorted_matched_row))
            content += ("\n      Measured Image    Meas.U.C    Meas.U.R     Method-WindowSize   Match.U.C   Match.U.R")
            content += ("     Match.C     Match.R   Quality  Obj.Pto.Fc  Obj.Pto.Sc  Obj.Pto.Tc")
            content += ("  Std.Fc  Std.Sc  Std.Tc")
            for measured_image_id in measured_by_image_id:
                measured_camera = self.at_block.get_camera_from_camera_id(measured_image_id)
                if measured_camera is None:
                    continue
                measured_camera_label = measured_camera.label
                if not measured_image_id in undistorted_measured_by_image_id:
                    continue
                undistorted_measured_column = undistorted_measured_by_image_id[measured_image_id][0]
                undistorted_measured_row = undistorted_measured_by_image_id[measured_image_id][1]
                if undistorted_measured_column is None or undistorted_measured_row is None:
                    continue
                content += "\n"
                content += ("{:20s}".format(measured_camera_label))
                content += ("{:12.2f}".format(undistorted_measured_column))
                content += ("{:12.2f}".format(undistorted_measured_row))
                distortedMeasuredValue = []
                distortedMeasuredValue.append(measured_by_image_id[measured_image_id][0])
                distortedMeasuredValue.append(measured_by_image_id[measured_image_id][1])
                distortedMeasuredValue.append(measured_by_image_id[measured_image_id][2])
                distortedMeasuredValue.append(measured_by_image_id[measured_image_id][3])

        # double pointHeight = mDsmHeight;

        # ...

        self.report_text += content
        self.report_text_last_step = content
        if self.report_file is not None:
            self.report_file.write(self.report_text_last_step)
            self.report_file.flush()
        return str_error

