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

        # IMAGES GRAPHOS === CAMERAS METASHAPE
        if not defs_gr.GRAPHOS_XML_IMAGES_TAG in xml_element:
            str_error = ('Not exists element: {} in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_IMAGES_TAG, self.file_path))
            return str_error
        images_element = xml_element[defs_gr.GRAPHOS_XML_IMAGES_TAG]
        if not defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG in images_element:
            str_error = ('Not exists element: {} in: {} in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG,
                                defs_gr.GRAPHOS_XML_IMAGES_IMAGES_TAG, self.file_path))
            return str_error
        images_content = images_element[defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG]
        if not isinstance(images_content, list):
            str_error = ('Element: {} in: {}\nis not a list in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG,
                                defs_gr.GRAPHOS_XML_IMAGES_IMAGES_TAG, self.file_path))
            return str_error
        sensor_id_by_camera_id = {}
        camera_file_basename_by_camera_id = {}
        for i in range(len(images_content)):
            image_content = images_content[i]
            if not defs_gr.GRAPHOS_XML_IMAGES_IMAGE_ID_TAG in image_content:
                str_error = ('Not exists element: {} in: {} in: {} in in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_IMAGES_IMAGE_ID_TAG,
                                    defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG,
                                    defs_gr.GRAPHOS_XML_IMAGES_IMAGES_TAG, str(i + 1), self.file_path))
                return str_error
            if not defs_gr.GRAPHOS_XML_IMAGES_IMAGE_CAMERA_ID_TAG in image_content:
                str_error = ('Not exists element: {} in: {} in: {} in in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_IMAGES_IMAGE_CAMERA_ID_TAG,
                                    defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG,
                                    defs_gr.GRAPHOS_XML_IMAGES_IMAGES_TAG, str(i+1), self.file_path))
                return str_error
            sensor_id_str = image_content[defs_gr.GRAPHOS_XML_IMAGES_IMAGE_CAMERA_ID_TAG]
            sensor_id = -1
            try:
                sensor_id = int(sensor_id_str)
            except ValueError:
                str_error = ('For image number: {} in element: {} in: {}\ncamera id: {} is not an integer in \nat block in XML file:\n{}'.
                             format(str(i+1), defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG,
                                    defs_gr.GRAPHOS_XML_IMAGES_IMAGES_TAG, str(i+1), sensor_id_str, self.file_path))
                return str_error
            if not sensor_id in self.sensor_by_id:
                str_error = ('For image number: {} in element: {} in: {}\ncamera id: {} not exists in \nat block in XML file:\n{}'.
                             format(str(i+1), defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG,
                                    defs_gr.GRAPHOS_XML_IMAGES_IMAGES_TAG, str(i+1), sensor_id, self.file_path))
                return str_error
            if not defs_gr.GRAPHOS_XML_IMAGES_IMAGE_FILE_TAG in image_content:
                str_error = ('Not exists element: {} in: {} in: {} in in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_IMAGES_IMAGE_FILE_TAG,
                                    defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG,
                                    defs_gr.GRAPHOS_XML_IMAGES_IMAGES_TAG, str(i+1), self.file_path))
            file_path = image_content[defs_gr.GRAPHOS_XML_IMAGES_IMAGE_FILE_TAG]
            file_basename_with_extension = os.path.basename(file_path)
            camera_id = image_content[defs_gr.GRAPHOS_XML_IMAGES_IMAGE_ID_TAG]
            sensor_id_by_camera_id[camera_id] = sensor_id
            camera_file_basename_by_camera_id[camera_id] = file_basename_with_extension

        # ORIENTATIONS GRAPHOS === CAMERAS METASHAPE
        if not defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG in xml_element:
            str_error = ('Not exists element: {} in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
            return str_error
        orientations_element = xml_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG]
        if not defs_gr.GRAPHOS_XML_ORIENTATIONS_CRS_TAG in orientations_element:
            str_error = ('Not exists element: {} in: {} in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_ORIENTATIONS_CRS_TAG,
                                defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
            return str_error
        crs_id_enu = orientations_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_CRS_TAG]
        if not defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG in orientations_element:
            str_error = ('Not exists element: {} in: {} in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
            return str_error
        orientation_images_content = orientations_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG]
        if not isinstance(orientation_images_content, list):
            str_error = ('Element: {} in: {}\nis not a list in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
            return str_error
        for i in range(len(orientation_images_content)):
            camera_element = orientation_images_content[i]
            if not defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ID_TAG in camera_element:
                str_error = ('Not exists element: {} in: {} in: {} in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ID_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, str(i + 1), self.file_path))
                return str_error
            camera_id = camera_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ID_TAG]
            if not camera_id in camera_file_basename_by_camera_id:
                str_error = ('Not found image for camera id: {} in: {} in: {}\nat block in XML file:\n{}'.
                             format(camera_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ID_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
                return str_error
            if not defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_X_TAG in camera_element:
                str_error = ('Not exists element: {} in: {} in: {} in in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_X_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, str(i + 1), self.file_path))
                return str_error
            camera_x_str = camera_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_X_TAG]
            camera_x = None
            try:
                camera_x = float(camera_x_str)
            except ValueError:
                str_error = ('For camera id: {} in element: {} value: {} is not a double\nat block in XML file:\n{}'.
                             format(camera_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_X_TAG, self.file_path))
                return str_error
            if not defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_Y_TAG in camera_element:
                str_error = ('Not exists element: {} in: {} in: {} in in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_Y_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, str(i + 1), self.file_path))
                return str_error
            camera_y_str = camera_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_Y_TAG]
            camera_y = None
            try:
                camera_y = float(camera_y_str)
            except ValueError:
                str_error = ('For camera id: {} in element: {} value: {} is not a double\nat block in XML file:\n{}'.
                             format(camera_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_Y_TAG, self.file_path))
                return str_error
            if not defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_Z_TAG in camera_element:
                str_error = ('Not exists element: {} in: {} in: {} in in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_Z_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, str(i + 1), self.file_path))
                return str_error
            camera_z_str = camera_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_Z_TAG]
            camera_z = None
            try:
                camera_z = float(camera_z_str)
            except ValueError:
                str_error = ('For camera id: {} in element: {} value: {} is not a double\nat block in XML file:\n{}'.
                             format(camera_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_Z_TAG, self.file_path))
                return str_error
            if not defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ROT_TAG in camera_element:
                str_error = ('Not exists element: {} in: {} in: {} in in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ROT_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, str(i + 1), self.file_path))
                return str_error
            camera_rot_str = camera_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ROT_TAG]
            rot_values = None
            try:
                rot_values = [float(x) for x in camera_rot_str.split()]
            except:
                str_error = ('For camera id: {} in element: {} value: {} is not a list of nine float values\nat block in XML file:\n{}'.
                             format(camera_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ROT_TAG, self.file_path))
                return str_error
            if len(rot_values) != 9:
                str_error = ('For camera id: {} in element: {} value: {} is not a list of nine float values\nat block in XML file:\n{}'.
                             format(camera_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ROT_TAG, self.file_path))
                return str_error
            camera_rotation = np.zeros((3, 3))
            for row in range(0, 3):
                for col in range(0, 3):
                    pos = row * 3 + col
                    camera_rotation[row, col] = rot_values[pos]

            yo = 1
            # camera = CameraGraphos(self)
            # str_error = camera.set_from_xml(camera_element)
            # if str_error:
            #     str_error = ('Loading camera position: {}\nError:\n{}'.format(str(i+1), str_error))
            #     return str_error
            # self.camera_by_id[camera.id] = camera


        return str_error

