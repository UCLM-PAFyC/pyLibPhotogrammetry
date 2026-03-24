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
from pyLibPhotogrammetry.lib.ObjectPointGraphos import ObjectPointGraphos
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
        new_camera_id_by_original_camera_id = {}
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
            # file_basename_without_extension = os.path.basename(file_path).split('.')[0]
            camera_id_str = image_content[defs_gr.GRAPHOS_XML_IMAGES_IMAGE_ID_TAG]
            camera_id = None
            try:
                camera_id = int(camera_id_str)
            except ValueError:
                str_error = ('Not integer element: {} in: {} in: {} in in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_IMAGES_IMAGE_CAMERA_ID_TAG,
                                    defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG,
                                    defs_gr.GRAPHOS_XML_IMAGES_IMAGES_TAG, str(i+1), self.file_path))
                return str_error
            # if camera_id in self.at_block.camera_by_id:
            #     str_error = ('Repeated element: {} in: {} in: {} in in image number: {}\nat block in XML file:\n{}'.
            #                  format(defs_gr.GRAPHOS_XML_IMAGES_IMAGE_CAMERA_ID_TAG,
            #                         defs_gr.GRAPHOS_XML_IMAGES_IMAGE_TAG,
            #                         defs_gr.GRAPHOS_XML_IMAGES_IMAGES_TAG, str(i+1), self.file_path))
            #     return str_error
            new_camera_id = i
            new_camera_id_by_original_camera_id[camera_id] = new_camera_id
            sensor_id_by_camera_id[new_camera_id] = sensor_id
            camera_file_basename_by_camera_id[new_camera_id] = file_basename_with_extension
            # camera_file_basename_by_camera_id[camera_id] = file_basename_without_extension

        # GROUND CONTROL POINTS GRAPHOS, needed for project crs_id, at least
        if not defs_gr.GRAPHOS_XML_GCPS_TAG in xml_element:
            str_error = ('Not exists element: {} in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
            return str_error
        gcps_element = xml_element[defs_gr.GRAPHOS_XML_GCPS_TAG]
        if not defs_gr.GRAPHOS_XML_GCPS_CRS_TAG in gcps_element:
            str_error = ('Not exists element: {} in: {} in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_GCPS_CRS_TAG,
                                defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
            return str_error
        self.crs_id = gcps_element[defs_gr.GRAPHOS_XML_GCPS_CRS_TAG]

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
        crs_enu_id = orientations_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_CRS_TAG]
        if not defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG in orientations_element:
            str_error = ('Not exists element: {} in: {} in at block in XML file:\n{}'.
                         format(defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
            return str_error
        crs_geo2d_id = self.project.crs_tools.get_crs_geo2d_for_crs(crs_enu_id)
        if crs_geo2d_id is None:
            str_error = ('Error getting GEO 2D CRS from value:\n{}\nin element: {} in: {} in at block in XML file:\n{}'.
                         format(crs_enu_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
            return str_error
        crs_ecef_ids = self.project.crs_tools.get_crs_ecef_ids_for_crs_geo2d_id(crs_geo2d_id)
        if crs_ecef_ids is None:
            str_error = ('Error getting ECEF CRS from value:\n{}\nin element: {} in: {} in at block in XML file:\n{}'.
                         format(crs_enu_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
            return str_error
        crs_ecef_id = crs_ecef_ids[0]
        crs_geo3d_ids = self.project.crs_tools.get_crs_geo3d_ids_for_crs_geo2d_id(crs_geo2d_id)
        if crs_geo3d_ids is None:
            str_error = ('Error getting GE= 3D CRS from value:\n{}\nin element: {} in: {} in at block in XML file:\n{}'.
                         format(crs_enu_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
            return str_error
        crs_geo3d_id = crs_geo3d_ids[0]
        # self.crs_enu_id = crs_enu_id
        self.crs_enu_id = crs_enu_id
        self.crs_geo2d_id = crs_geo2d_id
        self.crs_ecef_id = crs_ecef_id
        self.crs_geo3d_id = crs_geo3d_id
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
            camera_id_str = camera_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ID_TAG]
            camera_id = None
            try:
                camera_id = int(camera_id_str)
            except ValueError:
                str_error = ('Not integer element: {} in: {} in: {} in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ID_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, str(i + 1), self.file_path))
                return str_error
            camera_id = new_camera_id_by_original_camera_id[camera_id]
            if not camera_id in sensor_id_by_camera_id:
                str_error = ('Not found sensor for camera id: {} in: {} in: {}\nat block in XML file:\n{}'.
                             format(camera_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ID_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
                return str_error
            camera_sensor_id = sensor_id_by_camera_id[camera_id]
            if not camera_id in camera_file_basename_by_camera_id:
                str_error = ('Not found image for camera id: {} in: {} in: {}\nat block in XML file:\n{}'.
                             format(camera_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ID_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, self.file_path))
                return str_error
            camera_label = camera_file_basename_by_camera_id[camera_id]
            if not defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_X_TAG in camera_element:
                str_error = ('Not exists element: {} in: {} in: {} in in image number: {}\nat block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_X_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG, str(i + 1), self.file_path))
                return str_error
            camera_x_str = camera_element[defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_X_TAG]
            camera_enu_x = None
            try:
                camera_enu_x = float(camera_x_str)
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
            camera_enu_y = None
            try:
                camera_enu_y = float(camera_y_str)
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
            camera_enu_z = None
            try:
                camera_enu_z = float(camera_z_str)
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
            camera_enu_rot = np.zeros((3, 3))
            for row in range(0, 3):
                for col in range(0, 3):
                    pos = row * 3 + col
                    camera_enu_rot[row, col] = rot_values[pos]
            camera = CameraGraphos(self)
            str_error = camera.initialize(camera_id, camera_sensor_id, camera_label,
                                          camera_enu_x, camera_enu_y, camera_enu_z, camera_enu_rot)
            if str_error:
                str_error = ('Initializing camera id: {} in element: {} value: {} \nat block in XML file:\n{}\nError:\n{}'.
                             format(camera_id, defs_gr.GRAPHOS_XML_ORIENTATIONS_TAG,
                                    defs_gr.GRAPHOS_XML_ORIENTATIONS_IMAGES_IMAGE_ROT_TAG, self.file_path, str_error))
                return str_error
            self.camera_by_id[camera.id] = camera

        # GROUND CONTROL POINTS GRAPHOS, needed for project crs_id, at least
        # if not defs_gr.GRAPHOS_XML_GCPS_TAG in xml_element:
        #     str_error = ('Not exists element: {} in at block in XML file:\n{}'.
        #                  format(defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
        #     return str_error
        # gcps_element = xml_element[defs_gr.GRAPHOS_XML_GCPS_TAG]
        # if not defs_gr.GRAPHOS_XML_GCPS_CRS_TAG in gcps_element:
        #     str_error = ('Not exists element: {} in: {} in at block in XML file:\n{}'.
        #                  format(defs_gr.GRAPHOS_XML_GCPS_CRS_TAG,
        #                         defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
        #     return str_error
        # self.crs_id = gcps_element[defs_gr.GRAPHOS_XML_GCPS_CRS_TAG]
        if defs_gr.GRAPHOS_XML_GCPS_GCP_TAG in gcps_element:
            gcps_list = gcps_element[defs_gr.GRAPHOS_XML_GCPS_GCP_TAG]
            if not isinstance(gcps_list, list):
                str_error = ('Element: {} in: {}\nis not a list in at block in XML file:\n{}'.
                             format(defs_gr.GRAPHOS_XML_GCPS_GCP_TAG,
                                    defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                return str_error
            for i in range(len(gcps_list)):
                gcp_content = gcps_list[i]
                # name
                if not defs_gr.GRAPHOS_XML_GCPS_GCP_NAME_TAG in gcp_content:
                    str_error = ('Not {} in element: {} position: {} in: {}\nin at block in XML file:\n{}'.
                                 format(defs_gr.GRAPHOS_XML_GCPS_GCP_NAME_, defs_gr.GRAPHOS_XML_GCPS_GCP_TAG,
                                        str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                    return str_error
                gcp_id = gcp_content[defs_gr.GRAPHOS_XML_GCPS_GCP_NAME_TAG]
                # x
                if not defs_gr.GRAPHOS_XML_GCPS_GCP_X_TAG in gcp_content:
                    str_error = ('Not {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                 format(defs_gr.GRAPHOS_XML_GCPS_GCP_X_TAG, gcp_id,
                                        str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                    return str_error
                gcp_x_str = gcp_content[defs_gr.GRAPHOS_XML_GCPS_GCP_X_TAG]
                gcp_x = None
                try:
                    gcp_x = float(gcp_x_str)
                except ValueError:
                    str_error = ('Not x float in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                 format(defs_gr.GRAPHOS_XML_GCPS_GCP_X_TAG, gcp_id,
                                        str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                    return str_error
                # y
                if not defs_gr.GRAPHOS_XML_GCPS_GCP_Y_TAG in gcp_content:
                    str_error = ('Not {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                 format(defs_gr.GRAPHOS_XML_GCPS_GCP_X_TAG, gcp_id,
                                        str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                    return str_error
                gcp_y_str = gcp_content[defs_gr.GRAPHOS_XML_GCPS_GCP_Y_TAG]
                gcp_y = None
                try:
                    gcp_y = float(gcp_y_str)
                except ValueError:
                    str_error = ('Not y float in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                 format(defs_gr.GRAPHOS_XML_GCPS_GCP_Y_TAG, gcp_id,
                                        str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                    return str_error
                # z
                if not defs_gr.GRAPHOS_XML_GCPS_GCP_Z_TAG in gcp_content:
                    str_error = ('Not {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                 format(defs_gr.GRAPHOS_XML_GCPS_GCP_Z_TAG, gcp_id,
                                        str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                    return str_error
                gcp_z_str = gcp_content[defs_gr.GRAPHOS_XML_GCPS_GCP_Z_TAG]
                gcp_z = None
                try:
                    gcp_z = float(gcp_z_str)
                except ValueError:
                    str_error = ('Not z float in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                 format(defs_gr.GRAPHOS_XML_GCPS_GCP_Z_TAG, gcp_id,
                                        str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                    return str_error
                gcp = ObjectPointGraphos(self)
                str_error = gcp.initialize(gcp_id, gcp_x, gcp_y, gcp_z, self.crs_id)
                if str_error:
                    str_error = ('Initializing GCP: {} in: {}\nin at block in XML file:\n{}\nError:\n{}'.
                                 format(defs_gr.GRAPHOS_XML_GCPS_GCP_Z_TAG, gcp_id,
                                        str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path, str_error))
                    return str_error
                self.gcps_by_id[gcp.id] = gcp
                if not defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG in gcp_content:
                    # str_error = ('Not {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                    #              format(defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                    #                     str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                    # return str_error
                    continue
                image_points_content = gcp_content[defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG]
                if not isinstance(image_points_content, dict):
                    str_error = ('Not a list: {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                 format(defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                                        str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                    return str_error
                if not defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG in image_points_content:
                    # str_error = ('Not {} in {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                    #              format(defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG,
                    #                     defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                    #                     str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                    # return str_error
                    continue
                image_points_list = []
                image_points_element = image_points_content[defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG]
                if not isinstance(image_points_element, list):
                    image_points_list.append(image_points_element)
                else:
                    image_points_list = image_points_element
                # image_points_list = image_points_content[defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG]
                # if not isinstance(image_points_list, list):
                #     str_error = ('Not a list: {} in {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                #                  format(defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG,
                #                         defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                #                         str(i+1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                #     return str_error
                for j in range(len(image_points_list)):
                    image_point = image_points_list[j]
                    if not defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_ID_TAG in image_point:
                        str_error = ('Not {} in position: {} in {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                     format(defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_ID_TAG, str(j+1),
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG,
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                                            str(i + 1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                        return str_error
                    camera_id_str = image_point[defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_ID_TAG]
                    camera_id = None
                    try:
                        camera_id = int(camera_id_str)
                    except ValueError:
                        str_error = ('Not integer {} in position: {} in {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                     format(defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_ID_TAG, str(j+1),
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG,
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                                            str(i + 1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                        return str_error
                    camera_id = new_camera_id_by_original_camera_id[camera_id]
                    if not camera_id in camera_file_basename_by_camera_id:
                        str_error = ('Not found {} in position: {} in {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                     format(camera_id, str(j+1),
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG,
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                                            str(i + 1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                        return str_error
                    camera = self.camera_by_id[camera_id]
                    if not defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_X_TAG in image_point:
                        str_error = ('Not {} in position: {} in {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                     format(defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_X_TAG, str(j+1),
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG,
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                                            str(i + 1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                        return str_error
                    image_point_x_str = image_point[defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_X_TAG]
                    image_point_column = None
                    try:
                        image_point_column = float(image_point_x_str)
                    except ValueError:
                        str_error = ('Not a float {} in position: {} in {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                     format(defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_X_TAG, str(j+1),
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG,
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                                            str(i + 1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                        return str_error
                    if not defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_Y_TAG in image_point:
                        str_error = ('Not {} in position: {} in {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                     format(defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_Y_TAG, str(j+1),
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG,
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                                            str(i + 1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                        return str_error
                    image_point_y_str = image_point[defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_Y_TAG]
                    image_point_row = None
                    try:
                        image_point_row = float(image_point_y_str)
                    except ValueError:
                        str_error = ('Not a float {} in position: {} in {} in GCP: {} in: {}\nin at block in XML file:\n{}'.
                                     format(defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_Y_TAG, str(j+1),
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_TAG,
                                            defs_gr.GRAPHOS_XML_GCPS_GCP_IMAGE_POINTS_TAG, gcp_id,
                                            str(i + 1), defs_gr.GRAPHOS_XML_GCPS_TAG, self.file_path))
                        return str_error
                    image_point = ImagePoint(camera, gcp)
                    measured_values = [image_point_column, image_point_row]
                    image_point.set_measured_values(measured_values)
                    image_point.set_pinned(True)
                    # image_point.set_frame_id(frame_id)
                    if not gcp_id in self.image_points_by_gcp_id:
                        self.image_points_by_gcp_id[gcp_id] = []
                    self.image_points_by_gcp_id[gcp_id].append(image_point)
            # GRAPHOS_XML_GCPS_GCP_ERROR_TAG = "error"
            # GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_ERROR_X_TAG = "ex"
            # GRAPHOS_XML_GCPS_GCP_IMAGE_POINT_IMAGE_ERROR_Y_TAG = "ey"
        return str_error

