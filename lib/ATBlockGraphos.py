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
# from pyLibPhotogrammetry.defs import defs_metashape_markers as defs_msm
from pyLibPhotogrammetry.defs import defs_graphos as defs_gr

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
# from pyLibQtTools import Tools
# from pyLibGDAL import defs_gdal
# from pyLibGDAL.GDALTools import GDALTools

from pyLibPhotogrammetry.lib.ATBlock import ATBlock
from pyLibPhotogrammetry.lib.SensorGraphos import SensorGraphos
from pyLibPhotogrammetry.lib.CameraGraphos import CameraGraphos
# from pyLibPhotogrammetry.lib.ObjectPointMetashape import ObjectPointMetashape
from pyLibPhotogrammetry.lib.ImagePoint import ImagePoint

class ATBlockGraphos(ATBlock):
    def __init__(self,
                 file_path,
                 project):
        super().__init__(file_path, project)

    def set_from_xml(self,
                     xml_element):
        str_error = ''
        # label = xml_element[defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL]
        # if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_ENABLED in xml_element:
        #     str_error = ('Not exists attribute: {} in chunk in metashape markers XML file:\n{}'.
        #                  format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_ENABLED, self.file_path))
        #     return str_error
        label = defs_gr.GRAPHOS_AT_BLOCK_LABEL
        self.label = label

        # CAMERAS GRAPHOS === SENSORS METASHAPE
        if not defs_gr.GRAPHOS_XML_SENSORS_TAG in xml_element:
            str_error = ('Not exists element: {} in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSORS_TAG, self.file_path))
            return str_error
        sensors_element = xml_element[defs_gr.GRAPHOS_XML_SENSORS_TAG]
        if not defs_gr.GRAPHOS_XML_SENSOR_TAG in sensors_element:
            str_error = ('Not exists element: {} in: {} in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_SENSOR_TAG,
                                defs_gr.GRAPHOS_XML_SENSORS_TAG, self.file_path))
            return str_error
        sensors_content = sensors_element[defs_gr.GRAPHOS_XML_SENSOR_TAG]
        sensors_list = []
        if isinstance(sensors_content, dict):
            sensors_list.append(sensors_content)
        else:
            sensors_list = sensors_content
        is_multi_band = False
        for i in range(len(sensors_list)):
            sensor_element = sensors_list[i]
            sensor = SensorGraphos(self)
            str_error = sensor.set_from_xml(sensor_element)
            if str_error:
                str_error = ('Loading sensor position: {}\nError:\n{}'.format(str(i+1), str_error))
                return str_error
            self.sensor_by_id[sensor.id] = sensor
            if sensor.master_id != defs_gr.GRAPHOS_XML_SENSOR_NO_MASTER_ID:
                if not is_multi_band:
                    is_multi_band = True
        if is_multi_band:
            for sensor_id in self.sensor_by_id:
                sensor = self.sensor_by_id[sensor_id]
                band_name = sensor.band_names[0]
                self.sensor_id_by_band[band_name] = sensor.id

        return str_error

