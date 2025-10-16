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
from pyLibPhotogrammetry.defs import defs_metashape_markers as defs_msm

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
# from pyLibQtTools import Tools
# from pyLibGDAL import defs_gdal
# from pyLibGDAL.GDALTools import GDALTools

from pyLibPhotogrammetry.lib.Calibration import Calibration

class CalibrationMetashape(Calibration):
    def __init__(self,
                 sensor):
        super().__init__(sensor)

    def initialize_parameters(self):
        str_error = ''
        if self.type.casefold() == defs_msm.METASHAPE_SENSOR_CALIBRATION_TYPE_FRAME:
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_F_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CX_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CY_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B1_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B2_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K1_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K2_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K3_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K4_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P1_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P2_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P3_TAG] = 0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P4_TAG] = 0.0
            return str_error
        if self.type.casefold() == defs_msm.METASHAPE_CALIBRATION_TYPE_FISHEYE:
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_F_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CX_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CY_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B1_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B2_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K1_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K2_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K3_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K4_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P1_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P2_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P3_TAG]=0.0
            self.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P4_TAG]=0.0
            return str_error
        str_error = ('Invalid type: {}'.format(self.type))
        return str_error

    def set_from_metashape_xml(self,
                               xml_element):
        str_error = ''
        #type
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_TYPE in xml_element:
            str_error = ('Not exists attribute: {} in sensor: {} in calibration in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_TYPE,
                                self.sensor.label, self.sensor.at_block.file_path))
            return str_error
        type = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_TYPE]
        if (type.casefold() != defs_msm.METASHAPE_SENSOR_CALIBRATION_TYPE_FISHEYE.casefold()
                and type.casefold() != defs_msm.METASHAPE_SENSOR_CALIBRATION_TYPE_FRAME.casefold()):
            str_error = ('Invalid attribute: {} in sensor: {} in calibration in metashape markers XML file:\n{}\nmust be: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_TYPE,
                                self.sensor.label, self.sensor.at_block.file_path,
                                defs_msm.METASHAPE_SENSOR_CALIBRATION_TYPE_FRAME,
                                defs_msm.METASHAPE_SENSOR_CALIBRATION_TYPE_FISHEYE))
            return str_error
        self.type = type
        #kind (class)
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS in xml_element:
            str_error = ('Not exists attribute: {} in sensor: {} in calibration in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS,
                                self.sensor.label, self.sensor.at_block.file_path))
            return str_error
        kind = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS]
        if (kind.casefold() != defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_INITIAL.casefold()
                and kind.casefold() != defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_ADJUSTED.casefold()):
            str_error = ('Invalid attribute: {} in sensor: {} in calibration in metashape markers XML file:\n{}\nmust be: {} or {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_TYPE,
                                self.sensor.label, self.sensor.at_block.file_path,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_INITIAL,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_ADJUSTED))
            return str_error
        self.kind = kind
        # resolution: width and height
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_TAG in xml_element:
            str_error = ('Not exists attribute: {} in calibrarion: {} in sensor: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_TAG,
                                self.kind, self.sensor.label, self.sensor.at_block.file_path))
            return str_error
        resolution_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_TAG]
        if not isinstance(resolution_element, dict):
            str_error = (
                'Element: {} in calibrarion: {} in sensor: {} in metashape markers XML file:\n{}\npmust be a dictionary'.
                format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_TAG,
                                self.kind, self.sensor.label, self.sensor.at_block.file_path))
            return str_error
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_ATTRIBUTE_WIDTH in resolution_element:
            str_error = ('Not exists attribute: {} in: {} in calibrarion: {} in sensor: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_ATTRIBUTE_WIDTH,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_TAG,
                                self.kind, self.sensor.label, self.sensor.at_block.file_path))
            return str_error
        str_width = resolution_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_ATTRIBUTE_WIDTH]
        try:
            self.width = int(str_width)
        except ValueError:
            str_error = ('Attribute: {} in: {} in calibrarion: {} in sensor: {} in metashape markers XML file:\n{}\n must be an integer: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_ATTRIBUTE_WIDTH,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_TAG,
                                self.kind, self.sensor.label, self.sensor.at_block.file_path, str_width))
            return str_error
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_ATTRIBUTE_HEIGHT in resolution_element:
            str_error = ('Not exists attribute: {} in: {} in calibrarion: {} in sensor: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_ATTRIBUTE_HEIGHT,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_TAG,
                                self.kind, self.sensor.label, self.sensor.at_block.file_path))
            return str_error
        str_height = resolution_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_ATTRIBUTE_HEIGHT]
        try:
            self.height = int(str_height)
        except ValueError:
            str_error = ('Attribute: {} in: {} in calibrarion: {} in sensor: {} in metashape markers XML file:\n{}\n must be an integer: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_ATTRIBUTE_HEIGHT,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_RESOLUTION_TAG,
                                self.kind, self.sensor.label, self.sensor.at_block.file_path, str_height))
            return str_error
        str_error = self.initialize_parameters()
        if str_error:
            str_error = ('Initializing parameters in calibrarion: {} in sensor: {} in metashape markers XML file:\n{}\nError:\n{}'.
                         format(self.kind, self.sensor.label, self.sensor.at_block.file_path, str_error))
            return str_error
        for parameter_tag in self.parameters:
            if parameter_tag in xml_element:
                str_value = xml_element[parameter_tag]
                try:
                    value = float(str_value)
                except ValueError:
                    str_error = (
                        'Parameter: {} in calibrarion: {} in sensor: {} in metashape markers XML file:\n{}\n must be a float: {}'.
                        format(parameter_tag, self.kind, self.sensor.label, self.sensor.at_block.file_path, str_value))
                    return str_error
                self.parameters[parameter_tag] = value
        return str_error
