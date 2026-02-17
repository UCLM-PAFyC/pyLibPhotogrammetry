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
from pyLibPhotogrammetry.defs import defs_graphos as defs_gr

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
# from pyLibQtTools import Tools
# from pyLibGDAL import defs_gdal
# from pyLibGDAL.GDALTools import GDALTools

from pyLibPhotogrammetry.lib.Calibration import Calibration

class CalibrationGraphos(Calibration):
    def __init__(self,
                 sensor,
                 calibration_type):
        super().__init__(sensor)
        self.type = calibration_type
        self.kind = calibration_type # at the moment ...

    def initialize_parameters(self):
        str_error = ''
        if self.type.casefold() == defs_gr.GRAPHOS_SENSOR_CALIBRATION_TYPE_OPENCV_1.casefold():
            self.parameters[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_FX_TAG] = 0.0
            self.parameters[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_FY_TAG] = 0.0
            self.parameters[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_CX_TAG] = 0.0
            self.parameters[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_CY_TAG] = 0.0
            # self.parameters[defs_gr.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B1_TAG] = 0.0
            # self.parameters[defs_gr.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B2_TAG] = 0.0
            self.parameters[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_K1_TAG] = 0.0
            self.parameters[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_K2_TAG] = 0.0
            # self.parameters[defs_gr.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K3_TAG] = 0.0
            # self.parameters[defs_gr.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K4_TAG] = 0.0
            self.parameters[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_P1_TAG] = 0.0
            self.parameters[defs_gr.GRAPHOS_XML_SENSOR_CALIBRATION_P2_TAG] = 0.0
            # self.parameters[defs_gr.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P3_TAG] = 0.0
            # self.parameters[defs_gr.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P4_TAG] = 0.0
            return str_error
        str_error = ('Invalid type: {}'.format(self.type))
        return str_error

    def set_from_xml(self,
                     xml_element):
        str_error = ''
        if (self.type.casefold() != defs_gr.GRAPHOS_SENSOR_CALIBRATION_TYPE_OPENCV_1.casefold()):
            str_error = ('Invalid calibration type in XML file:\n{}\nmust be: {}'.
                         format(self.type))
            return str_error
        str_error = self.initialize_parameters()
        if str_error:
            str_error = ('Initializing parameters in calibration: {} in sensor: {} in XML file:\n{}\nError:\n{}'.
                         format(self.type, self.sensor.label, self.sensor.at_block.file_path, str_error))
            return str_error
        for parameter_tag in self.parameters:
            if parameter_tag in xml_element:
                str_value = xml_element[parameter_tag]
                try:
                    value = float(str_value)
                except ValueError:
                    str_error = (
                        'Parameter: {} in calibrarion: {} in sensor: {} in metashape markers XML file:\n{}\n must be a float: {}'.
                        format(parameter_tag, self.kind, self.sensor.model, self.sensor.at_block.file_path, str_value))
                    return str_error
                self.parameters[parameter_tag] = value
        return str_error
