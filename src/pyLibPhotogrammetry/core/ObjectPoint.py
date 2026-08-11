# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import numpy as np

from ..defs import defs_processes
from .ImagePoint import ImagePoint

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
        self.report_file_name = None
        self.report_file = None
        self.report_text = ""
        self.image_point_by_image_id = {}

    def add_image_projected_value(self,
                                  camera,
                                  projected_values,
                                  projected_undistorted_values):
        camera_id = camera.id
        image_point = None
        if camera_id not in self.image_point_by_image_id:
            image_point = self.image_point_by_image_id[camera_id]
        else:
            image_point = ImagePoint(camera, self)
            self.image_point_by_image_id[camera_id] = image_point
        image_point.set_projected_values(projected_values)
        image_point.set_projected_undistorted_values(projected_undistorted_values)
        return

    def get_report(self):
        return self.report_text

    def open_report_file(self, id):
        str_error = ''
        report_file_path = self.at_block.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_REPORT_FILES_OUTPUT_PATH]
        report_file_path += "/ObjectPoint_" + str(id) + ".txt"
        try:
            self.report_file = open(report_file_path, "w")
        except Exception as e:
            str_error = ('Opening report file:\nError:\n'.format(report_file_path, e))
            self.report_file = None
            return str_error
        self.report_file_name = report_file_path
        # self.report_text = None
        return str_error

    def set_id(self, id, write_report = False):
        str_error = ''
        if write_report and self.report_file is None:
            str_error = self.open_report_file(id)
            if str_error:
                return str_error
        content = "\n- ObjectPoint.set_id"
        content += "\n  - Id ...................: " + str(id)
        self.report_text += content
        if self.report_file is not None:
            self.report_file.write(content)
            self.report_file.flush()
        self.id = id
        return str_error

    def set_label(self, label):
        self.label = label

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



