# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

from PyQt5.QtWidgets import QApplication, QMessageBox, QDialog, QFileDialog, QPushButton, QComboBox
from PyQt5.QtCore import QDir, QFileInfo, QFile, QDate, QDateTime

import os
import sys
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
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from pyLibPhotogrammetry.defs import defs_project, defs_processes
from pyLibPhotogrammetry.defs import defs_images as defs_img
from pyLibPhotogrammetry.defs import defs_metashape_markers as defs_msm
from pyLibParameters import defs_pars
from pyLibParameters.ParametersManager import ParametersManager
from pyLibPhotogrammetry.gui.ProjectDefinitionDialog import ProjectDefinitionDialog
from pyLibPhotogrammetry.lib.ATBlockMetashape import ATBlockMetashape
from pyLibPhotogrammetry.lib.IExifTool import IExifTool

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
from pyLibQtTools import Tools
from pyLibGDAL import defs_gdal
from pyLibGDAL.GDALTools import GDALTools
from pyLibGDAL.RasterDEM import RasterDEM

class Project:
    def __init__(self,
                 qgis_iface,
                 settings):
        self.qgis_iface = qgis_iface
        self.settings = settings
        self.file_path = None
        self.project_definition = {}
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_NAME] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_TAG] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR] = None
        # self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_GEO3D_CRS] = None
        # self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_GEO2D_CRS] = None
        # self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_ECEF_CRS] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS] = defs_project.CRS_PROJECTED_DEFAULT
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS] = defs_project.CRS_VERTICAL_DEFAULT
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_DESCRIPTION] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_START_DATE] = None
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE] = None
        self.crs_id = ''
        self.crs_tools = None
        # self.gpkg_tools = None
        self.map_views = {}
        self.process_by_label = {}
        self.initialize()
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
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FIELD_FILE
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME][defs_project.IMAGES_FIELD_FILE]
            field[defs_gdal.FIELD_VALUE_TAG] = image_file_path
            feature.append(field)
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FIELD_EXIF
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME][defs_project.IMAGES_FIELD_EXIF]
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
        features_by_layer[defs_project.IMAGES_TABLE_NAME] = features
        features_filters_by_layer = {}
        features_filters_by_layer[defs_project.IMAGES_TABLE_NAME] = features_filters
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

    def add_map_view(self,
                      map_view_id,
                      map_view_wkb_geometry):
        str_error = ''
        if map_view_id in self.map_views:
            str_error = ('Exists a previous location with name: {}'.format(map_view_id))
            return str_error
        update = False
        return self.save_map_view(map_view_id,
                                  map_view_wkb_geometry,
                                  update)

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
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FIELD_UNDISTORTED_FILE
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME][defs_project.IMAGES_FIELD_UNDISTORTED_FILE]
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
        features_by_layer[defs_project.IMAGES_TABLE_NAME] = features
        features_filters_by_layer = {}
        features_filters_by_layer[defs_project.IMAGES_TABLE_NAME] = features_filters
        str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
        if not str_error:
            for camera_id in undistort_image_file_by_camera_id:
                undistort_image_file_path = undistort_image_file_by_camera_id[camera_id]
                at_block_label = at_block_label_by_image_file[undistort_image_file_path]
                camera = self.at_block_by_label[at_block_label].get_camera_from_camera_id(camera_id)
                camera.undistort_image_file_path = undistort_image_file_path
        return str_error

    def create_layer_managment(self,
                               file_path):
        str_error = ''
        for layer_name in defs_project.fields_by_layer:
            if layer_name != defs_project.MANAGEMENT_LAYER_NAME:
                continue
            layers_definition = {}
            layers_definition[layer_name] = {}
            layers_definition[layer_name] \
                = defs_project.fields_by_layer[layer_name]
            layers_crs_id = {}
            if defs_project.fields_by_layer[layer_name][defs_gdal.LAYERS_GEOMETRY_TAG] == defs_gdal.geometry_type_by_name['none']:
                layers_crs_id[layer_name] = None
            else:
                # project_crs_id =  self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
                # self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS] = defs_project.CRS_VERTICAL_DEFAULT
                layer_crs_id = self.crs_id
                layers_crs_id[layer_name] = layer_crs_id
            ignore_existing_layers = False  # create new gpkg
            create_options = defs_project.create_options
            str_error = GDALTools.create_vector(file_path,
                                                layers_definition,
                                                layers_crs_id,
                                                ignore_existing_layers,
                                                create_options)
            if str_error:
                str_error = ('Creating layer:\n{}\nin file:\n{}\nError:\n{}'.format(layer_name, file_path, str_error))
                return str_error
        self.file_path = file_path
        return str_error

    def create_layers(self,
                      file_path):
        str_error = ''
        for layer_name in defs_project.fields_by_layer:
            if layer_name == defs_project.MANAGEMENT_LAYER_NAME:
                continue
            layers_definition = {}
            layers_definition[layer_name] = {}
            layers_definition[layer_name] \
                = defs_project.fields_by_layer[layer_name]
            layers_crs_id = {}
            if defs_project.fields_by_layer[layer_name][defs_gdal.LAYERS_GEOMETRY_TAG] == defs_gdal.geometry_type_by_name['none']:
                layers_crs_id[layer_name] = None
            else:
                # project_crs_id =  self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
                # self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS] = defs_project.CRS_VERTICAL_DEFAULT
                layer_crs_id = self.crs_id
                layers_crs_id[layer_name] = layer_crs_id
            ignore_existing_layers = True  # create new gpkg
            create_options = defs_project.create_options
            str_error = GDALTools.create_vector(file_path,
                                                layers_definition,
                                                layers_crs_id,
                                                ignore_existing_layers,
                                                create_options)
            if str_error:
                str_error = ('Creating layer:\n{}\nin file:\n{}\nError:\n{}'.format(layer_name, file_path, str_error))
                return str_error
        return str_error

    # def create_locations_layer(self):
    #     str_error = ''
    #     layers_definition = {}
    #     layers_definition[defs_project.LOCATIONS_LAYER_NAME] = {}
    #     layers_definition[defs_project.LOCATIONS_LAYER_NAME] \
    #         = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME]
    #     layers_crs_id = {}
    #     layers_crs_id[defs_project.LOCATIONS_LAYER_NAME] \
    #         = self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
    #     ignore_existing_layers = True # no create new gpkg
    #     str_error = GDALTools.create_vector(self.file_path,
    #                                         layers_definition,
    #                                         layers_crs_id,
    #                                         ignore_existing_layers)
    #     return str_error

    def create_processes_layer(self):
        str_error = ''
        str_error, exists_layer = GDALTools.exists_layer(self.file_path, defs_project.PROCESESS_LAYER_NAME)
        if str_error:
            return str_error
        if exists_layer:
            return str_error
        layers_definition = {}
        layers_definition[defs_project.PROCESESS_LAYER_NAME] = {}
        layers_definition[defs_project.PROCESESS_LAYER_NAME] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME]
        layers_crs_id = {}
        layers_crs_id[defs_project.PROCESESS_LAYER_NAME] = None
        ignore_existing_layers = True # create new gpkg
        str_error = GDALTools.create_vector(self.file_path,
                                            layers_definition,
                                            layers_crs_id,
                                            ignore_existing_layers)
        return str_error

    def get_camera_from_image_file_path(self,
                                        image_file_path):
         for at_block_label in self.at_block_by_label:
             at_block = self.at_block_by_label[at_block_label]
             camera = at_block.get_camera_from_image_file_path(image_file_path)
             if camera:
                 return camera
         return None

    def get_map_views(self):
        return self.map_views.keys()

    def get_map_view_wkb_geometry(self,
                                  map_view_id):
        str_error = ''
        wkb_geometry = None
        if not map_view_id in self.map_views:
            str_error = ('Not exists location: {}'.format(map_view_id))
            return str_error
        wkb_geometry = self.map_views[map_view_id]
        return str_error, wkb_geometry

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
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME
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
                field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FIELD_LABEL
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME][
                    defs_project.IMAGES_FIELD_LABEL]
                field[defs_gdal.FIELD_VALUE_TAG] = camera.label
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FIELD_CHUNK_LABEL
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME][
                    defs_project.IMAGES_FIELD_CHUNK_LABEL]
                field[defs_gdal.FIELD_VALUE_TAG] = at_block_label
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FIELD_CAMERA_ID
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME][
                    defs_project.IMAGES_FIELD_CAMERA_ID]
                field[defs_gdal.FIELD_VALUE_TAG] = camera.id
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FIELD_ENABLED
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME][
                    defs_project.IMAGES_FIELD_ENABLED]
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
                field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FIELD_PC_GEOM
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME][
                    defs_project.IMAGES_FIELD_PC_GEOM]
                field[defs_gdal.FIELD_VALUE_TAG] = pc_wkb
                feature.append(field)
                features.append(feature)
                # features_by_layer = {}
                # features_by_layer[defs_project.IMAGES_TABLE_NAME] = features
                # str_error = GDALTools.write_features(self.file_path, features_by_layer)
                # if str_error:
                #     return str_error
        features_by_layer = {}
        features_by_layer[defs_project.IMAGES_TABLE_NAME] = features
        str_error = GDALTools.write_features(self.file_path, features_by_layer)
        if str_error:
            return str_error
        # update fid
        str_error = self.load_images_data_from_db(self.file_path)
        if str_error:
            return str_error
        return str_error

    def initialize(self):
        self.crs_tools = CRSsTools()
        epsg_crs_prefix = defs_crs.EPSG_TAG + ':'
        crs_2d_id = self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
        crs_2d_epsg_code = int(crs_2d_id.replace(epsg_crs_prefix, ''))
        self.crs_id = epsg_crs_prefix + str(crs_2d_epsg_code)
        crs_vertical_id = self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS]
        if crs_vertical_id != defs_crs.VERTICAL_ELLIPSOID_TAG:
            crs_vertical_epsg_code = int(crs_vertical_id.replace(epsg_crs_prefix, ''))
            self.crs_id += ('+' + str(crs_vertical_epsg_code))
        # self.gpkg_tools = GpkgTools(self.crs_tools)
        if self.qgis_iface:
            self.qgis_iface.set_project(self)
        return

    def load_images_data_from_db(self,
                                 file_path):
        str_error = ''
        layer_name = defs_project.IMAGES_TABLE_NAME
        fields = defs_project.fields_by_layer[defs_project.IMAGES_TABLE_NAME]
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
                          format(defs_project.IMAGES_TABLE_NAME,
                                 file_path, str_error))
            return str_error
        if len(features) == 0:  # not import metashape markers xml file yet
            str_error += ('There are no features in layer {} from gpgk:\n{}'.
                          format(defs_project.IMAGES_TABLE_NAME,
                                 file_path))
            return str_error
        for i in range(len(features)):
            feature = features[i]
            block_label = feature[defs_project.IMAGES_FIELD_CHUNK_LABEL]
            camera_label = feature[defs_project.IMAGES_FIELD_LABEL]
            if not block_label in self.at_block_by_label:
                str_error = ('Not exists block: {} for camera: {} in layer {} from gpgk:\n{}'.
                             format(block_label, camera_label, defs_project.IMAGES_TABLE_NAME,
                                    file_path))
            camera_id = feature[defs_project.IMAGES_FIELD_CAMERA_ID]
            camera = self.at_block_by_label[block_label].get_camera_from_camera_id(camera_id)
            if not camera:
                str_error = ('Not exists camera: {} in block: {} in layer {} from gpgk:\n{}'.
                             format(camera_label, block_label, defs_project.IMAGES_TABLE_NAME,
                                    file_path))
            camera.fid = feature[defs_gdal.LAYERS_FIELD_FID_FIELD_NAME]
            value = feature[defs_project.IMAGES_FIELD_FILE]
            if value:
                camera.image_file_path = value
            enabled = True
            value = feature[defs_project.IMAGES_FIELD_ENABLED] #int
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
            value = feature[defs_project.IMAGES_FIELD_UNDISTORTED_FILE]
            if value:
                camera.undistort_image_file_path = value
            value = feature[defs_project.IMAGES_FIELD_STRING_ID]
            if value:
                camera.string_id = value
            value = feature[defs_project.IMAGES_FIELD_DATE]
            if value:
                try:
                    date = datetime.strptime(value, defs_project.DATE_STRING_FORMAT)
                    # date_str = start_date.strftime('%Y-%m-%d')
                except ValueError:
                    str_error = ('Invalid value in field: {} for camera: {} in block: {} in layer {} from gpgk:\n{}'.
                                 format(defs_project.IMAGES_FIELD_DATE, camera_label, block_label,
                                        defs_project.IMAGES_TABLE_NAME, file_path))
                    return str_error
                camera.date = date
            value = feature[defs_project.IMAGES_FIELD_UTC]
            if value:
                try:
                    utc = datetime.strptime(value, defs_project.TIME_STRING_FORMAT)
                    # date_str = start_date.strftime('%Y-%m-%d')
                except ValueError:
                    str_error = ('Invalid value in field: {} for camera: {} in block: {} in layer {} from gpgk:\n{}'.
                                 format(defs_project.IMAGES_FIELD_UTC, camera_label, block_label,
                                        defs_project.IMAGES_TABLE_NAME, file_path))
                    return str_error
                camera.utc = utc
            value = feature[defs_project.IMAGES_FIELD_SUN_AZIMUTH] # float
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
            value = feature[defs_project.IMAGES_FIELD_SUN_ELEVATION] # float
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
            value = feature[defs_project.IMAGES_FIELD_SUN_GLINT]
            if value:
                camera.sun_glint = value
            value = feature[defs_project.IMAGES_FIELD_HOTSPOT]
            if value:
                camera.sun_hotspot = value
            value = feature[defs_project.IMAGES_FIELD_EXIF]
            if value:
                value_as_dict = json.loads(value)
                camera.exif = value_as_dict
            value = feature[defs_project.IMAGES_FIELD_CONTENT]
            if value:
                value_as_dict = json.loads(value)
                camera.content = value_as_dict
        # load footprints
        layer_name = defs_project.IMAGES_FP_TABLE_NAME
        fields = defs_project.fields_by_layer[defs_project.IMAGES_FP_TABLE_NAME]
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
                          format(defs_project.IMAGES_FP_TABLE_NAME,
                                 file_path, str_error))
            return str_error
        for i in range(len(features)):
            feature = features[i]
            block_label = feature[defs_project.IMAGES_FP_FIELD_CHUNK_LABEL]
            camera_id = feature[defs_project.IMAGES_FP_FIELD_IMAGE_ID]
            camera = self.at_block_by_label[block_label].get_camera_from_camera_id(camera_id)
            if not camera:
                str_error = ('Not exists camera id: {} in block: {} in layer {} from gpgk:\n{}'.
                             format(str(camera_id), block_label, defs_project.IMAGES_FP_TABLE_NAME,
                                    file_path))
            wkb_geometry = feature[defs_project.IMAGES_FP_FIELD_FP_GEOM]
            ogr_geometry = None
            try:
                ogr_geometry = ogr.CreateGeometryFromWkb(wkb_geometry)
            except Exception as e:
                str_error = ('Computing footprint for image: {}\nGDAL error:\n{}'
                             .format(camera.label, e.args[0]))
                return str_error
            camera.footprint_geometry = ogr_geometry
        # load undistorted footprints
        layer_name = defs_project.IMAGES_UNDISTORTED_FP_TABLE_NAME
        fields = defs_project.fields_by_layer[defs_project.IMAGES_UNDISTORTED_FP_TABLE_NAME]
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
                          format(defs_project.IMAGES_UNDISTORTED_FP_TABLE_NAME,
                                 file_path, str_error))
            return str_error
        for i in range(len(features)):
            feature = features[i]
            block_label = feature[defs_project.IMAGES_UNDISTORTED_FP_FIELD_CHUNK_LABEL]
            camera_id = feature[defs_project.IMAGES_UNDISTORTED_FP_FIELD_IMAGE_ID]
            camera = self.at_block_by_label[block_label].get_camera_from_camera_id(camera_id)
            if not camera:
                str_error = ('Not exists camera id: {} in block: {} in layer {} from gpgk:\n{}'.
                             format(str(camera_id), block_label, defs_project.IMAGES_UNDISTORTED_FP_TABLE_NAME,
                                    file_path))
            wkb_geometry = feature[defs_project.IMAGES_UNDISTORTED_FP_FIELD_FP_GEOM]
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

        # "Project Definition"
        layer_name = defs_project.MANAGEMENT_LAYER_NAME
        fields = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME]
        fields = {}
        field_name = defs_project.MANAGEMENT_FIELD_CONTENT
        fields[field_name] = defs_project.fields_by_layer[layer_name][field_name]
        filter_fields = {}
        filter_field_name = defs_project.MANAGEMENT_FIELD_NAME
        filter_field_value = defs_project.PROJECT_DEFINITIONS_MANAGEMENT_FIELD_NAME
        filter_fields[filter_field_name] = filter_field_value
        str_error, features = GDALTools.get_features(file_path,
                                                     layer_name,
                                                     fields,
                                                     filter_fields)
        if str_error:
            str_error = ('Getting {} from management from gpgk:\n{}\nError:\n{}'.
                         format(defs_project.PROJECT_DEFINITIONS_MANAGEMENT_FIELD_NAME,
                                file_path, str_error))
            return str_error
        if len(features) != 1:
            str_error = ('Loading {} from management from gpgk:\n{}\nError: not one value for field: {} in layer: {}'.
                         format(defs_project.PROJECT_DEFINITIONS_MANAGEMENT_FIELD_NAME,
                                file_path, defs_project.MANAGEMENT_FIELD_CONTENT, defs_project.MANAGEMENT_LAYER_NAME))
            return str_error
        value = features[0][defs_project.MANAGEMENT_FIELD_CONTENT]
        # json_acceptable_string = value.replace("'", "\"")
        # management_json_content = json.loads(json_acceptable_string)
        project_definition_json_content = json.loads(value)
        str_error = self.set_definition_from_json(project_definition_json_content)
        if str_error:
            str_error = ('\nSetting definition from json project file:\n{}\nerror:\n{}'.format(file_path, str_error))
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
        filter_field_value = defs_project.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME
        filter_fields[filter_field_name] = filter_field_value
        str_error, features = GDALTools.get_features(file_path,
                                                     layer_name,
                                                     fields,
                                                     filter_fields)
        if str_error:
            str_error = ('Getting {} from management from gpgk:\n{}\nError:\n{}'.
                         format(defs_project.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME,
                                file_path, str_error))
            return str_error
        if len(features) != 1: # not import metashape markers xml file yet
            return str_error
            # str_error = ('Loading {} from management from gpgk:\n{}\nError: not one value for field: {} in layer: {}'.
            #              format(defs_project.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME,
            #                     file_name, defs_project.MANAGEMENT_FIELD_CONTENT, defs_project.MANAGEMENT_LAYER_NAME))
            # return str_error
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

    def load_map_views_from_db(self):
        str_error = ''
        file_name = self.file_path
        # str_error, layer_names = self.gpkg_tools.get_layers_names(file_name)
        str_error, layer_names = GDALTools.get_layers_names(file_name)
        if str_error:
            str_error = ('Loading gpgk:\n{}\nError:\n{}'.
                         format(file_name, str_error))
            return str_error
        if not defs_project.LOCATIONS_LAYER_NAME in layer_names:
            str_error = ('Loading gpgk:\n{}\nError: not exists layer:\n{}'.
                         format(file_name, defs_project.LOCATIONS_LAYER_NAME))
            return str_error
        layer_name = defs_project.LOCATIONS_LAYER_NAME
        fields = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME]
        fields = {}
        field_name = defs_project.LOCATIONS_FIELD_NAME
        fields[field_name] = defs_project.fields_by_layer[layer_name][field_name]
        field_geometry = defs_project.LOCATIONS_FIELD_GEOMETRY
        fields[field_geometry] = defs_project.fields_by_layer[layer_name][field_geometry]
        filter_fields = None
        # str_error, features = self.gpkg_tools.get_features(file_name,
        #                                                    layer_name,
        #                                                    fields,
        #                                                    filter_fields)
        str_error, features = GDALTools.get_features(file_name,
                                                     layer_name,
                                                     fields,
                                                     filter_fields)
        if str_error:
            str_error = ('Getting locations from gpgk:\n{}\nError:\n{}'.
                         format(file_name, str_error))
            return str_error
        self.map_views.clear()
        for i in range(len(features)):
            name = features[i][defs_project.LOCATIONS_FIELD_NAME]
            wkb_geometry = features[i][defs_project.LOCATIONS_FIELD_GEOMETRY]
            self.map_views[name] = wkb_geometry
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

    def load_processes(self):
        str_error = ''
        str_error, layer_names = GDALTools.get_layers_names(self.file_path)
        if str_error:
            str_error = ('Loading gpgk:\n{}\nError:\n{}'.
                         format(self.file_path, str_error))
            return str_error
        if not defs_project.PROCESESS_LAYER_NAME in layer_names:
            str_error = ('Loading gpgk:\n{}\nError: not exists layer:\n{}'.
                         format(self.file_path, defs_project.MANAGEMENT_LAYER_NAME))
            return str_error
        layer_name = defs_project.PROCESESS_LAYER_NAME
        fields = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME]
        str_error, features = GDALTools.get_features(self.file_path,
                                                     layer_name,
                                                     fields)
        if str_error:
            str_error = ('Getting processes from gpgk:\n{}\nError:\n{}'.
                         format(self.file_path, str_error))
            return str_error
        for feature in features:
            process_label = feature[defs_project.PROCESESS_FIELD_LABEL]
            process_dict = {}
            for field_name in defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME]:
                if field_name == defs_project.PROCESESS_FIELD_GEOMETRY:
                    continue
                field_value = ''
                if field_name in feature:
                    field_value = feature[field_name]
                process_dict[field_name] = field_value
            if process_label in self.process_by_label:
                self.process_by_label.pop(process_label)
            self.process_by_label[process_label] = process_dict
        return str_error

    def process_gcps_accuracy_analysis(self,
                                       process):
        str_error = ''
        name = process[defs_processes.PROCESS_FIELD_NAME]
        parametes_manager = process[defs_processes.PROCESS_FIELD_PARAMETERS]
        if not defs_project.PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_PARAMETER_OUTPUT_FILE_LABEL in parametes_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_project.PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_PARAMETER_OUTPUT_FILE_LABEL))
            return str_error
        parameter_output_file = parametes_manager.parameters[defs_project.PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_PARAMETER_OUTPUT_FILE_LABEL]
        output_file_path = str(parameter_output_file)
        if not output_file_path:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name, defs_project.PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_PARAMETER_OUTPUT_FILE_LABEL))
            return str_error
        content  = 'GROUND CONTROL POINTS ACCURACY ANALYSIS'
        content += '\n======================================='
        content += '\nProject definition: '
        content += '\n- Name ..........................: ' + self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_NAME]
        content += '\n- Author ........................: ' + self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR]
        content += '\n- CRS id ........................: ' + self.crs_id
        content += '\n  Projected CRS id ..............: ' + self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
        content += '\n- Vertical CRS id ...............: ' + self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS]
        # content += '\n- Metashape markers xml file ....: ' + self.metashape_markers_xml_file
        content += '\n- Number of AT Blocks ...........: ' + str(len(self.at_block_by_label))
        for at_block_label in self.at_block_by_label:
            at_block = self.at_block_by_label[at_block_label]
            str_error, at_block_crs_is_geographic = self.crs_tools.is_geographic(at_block.crs_id)
            if str_error:
                str_error = ('For AT Block: {}, getting is geographic CRS: {}\nError:\n{}'
                             .format(at_block_label, at_block.crs_id, str_error))
                return str_error
            gcp_crs2d_precision = 4
            ellipsoid_a = ellipsoid_rf = ellipsoid_b = ellipsoid_e2 = None
            if at_block_crs_is_geographic:
                str_error, ellipsoid = self.crs_tools.get_ellipsoid(at_block.crs_id)
                if str_error:
                    str_error = ('For AT Block: {}, getting ellipsoid from CRS: {}\nError:\n{}'
                                 .format(at_block_label, at_block.crs_id, str_error))
                    return str_error
                ellipsoid_a = ellipsoid.semi_major_metre
                ellipsoid_rf = ellipsoid.inverse_flattening
                ellipsoid_b = ellipsoid.semi_minor_metre
                ellipsoid_e2 = ellipsoid.es
                gcp_crs2d_precision = 9
            content += '\nAT Block label ..................: ' + at_block.label
            content += '\n- CRS id ........................: ' + at_block.crs_id
            content += '\n- Cameras CRS id ................: ' + at_block.camera_crs_id
            content += '\n- GCPs CRS id ...................: ' + at_block.gcps_crs_id
            content += '\n- Cameras data in AT Block CRSs (only master cameras for compound cameras):'
            content += "\n      Id  Longitude.DEG   Latitude.DEG         H          X.CRS          Y.CRS          H.CRS         ECEF.X         ECEF.Y         ECEF.Z     Chunk.X     Chunk.Y     Chunk.Z  Label"
            for camera_id in at_block.camera_by_id:
                camera = at_block.camera_by_id[camera_id]
                label = camera.label
                if not isinstance(camera.pc, np.ndarray): # not orientated images
                    continue
                pc = camera.get_pc()
                pc_ecef = camera.get_pc_ecef()
                pc_chunk = camera.get_pc_chunk()
                pc_geo3d = camera.get_pc_geo3d()
                content += '\n{:>8s}'.format(str(camera.id))
                content += '{:15.9f}'.format(pc_geo3d[0])
                content += '{:15.9f}'.format(pc_geo3d[1])
                content += '{:10.4f}'.format(pc_geo3d[2])
                content += '{:15.4f}'.format(pc[0])
                content += '{:15.4f}'.format(pc[1])
                content += '{:15.4f}'.format(pc[2])
                content += '{:15.4f}'.format(pc_ecef[0])
                content += '{:15.4f}'.format(pc_ecef[1])
                content += '{:15.4f}'.format(pc_ecef[2])
                content += '{:12.4f}'.format(pc_chunk[0])
                content += '{:12.4f}'.format(pc_chunk[1])
                content += '{:12.4f}'.format(pc_chunk[2])
                content += '  {}'.format(camera.label)
            content += '\n- GCPs data in AT Block CRSs:'
            content += '\n      Id          X.CRS          Y.CRS         H         ECEF.X         ECEF.Y         ECEF.Z     Chunk.X     Chunk.Y     Chunk.Z  Label'
            gcp_label_max_length = 0
            for gcp_id in at_block.gcps_by_id:
                gcp = at_block.gcps_by_id[gcp_id]
                content += '\n{:>8s}'.format(str(gcp.id))
                content += '{:15.4f}'.format(gcp.position[0])
                content += '{:15.4f}'.format(gcp.position[1])
                content += '{:10.4f}'.format(gcp.position[2])
                content += '{:15.4f}'.format(gcp.position_ecef[0])
                content += '{:15.4f}'.format(gcp.position_ecef[1])
                content += '{:15.4f}'.format(gcp.position_ecef[2])
                content += '{:12.4f}'.format(gcp.position_chunk[0])
                content += '{:12.4f}'.format(gcp.position_chunk[1])
                content += '{:12.4f}'.format(gcp.position_chunk[2])
                content += '  {}'.format(gcp.label)
                if len(gcp.label) > gcp_label_max_length:
                    gcp_label_max_length = len(gcp.label)
            content += '\n- From object space to image space (photogrammetric backward projection), ignoring no pinned image points:'
            content += '\n  GCP.Id    Column       Row   ColumnM      RowM  ErrorC  ErrorR Error2d  Image                              Und.Column   Und.Row  Change  GCP.Label'
            for gcp_id in at_block.image_points_by_gcp_id:
                if not gcp_id in at_block.gcps_by_id:
                    continue
                gcp = at_block.gcps_by_id[gcp_id]
                gcp_chunk = gcp.position_chunk
                image_points = at_block.image_points_by_gcp_id[gcp_id]
                for i in range(len(image_points)):
                    image_point = image_points[i]
                    if not image_point.pinned:
                        continue
                    if not defs_img.IMAGE_POINT_MEASURED in image_point.values:
                        continue
                    camera = image_point.camera
                    image_point_measured_coordinates = image_point.values[defs_img.IMAGE_POINT_MEASURED]
                    column_m = image_point_measured_coordinates[0]
                    row_m = image_point_measured_coordinates[1]
                    str_error, within, withinAfterUndistortion, position_image, position_undistorted_image \
                        = camera.from_chunk_to_sensor(gcp_chunk)
                    if str_error:
                        return str_error
                    # set undistoted computed as measured for test backwar-forward model
                    image_point.set_measured_undistorted_values(position_undistorted_image)
                    error_column = column_m - position_image[0]
                    error_row = row_m - position_image[1]
                    error_2d = np.sqrt((error_column * error_column) + (error_row * error_row))
                    undistort_change_column = position_undistorted_image[0] - position_image[0]
                    undistort_change_row = position_undistorted_image[1] - position_image[1]
                    undistort_change_2d = np.sqrt(undistort_change_column ** 2. + undistort_change_row ** 2.)
                    content += '\n{:>8s}'.format(str(gcp.id))
                    content += '{:10.2f}'.format(position_image[0])
                    content += '{:10.2f}'.format(position_image[1])
                    content += '{:10.2f}'.format(column_m)
                    content += '{:10.2f}'.format(row_m)
                    content += '{:8.2f}'.format(error_column)
                    content += '{:8.2f}'.format(error_row)
                    content += '{:8.2f}'.format(error_2d)
                    content += '  {:35s}'.format(camera.label)
                    content += '{:10.2f}'.format(position_undistorted_image[0])
                    content += '{:10.2f}'.format(position_undistorted_image[1])
                    content += '{:8.2f}'.format(undistort_change_2d)
                    content += '  {:s}'.format(gcp.label)
            content += '\n- From image space to object space (photogrammetric forward projection), ignoring no pinned image points:'
            for gcp_id in at_block.image_points_by_gcp_id:
                if not gcp_id in at_block.gcps_by_id:
                    continue
                gcp = at_block.gcps_by_id[gcp_id]
                gcp_chunk = gcp.position_chunk
                image_points = at_block.image_points_by_gcp_id[gcp_id]
                image_measured_coordinates_by_camera_id = {}
                image_undistorted_coordinates_by_camera_id = {}
                number_of_measured_image_points = 0
                for i in range(len(image_points)):
                    image_point = image_points[i]
                    if not image_point.pinned:
                        continue
                    if not defs_img.IMAGE_POINT_MEASURED in image_point.values:
                        continue
                    camera = image_point.camera
                    image_point_measured_coordinates = image_point.values[defs_img.IMAGE_POINT_MEASURED]
                    image_measured_coordinates_by_camera_id[camera.id] = image_point_measured_coordinates
                    image_point_measured_undistorted_coordinates = image_point.undistorted_values[defs_img.IMAGE_POINT_MEASURED]
                    image_undistorted_coordinates_by_camera_id[camera.id] = image_point_measured_undistorted_coordinates
                    number_of_measured_image_points = number_of_measured_image_points + 1
                if number_of_measured_image_points < 2:
                    content += "\n  - GCP .........................: "
                    content += gcp.label
                    content += "\n    The point has not been measured in the minimum number of images"
                    continue
                compute_backward_camera_coordinates = True
                use_distortion = True
                use_ppa = True
                str_error, position, std_position, image_position_backward_error_by_camera_id \
                    = at_block.from_sensors_to_object(image_measured_coordinates_by_camera_id,
                                                      at_block.crs_id,
                                                      compute_backward_camera_coordinates,
                                                      use_distortion, use_ppa)
                if str_error:
                    return str_error
                error_fc = gcp.position[0] - position[0]
                error_sc = gcp.position[1] - position[1]
                error_tc = gcp.position[2] - position[2]
                if ellipsoid_a:
                    latitude = gcp.position[1] * np.pi / 180.
                    rp = ellipsoid_a / np.sqrt(1.0 - ellipsoid_e2 * np.sin(latitude) ** 2.0) * np.cos(latitude)
                    rm = ellipsoid_a * (1 - ellipsoid_e2) / ((1.0 - ellipsoid_e2 * np.sin(latitude) ** 2.0) ** 3./2.)
                    error_fc = rp * error_fc * np.pi / 180.
                    error_sc = rm * error_sc * np.pi / 180.
                content += "\n  - GCP ...........................: "
                content += gcp.label.ljust(gcp_label_max_length)
                if not ellipsoid_a:
                    content += "      X.GCPsCRS      Y.GCPsCRS      H.GCPsCRS"
                else:
                    content += "   Long.GCPsCRS    Lat.GCPsCRS      H.GCPsCRS"
                content += "\n    - Measured coordinates ........: "
                content += ('').ljust(gcp_label_max_length)
                if ellipsoid_a:
                    content += ("{:15.9f}".format(gcp.position[0]))
                    content += ("{:15.9f}".format(gcp.position[1]))
                else:
                    content += ("{:15.4f}".format(gcp.position[0]))
                    content += ("{:15.4f}".format(gcp.position[1]))
                content += ("{:15.4f}".format(gcp.position[2]))
                content += "\n    - Computed coordinates ........: "
                content += ('').ljust(gcp_label_max_length)
                if ellipsoid_a:
                    content += ("{:15.9f}".format(position[0]))
                    content += ("{:15.9f}".format(position[1]))
                else:
                    content += ("{:15.4f}".format(position[0]))
                    content += ("{:15.4f}".format(position[1]))
                content += ("{:15.4f}".format(position[2]))
                content += "\n    - Std computed coordinates ....: "
                content += ('').ljust(gcp_label_max_length)
                if ellipsoid_a:
                    content += ("{:15.9f}".format(std_position[0]))
                    content += ("{:15.9f}".format(std_position[1]))
                else:
                    content += ("{:15.4f}".format(std_position[0]))
                    content += ("{:15.4f}".format(std_position[1]))
                content += ("{:15.4f}".format(std_position[2]))
                content += "\n    - Error computed coordinates ..: "
                content += ('').ljust(gcp_label_max_length)
                if ellipsoid_a:
                    content += ("{:12.4f}(E)".format(error_fc))
                    content += ("{:12.4f}(N)".format(error_sc))
                else:
                    content += ("{:15.4f}".format(error_fc))
                    content += ("{:15.4f}".format(error_sc))
                content += ("{:15.4f}".format(error_tc))
                content += "\n   ColumnM      RowM   ColumnC      RowC  ErrorC  ErrorR Error2d  Image"
                for camera_id in image_position_backward_error_by_camera_id:
                    measured = image_measured_coordinates_by_camera_id[camera_id]
                    error_computed = image_position_backward_error_by_camera_id[camera_id]
                    error_c = error_computed[0]
                    error_r = error_computed[1]
                    error_2d = np.sqrt(error_c ** 2 + error_r ** 2)
                    camera = at_block.camera_by_id[camera_id]
                    content += '\n{:10.2f}'.format(measured[0])
                    content += '{:10.2f}'.format(measured[1])
                    content += '{:10.2f}'.format(measured[0] - error_c)
                    content += '{:10.2f}'.format(measured[1] - error_r)
                    content += '{:8.2f}'.format(error_c)
                    content += '{:8.2f}'.format(error_r)
                    content += '{:8.2f}'.format(error_2d)
                    content += '  {:s}'.format(camera.label)
                # undistorted computed image points
                compute_backward_camera_coordinates = True
                use_distortion = False
                use_ppa = True
                str_error, position, std_position, image_position_backward_error_by_camera_id \
                    = at_block.from_sensors_to_object(image_undistorted_coordinates_by_camera_id,
                                                      at_block.crs_id,
                                                      compute_backward_camera_coordinates,
                                                      use_distortion, use_ppa)
                if str_error:
                    return str_error
                error_fc = gcp.position[0] - position[0]
                error_sc = gcp.position[1] - position[1]
                error_tc = gcp.position[2] - position[2]
                if ellipsoid_a:
                    latitude = gcp.position[1] * np.pi / 180.
                    rp = ellipsoid_a / np.sqrt(1.0 - ellipsoid_e2 * np.sin(latitude) ** 2.0) * np.cos(latitude)
                    rm = ellipsoid_a * (1 - ellipsoid_e2) / ((1.0 - ellipsoid_e2 * np.sin(latitude) ** 2.0) ** 3./2.)
                    error_fc = rp * error_fc * np.pi / 180.
                    error_sc = rm * error_sc * np.pi / 180.
                content += "\n  - GCP (undistorted computed) ....: "
                content += gcp.label.ljust(gcp_label_max_length)
                if not ellipsoid_a:
                    content += "      X.GCPsCRS      Y.GCPsCRS      H.GCPsCRS"
                else:
                    content += "   Long.GCPsCRS    Lat.GCPsCRS      H.GCPsCRS"
                content += "\n    - Measured coordinates ........: "
                content += ('').ljust(gcp_label_max_length)
                if ellipsoid_a:
                    content += ("{:15.9f}".format(gcp.position[0]))
                    content += ("{:15.9f}".format(gcp.position[1]))
                else:
                    content += ("{:15.4f}".format(gcp.position[0]))
                    content += ("{:15.4f}".format(gcp.position[1]))
                content += ("{:15.4f}".format(gcp.position[2]))
                content += "\n    - Computed coordinates ........: "
                content += ('').ljust(gcp_label_max_length)
                if ellipsoid_a:
                    content += ("{:15.9f}".format(position[0]))
                    content += ("{:15.9f}".format(position[1]))
                else:
                    content += ("{:15.4f}".format(position[0]))
                    content += ("{:15.4f}".format(position[1]))
                content += ("{:15.4f}".format(position[2]))
                content += "\n    - Std computed coordinates ....: "
                content += ('').ljust(gcp_label_max_length)
                if ellipsoid_a:
                    content += ("{:15.9f}".format(std_position[0]))
                    content += ("{:15.9f}".format(std_position[1]))
                else:
                    content += ("{:15.4f}".format(std_position[0]))
                    content += ("{:15.4f}".format(std_position[1]))
                content += ("{:15.4f}".format(std_position[2]))
                content += "\n    - Error computed coordinates ..: "
                content += ('').ljust(gcp_label_max_length)
                if ellipsoid_a:
                    content += ("{:12.4f}(E)".format(error_fc))
                    content += ("{:12.4f}(N)".format(error_sc))
                else:
                    content += ("{:15.4f}".format(error_fc))
                    content += ("{:15.4f}".format(error_sc))
                content += ("{:15.4f}".format(error_tc))
                content += "\n   ColumnM      RowM   ColumnC      RowC  ErrorC  ErrorR Error2d  Image"
                for camera_id in image_position_backward_error_by_camera_id:
                    measured = image_undistorted_coordinates_by_camera_id[camera_id]
                    error_computed = image_position_backward_error_by_camera_id[camera_id]
                    error_c = error_computed[0]
                    error_r = error_computed[1]
                    error_2d = np.sqrt(error_c ** 2 + error_r ** 2)
                    camera = at_block.camera_by_id[camera_id]
                    content += '\n{:10.2f}'.format(measured[0])
                    content += '{:10.2f}'.format(measured[1])
                    content += '{:10.2f}'.format(measured[0] - error_c)
                    content += '{:10.2f}'.format(measured[1] - error_r)
                    content += '{:8.2f}'.format(error_c)
                    content += '{:8.2f}'.format(error_r)
                    content += '{:8.2f}'.format(error_2d)
                    content += '  {:s}'.format(camera.label)
        try:
            with open(output_file_path, "w") as f:
                f.write(content)
        except Exception as e:
            str_error = ('Process {}\nError occurred when opening:\n{}\nto read:\n{}'.format(name, output_file_path, e))
        return str_error

    def process_get_image_footprints(self,
                                     process,
                                     dialog):
        str_error = ''
        name = process[defs_processes.PROCESS_FIELD_NAME]
        parametes_manager = process[defs_processes.PROCESS_FIELD_PARAMETERS]
        if not defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM in parametes_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM))
            return str_error
        parameter_dem_file_path = parametes_manager.parameters[defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM]
        parameter_dem_file_as_dict = json.loads(str(parameter_dem_file_path))
        dem_file_path = parameter_dem_file_as_dict[defs_pars.TAG_FILE_PATH]
        dem_file_path = os.path.normpath(dem_file_path)
        dem_layer_index = parameter_dem_file_as_dict[defs_pars.TAG_LAYER_INDEX]
        dem_file_scale = parameter_dem_file_as_dict[defs_pars.TAG_SCALE]
        dem_file_offset = parameter_dem_file_as_dict[defs_pars.TAG_OFFSET]
        if not dem_file_path:
            str_error = ('Process: {} has a empty parameter: {}'.
                         format(name, defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM))
            return str_error
        if not os.path.exists(dem_file_path):
            str_error = ('Process: {} has a parameter: {}\ndoes not exists'.
                         format(name, defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM))
            return str_error
        if not defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM_CRS in parametes_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM_CRS))
            return str_error
        parameter_dem_crs_id = parametes_manager.parameters[defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM_CRS]
        dem_crs_id = str(parameter_dem_crs_id) # can be empty for use internal of the DEM
        # if not dem_crs_id:
        #     str_error = ('Process: {} has a empty parameter: {}'.
        #                  format(name, defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM_CRS))
        #     return str_error
        if not defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_NOP in parametes_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_NOP))
            return str_error
        parameter_nop = parametes_manager.parameters[defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_NOP]
        str_nop = str(parameter_nop)
        number_of_points_by_side = 3
        try:
            number_of_points_by_side = int(str_nop)
        except ValueError:
            str_error = ('Process: {} does not have a integer parameter: {}, is: {}'.
                         format(name, defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_NOP, str_nop))
            return str_error
        if not defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_ENABLED_IMAGES in parametes_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_ENABLED_IMAGES))
            return str_error
        parameter_enabled_images = parametes_manager.parameters[defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_ENABLED_IMAGES]
        str_enabled = str(parameter_enabled_images)
        only_enabled_images = True
        if str_enabled.casefold() == 'false':
            only_enabled_images = False
        raster_dem = None
        if not dem_file_path in self.raster_dem_by_file_path:
            raster_dem = RasterDEM(defs_project.RASTER_DEM_PRECISION_CODE)
            if dem_crs_id:
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
            self.raster_dem_by_file_path[dem_file_path] = raster_dem
        else:
            raster_dem = self.raster_dem_by_file_path[dem_file_path]
        str_error = raster_dem.load()
        if str_error:
            str_error = ('Loading in memory raster DEM from file: {}\nError:\n{}'
                         .format(dem_file_path, str_error))
            return str_error
        str_error = self.update_enabled_images_from_db()
        if str_error:
            str_error = ('Updating enabled images from file: {}\nError:\n{}'
                         .format(self.file_path, str_error))
            return str_error
        cameras_to_process = []
        for at_block_label in self.at_block_by_label:
            at_block = self.at_block_by_label[at_block_label]
            for camera_id in at_block.camera_by_id:
                camera = at_block.camera_by_id[camera_id]
                camera_enabled = camera.get_enabled() # multisensor ...
                if camera_enabled:
                    if camera.is_usefull():
                        cameras_to_process.append(camera)
        if dialog:
            dialog.processInformationGroupBox.setEnabled(True)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            dialog.processLineEdit.setText('Getting image footprints ...')
            dialog.processLineEdit.adjustSize()
            dialog.processProgressBar.setMaximum(len(cameras_to_process))
            dialog.processLineEdit.adjustSize()
            QApplication.processEvents()
        features = []
        undistorted_features = []
        for i in range(len(cameras_to_process)):
            if dialog:
                dialog.processProgressBar.setValue(i)
                QApplication.processEvents()
            camera = cameras_to_process[i]
            camera_id = camera.id
            # if camera_id < 26:
            #     continue
            str_error, footprint_wkt, undistorted_footprint_wkt = camera.compute_footprint(raster_dem,
                                                                                           number_of_points_by_side)
            if str_error:
                if dialog:
                    dialog.processProgressBar.setValue(len(cameras_to_process))
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                str_error = ('Computing footprint for image: {}\nError:\n{}'
                             .format(camera.label, str_error))
                return str_error
            footprint_geometry = None
            try:
                footprint_geometry = ogr.CreateGeometryFromWkt(footprint_wkt)
            except Exception as e:
                str_error = ('Computing footprint for image: {}\nGDAL error:\n{}'
                             .format(camera.label, e.args[0]))
                if dialog:
                    dialog.processProgressBar.setValue(len(cameras_to_process))
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                return str_error
            if not footprint_geometry.IsValid():
                str_error = ('Computing footprint for image: {}\nInvalid geometry'.format(camera.label))
                if dialog:
                    dialog.processProgressBar.setValue(len(cameras_to_process))
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                return str_error
            footprint_geometry_wkb = None
            try:
                footprint_geometry_wkb = footprint_geometry.ExportToWkb()
            except Exception as e:
                str_error = ('Exporting to WKB computed footprint for image: {}\nGDAL error:\n{}'
                             .format(camera.label, e.args[0]))
                if dialog:
                    dialog.processProgressBar.setValue(len(cameras_to_process))
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                return str_error
            undistorted_footprint_geometry = None
            try:
                undistorted_footprint_geometry = ogr.CreateGeometryFromWkt(undistorted_footprint_wkt)
            except Exception as e:
                str_error = ('Computing undistorted footprint for image: {}\nGDAL error:\n{}'
                             .format(camera.label, e.args[0]))
                if dialog:
                    dialog.processProgressBar.setValue(len(cameras_to_process))
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                return str_error
            if not undistorted_footprint_geometry.IsValid():
                str_error = ('Computing undistorted footprint for image: {}\nInvalid geometry'.format(camera.label))
                if dialog:
                    dialog.processProgressBar.setValue(len(cameras_to_process))
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                return str_error
            undistorted_footprint_geometry_wkb = None
            try:
                undistorted_footprint_geometry_wkb = undistorted_footprint_geometry.ExportToWkb()
            except Exception as e:
                str_error = ('Exporting to WKB computed undistorted footprint for image: {}\nGDAL error:\n{}'
                             .format(camera.label, e.args[0]))
                if dialog:
                    dialog.processProgressBar.setValue(len(cameras_to_process))
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                return str_error
            feature = []
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FP_FIELD_CHUNK_LABEL
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_FP_TABLE_NAME][
                defs_project.IMAGES_FP_FIELD_CHUNK_LABEL]
            field[defs_gdal.FIELD_VALUE_TAG] = camera.at_block.label
            feature.append(field)
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FP_FIELD_IMAGE_ID
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_FP_TABLE_NAME][
                defs_project.IMAGES_FP_FIELD_IMAGE_ID]
            field[defs_gdal.FIELD_VALUE_TAG] = camera.id
            feature.append(field)
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FP_FIELD_IMAGE_FILE_NAME
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_FP_TABLE_NAME][
                defs_project.IMAGES_FP_FIELD_IMAGE_FILE_NAME]
            field[defs_gdal.FIELD_VALUE_TAG] = camera.image_file_path
            feature.append(field)
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_FP_FIELD_FP_GEOM
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_FP_TABLE_NAME][
                defs_project.IMAGES_FP_FIELD_FP_GEOM]
            field[defs_gdal.FIELD_VALUE_TAG] = footprint_geometry_wkb
            feature.append(field)
            features.append(feature)
            # undistorted
            feature = []
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_UNDISTORTED_FP_FIELD_CHUNK_LABEL
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_UNDISTORTED_FP_TABLE_NAME][
                defs_project.IMAGES_UNDISTORTED_FP_FIELD_CHUNK_LABEL]
            field[defs_gdal.FIELD_VALUE_TAG] = camera.at_block.label
            feature.append(field)
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_UNDISTORTED_FP_FIELD_IMAGE_ID
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_UNDISTORTED_FP_TABLE_NAME][
                defs_project.IMAGES_UNDISTORTED_FP_FIELD_IMAGE_ID]
            field[defs_gdal.FIELD_VALUE_TAG] = camera.id
            feature.append(field)
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_UNDISTORTED_FP_FIELD_IMAGE_FILE_NAME
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_UNDISTORTED_FP_TABLE_NAME][
                defs_project.IMAGES_UNDISTORTED_FP_FIELD_IMAGE_FILE_NAME]
            field[defs_gdal.FIELD_VALUE_TAG] = camera.undistort_image_file_path
            feature.append(field)
            field = {}
            field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_UNDISTORTED_FP_FIELD_FP_GEOM
            field[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.IMAGES_UNDISTORTED_FP_TABLE_NAME][
                defs_project.IMAGES_UNDISTORTED_FP_FIELD_FP_GEOM]
            field[defs_gdal.FIELD_VALUE_TAG] = undistorted_footprint_geometry_wkb
            feature.append(field)
            undistorted_features.append(feature)
            self.footprint_geometry = footprint_geometry
            self.undistorted_footprint_geometry = undistorted_footprint_geometry
        if dialog:
            dialog.processProgressBar.setValue(len(cameras_to_process))
            dialog.processInformationGroupBox.setEnabled(False)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            QApplication.processEvents()
        features_by_layer = {}
        features_by_layer[defs_project.IMAGES_FP_TABLE_NAME] = features
        str_error = GDALTools.write_features(self.file_path, features_by_layer)
        if str_error:
            str_error = ('Error storing footprints:\n{}'.format(str_error))
            return str_error
        features_by_layer = {}
        features_by_layer[defs_project.IMAGES_UNDISTORTED_FP_TABLE_NAME] = undistorted_features
        str_error = GDALTools.write_features(self.file_path, features_by_layer)
        if str_error:
            str_error = ('Error storing footprints:\n{}'.format(str_error))
            return str_error
        return str_error



    def project_definition_gui(self,
                               is_process_creation):
        str_error = ""
        definition_is_saved = False
        title = defs_project.PROJECT_DEFINITION_DIALOG_TITLE
        dialog = ProjectDefinitionDialog(self, title, is_process_creation)
        dialog_result = dialog.exec()
        definition_is_saved = dialog.is_saved
        if dialog_result != QDialog.Accepted:
            return str_error, definition_is_saved
        return str_error, definition_is_saved

    def remove_map_view(self,
                        map_view_id):
        str_error = ''
        if not map_view_id in self.map_views:
            str_error = ('Not exists location with name: {}'.format(map_view_id))
            return str_error
        features_filters = []
        feature_filters = []
        filter = {}
        filter[defs_gdal.FIELD_NAME_TAG] = defs_project.LOCATIONS_FIELD_NAME
        filter[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME][defs_project.LOCATIONS_FIELD_NAME]
        filter[defs_gdal.FIELD_VALUE_TAG] = map_view_id
        feature_filters.append(filter)
        features_filters.append(feature_filters)
        features_filters_by_layer = {}
        features_filters_by_layer[defs_project.LOCATIONS_LAYER_NAME] = features_filters
        return GDALTools.remove_features(self.file_path, features_filters_by_layer)

    def remove_process(self,
                       process_label):
        str_error = ''
        features_filters = []
        feature_filters = []
        filter = {}
        filter[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LABEL
        filter[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LABEL]
        filter[defs_gdal.FIELD_VALUE_TAG] = process_label
        feature_filters.append(filter)
        features_filters.append(feature_filters)
        features_filters_by_layer = {}
        features_filters_by_layer[defs_project.PROCESESS_LAYER_NAME] = features_filters
        str_error = GDALTools.remove_features(self.file_path, features_filters_by_layer)
        if not str_error:
            self.process_by_label.pop(process_label)
        return str_error

    def run_library_process(self,
                            process,
                            dialog):
        str_error = ''
        process_name = process[defs_processes.PROCESS_FIELD_NAME]
        if process[
            defs_processes.PROCESS_FIELD_SRC].casefold() != defs_processes.PROCESSES_SRC_TYPE_LIBRARY_FUNCTION.casefold():
            str_error = ('Process: {} has a field: {} not equal to: {}'
                         .format(process_name, defs_processes.PROCESS_FIELD_SRC,
                                 defs_processes.PROCESSES_SRC_TYPE_LIBRARY_FUNCTION))
            return str_error
        find_funtion = False
        if process_name.casefold() == defs_project.PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_NAME.casefold():
            find_funtion = True
            str_error = self.process_gcps_accuracy_analysis(process)
            if str_error:
                return str_error
        elif process_name.casefold() == defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_NAME.casefold():
            find_funtion = True
            str_error = self.process_get_image_footprints(process, dialog)
            if str_error:
                return str_error
        if not find_funtion:
            str_error = ('Not exists process: {}'
                         .format(process_name))
        return str_error

    def save_map_view(self,
                      map_view_id,
                      map_view_wkb_geometry,
                      update = False):
        str_error = ""
        features = []
        feature = []
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.LOCATIONS_FIELD_NAME
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME][defs_project.LOCATIONS_FIELD_NAME]
        field[defs_gdal.FIELD_VALUE_TAG] = map_view_id
        feature.append(field)
        # field = {}
        # field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_CONTENT
        # field[defs_gdal.FIELD_TYPE_TAG] \
        #     = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME][defs_project.MANAGEMENT_FIELD_CONTENT]
        # field[defs_gdal.FIELD_VALUE_TAG] = value_as_string
        # feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.LOCATIONS_FIELD_GEOMETRY
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME][defs_project.LOCATIONS_FIELD_GEOMETRY]
        field[defs_gdal.FIELD_VALUE_TAG] = map_view_wkb_geometry
        feature.append(field)
        features.append(feature)
        features_by_layer = {}
        features_by_layer[defs_project.LOCATIONS_LAYER_NAME] = features
        if not update:
            str_error = GDALTools.write_features(self.file_path, features_by_layer)
            # str_error = self.gpkg_tools.write(self.file_name,
            #                                   features_by_layer)
        else:
            features_filters = []
            feature_filters= []
            filter = {}
            filter[defs_gdal.FIELD_NAME_TAG] = defs_project.LOCATIONS_FIELD_NAME
            filter[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.LOCATIONS_LAYER_NAME][defs_project.LOCATIONS_FIELD_NAME]
            filter[defs_gdal.FIELD_VALUE_TAG] = map_view_id
            feature_filters.append(filter)
            features_filters.append(feature_filters)
            features_filters_by_layer = {}
            features_filters_by_layer[defs_project.LOCATIONS_LAYER_NAME] = features_filters
            str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
            # str_error = self.gpkg_tools.update(self.file_name,
            #                                    features_by_layer,
            #                                    features_filters_by_layer)
        return str_error

    def save_management(self,
                        update = False):
        str_error = ""
        # value_as_string = str(self.project_definition)
        value_as_json = json.dumps(self.project_definition, indent=4)
        features = []
        feature = []
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_NAME
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_NAME]
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project.PROJECT_DEFINITIONS_MANAGEMENT_FIELD_NAME
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_CONTENT
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_CONTENT]
        field[defs_gdal.FIELD_VALUE_TAG] = value_as_json
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
        if not update:
            str_error = GDALTools.write_features(self.file_path, features_by_layer)
            # str_error = self.gpkg_tools.write(self.file_name,
            #                                   features_by_layer)
        else:
            features_filters = []
            feature_filters= []
            filter = {}
            filter[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_NAME
            filter[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_NAME]
            filter[defs_gdal.FIELD_VALUE_TAG] = defs_project.PROJECT_DEFINITIONS_MANAGEMENT_FIELD_NAME
            feature_filters.append(filter)
            features_filters.append(feature_filters)
            features_filters_by_layer = {}
            features_filters_by_layer[defs_project.MANAGEMENT_LAYER_NAME] = features_filters
            str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
            # str_error = self.gpkg_tools.update(self.file_name,
            #                                    features_by_layer,
            #                                    features_filters_by_layer)
        return str_error

    def save_process(self,
                     process_content,
                     process_author,
                     process_label,
                     process_description,
                     process_log,
                     process_date_time_as_string,
                     process_output,
                     process_remarks):
        str_error = ''
        # if map_view_id in self.map_views:
        #     str_error = ('Exists a previous location with name: {}'.format(map_view_id))
        #     return str_error
        features = []
        feature = []
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LABEL
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LABEL]
        field[defs_gdal.FIELD_VALUE_TAG] = process_label
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_AUTHOR
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_AUTHOR]
        field[defs_gdal.FIELD_VALUE_TAG] = process_author
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_DESCRIPTION
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_DESCRIPTION]
        field[defs_gdal.FIELD_VALUE_TAG] = process_description
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_DATE_TIME
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_DATE_TIME]
        field[defs_gdal.FIELD_VALUE_TAG] = process_date_time_as_string
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_PROCESS_CONTENT
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_PROCESS_CONTENT]
        field[defs_gdal.FIELD_VALUE_TAG] = process_content
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LOG
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LOG]
        field[defs_gdal.FIELD_VALUE_TAG] = process_log
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_OUTPUT
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_OUTPUT]
        field[defs_gdal.FIELD_VALUE_TAG] = process_output
        feature.append(field)
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_REMARKS
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_REMARKS]
        field[defs_gdal.FIELD_VALUE_TAG] = process_remarks
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_GEOMETRY
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_GEOMETRY]
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project.fields_by_layer[
            defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_GEOMETRY]
        feature.append(field)
        features.append(feature)
        features_by_layer = {}
        features_by_layer[defs_project.PROCESESS_LAYER_NAME] = features
        if not process_label in self.process_by_label:
            str_error = GDALTools.write_features(self.file_path, features_by_layer)
            # str_error = self.gpkg_tools.write(self.file_name,
            #                                   features_by_layer)
            if not str_error:
                self.process_by_label[process_label] = {}
        else:
            features_filters = []
            feature_filters= []
            filter = {}
            filter[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LABEL
            filter[defs_gdal.FIELD_TYPE_TAG] \
                = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LABEL]
            filter[defs_gdal.FIELD_VALUE_TAG] = process_label
            feature_filters.append(filter)
            features_filters.append(feature_filters)
            features_filters_by_layer = {}
            features_filters_by_layer[defs_project.PROCESESS_LAYER_NAME] = features_filters
            str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
        if not str_error:
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_LABEL] = process_label
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_AUTHOR] = process_author
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_DESCRIPTION] = process_description
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_DATE_TIME] = process_date_time_as_string
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_PROCESS_CONTENT] = process_content
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_LOG] = process_log
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_OUTPUT] = process_output
            self.process_by_label[process_label][defs_project.PROCESESS_FIELD_REMARKS] = process_remarks
        return str_error

    def set_definition_from_json(self, json_content):
        str_error = ''
        if not defs_project.PROJECT_DEFINITIONS_TAG_NAME in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_NAME,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_TAG in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_TAG,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_START_DATE in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_START_DATE,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        if not defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE in json_content:
            str_error = ("No {} in json content {}".format(defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE,
                                                           defs_project.PROJECT_DEFINITIONS_TAG))
            return str_error
        name = json_content[defs_project.PROJECT_DEFINITIONS_TAG_NAME]
        tag = json_content[defs_project.PROJECT_DEFINITIONS_TAG_TAG]
        author = json_content[defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR]
        crs_projected_id = json_content[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
        crs_vertical_id = json_content[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS]
        output_path = json_content[defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH]
        description = json_content[defs_project.PROJECT_DEFINITIONS_TAG_DESCRIPTION]
        start_date = json_content[defs_project.PROJECT_DEFINITIONS_TAG_START_DATE]
        if start_date:
            date_start_date = QDate.fromString(start_date, defs_project.QDATE_TO_STRING_FORMAT)
            if not date_start_date.isValid():
                str_error = ("Invalid date: {} for format: {}".format(start_date, defs_project.QDATE_TO_STRING_FORMAT))
                return str_error
        finish_date = json_content[defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE]
        if finish_date:
            date_finish_date = QDate.fromString(finish_date, defs_project.QDATE_TO_STRING_FORMAT)
            if not date_finish_date.isValid():
                str_error = ("Invalid date: {} for format: {}".format(finish_date, defs_project.QDATE_TO_STRING_FORMAT))
                return str_error
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_NAME] = name
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_TAG] = tag
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR] = author
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS] = crs_projected_id
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS] = crs_vertical_id
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH] = output_path
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_DESCRIPTION] = description
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_START_DATE] = start_date
        self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE] = finish_date
        epsg_crs_prefix = defs_crs.EPSG_TAG + ':'
        crs_2d_id = self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
        crs_2d_epsg_code = int(crs_2d_id.replace(epsg_crs_prefix, ''))
        self.crs_id = epsg_crs_prefix + str(crs_2d_epsg_code)
        crs_vertical_id = self.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS]
        if crs_vertical_id != defs_crs.VERTICAL_ELLIPSOID_TAG:
            crs_vertical_epsg_code = int(crs_vertical_id.replace(epsg_crs_prefix, ''))
            self.crs_id += ('+' + str(crs_vertical_epsg_code))

    def update_map_view(self,
                        map_view_id,
                        map_view_wkb_geometry):
        str_error = ''
        if not map_view_id in self.map_views:
            str_error = ('Not exists location with name: {}'.format(map_view_id))
            return str_error
        update = True
        return self.save_map_view(map_view_id,
                                  map_view_wkb_geometry,
                                  update)

    def update_enabled_images_from_db(self):
        str_error = ''
        layer_name = defs_project.IMAGES_TABLE_NAME
        camera_label_field_name = defs_project.IMAGES_FIELD_LABEL
        block_label_field_name = defs_project.IMAGES_FIELD_CHUNK_LABEL
        camera_id_field_name = defs_project.IMAGES_FIELD_CAMERA_ID
        enabled_field_name = defs_project.IMAGES_FIELD_ENABLED
        fields = {}
        fields[camera_label_field_name] = defs_project.fields_by_layer[layer_name][camera_label_field_name]
        fields[block_label_field_name] = defs_project.fields_by_layer[layer_name][block_label_field_name]
        fields[camera_id_field_name] = defs_project.fields_by_layer[layer_name][camera_id_field_name]
        fields[enabled_field_name] = defs_project.fields_by_layer[layer_name][enabled_field_name]
        fid_field_name = defs_gdal.LAYERS_FIELD_FID_FIELD_NAME
        fields[fid_field_name] = defs_gdal.LAYERS_FIELD_FID_FIELD_TYPE
        filter_fields = {}
        # filter_field_name = defs_project.MANAGEMENT_FIELD_NAME
        # filter_field_value = defs_project.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME
        # filter_fields[filter_field_name] = filter_field_value
        str_error, features = GDALTools.get_features(self.file_path,
                                                     layer_name,
                                                     fields,
                                                     filter_fields)
        if str_error:
            str_error += ('Getting layer {} from gpgk:\n{}\nError:\n{}'.
                          format(defs_project.IMAGES_TABLE_NAME,
                                 self.file_path, str_error))
            return str_error
        if len(features) == 0:  # not import metashape markers xml file yet
            str_error += ('There are no features in layer {} from gpgk:\n{}'.
                          format(defs_project.IMAGES_TABLE_NAME,
                                 self.file_path))
            return str_error
        for i in range(len(features)):
            feature = features[i]
            block_label = feature[defs_project.IMAGES_FIELD_CHUNK_LABEL]
            camera_label = feature[defs_project.IMAGES_FIELD_LABEL]
            if not block_label in self.at_block_by_label:
                str_error = ('Not exists block: {} for camera: {} in layer {} from gpgk:\n{}'.
                             format(block_label, camera_label, defs_project.IMAGES_TABLE_NAME,
                                    self.file_path))
            camera_id = feature[defs_project.IMAGES_FIELD_CAMERA_ID]
            camera = self.at_block_by_label[block_label].get_camera_from_camera_id(camera_id)
            if not camera:
                str_error = ('Not exists camera: {} in block: {} in layer {} from gpgk:\n{}'.
                             format(camera_label, block_label, defs_project.IMAGES_TABLE_NAME,
                                    self.file_path))
            # camera.fid = feature[defs_gdal.LAYERS_FIELD_FID_FIELD_NAME]
            value = feature[defs_project.IMAGES_FIELD_ENABLED]
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
        return str_error

    def update_process(self,
                       original_process_label,
                       process_label): # is modified in self.processes
        str_error = ''
        if not process_label in self.process_by_label:
            str_error = ('Not exists process: {}'.format(process_label))
            return str_error
        features = []
        feature = []
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LABEL
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LABEL]
        field[defs_gdal.FIELD_VALUE_TAG] = process_label
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_AUTHOR
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_AUTHOR]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_AUTHOR]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_DESCRIPTION
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_DESCRIPTION]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_DESCRIPTION]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_DATE_TIME
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_DATE_TIME]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_DATE_TIME]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_PROCESS_CONTENT
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_PROCESS_CONTENT]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_PROCESS_CONTENT]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LOG
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LOG]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_LOG]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_REMARKS
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_REMARKS]
        field[defs_gdal.FIELD_VALUE_TAG] = self.process_by_label[process_label][defs_project.PROCESESS_FIELD_REMARKS]
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_GEOMETRY
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_GEOMETRY]
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project.fields_by_layer[
            defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_GEOMETRY]
        feature.append(field)
        features.append(feature)
        features_by_layer = {}
        features_by_layer[defs_project.PROCESESS_LAYER_NAME] = features
        features_filters = []
        feature_filters = []
        filter = {}
        filter[defs_gdal.FIELD_NAME_TAG] = defs_project.PROCESESS_FIELD_LABEL
        filter[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.PROCESESS_LAYER_NAME][defs_project.PROCESESS_FIELD_LABEL]
        filter[defs_gdal.FIELD_VALUE_TAG] = original_process_label
        feature_filters.append(filter)
        features_filters.append(feature_filters)
        features_filters_by_layer = {}
        features_filters_by_layer[defs_project.PROCESESS_LAYER_NAME] = features_filters
        str_error = GDALTools.update_features(self.file_path, features_by_layer, features_filters_by_layer)
        return str_error
