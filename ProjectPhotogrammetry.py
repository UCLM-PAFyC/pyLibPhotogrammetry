# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os, sys
import json
import xmltodict
import math
import random
import re
import json
import xmltodict
import numpy as np
from datetime import datetime

from osgeo import gdal, osr, ogr
gdal.UseExceptions()

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))

from PyQt5.QtCore import QDir, QFileInfo, QFile, QDate, QDateTime

# common_libs_absolute_path = os.path.join(current_path, defs_paths.COMMON_LIBS_RELATIVE_PATH)
# sys.path.append(common_libs_absolute_path)

from pyLibProject.defs import defs_project_definition
from pyLibProject.lib.Project import Project
from pyLibProject.defs import defs_project
# from pyLibProject.defs import defs_layers_groups
# from pyLibProject.defs import defs_layers
from pyLibProcesses.defs import defs_project as processes_defs_project
from pyLibProcesses.defs import defs_processes as processes_defs_processes
# from pyLibPhotogrammetry.defs import defs_project as defs_project_lib
from pyLibPhotogrammetry.defs import defs_project_photogrammetry as defs_project_photogrammetry
from pyLibPhotogrammetry.defs import defs_processes
from pyLibPhotogrammetry.defs import defs_images as defs_img
from pyLibPhotogrammetry.defs import defs_metashape_markers as defs_msm
from pyLibParameters import defs_pars
from pyLibParameters.ParametersManager import ParametersManager
from pyLibProject.gui.ProjectDefinitionDialog import ProjectDefinitionDialog
# from pyLibPhotogrammetry.gui.ProjectDefinitionDialog import ProjectDefinitionDialog
from pyLibPhotogrammetry.lib.ATBlockMetashape import ATBlockMetashape
from pyLibPhotogrammetry.lib.IExifTool import IExifTool

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
from pyLibQtTools import Tools
from pyLibGDAL import defs_gdal
from pyLibGDAL.GDALTools import GDALTools
from pyLibGDAL.RasterDEM import RasterDEM

class ProjectPhotogrammetry(Project):
    def __init__(self, qgis_iface, settings, crs_tools):
        super().__init__(qgis_iface, settings, crs_tools)
        self.file_path = None
        self.metashape_markers_xml_file = None
        self.at_block_by_label = {}
        self.raster_dem_by_file_path = {}

    def add_image_files(self,
                        files,
                        dialog):
        str_error = ''
        str_error, exif_data_as_dict_by_file = IExifTool.get_metadata_as_dict(files, dialog)
        features = []
        features_filters = []
        at_block_label_by_image_file = {} # to update camera before update db
        image_file_by_camera_id = {} # to update camera before update db
        exif_by_camera_id = {} # to update camera before update db
        cont = 0
        for image_file_path in files:
            camera = self.get_camera_from_image_file_path(image_file_path)
            if camera: # exists
                continue
            image_file_path_lower = image_file_path.lower()
            image_db_id = -1
            image_camera_id = -1
            image_camera_fid = -1
            image_camera_label = ''
            image_at_block_label = ''
            coincidences_by_at_block = {}
            number_of_coincidences = 0
            for at_block_label in self.at_block_by_label:
                at_block = self.at_block_by_label[at_block_label]
                for camera_id in at_block.camera_by_id:
                    camera = at_block.camera_by_id[camera_id]
                    camera_label = camera.label
                    if camera_label.lower() in image_file_path_lower:
                        number_of_coincidences = number_of_coincidences + 1
                        if not at_block_label in coincidences_by_at_block:
                            coincidences_by_at_block[at_block_label] = []
                        coincidences_by_at_block[at_block_label].append(camera_id)
                        image_camera_label = camera.label
                        image_camera_id = camera_id
                        image_at_block_label = at_block.label
                        image_camera_fid = camera.fid
            if number_of_coincidences == 0:
                continue
            elif number_of_coincidences > 1:
                continue # ¿error?
                # self.add_image_file(image_file_path, image_at_block_label, image_camera_label, image_camera_id)
            feature = []
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project_photogrammetry.IMAGES_FIELD_FILE
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME][defs_project_photogrammetry.IMAGES_FIELD_FILE]
            field[defs_gdal.FIELD_VALUE_TAG] = image_file_path
            feature.append(field)
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project_photogrammetry.IMAGES_FIELD_EXIF
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME][defs_project_photogrammetry.IMAGES_FIELD_EXIF]
            metadata = None
            metadata_as_json = ''
            if image_file_path in exif_data_as_dict_by_file:
                metadata = exif_data_as_dict_by_file[image_file_path]
                metadata_as_json = json.dumps(metadata, indent=4)
            field[defs_gdal.FIELD_VALUE_TAG] = metadata_as_json
            feature.append(field)
            features.append(feature)
            feature_filters= []
            filter = {}
            filter[defs_gdal.FIELD_NAME_TAG] = defs_gdal.LAYERS_FIELD_FID_FIELD_NAME
            filter[defs_gdal.FIELD_TYPE_TAG] = defs_gdal.LAYERS_FIELD_FID_FIELD_TYPE
            filter[defs_gdal.FIELD_VALUE_TAG] = image_camera_fid
            # filter[defs_gdal.FIELD_TYPE_TAG] \
            #     = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME][defs_project.IMAGES_FIELD_CAMERA_ID]
            # filter[defs_gdal.FIELD_VALUE_TAG] = camera_id
            feature_filters.append(filter)
            features_filters.append(feature_filters)
            at_block_label_by_image_file[image_file_path] = image_at_block_label
            image_file_by_camera_id[image_camera_id] = image_file_path
            exif_by_camera_id[image_camera_id] = metadata
            cont = cont + 1
        features_by_layer = {}
        features_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME] = features
        features_filters_by_layer = {}
        features_filters_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME] = features_filters
        str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
        if not str_error:
            for camera_id in image_file_by_camera_id:
                image_file_path = image_file_by_camera_id[camera_id]
                at_block_label = at_block_label_by_image_file[image_file_path]
                exif_as_dict = exif_by_camera_id[camera_id]
                camera = self.at_block_by_label[at_block_label].get_camera_from_camera_id(camera_id)
                camera.image_file_path = image_file_path
                camera.exif = exif_as_dict
        return str_error

    def add_undistort_image_files(self,
                                  files,
                                  dialog):
        str_error = ''
        features = []
        features_filters = []
        at_block_label_by_image_file = {} # to update camera before update db
        undistort_image_file_by_camera_id = {} # to update camera before update db
        for undistort_image_file_path in files:
            camera = self.get_camera_from_image_file_path(undistort_image_file_path)
            if camera: # exists
                continue
            undistort_image_file_path_lower = undistort_image_file_path.lower()
            image_db_id = -1
            image_camera_id = -1
            image_camera_fid = -1
            image_camera_label = ''
            image_at_block_label = ''
            coincidences_by_at_block = {}
            number_of_coincidences = 0
            for at_block_label in self.at_block_by_label:
                at_block = self.at_block_by_label[at_block_label]
                for camera_id in at_block.camera_by_id:
                    camera = at_block.camera_by_id[camera_id]
                    camera_label = camera.label
                    if camera_label.lower() in undistort_image_file_path_lower:
                        number_of_coincidences = number_of_coincidences + 1
                        if not at_block_label in coincidences_by_at_block:
                            coincidences_by_at_block[at_block_label] = []
                        coincidences_by_at_block[at_block_label].append(camera_id)
                        image_camera_label = camera.label
                        image_camera_id = camera_id
                        image_at_block_label = at_block.label
                        image_camera_fid = camera.fid
            if number_of_coincidences == 0:
                continue
            elif number_of_coincidences > 1:
                continue # ¿error?
                # self.add_image_file(image_file_path, image_at_block_label, image_camera_label, image_camera_id)
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project_photogrammetry.IMAGES_FIELD_UNDISTORTED_FILE
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME][defs_project_photogrammetry.IMAGES_FIELD_UNDISTORTED_FILE]
            field[defs_gdal.FIELD_VALUE_TAG] = undistort_image_file_path
            feature = []
            feature.append(field)
            features.append(feature)
            feature_filters= []
            filter = {}
            filter[defs_gdal.FIELD_NAME_TAG] = defs_gdal.LAYERS_FIELD_FID_FIELD_NAME
            filter[defs_gdal.FIELD_TYPE_TAG] = defs_gdal.LAYERS_FIELD_FID_FIELD_TYPE
            filter[defs_gdal.FIELD_VALUE_TAG] = image_camera_fid
            # filter[defs_gdal.FIELD_TYPE_TAG] \
            #     = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME][defs_project.IMAGES_FIELD_CAMERA_ID]
            # filter[defs_gdal.FIELD_VALUE_TAG] = camera_id
            feature_filters.append(filter)
            features_filters.append(feature_filters)
            at_block_label_by_image_file[undistort_image_file_path] = image_at_block_label
            undistort_image_file_by_camera_id[image_camera_id] = undistort_image_file_path
        features_by_layer = {}
        features_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME] = features
        features_filters_by_layer = {}
        features_filters_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME] = features_filters
        str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
        if not str_error:
            for camera_id in undistort_image_file_by_camera_id:
                undistort_image_file_path = undistort_image_file_by_camera_id[camera_id]
                at_block_label = at_block_label_by_image_file[undistort_image_file_path]
                camera = self.at_block_by_label[at_block_label].get_camera_from_camera_id(camera_id)
                camera.undistort_image_file_path = undistort_image_file_path
        return str_error

    def create(self, file_path, parent_widget = None):
        str_error = ''
        definition_is_saved = False
        is_process_creation = True
        # create layers
        str_error = super().create_layers(file_path = file_path)
        if str_error:
            str_error = ('Creating project for file:\n{}\nError:\n{}'
                         .format(file_path, str_error))
            return str_error, definition_is_saved
        self.file_path = file_path
        str_error, definition_is_saved = self.project_definition_gui(is_process_creation, parent_widget)
        if str_error:
            str_error = ('Project definition, error:\n{}'.format(str_error))
            return str_error, definition_is_saved
        if not definition_is_saved:
            return str_error, definition_is_saved
        return str_error, definition_is_saved

    def get_camera_from_image_file_path(self,
                                        image_file_path):
         for at_block_label in self.at_block_by_label:
             at_block = self.at_block_by_label[at_block_label]
             camera = at_block.get_camera_from_image_file_path(image_file_path)
             if camera:
                 return camera
         return None

    def import_metashape_markers(self,
                                 file_path):
        str_error = ''
        if self.metashape_markers_xml_file:
            str_error = ('Metashape markers XML file has already been imported into the project')
            return str_error
        if not os.path.exists(file_path):
            str_error = ('Not exists metashape markers XML file: {}'.format(file_path))
            return str_error
        with open(file_path, 'r', encoding='utf-8') as file:
            value_as_xml = file.read()
        try:
            value_as_dict = xmltodict.parse(value_as_xml)
        except xmltodict.expat.ExpatError as e:
            str_error = ('Parsing XML file: {}\nError:\n{}'.format(file_path, str(e)))
            return str_error
        # value_as_string = str(value_as_dict)
        # build project from xml
        if not defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG in value_as_dict:
            str_error = ('Not exists tag: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG, file_path))
            return str_error
        root = value_as_dict[defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION in root:
            str_error = ('Not exists attribute: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION, file_path))
            return str_error
        version = root[defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION]
        if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG in root:
            str_error = ('Not exists tag: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG, file_path))
            return str_error
        chunk_element = root[defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL in chunk_element:
            str_error = ('Not exists attribute: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL, file_path))
            return str_error

        # several blocks???
        at_block = ATBlockMetashape(file_path, self)
        str_error = at_block.set_from_metashape_xml(chunk_element)
        if str_error:
            return str_error
        if at_block.label in self.at_block_by_label:
            str_error = ('Exists previous chunk: {} equal label as in metashape markers XML file:\n{}'.
                         format(at_block.label, defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL, file_path))
            return str_error
        self.at_block_by_label[at_block.label] = at_block

        self.metashape_markers_xml_file = value_as_dict
        # store in db metashape markers xml
        value_as_json = json.dumps(value_as_dict, indent=4)
        features = []
        feature = []
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_NAME
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_NAME]
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project_photogrammetry.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_CONTENT
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_CONTENT]
        field[defs_gdal.FIELD_VALUE_TAG] = value_as_json
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_REMARKS
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_REMARKS]
        field[defs_gdal.FIELD_VALUE_TAG] = os.path.normpath(file_path)
        feature.append(field)
        geometry_value = None
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_GEOMETRY
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_GEOMETRY]
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project.fields_by_layer[
            defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_GEOMETRY]
        feature.append(field)
        features.append(feature)
        features_by_layer = {}
        features_by_layer[defs_project.MANAGEMENT_LAYER_NAME] = features
        str_error = GDALTools.write_features(self.file_path, features_by_layer)
        if str_error:
            return str_error
        # store in db images at_block
        features = []
        for at_block_label in self.at_block_by_label:
            at_block = self.at_block_by_label[at_block_label]
            for camera_id in at_block.camera_by_id:
                camera = at_block.camera_by_id[camera_id]
                # if camera.label != "IMG_0022_1" and camera.label != "IMG_0194_1":
                #     continue
                if "IMG_0022" in camera.label:
                    yo = 1
                feature = []
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_project_photogrammetry.IMAGES_FIELD_LABEL
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME][
                    defs_project_photogrammetry.IMAGES_FIELD_LABEL]
                field[defs_gdal.FIELD_VALUE_TAG] = camera.label
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_project_photogrammetry.IMAGES_FIELD_CHUNK_LABEL
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME][
                    defs_project_photogrammetry.IMAGES_FIELD_CHUNK_LABEL]
                field[defs_gdal.FIELD_VALUE_TAG] = at_block_label
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_project_photogrammetry.IMAGES_FIELD_CAMERA_ID
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME][
                    defs_project_photogrammetry.IMAGES_FIELD_CAMERA_ID]
                field[defs_gdal.FIELD_VALUE_TAG] = camera.id
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_project_photogrammetry.IMAGES_FIELD_ENABLED
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME][
                    defs_project_photogrammetry.IMAGES_FIELD_ENABLED]
                image_enabled = 1
                if not camera.enabled:
                    image_enabled = 0
                field[defs_gdal.FIELD_VALUE_TAG] = image_enabled
                feature.append(field)
                pc_wkb = None
                camera_pc = camera.get_pc()
                if isinstance(camera_pc, np.ndarray):
                # if camera_pc != None:
                # if camera.exists_orientation:
                    pc = [[camera_pc[0], camera_pc[1], camera_pc[2]]]
                    if at_block.crs_id != self.crs_id:
                        str_error = self.crs_tools.operation(at_block.crs_id, self.crs_id,
                                                             pc)
                        if str_error:
                            str_error = (
                                'Recovering PC in camera: {} from metashape markers XML file:\n{}\nError in CRSs operation:\n{}'.
                                format(camera.label, file_path, str_error))
                            return str_error
                    fc = pc[0][0]
                    sc = pc[0][1]
                    tc = pc[0][2]
                    point_geometry = ogr.Geometry(ogr.wkbPoint)
                    point_geometry.AddPoint(fc, sc, tc)
                    pc_wkb = point_geometry.ExportToWkb()
                else:
                    pc_wkb = defs_gdal.geometry_type_by_name['none']
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_project_photogrammetry.IMAGES_FIELD_PC_GEOM
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME][
                    defs_project_photogrammetry.IMAGES_FIELD_PC_GEOM]
                field[defs_gdal.FIELD_VALUE_TAG] = pc_wkb
                feature.append(field)
                features.append(feature)
                # features_by_layer = {}
                # features_by_layer[defs_project.IMAGES_TABLE_NAME] = features
                # str_error = GDALTools.write_features(self.file_path, features_by_layer)
                # if str_error:
                #     return str_error
        features_by_layer = {}
        features_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME] = features
        str_error = GDALTools.write_features(self.file_path, features_by_layer)
        if str_error:
            return str_error
        # update fid
        str_error = self.load_images_data_from_db(self.file_path)
        if str_error:
            return str_error
        return str_error

    def load_from_db_metashape_markers(self,
                                       value_as_dict,
                                       file_path):
        str_error = ''
        if not defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG in value_as_dict:
            str_error = ('Not exists tag: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG, file_path))
            return str_error
        root = value_as_dict[defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION in root:
            str_error = ('Not exists attribute: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION, file_path))
            return str_error
        version = root[defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION]
        if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG in root:
            str_error = ('Not exists tag: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG, file_path))
            return str_error
        chunk_element = root[defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL in chunk_element:
            str_error = ('Not exists attribute: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL, file_path))
            return str_error
        at_block = ATBlockMetashape(file_path, self)
        str_error = at_block.set_from_metashape_xml(chunk_element)
        if str_error:
            return str_error
        if at_block.label in self.at_block_by_label:
            str_error = ('Exists previous chunk: {} equal label as in metashape markers XML file:\n{}'.
                         format(at_block.label, defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL, file_path))
            return str_error
        self.metashape_markers_xml_file = value_as_dict
        self.at_block_by_label[at_block.label] = at_block
        return str_error

    def load_images_data_from_db(self,
                                 file_path):
        str_error = ''
        layer_name = defs_project_photogrammetry.IMAGES_TABLE_NAME
        fields = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_TABLE_NAME]
        fid_field_name = defs_gdal.LAYERS_FIELD_FID_FIELD_NAME
        fields[fid_field_name] = defs_gdal.LAYERS_FIELD_FID_FIELD_TYPE
        filter_fields = {}
        # filter_field_name = defs_project.MANAGEMENT_FIELD_NAME
        # filter_field_value = defs_project.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME
        # filter_fields[filter_field_name] = filter_field_value
        str_error, features = GDALTools.get_features(file_path,
                                                     layer_name,
                                                     fields,
                                                     filter_fields)
        if str_error:
            str_error += ('Getting layer {} from gpgk:\n{}\nError:\n{}'.
                          format(defs_project_photogrammetry.IMAGES_TABLE_NAME,
                                 file_path, str_error))
            return str_error
        if len(features) == 0:  # not import metashape markers xml file yet
            str_error += ('There are no features in layer {} from gpgk:\n{}'.
                          format(defs_project_photogrammetry.IMAGES_TABLE_NAME,
                                 file_path))
            return str_error
        for i in range(len(features)):
            feature = features[i]
            block_label = feature[defs_project_photogrammetry.IMAGES_FIELD_CHUNK_LABEL]
            camera_label = feature[defs_project_photogrammetry.IMAGES_FIELD_LABEL]
            if not block_label in self.at_block_by_label:
                str_error = ('Not exists block: {} for camera: {} in layer {} from gpgk:\n{}'.
                             format(block_label, camera_label, defs_project_photogrammetry.IMAGES_TABLE_NAME,
                                    file_path))
            camera_id = feature[defs_project_photogrammetry.IMAGES_FIELD_CAMERA_ID]
            camera = self.at_block_by_label[block_label].get_camera_from_camera_id(camera_id)
            if not camera:
                str_error = ('Not exists camera: {} in block: {} in layer {} from gpgk:\n{}'.
                             format(camera_label, block_label, defs_project_photogrammetry.IMAGES_TABLE_NAME,
                                    file_path))
            camera.fid = feature[defs_gdal.LAYERS_FIELD_FID_FIELD_NAME]
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_FILE]
            if value:
                camera.image_file_path = value
            enabled = True
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_ENABLED] #int
            camera.enabled = True
            if value == 0:
                camera.enabled = False
            # if value:
            #     try:
            #         int_value = int(value)
            #     except ValueError:
            #         str_error = ('Invalid value in field: {} for camera: {} in block: {} for camera: {} in layer {} from gpgk:\n{}'.
            #                      format(defs_project.IMAGES_FIELD_ENABLED, camera_label, block_label,
            #                             defs_project.IMAGES_TABLE_NAME, file_path))
            #         return str_error
            #     if int_value == 0:
            #         enabled = False
            #     camera.enabled = enabled
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_UNDISTORTED_FILE]
            if value:
                camera.undistort_image_file_path = value
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_STRING_ID]
            if value:
                camera.string_id = value
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_DATE]
            if value:
                try:
                    date = datetime.strptime(value, defs_project.DATE_STRING_FORMAT)
                    # date_str = start_date.strftime('%Y-%m-%d')
                except ValueError:
                    str_error = ('Invalid value in field: {} for camera: {} in block: {} in layer {} from gpgk:\n{}'.
                                 format(defs_project_photogrammetry.IMAGES_FIELD_DATE, camera_label, block_label,
                                        defs_project_photogrammetry.IMAGES_TABLE_NAME, file_path))
                    return str_error
                camera.date = date
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_UTC]
            if value:
                try:
                    utc = datetime.strptime(value, defs_project.TIME_STRING_FORMAT)
                    # date_str = start_date.strftime('%Y-%m-%d')
                except ValueError:
                    str_error = ('Invalid value in field: {} for camera: {} in block: {} in layer {} from gpgk:\n{}'.
                                 format(defs_project_photogrammetry.IMAGES_FIELD_UTC, camera_label, block_label,
                                        defs_project_photogrammetry.IMAGES_TABLE_NAME, file_path))
                    return str_error
                camera.utc = utc
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_SUN_AZIMUTH] # float
            camera.sun_azimuth = value
            # if value:
            #     try:
            #         float_value = float(value)
            #     except ValueError:
            #         str_error = ('Invalid value in field: {} for camera: {} in block: {} for camera: {} in layer {} from gpgk:\n{}'.
            #                      format(defs_project.IMAGES_FIELD_SUN_AZIMUTH, camera_label, block_label,
            #                             defs_project.IMAGES_TABLE_NAME, file_path))
            #         return str_error
            #     camera.sun_azimuth = float_value
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_SUN_ELEVATION] # float
            camera.sun_elevation = value
            # if value:
            #     try:
            #         float_value = float(value)
            #     except ValueError:
            #         str_error = ('Invalid value in field: {} for camera: {} in block: {} for camera: {} in layer {} from gpgk:\n{}'.
            #                      format(defs_project.IMAGES_FIELD_SUN_ELEVATION, camera_label, block_label,
            #                             defs_project.IMAGES_TABLE_NAME, file_path))
            #         return str_error
            #     camera.sun_elevation = float_value
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_SUN_GLINT]
            if value:
                camera.sun_glint = value
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_HOTSPOT]
            if value:
                camera.sun_hotspot = value
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_EXIF]
            if value:
                value_as_dict = json.loads(value)
                camera.exif = value_as_dict
            value = feature[defs_project_photogrammetry.IMAGES_FIELD_CONTENT]
            if value:
                value_as_dict = json.loads(value)
                camera.content = value_as_dict
        # load footprints
        layer_name = defs_project_photogrammetry.IMAGES_FP_TABLE_NAME
        fields = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_FP_TABLE_NAME]
        filter_fields = {}
        # filter_field_name = defs_project.MANAGEMENT_FIELD_NAME
        # filter_field_value = defs_project.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME
        # filter_fields[filter_field_name] = filter_field_value
        str_error, features = GDALTools.get_features(file_path,
                                                     layer_name,
                                                     fields,
                                                     filter_fields)
        if str_error:
            str_error += ('Getting layer {} from gpgk:\n{}\nError:\n{}'.
                          format(defs_project_photogrammetry.IMAGES_FP_TABLE_NAME,
                                 file_path, str_error))
            return str_error
        for i in range(len(features)):
            feature = features[i]
            block_label = feature[defs_project_photogrammetry.IMAGES_FP_FIELD_CHUNK_LABEL]
            camera_id = feature[defs_project_photogrammetry.IMAGES_FP_FIELD_IMAGE_ID]
            camera = self.at_block_by_label[block_label].get_camera_from_camera_id(camera_id)
            if not camera:
                str_error = ('Not exists camera id: {} in block: {} in layer {} from gpgk:\n{}'.
                             format(str(camera_id), block_label, defs_project_photogrammetry.IMAGES_FP_TABLE_NAME,
                                    file_path))
            wkb_geometry = feature[defs_project_photogrammetry.IMAGES_FP_FIELD_FP_GEOM]
            ogr_geometry = None
            try:
                ogr_geometry = ogr.CreateGeometryFromWkb(wkb_geometry)
            except Exception as e:
                str_error = ('Computing footprint for image: {}\nGDAL error:\n{}'
                             .format(camera.label, e.args[0]))
                return str_error
            camera.footprint_geometry = ogr_geometry
        # load undistorted footprints
        layer_name = defs_project_photogrammetry.IMAGES_UNDISTORTED_FP_TABLE_NAME
        fields = defs_project.fields_by_layer[defs_project_photogrammetry.IMAGES_UNDISTORTED_FP_TABLE_NAME]
        filter_fields = {}
        # filter_field_name = defs_project.MANAGEMENT_FIELD_NAME
        # filter_field_value = defs_project.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME
        # filter_fields[filter_field_name] = filter_field_value
        str_error, features = GDALTools.get_features(file_path,
                                                     layer_name,
                                                     fields,
                                                     filter_fields)
        if str_error:
            str_error += ('Getting layer {} from gpgk:\n{}\nError:\n{}'.
                          format(defs_project_photogrammetry.IMAGES_UNDISTORTED_FP_TABLE_NAME,
                                 file_path, str_error))
            return str_error
        for i in range(len(features)):
            feature = features[i]
            block_label = feature[defs_project_photogrammetry.IMAGES_UNDISTORTED_FP_FIELD_CHUNK_LABEL]
            camera_id = feature[defs_project_photogrammetry.IMAGES_UNDISTORTED_FP_FIELD_IMAGE_ID]
            camera = self.at_block_by_label[block_label].get_camera_from_camera_id(camera_id)
            if not camera:
                str_error = ('Not exists camera id: {} in block: {} in layer {} from gpgk:\n{}'.
                             format(str(camera_id), block_label, defs_project_photogrammetry.IMAGES_UNDISTORTED_FP_TABLE_NAME,
                                    file_path))
            wkb_geometry = feature[defs_project_photogrammetry.IMAGES_UNDISTORTED_FP_FIELD_FP_GEOM]
            ogr_geometry = None
            try:
                ogr_geometry = ogr.CreateGeometryFromWkb(wkb_geometry)
            except Exception as e:
                str_error = ('Loading undistorted footprint for image: {}\nGDAL error:\n{}'
                             .format(camera.label, e.args[0]))
                return str_error
            camera.undistorted_footprint_geometry = ogr_geometry

        return str_error

    def load_project(self, file_path):
        str_error = ''
        # str_error, layer_names = self.gpkg_tools.get_layers_names(file_name)
        str_error, layer_names = GDALTools.get_layers_names(file_path)
        if str_error:
            str_error = ('Loading gpgk:\n{}\nError:\n{}'.
                         format(file_path, str_error))
            return str_error
        if not defs_project.MANAGEMENT_LAYER_NAME in layer_names:
            str_error = ('Loading gpgk:\n{}\nError: not exists layer:\n{}'.
                         format(file_path, defs_project.MANAGEMENT_LAYER_NAME))
            return str_error

        str_error = super().load_project_definition(file_path = file_path)
        if str_error:
            str_error = ('Loading project definition from gpgk:\n{}\nError:\n{}'.
                         format(file_path, str_error))
            return str_error

        # To do: one case for each project type. At the moment, only metashape

        # "Metashape Markers XML File"
        layer_name = defs_project.MANAGEMENT_LAYER_NAME
        fields = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME]
        fields = {}
        field_name = defs_project.MANAGEMENT_FIELD_CONTENT
        fields[field_name] = defs_project.fields_by_layer[layer_name][field_name]
        field_name = defs_project.MANAGEMENT_FIELD_REMARKS
        fields[field_name] = defs_project.fields_by_layer[layer_name][field_name]
        filter_fields = {}
        filter_field_name = defs_project.MANAGEMENT_FIELD_NAME
        filter_field_value = defs_project_photogrammetry.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME
        filter_fields[filter_field_name] = filter_field_value
        str_error, features = GDALTools.get_features(file_path,
                                                     layer_name,
                                                     fields,
                                                     filter_fields)
        if str_error:
            str_error = ('Getting {} from management from gpgk:\n{}\nError:\n{}'.
                         format(defs_project_photogrammetry.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME,
                                file_path, str_error))
            return str_error
        # if len(features) != 1: # not import metashape markers xml file yet
        #     return str_error
        #     # str_error = ('Loading {} from management from gpgk:\n{}\nError: not one value for field: {} in layer: {}'.
        #     #              format(defs_project.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME,
        #     #                     file_name, defs_project.MANAGEMENT_FIELD_CONTENT, defs_project.MANAGEMENT_LAYER_NAME))
        #     # return str_error
        if len(features) == 1: # not import metashape markers xml file yet
            markers_xml_json_content = features[0][defs_project.MANAGEMENT_FIELD_CONTENT]
            markers_xml_file_path = features[0][defs_project.MANAGEMENT_FIELD_REMARKS]
            # json_acceptable_string = value.replace("'", "\"")
            # management_json_content = json.loads(json_acceptable_string)
            markers_xml_json_content = json.loads(markers_xml_json_content)
            str_error = self.load_from_db_metashape_markers(markers_xml_json_content,
                                                            markers_xml_file_path)
            if str_error:
                str_error = ('\nSetting metashape markers from project file:\n{}\nerror:\n{}'.format(file_path, str_error))
                return str_error

            # images
            str_error = self.load_images_data_from_db(file_path)
            if str_error:
                return str_error
        self.file_path = file_path
        return str_error

    def project_definition_gui(self,
                               is_process_creation,
                               parent_widget = None):
        return super().project_definition_gui(is_process_creation, parent_widget)

    def save(self, is_process_creation = True):
        str_error = ''
        update = True
        if is_process_creation:
            update = False
        str_aux_error = super().save_project_definition(update,
                                                        file_path = self.file_path)
        if str_aux_error:
            if not is_process_creation:
                str_error = ('Error updating project definition:\n{}'.
                             format(str_aux_error))
            else:
                str_error = ('Error saving project definition:\n{}'.
                             format(str_aux_error))
        else:
            self.is_saved = True
        return str_error

