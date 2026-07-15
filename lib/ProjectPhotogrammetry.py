# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
from numpy.core.multiarray import array_function_from_c_func_and_dispatcher
from qgis.PyQt.QtWidgets import QApplication, QMessageBox, QDialog, QFileDialog, QPushButton, QComboBox
from qgis.PyQt.QtCore import QDir, QFileInfo, QFile, QDate, QDateTime

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
import copy
import quaternion

from osgeo import gdal, osr, ogr
gdal.UseExceptions()

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))

from qgis.PyQt.QtCore import QDir, QFileInfo, QFile, QDate, QDateTime

# common_libs_absolute_path = os.path.join(current_path, defs_paths.COMMON_LIBS_RELATIVE_PATH)
# sys.path.append(common_libs_absolute_path)

from pyLibProject.defs import defs_project_definition
from pyLibProject.lib.Project import Project
# from pyLibProject.defs import defs_project
# from pyLibProject.defs import defs_layers_groups
# from pyLibProject.defs import defs_layers
from pyLibProcesses.defs import defs_project as processes_defs_project
from pyLibProcesses.defs import defs_processes as processes_defs_processes
# from pyLibPhotogrammetry.defs import defs_project as defs_project_lib
# from pyLibPhotogrammetry.defs import defs_project_photogrammetry as defs_project_photogrammetry
from pyLibPhotogrammetry.defs import defs_project as defs_project
from pyLibPhotogrammetry.defs import defs_processes
from pyLibPhotogrammetry.defs import defs_images as defs_img
from pyLibPhotogrammetry.defs import defs_metashape_markers as defs_msm
from pyLibPhotogrammetry.defs import defs_graphos as defs_gr
from pyLibParameters import defs_pars
from pyLibParameters.ParametersManager import ParametersManager
from pyLibProject.gui.ProjectDefinitionDialog import ProjectDefinitionDialog
# from pyLibPhotogrammetry.gui.ProjectDefinitionDialog import ProjectDefinitionDialog
from pyLibPhotogrammetry.lib.ATBlockMetashape import ATBlockMetashape
from pyLibPhotogrammetry.lib.ATBlockGraphos import ATBlockGraphos
from pyLibPhotogrammetry.lib.IExifTool import IExifTool
from pyLibPhotogrammetry.lib.computations import *
from pyLibPhotogrammetry.lib.ObjectPointMetashape import ObjectPointMetashape

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibCRSs.CRSsTools import CRSsTools
from pyLibQtTools import Tools
from pyLibGDAL import defs_gdal
from pyLibGDAL.GDALTools import GDALTools
from pyLibGDAL.RasterDEM import RasterDEM
from pyLibOpenCV.OpenCVTools import OpenCVTools
from pyLibOpenCV.IOpenCV import warp_perspective

class ProjectPhotogrammetry(Project):
    def __init__(self, qgis_iface, settings, crs_tools):
        super().__init__(qgis_iface, settings, crs_tools)
        self.file_path = None
        self.is_graphos_model = False
        self.is_metashape_model = True
        self.xml_file_content = None
        self.at_block_by_label = {}
        self.raster_dem_by_file_path = {}
        self.opencv_tools = None
        self.digitizing_parameters = None

        self.spUnionMinFc = None
        self.spUnionMinSc = None
        self.spUnionMaxFc = None
        self.spUnionMaxSc = None
        self.stereopair_union_geometry = None
        self.imagesMaximumRamMBsBySize = {}
        self.imagesTileRamMBsBySize = {}
        self.imagesTilesImagesIdBySize = {}
        self.geometryTileBySize = {}
        self.spObjectGeometryByImagesIds = {}
        self.spImageGeometryByImagesIds = {}
        self.spUndistortedImageGeometryByImagesIds = {}
        self.spEpipolarEnvelopeByImagesIds = {}
        self.homographyMatrixByCamerasId = {}
        self.inverseHomographyMatrixByCamerasId = {}
        self.epipolarFileNameByCamerasId = {}
        self.process_set_digitizing_parameters = None
        # self.edition_start_msec = None
        # self.object_point_by_id_by_chunk_label = {}
        self.object_point_by_id = {}
        self.object_by_fully_qualified_name = {}
        self.point_id = 0 # starting in 1 when add first point

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

    def add_object_point_from_object_space(self,
                                           point_coordinates,
                                           crs_id,
                                           use_dem):
        str_error = ''
        point_id = None
        if not self.is_metashape_model:
            str_error = ('Algorithm add object point is only valid for projects of type metashape')
            return str_error, point_id
        if not isinstance(point_coordinates, list):
            str_error = ('Point object space coordinates must be a list with two or three values')
            return str_error, point_id
        if len(point_coordinates) < 2:
            str_error = ('Point object space coordinates must be a list with two or three values')
            return str_error, point_id
        if len(self.at_block_by_label) > 1:
            str_error = ('Algorithm add object point is only valid for one AT block')
            return str_error, end_date_time, log
        at_block_label = list(self.at_block_by_label.keys())[0]
        at_block = self.at_block_by_label[at_block_label]
        exists_height = False
        if len(point_coordinates) == 3:
            exists_height = True
        if not exists_height and not use_dem:
            str_error = ('Adding object point, invalid option: no height and no use DSM')
            return str_error, point_id
        # digitizing parameters
        if self.process_set_digitizing_parameters is None:
            process_set_digitizing_parameters_name = defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_NAME
            process_set_digitizing_parameters = None
            process_provider = None
            for process_provider in self.processes_manager.processes_by_provider:
                if process_set_digitizing_parameters_name in self.processes_manager.processes_by_provider[process_provider]:
                    self.process_set_digitizing_parameters = self.processes_manager.processes_by_provider[
                        process_provider][process_set_digitizing_parameters_name]
                    break
            if self.process_set_digitizing_parameters is None:
                str_error = ('Adding object point, not found process: {}'
                             .format(process_set_digitizing_parameters_name))
                return str_error, point_id
        str_error, end_date_time, log = self.set_digitizing_parameters(self.process_set_digitizing_parameters)
        if str_error:
            return str_error, point_id
        str_error, point_id = at_block.add_object_point_from_object_space(point_coordinates, crs_id, use_dem,
                                                                          self.digitizing_parameters)
        return str_error, point_id
        # raster_dem = None
        # raster_dem_crs_id = None
        # fc = point_coordinates[0]
        # sc = point_coordinates[1]
        # tc = None
        # if use_dem:
        #     dem_file_path = self.digitizing_parameters[
        #         defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM]
        #     if not dem_file_path in self.raster_dem_by_file_path:
        #         raster_dem = RasterDEM(defs_project.RASTER_DEM_PRECISION_CODE)
        #         dem_crs_id = self.digitizing_parameters[
        #             defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM_CRS]
        #         if dem_crs_id: # can be empty for use internal of the DEM
        #             str_error = raster_dem.set_crs_id_by_user(dem_crs_id)
        #             if str_error:
        #                 str_error = ('Adding object point, setting CRS to raster DEM from file: {}\nError:\n{}'
        #                              .format(dem_file_path, str_error))
        #                 return str_error, point_id
        #         str_error = raster_dem.set_from_file(dem_file_path)
        #         if str_error:
        #             str_error = ('Adding object point, setting raster DEM from file: {}\nError:\n{}'
        #                          .format(dem_file_path, str_error))
        #             return str_error, point_id
        #         raster_dem.set_check_domain(False) # get solution for out points
        #         self.raster_dem_by_file_path[dem_file_path] = raster_dem
        #     else:
        #         raster_dem = self.raster_dem_by_file_path[dem_file_path]
        #     str_error = raster_dem.load()
        #     if str_error:
        #         str_error = ('Adding object point, loading in memory raster DEM from file: {}\nError:\n{}'
        #                      .format(dem_file_path, str_error))
        #         return str_error, point_id
        #     raster_dem_crs_id = raster_dem.get_crs_id()
        #     if raster_dem_crs_id.casefold() != at_block.crs_id.casefold():
        #         pto = [[fc, sc, 0.]]
        #         str_error = self.crs_tools.operation(at_block.crs_id, raster_dem_crs_id,
        #                                              pto)
        #         if str_error:
        #             str_error += ('Adding object point from object space')
        #             str_error += ('\nFrom AT Block CRS: {} to CRS: {}\nfor point: [{:.3f}, {:.3f}]\nerror:\n{}'.
        #                           format(at_block.crs_id, raster_dem_crs_id,
        #                                  fc, sc, str_error))
        #             return str_error, point_id
        #         fc = pto[0][0]
        #         sc = pto[0][1]
        #     str_error, elevation, point_out_edge, is_no_data = raster_dem.get_elevation(fc, sc)
        #     if str_error:
        #         str_error += ('Adding object point from object space')
        #         str_error += ('\nGetting height from dem:\n{}\nfor point: ({:3.f}, {:.3f})\nerror:\n:{}'.
        #                       format(dem_file_path, fc, sc, str_error))
        #         return str_error, point_id
        # else:
        #     tc = point_coordinates[2]
        # point_id = int(QDateTime.currentDateTime().toMSecsSinceEpoch() - self.edition_start_msec)
        # if point_id in self.object_point_by_id:
        #     str_error = ('Adding object point, exists previous object point: {}'
        #                  .format(str(point_id)))
        #     return str_error, None
        # object_point = ObjectPointMetashape(at_block)
        # self.object_point_by_id[point_id] = object_point




        return str_error, point_id

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

    def exists_footprints(self):
        exists_footprints = True
        for at_block_label in self.at_block_by_label:
            if not self.at_block_by_label[at_block_label].exists_footprints():
                exists_footprints = False
                break
        return exists_footprints

    def exists_footprints_undistorted(self):
        exists_footprints = True
        for at_block_label in self.at_block_by_label:
            if not self.at_block_by_label[at_block_label].exists_footprints_undistorted():
                exists_footprints = False
                break
        return exists_footprints

    def get_camera_from_camera_id(self,
                                  camera_id):
         for at_block_label in self.at_block_by_label:
             at_block = self.at_block_by_label[at_block_label]
             camera = at_block.get_camera_from_camera_id(camera_id)
             if camera:
                 return camera
         return None

    def get_camera_from_image_file_path(self,
                                        image_file_path):
         for at_block_label in self.at_block_by_label:
             at_block = self.at_block_by_label[at_block_label]
             camera = at_block.get_camera_from_image_file_path(image_file_path)
             if camera:
                 return camera
         return None

    def import_from_json_content(self,
                                 file_path,
                                 value_as_dict):
        str_error = ''
        self.is_graphos_model = False
        self.is_metashape_model = True
        at_blocks = []
        at_block_tag = ''
        if not defs_gr.GRAPHOS_DOCUMENT_TAG in value_as_dict:
            str_aux_error, at_blocks = self.import_metashape_markers(file_path, value_as_dict)
            at_block_tag = defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL
        else:
            str_aux_error, at_blocks = self.import_graphos(file_path, value_as_dict)
            self.is_graphos_model = True
            self.is_metashape_model = False
            at_block_tag = 'No defined'
        if str_aux_error:
            str_error = ('Error importing:\n{}'.format(str_aux_error))
            return str_error
        for at_block in at_blocks:
            if at_block.label in self.at_block_by_label:
                str_error = ('Exists previous chunk: {} equal label as in XML file:\n{}'.
                             format(at_block.label, at_block_tag, file_path))
                return str_error
            self.at_block_by_label[at_block.label] = at_block
        self.xml_file_content = value_as_dict
        return str_error

    def import_from_xml_file(self,
                             file_path):
        str_error = ''
        if self.xml_file_content:
            str_error = ('XML file has already been imported into the project')
            return str_error
        if not os.path.exists(file_path):
            str_error = ('Not exists XML file: {}'.format(file_path))
            return str_error
        with open(file_path, 'r', encoding='utf-8') as file:
            value_as_xml = file.read()
        try:
            value_as_dict = xmltodict.parse(value_as_xml)
        except xmltodict.expat.ExpatError as e:
            str_error = ('Parsing XML file: {}\nError:\n{}'.format(file_path, str(e)))
            return str_error
        str_aux_error = self.import_from_json_content(file_path, value_as_dict)
        if str_aux_error:
            str_error = ('Importing from XML file: {}\nError:\n{}'.format(file_path, str_aux_error))
            return str_error
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

    def import_graphos(self,
                       file_path,
                       value_as_dict):
        str_error = ''
        at_blocks = []
        if not defs_gr.GRAPHOS_DOCUMENT_TAG in value_as_dict:
            str_error = ('Not exists tag: {} in graphos XML file:\n{}'.
                         format(defs_msm.GRAPHOS_DOCUMENT_TAG, file_path))
            return str_error
        root = value_as_dict[defs_gr.GRAPHOS_DOCUMENT_TAG]
        # if not defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION in root:
        #     str_error = ('Not exists attribute: {} in metashape markers XML file:\n{}'.
        #                  format(defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION, file_path))
        #     return str_error
        # version = root[defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION]
        # if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG in root:
        #     str_error = ('Not exists tag: {} in metashape markers XML file:\n{}'.
        #                  format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG, file_path))
        #     return str_error
        # chunk_element = root[defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG]
        # if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL in chunk_element:
        #     str_error = ('Not exists attribute: {} in chunk in metashape markers XML file:\n{}'.
        #                  format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL, file_path))
        #     return str_error
        at_block_element = root

        # several blocks???
        at_block = ATBlockGraphos(file_path, self)
        str_error = at_block.set_from_xml(at_block_element)
        at_blocks.append(at_block)
        if str_error:
            return str_error, at_blocks

        return str_error, at_blocks

    def import_metashape_markers(self,
                                 file_path,
                                 value_as_dict):
        str_error = ''
        at_blocks = []
        # value_as_string = str(value_as_dict)
        # build project from xml
        if not defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG in value_as_dict:
            str_error = ('Not exists tag: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG, file_path))
            return str_error, at_blocks
        root = value_as_dict[defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION in root:
            str_error = ('Not exists attribute: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION, file_path))
            return str_error, at_blocks
        version = root[defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION]
        if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG in root:
            str_error = ('Not exists tag: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG, file_path))
            return str_error, at_blocks
        chunk_element = root[defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG]
        if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL in chunk_element:
            str_error = ('Not exists attribute: {} in chunk in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL, file_path))
            return str_error, at_blocks

        # several blocks???
        at_block = ATBlockMetashape(file_path, self)
        str_error = at_block.set_from_xml(chunk_element)
        at_blocks.append(at_block)
        if str_error:
            return str_error, at_blocks
        return str_error, at_blocks

    # def load_from_db_metashape_markers(self,
    #                                    value_as_dict,
    #                                    file_path):
    #     str_error = ''
    #     if not defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG in value_as_dict:
    #         str_error = ('Not exists tag: {} in metashape markers XML file:\n{}'.
    #                      format(defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG, file_path))
    #         return str_error
    #     root = value_as_dict[defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_TAG]
    #     if not defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION in root:
    #         str_error = ('Not exists attribute: {} in metashape markers XML file:\n{}'.
    #                      format(defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION, file_path))
    #         return str_error
    #     version = root[defs_msm.METASHAPE_MARKERS_XML_DOCUMENT_ATTRIBUTE_VERSION]
    #     if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG in root:
    #         str_error = ('Not exists tag: {} in metashape markers XML file:\n{}'.
    #                      format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG, file_path))
    #         return str_error
    #     chunk_element = root[defs_msm.METASHAPE_MARKERS_XML_CHUNK_TAG]
    #     if not defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL in chunk_element:
    #         str_error = ('Not exists attribute: {} in chunk in metashape markers XML file:\n{}'.
    #                      format(defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL, file_path))
    #         return str_error
    #     at_block = ATBlockMetashape(file_path, self)
    #     str_error = at_block.set_from_xml(chunk_element)
    #     if str_error:
    #         return str_error
    #     if at_block.label in self.at_block_by_label:
    #         str_error = ('Exists previous chunk: {} equal label as in metashape markers XML file:\n{}'.
    #                      format(at_block.label, defs_msm.METASHAPE_MARKERS_XML_CHUNK_ATTRIBUTE_LABEL, file_path))
    #         return str_error
    #     self.xml_file_content = value_as_dict
    #     self.at_block_by_label[at_block.label] = at_block
    #     return str_error

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

    def load_images_rh_from_db(self, file_path):
        str_error = ''
        layer_name = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME
        fields = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME]
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
                          format(defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME,
                                 file_path, str_error))
            return str_error
        if len(features) == 0:  # not import metashape markers xml file yet
            # str_error += ('There are no features in layer {} from gpgk:\n{}'.
            #               format(defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME,
            #                      file_path))
            return str_error
        for nf in range(len(features)):
            feature = features[nf]
            first_camera_id = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_ID]
            second_camera_id = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_ID]
            first_image_geometry_wkt = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_WKT]
            first_image_geometry_und_wkt = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_UND_WKT]
            first_image_epipolar_envelope = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_EPIPOLAR_ENVELOPE]
            firstEpipolarEnvelopeStr = first_image_epipolar_envelope.split(defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR)
            firstEpipolarEnvelope = []
            for i in range(len(firstEpipolarEnvelopeStr)):
                firstEpipolarEnvelope.append(int(firstEpipolarEnvelopeStr[i]))
            first_image_H = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_HOMOGRAPHY]
            first_image_invH = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_INVERSE_HOMOGRAPHY]
            firstHomographyImageFileName = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_FILE]
            second_image_geometry_wkt = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_WKT]
            second_image_geometry_und_wkt = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_UND_WKT]
            second_image_epipolar_envelope = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_EPIPOLAR_ENVELOPE]
            secondEpipolarEnvelopeStr = second_image_epipolar_envelope.split(defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR)
            secondEpipolarEnvelope = []
            for i in range(len(secondEpipolarEnvelopeStr)):
                secondEpipolarEnvelope.append(int(secondEpipolarEnvelopeStr[i]))
            second_image_H = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_HOMOGRAPHY]
            second_image_invH = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_INVERSE_HOMOGRAPHY]
            secondHomographyImageFileName = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_FILE]
            wkb_geometry = feature[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FP_GEOM]
            first_image_geometry = None
            try:
                first_image_geometry = ogr.CreateGeometryFromWkt(first_image_geometry_wkt)
            except Exception as e:
                str_error = ('Recovering stereopair image geometry for image id: {}\nGDAL error:\n{}'
                             .format(str(first_camera_id), e.args[0]))
                return str_error
            first_undistorted_image_geometry = None
            try:
                first_undistorted_image_geometry = ogr.CreateGeometryFromWkt(first_image_geometry_und_wkt)
            except Exception as e:
                str_error = ('Recovering stereopair image undistorted geometry for image id: {}\nGDAL error:\n{}'
                             .format(str(first_camera_id), e.args[0]))
                return str_error
            second_image_geometry = None
            try:
                second_image_geometry = ogr.CreateGeometryFromWkt(second_image_geometry_wkt)
            except Exception as e:
                str_error = ('Recovering stereopair image geometry for image id: {}\nGDAL error:\n{}'
                             .format(str(second_camera_id), e.args[0]))
                return str_error
            second_undistorted_image_geometry = None
            try:
                second_undistorted_image_geometry = ogr.CreateGeometryFromWkt(second_image_geometry_und_wkt)
            except Exception as e:
                str_error = ('Recovering stereopair image undistorted geometry for image id: {}\nGDAL error:\n{}'
                             .format(str(second_camera_id), e.args[0]))
                return str_error
            stereopair_geometry = None
            try:
                stereopair_geometry = ogr.CreateGeometryFromWkb(wkb_geometry)
            except Exception as e:
                str_error = ('Recovering stereopair object geometry for images ids: {} and: {}\nGDAL error:\n{}'
                             .format(str(first_camera_id), str(second_camera_id), e.args[0]))
                return str_error
            first_camera_H = np.zeros((3, 3))
            second_camera_H = np.zeros((3, 3))
            first_camera_invH = np.zeros((3, 3))
            second_camera_invH = np.zeros((3, 3))
            first_image_H_str_values = first_image_H.split(defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR)
            first_image_invH_str_values = first_image_invH.split(defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR)
            second_image_H_str_values = second_image_H.split(defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR)
            second_image_invH_str_values = second_image_invH.split(defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR)
            pos = -1
            for row in range(3):
                for column in range(3):
                    pos = pos + 1
                    first_camera_H[row, column] = float(first_image_H_str_values[pos])
                    second_camera_H[row, column] = float(second_image_H_str_values[pos])
                    first_camera_invH[row, column] = float(first_image_invH_str_values[pos])
                    second_camera_invH[row, column] = float(second_image_invH_str_values[pos])
            if not first_camera_id in self.spObjectGeometryByImagesIds:
                self.spObjectGeometryByImagesIds[first_camera_id] = {}
            self.spObjectGeometryByImagesIds[first_camera_id][second_camera_id] = stereopair_geometry
            if not second_camera_id in self.spObjectGeometryByImagesIds:
                self.spObjectGeometryByImagesIds[second_camera_id] = {}
            self.spObjectGeometryByImagesIds[second_camera_id][first_camera_id] = stereopair_geometry
            if not first_camera_id in self.spImageGeometryByImagesIds:
                self.spImageGeometryByImagesIds[first_camera_id] = {}
            self.spImageGeometryByImagesIds[first_camera_id][second_camera_id] = first_image_geometry
            if not second_camera_id in self.spImageGeometryByImagesIds:
                self.spImageGeometryByImagesIds[second_camera_id] = {}
            self.spImageGeometryByImagesIds[second_camera_id][first_camera_id] = second_image_geometry
            if not first_camera_id in self.spUndistortedImageGeometryByImagesIds:
                self.spUndistortedImageGeometryByImagesIds[first_camera_id] = {}
            self.spUndistortedImageGeometryByImagesIds[first_camera_id][
                second_camera_id] = first_undistorted_image_geometry
            if not second_camera_id in self.spUndistortedImageGeometryByImagesIds:
                self.spUndistortedImageGeometryByImagesIds[second_camera_id] = {}
            self.spUndistortedImageGeometryByImagesIds[second_camera_id][
                first_camera_id] = second_undistorted_image_geometry
            if not first_camera_id in self.spEpipolarEnvelopeByImagesIds:
                self.spEpipolarEnvelopeByImagesIds[first_camera_id] = {}
            self.spEpipolarEnvelopeByImagesIds[first_camera_id][
                second_camera_id] = firstEpipolarEnvelope  # minColum,minRow,maxColum,maxRow
            if not second_camera_id in self.spEpipolarEnvelopeByImagesIds:
                self.spEpipolarEnvelopeByImagesIds[second_camera_id] = {}
            self.spEpipolarEnvelopeByImagesIds[second_camera_id][
                first_camera_id] = secondEpipolarEnvelope  # minColum,minRow,maxColum,maxRow
            if not first_camera_id in self.homographyMatrixByCamerasId:
                self.homographyMatrixByCamerasId[first_camera_id] = {}
            self.homographyMatrixByCamerasId[first_camera_id][second_camera_id] = first_camera_H
            if not second_camera_id in self.homographyMatrixByCamerasId:
                self.homographyMatrixByCamerasId[second_camera_id] = {}
            self.homographyMatrixByCamerasId[second_camera_id][first_camera_id] = second_camera_H
            if not first_camera_id in self.inverseHomographyMatrixByCamerasId:
                self.inverseHomographyMatrixByCamerasId[first_camera_id] = {}
            self.inverseHomographyMatrixByCamerasId[first_camera_id][second_camera_id] = first_camera_invH
            if not second_camera_id in self.inverseHomographyMatrixByCamerasId:
                self.inverseHomographyMatrixByCamerasId[second_camera_id] = {}
            self.inverseHomographyMatrixByCamerasId[second_camera_id][first_camera_id] = second_camera_invH
            if not first_camera_id in self.epipolarFileNameByCamerasId:
                self.epipolarFileNameByCamerasId[first_camera_id] = {}
            self.epipolarFileNameByCamerasId[first_camera_id][second_camera_id] = firstHomographyImageFileName
            if not second_camera_id in self.epipolarFileNameByCamerasId:
                self.epipolarFileNameByCamerasId[second_camera_id] = {}
            self.epipolarFileNameByCamerasId[second_camera_id][first_camera_id] = secondHomographyImageFileName
        return str_error

    def load_images_tiles_from_db(self, file_path):
        str_error = ''
        str_tiles_values = defs_project.IMAGES_TILES_VALUES
        for i in range(len(str_tiles_values)):
            tile_str = str_tiles_values[i]
            lodSize = int(tile_str)
            self.imagesMaximumRamMBsBySize[lodSize] = 0.
            layer_name = defs_project.IMAGES_TILES_PREFIX_TABLE_NAME + tile_str
            fields = defs_project.fields_by_layer[layer_name]
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
                              format(defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME,
                                     file_path, str_error))
                return str_error
            if len(features) == 0:  # not import metashape markers xml file yet
                # str_error += ('There are no features in layer {} from gpgk:\n{}'.
                #               format(defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME,
                #                      file_path))
                continue
            for nf in range(len(features)):
                feature = features[nf]
                tileX = feature[defs_project.IMAGES_TILES_FIELD_TILE_X]
                tileY = feature[defs_project.IMAGES_TILES_FIELD_TILE_Y]
                images_ids = feature[defs_project.IMAGES_TILES_IMAGES_ID]
                imagesIdsStr = images_ids.split(";")
                imagesIds = []
                for j in range(len(imagesIdsStr)):
                    imagesIds.append(int(imagesIdsStr[j]))
                ramMbs = feature[defs_project.IMAGES_TILES_FIELD_RAM_MBS]
                wkb_geometry = feature[defs_project.IMAGES_TILES_FIELD_FP_GEOM]
                tile_geometry = None
                try:
                    tile_geometry = ogr.CreateGeometryFromWkb(wkb_geometry)
                except Exception as e:
                    str_error = ('Recovering geometry for tile x: {} and tile y: {}\nGDAL error:\n{}'
                                 .format(str(tileX), str(tileY), e.args[0]))
                    return str_error
                if lodSize in self.imagesMaximumRamMBsBySize:
                    if ramMbs > self.imagesMaximumRamMBsBySize[lodSize]:
                        self.imagesMaximumRamMBsBySize[lodSize] = ramMbs
                    else:
                        self.imagesMaximumRamMBsBySize[lodSize] = ramMbs
                if not lodSize in self.imagesTileRamMBsBySize:
                    self.imagesTileRamMBsBySize[lodSize] = {}
                if not tileX in self.imagesTileRamMBsBySize[lodSize]:
                    self.imagesTileRamMBsBySize[lodSize][tileX] = {}
                self.imagesTileRamMBsBySize[lodSize][tileX][tileY] = ramMbs
                if not lodSize in self.imagesTilesImagesIdBySize:
                    self.imagesTilesImagesIdBySize[lodSize] = {}
                if not tileX in self.imagesTilesImagesIdBySize[lodSize]:
                    self.imagesTilesImagesIdBySize[lodSize][tileX] = {}
                self.imagesTilesImagesIdBySize[lodSize][tileX][tileY] = imagesIds
                if not lodSize in self.geometryTileBySize:
                    self.geometryTileBySize[lodSize] = {}
                if not tileX in self.geometryTileBySize[lodSize]:
                    self.geometryTileBySize[lodSize][tileX] = {}
                self.geometryTileBySize[lodSize][tileX][tileY] = tile_geometry
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
        # if len(features) != 1: # not import metashape markers xml file yet
        #     return str_error
        #     # str_error = ('Loading {} from management from gpgk:\n{}\nError: not one value for field: {} in layer: {}'.
        #     #              format(defs_project.METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME,
        #     #                     file_name, defs_project.MANAGEMENT_FIELD_CONTENT, defs_project.MANAGEMENT_LAYER_NAME))
        #     # return str_error
        if len(features) == 1: # exists metashape markers xml
            json_content = features[0][defs_project.MANAGEMENT_FIELD_CONTENT]
            xml_file_path = features[0][defs_project.MANAGEMENT_FIELD_REMARKS]
            # json_acceptable_string = value.replace("'", "\"")
            # management_json_content = json.loads(json_acceptable_string)
            json_content = json.loads(json_content)
            # str_error = self.load_from_db_metashape_markers(xml_file_path,
            #                                                 json_content)
            str_error = self.import_from_json_content(xml_file_path,
                                                      json_content)
            if str_error:
                str_error = ('\nSetting from project file:\n{}\nerror:\n{}'.format(file_path, str_error))
                return str_error

            # images
            str_error = self.load_images_data_from_db(file_path)
            if str_error:
                return str_error

            # Stereoscopic data from management
            layer_name = defs_project.MANAGEMENT_LAYER_NAME
            fields = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME]
            fields = {}
            field_name = defs_project.MANAGEMENT_FIELD_CONTENT
            fields[field_name] = defs_project.fields_by_layer[layer_name][field_name]
            field_name = defs_project.MANAGEMENT_FIELD_REMARKS
            fields[field_name] = defs_project.fields_by_layer[layer_name][field_name]
            filter_fields = {}
            filter_field_name = defs_project.MANAGEMENT_FIELD_NAME
            filter_field_value = defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_FIELD_NAME
            filter_fields[filter_field_name] = filter_field_value
            str_error, features = GDALTools.get_features(file_path,
                                                         layer_name,
                                                         fields,
                                                         filter_fields)
            if str_error:
                str_error = ('Getting {} from management from gpgk:\n{}\nError:\n{}'.
                             format(defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_FIELD_NAME,
                                    file_path, str_error))
                return str_error
            if len(features) == 1: # exists stereoscopic data
                json_content = features[0][defs_project.MANAGEMENT_FIELD_CONTENT]
                json_content = json.loads(json_content)
                self.spUnionMinFc = json_content[defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_TAG_MINIMUM_FC]
                self.spUnionMinSc = json_content[defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_TAG_MINIMUM_SC]
                self.spUnionMaxFc = json_content[defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_TAG_MAXIMUM_FC]
                self.spUnionMaxSc = json_content[defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_TAG_MAXIMUM_SC]
                geometry_wkt = json_content[defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_TAG_WKT_GEOMETRY]
                self.stereopair_union_geometry = None
                try:
                    self.stereopair_union_geometry = ogr.CreateGeometryFromWkt(geometry_wkt)
                except Exception as e:
                    str_error = ('Creating stereoscopic geometry from WKT GDAL error:\n{}'
                                 .format(e.args[0]))
                    return str_error
                str_error = self.load_images_rh_from_db(file_path)
                if str_error:
                    str_error = ('Error loading images rectifiying homographies data from db:\n{}'
                                 .format(str_error))
                    return str_error
                str_error = self.load_images_tiles_from_db(file_path)
                if str_error:
                    str_error = ('Error loading images tiles data from db:\n{}'
                                 .format(str_error))
                    return str_error
        self.file_path = file_path
        self.opencv_tools = OpenCVTools()
        self.opencv_tools.initialize()
        return str_error

    def process_computing_rectifying_homographies(self,
                                                  process,
                                                  dialog):
        str_error = ''
        end_date_time = None
        log = None
        if not self.is_metashape_model:
            str_error = ('Algorithm computing rectifying homographies is only valid for projects of type metashape')
            return str_error, end_date_time, log
        self.spUnionMinFc = None
        self.spUnionMinSc = None
        self.spUnionMaxFc = None
        self.spUnionMaxSc = None
        self.stereopair_union_geometry = None
        self.imagesMaximumRamMBsBySize = {}
        self.imagesTileRamMBsBySize = {}
        self.imagesTilesImagesIdBySize = {}
        self.geometryTileBySize = {}
        self.spObjectGeometryByImagesIds = {}
        self.spImageGeometryByImagesIds = {}
        self.spUndistortedImageGeometryByImagesIds = {}
        self.spEpipolarEnvelopeByImagesIds = {}
        self.homographyMatrixByCamerasId = {}
        self.inverseHomographyMatrixByCamerasId = {}
        self.epipolarFileNameByCamerasId = {}
        geometryImagesInStereopairsByImageId = {}
        name = process[processes_defs_processes.PROCESS_FIELD_NAME]
        parameters_manager = process[processes_defs_processes.PROCESS_FIELD_PARAMETERS]
        # parameter dem
        if not defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_DEM in parameters_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_DEM))
            return str_error, end_date_time, log
        parameter_dem_file_path = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_DEM]
        parameter_dem_file_as_dict = json.loads(str(parameter_dem_file_path))
        dem_file_path = parameter_dem_file_as_dict[defs_pars.TAG_FILE_PATH]
        dem_file_path = os.path.normpath(dem_file_path)
        dem_layer_index = parameter_dem_file_as_dict[defs_pars.TAG_LAYER_INDEX]
        dem_file_scale = parameter_dem_file_as_dict[defs_pars.TAG_SCALE]
        dem_file_offset = parameter_dem_file_as_dict[defs_pars.TAG_OFFSET]
        if not dem_file_path:
            str_error = ('Process: {} has a empty parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_DEM))
            return str_error, end_date_time, log
        if not os.path.exists(dem_file_path):
            str_error = ('Process: {} has a parameter: {}\ndoes not exists'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_DEM))
            return str_error, end_date_time, log
        # parameter dem crs
        if not (defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_DEM_CRS
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_DEM_CRS))
            return str_error, end_date_time, log
        parameter_dem_crs_id = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_DEM_CRS]
        dem_crs_id = str(parameter_dem_crs_id) # can be empty for use internal of the DEM
        # parameter process only enabled images
        if not (defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_ENABLED_IMAGES
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_ENABLED_IMAGES))
            return str_error, end_date_time, log
        parameter_enabled_images = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_ENABLED_IMAGES]
        str_enabled = str(parameter_enabled_images)
        only_enabled_images = True
        if str_enabled.casefold() == 'false':
            only_enabled_images = False
        # parameter computing algorithm
        if not (defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_ALGORITHM
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_ALGORITHM))
            return str_error, end_date_time, log
        parameter_computing_algorithm = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_ALGORITHM]
        computing_algorithm = str(parameter_computing_algorithm)
        if (computing_algorithm.casefold() !=
                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_ALGORITHM_KNOWN_ORIENTATION.casefold()):
            str_error = ('Process: {} parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_ALGORITHM_KNOWN_ORIENTATION))
            str_error += ('\noption: {} not implemented'.
                         format(computing_algorithm))
            return str_error, end_date_time, log
        # parameter Ignored sensor percentage
        if not (defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_IGNORED_SENSOR_PERCENTAGE
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_IGNORED_SENSOR_PERCENTAGE))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_IGNORED_SENSOR_PERCENTAGE]
        str_value = str(parameter_value)
        ignored_sensor_percentage = None
        try:
            ignored_sensor_percentage = float(str_value)
        except ValueError:
            str_error = ('Process: {} does not have a float parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_IGNORED_SENSOR_PERCENTAGE,
                                str_value))
            return str_error, end_date_time, log
        # parameter Minimum overlap percentage
        if not (defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_MINIMUM_OVERLAP_PERCENTAGE
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_MINIMUM_OVERLAP_PERCENTAGE))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_MINIMUM_OVERLAP_PERCENTAGE]
        str_value = str(parameter_value)
        minimum_overlap_percentage = None
        try:
            minimum_overlap_percentage = float(str_value)
        except ValueError:
            str_error = ('Process: {} does not have a float parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_MINIMUM_OVERLAP_PERCENTAGE,
                                str_value))
            return str_error, end_date_time, log
        # parameter Save rectified homographies images
        if not (defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_SAVE_RECTIFIED_HOMOGRAPHIES_IMAGES
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_SAVE_RECTIFIED_HOMOGRAPHIES_IMAGES))
            return str_error, end_date_time, log
        parameter_save_recitified_images = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_SAVE_RECTIFIED_HOMOGRAPHIES_IMAGES]
        str_save_rectified_images = str(parameter_save_recitified_images)
        save_rectified_homographies_images = True
        if str_save_rectified_images.casefold() == 'false':
            save_rectified_homographies_images = False
        # parameter Rectified homographies images output path
        if not (defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH))
            return str_error, end_date_time, log
        parameter_output_path = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH]
        rectified_homographies_images_output_path = str(parameter_output_path)
        if not rectified_homographies_images_output_path:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH))
            return str_error, end_date_time, log
        rectified_homographies_images_output_path = os.path.normpath(rectified_homographies_images_output_path)
        if not os.path.exists(rectified_homographies_images_output_path):
            str_error = ('Process {} parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH))
            str_error += ('\nnot exists path: {}'.
                         format(rectified_homographies_images_output_path))
            return str_error, end_date_time, log
        # parameter Report files output path
        if not (defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_REPORT_FILES_OUTPUT_PATH
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_REPORT_FILES_OUTPUT_PATH))
            return str_error, end_date_time, log
        parameter_output_path = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_REPORT_FILES_OUTPUT_PATH]
        report_files_output_path = str(parameter_output_path)
        if not report_files_output_path:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_REPORT_FILES_OUTPUT_PATH))
            return str_error, end_date_time, log
        report_files_output_path = os.path.normpath(report_files_output_path)
        if not os.path.exists(report_files_output_path):
            str_error = ('Process {} parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_COMPUTING_RECTIFYING_HOMOGRAPHIES_PARAMETER_REPORT_FILES_OUTPUT_PATH))
            str_error += ('\nnot exists path: {}'.
                         format(report_files_output_path))
            return str_error, end_date_time, log
        # starting ...
        if not self.exists_footprints():
            str_error = ('Images footprints are not loaded')
            return str_error, end_date_time, log
        if not self.exists_footprints_undistorted():
            str_error = ('Images undistorted footprints are not loaded')
            return str_error, end_date_time, log
        if only_enabled_images:
            str_error = self.update_enabled_images_from_db()
            if str_error:
                str_error = ('Updating enabled images from file: {}\nError:\n{}'
                             .format(self.file_path, str_error))
                return str_error, end_date_time, log
        cameras_to_process = []
        exists_footprints = False
        at_block_labels = []
        at_blok_label_by_camera_id = {}
        for at_block_label in self.at_block_by_label:
            at_block = self.at_block_by_label[at_block_label]
            for camera_id in at_block.camera_by_id:
                camera = at_block.camera_by_id[camera_id]
                camera_enabled = camera.get_enabled() # multisensor ...
                if camera_enabled:
                    if camera.is_usefull():
                        cameras_to_process.append(camera)
                        at_blok_label_by_camera_id[camera_id] = at_block_label
                        if not at_block_label in at_block_labels:
                            at_block_labels.append(at_block_label)
        if len(at_block_labels) != 1:
            str_error = ('Algorithm computing rectifying homographies is only valid for one AT block')
            return str_error, end_date_time, log
        at_block_label = at_block_labels[0]
        at_block = self.at_block_by_label[at_block_label]
        # QMap < int, OGRGeometry * > ptrGeometryImagesInStereopairsByImageId;
        # QMap < int, QMap < int, OGRGeometry * > > ptrStereoPairGeometryByImagesIds;
        stereoPairGeometryByImagesIds = {}
        camera_by_id = {}
        numberOfPairsToProcess = 0
        if dialog:
            dialog.processInformationGroupBox.setEnabled(True)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            dialog.processLineEdit.setText('Computing stereo pairs ...')
            dialog.processLineEdit.adjustSize()
            dialog.processProgressBar.setMaximum(len(cameras_to_process)-1)
            dialog.processLineEdit.adjustSize()
            QApplication.processEvents()
        for i1 in range(len(cameras_to_process)-1):
            if dialog:
                dialog.processProgressBar.setValue(i1)
                QApplication.processEvents()
            first_camera = cameras_to_process[i1]
            first_camera_id = first_camera.id
            first_camera_footprint_geometry = first_camera.footprint_geometry
            first_camera_footprint_area = first_camera_footprint_geometry.GetArea()
            for i2 in range(i1 + 1, len(cameras_to_process)):
                second_camera = cameras_to_process[i2]
                second_camera_id = second_camera.id
                second_camera_footprint_geometry = second_camera.footprint_geometry
                second_camera_footprint_area = second_camera_footprint_geometry.GetArea()
                if first_camera_footprint_geometry.Intersects(second_camera_footprint_geometry):
                    stereopair_geometry = first_camera_footprint_geometry.Intersection(
                        second_camera_footprint_geometry)
                    stereopair_geometry_type = stereopair_geometry.GetGeometryType()
                    is_valid_stereopair_geometry = False
                    if stereopair_geometry_type == ogr.wkbPolygon:
                        is_valid_stereopair_geometry = True
                    if not is_valid_stereopair_geometry:
                        continue
                    stereopair_geometry_area = stereopair_geometry.GetArea()
                    if (stereopair_geometry_area < (minimum_overlap_percentage / 100. * first_camera_footprint_area)
                            or stereopair_geometry_area < (
                                    minimum_overlap_percentage / 100. * second_camera_footprint_area)):
                        continue
                    if not first_camera_id in stereoPairGeometryByImagesIds:
                        stereoPairGeometryByImagesIds[first_camera_id] = {}
                    stereoPairGeometryByImagesIds[first_camera_id][second_camera_id] = stereopair_geometry
                    if not first_camera_id in camera_by_id:
                        camera_by_id[first_camera_id] = first_camera
                    if not second_camera_id in camera_by_id:
                        camera_by_id[second_camera_id] = second_camera
                    if not first_camera_id in geometryImagesInStereopairsByImageId:
                        geometryImagesInStereopairsByImageId[first_camera_id] = first_camera_footprint_geometry
                    if not second_camera_id in geometryImagesInStereopairsByImageId:
                        geometryImagesInStereopairsByImageId[second_camera_id] = second_camera_footprint_geometry
                    numberOfPairsToProcess = numberOfPairsToProcess + 1
        if dialog:
            dialog.processProgressBar.setValue(len(cameras_to_process)-1)
            dialog.processInformationGroupBox.setEnabled(False)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            QApplication.processEvents()
        if numberOfPairsToProcess == 0:
            end_date_time = datetime.now()
            return str_error, end_date_time, log
        # digitizing parameters
        if self.process_set_digitizing_parameters is None:
            process_set_digitizing_parameters_name = defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_NAME
            process_set_digitizing_parameters = None
            process_provider = None
            for process_provider in self.processes_manager.processes_by_provider:
                if process_set_digitizing_parameters_name in self.processes_manager.processes_by_provider[process_provider]:
                    self.process_set_digitizing_parameters = self.processes_manager.processes_by_provider[
                        process_provider][process_set_digitizing_parameters_name]
                    break
            if self.process_set_digitizing_parameters is None:
                str_error = ('Not found process: {}'
                             .format(process_set_digitizing_parameters_name))
                return str_error, end_date_time, log
        str_error, end_date_time, log = self.set_digitizing_parameters(self.process_set_digitizing_parameters)
        if str_error:
            return str_error, end_date_time, log
        # DEM
        raster_dem = None
        if not dem_file_path in self.raster_dem_by_file_path:
            raster_dem = RasterDEM(defs_project.RASTER_DEM_PRECISION_CODE)
            if dem_crs_id:
                str_error = raster_dem.set_crs_id_by_user(dem_crs_id)
                if str_error:
                    str_error = ('Setting CRS to raster DEM from file: {}\nError:\n{}'
                                 .format(dem_file_path, str_error))
                    return str_error, end_date_time, log
            str_error = raster_dem.set_from_file(dem_file_path)
            if str_error:
                str_error = ('Setting raster DEM from file: {}\nError:\n{}'
                             .format(dem_file_path, str_error))
                return str_error, end_date_time, log
            raster_dem.set_check_domain(False) # get solution for out points
            self.raster_dem_by_file_path[dem_file_path] = raster_dem
        else:
            raster_dem = self.raster_dem_by_file_path[dem_file_path]
        str_error = raster_dem.load()
        if str_error:
            str_error = ('Loading in memory raster DEM from file: {}\nError:\n{}'
                         .format(dem_file_path, str_error))
            return str_error, end_date_time, log
        raster_dem_crs_id = raster_dem.get_crs_id()
        # process
        stereopair_multigeometry = ogr.Geometry(ogr.wkbMultiPolygon)
        if dialog:
            dialog.processInformationGroupBox.setEnabled(True)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            dialog.processLineEdit.setText('Computing rectifying homographies for {} stereopairs'
                                           .format(numberOfPairsToProcess))
            dialog.processLineEdit.adjustSize()
            dialog.processProgressBar.setMaximum(numberOfPairsToProcess)
            dialog.processLineEdit.adjustSize()
            QApplication.processEvents()
        features = []
        numberOfProcessedPairs = 0
        for first_camera_id in stereoPairGeometryByImagesIds:
            # debug
            if len(features) > 2:
                break
            numberOfProcessedPairs = numberOfProcessedPairs + 1
            if dialog:
                dialog.processProgressBar.setValue(numberOfProcessedPairs)
                QApplication.processEvents()
            first_camera = camera_by_id[first_camera_id]
            str_error = first_camera.set_pinhole_camera_model()
            if str_error:
                str_error = ('Getting pinhole camera model for image: {}\nError:\n{}'
                             .format(first_camera_id, str_error))
                if dialog:
                    dialog.processProgressBar.setValue(numberOfPairsToProcess)
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                    QApplication.processEvents()
                return str_error, end_date_time, log
            first_sensor = self.at_block_by_label[at_block_label].sensor_by_id[first_camera.sensor_id]
            first_camera_columns = first_sensor.width
            first_camera_rows = first_sensor.height
            for second_camera_id in stereoPairGeometryByImagesIds[first_camera_id]:
                # debug
                if len(features) > 2:
                    break
                numberOfProcessedPairs = numberOfProcessedPairs + 1
                if dialog:
                    dialog.processProgressBar.setValue(numberOfProcessedPairs)
                    QApplication.processEvents()
                second_camera = camera_by_id[second_camera_id]
                str_error = second_camera.set_pinhole_camera_model()
                if str_error:
                    str_error = ('Getting pinhole camera model for image: {}\nError:\n{}'
                                 .format(second_camera_id, str_error))
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfPairsToProcess)
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        QApplication.processEvents()
                    return str_error, end_date_time, log
                second_sensor = self.at_block_by_label[at_block_label].sensor_by_id[second_camera.sensor_id]
                second_camera_columns = second_sensor.width
                second_camera_rows = second_sensor.height
                stereopair_geometry = stereoPairGeometryByImagesIds[first_camera_id][second_camera_id]
                R33_1 = copy.deepcopy(first_camera.pinhole_camera_model[defs_img.PINHOLE_CAMERA_MODEL_R])
                quat1 = quaternion.from_rotation_matrix(R33_1)
                qvec1 = np.zeros(4)
                qvec1[0] = quat1.w
                qvec1[1] = quat1.x
                qvec1[2] = quat1.y
                qvec1[3] = quat1.z
                qvec1_negative = -1. * qvec1 # qvec1 is -1 eigen
                tvec1 = copy.deepcopy(first_camera.pinhole_camera_model[defs_img.PINHOLE_CAMERA_MODEL_t])
                R33_2 = copy.deepcopy(second_camera.pinhole_camera_model[defs_img.PINHOLE_CAMERA_MODEL_R])
                quat2 = quaternion.from_rotation_matrix(R33_2)
                qvec2 = np.zeros(4)
                qvec2[0] = quat2.w
                qvec2[1] = quat2.x
                qvec2[2] = quat2.y
                qvec2[3] = quat2.z
                qvec2_negative = -1. * qvec2 # qvec2 is -1 eigen
                tvec2 = copy.deepcopy(second_camera.pinhole_camera_model[defs_img.PINHOLE_CAMERA_MODEL_t])
                str_image1 = ("{:.12f} {:.12f} {:.12f} {:.12f}".format(qvec1[0], qvec1[1], qvec1[2], qvec1[3]))
                str_image1 += (" {:.6f} {:.6f} {:.6f}".format(tvec1[0], tvec1[1], tvec1[2]))
                str_image2 = ("{:.12f} {:.12f} {:.12f} {:.12f}".format(qvec2[0], qvec2[1], qvec2[2], qvec2[3]))
                str_image2 += (" {:.6f} {:.6f} {:.6f}".format(tvec2[0], tvec2[1], tvec2[2]))
                # compute relative pose
                inv_qvec1 = invert_quaternion(qvec1)
                # inv_qvec1 = pyLibPhotogrammetry.lib.computations.inverse_quaternion(qvec1)
                qvec12 = concatenate_quaternions(inv_qvec1, qvec2)
                tvec12 = tvec2 - quaternion_rotate_point(qvec12, tvec1)
                K1 = first_camera.pinhole_camera_model[defs_img.PINHOLE_CAMERA_MODEL_K]
                K2 = second_camera.pinhole_camera_model[defs_img.PINHOLE_CAMERA_MODEL_K]
                H1, H2, Q = rectify_stereo_cameras(K1, K2, qvec12, tvec12)
                invH1 = np.linalg.inv(H1)
                invH2 = np.linalg.inv(H2)
                first_camera_H = np.zeros((3,3))
                second_camera_H = np.zeros((3,3))
                first_camera_invH = np.zeros((3,3))
                second_camera_invH = np.zeros((3,3))
                for row in range(3):
                    for column in range(3):
                        first_camera_H[row, column] = H1[row, column]
                        second_camera_H[row, column] = H2[row, column]
                        first_camera_invH[row, column] = invH1[row, column]
                        second_camera_invH[row, column] = invH2[row, column]
                # stereo footprint geometries
                stereopair_nrings = stereopair_geometry.GetGeometryCount()
                stereopair_exterior_ring = stereopair_geometry.GetGeometryRef(0)
                stereopair_points = []
                for i in range(stereopair_exterior_ring.GetPointCount()):
                    point = stereopair_exterior_ring.GetPoint(i)
                    fc = stereopair_exterior_ring.GetX(i)
                    sc = stereopair_exterior_ring.GetY(i)
                    if raster_dem_crs_id.casefold() != at_block.crs_id.casefold():
                        pto = [[fc, sc, 0.]]
                        str_error = self.crs_tools.operation(at_block.crs_id, raster_dem_crs_id,
                                                         pto)
                        if str_error:
                            str_error += ('Computing rectifying homographies')
                            str_error += ('\nFor image: {} and image: {}'.
                                          format(first_camera.label, second_camera.label))
                            str_error += ('\nFrom AT Block CRS: {} to CRS: {}\nfor point: [{:.3f}, {:.3f}]\nerror:\n{}'.
                                         format(at_block.crs_id, raster_dem_crs_id,
                                                fc, sc, str_error))
                            if dialog:
                                dialog.processProgressBar.setValue(numberOfPairsToProcess)
                                dialog.processInformationGroupBox.setEnabled(False)
                                dialog.processLineEdit.clear()
                                dialog.processProgressBar.reset()
                                QApplication.processEvents()
                            return str_error, end_date_time, log
                        fc = pto[0][0]
                        sc = pto[0][1]
                    str_error, elevation, point_out_edge, is_no_data = raster_dem.get_elevation(fc,sc)
                    stereopair_points.append([fc, sc, elevation])
                firstImageWktGeometry = "POLYGON(("
                firstUndistortedImageWktGeometry = "POLYGON(("
                secondImageWktGeometry = "POLYGON(("
                secondUndistortedImageWktGeometry = "POLYGON(("
                firstImageEpipolarWktGeometry = "POLYGON(("
                secondImageEpipolarWktGeometry = "POLYGON(("
                fImgEpiMinColumn = 1000000
                fImgEpiMinRow = 1000000
                fImgEpiMaxColumn = 0
                fImgEpiMaxRow = 0
                sImgEpiMinColumn = 1000000
                sImgEpiMinRow = 1000000
                sImgEpiMaxColumn = 0
                sImgEpiMaxRow = 0
                fpFImgEpiColumn = None
                fpFImgEpiRow = None
                fpSImgEpiColumn = None
                fpSImgEpiRow = None
                for i in range(len(stereopair_points)):
                    stereopair_point = stereopair_points[i]
                    position = np.array([stereopair_point[0], stereopair_point[1], stereopair_point[2]])
                    if at_block.crs_id != at_block.crs_ecef_id:
                        position_ecef = [position.tolist()]
                        str_error = self.crs_tools.operation(at_block.crs_id, at_block.crs_ecef_id, position_ecef)
                        if str_error:
                            str_error += ('Computing rectifying homographies')
                            str_error += ('\nFor image: {} and image: {}'.
                                          format(first_camera.label, second_camera.label))
                            str_error += ('\nFrom CRS: {} to CRS: {}\nfor point: [{:.3f}, {:.3f}]\nerror:\n{}'.
                                         format(at_block.crs_id, at_block.crs_ecef_id,
                                                position[0][0], position[0][1], str_error))
                            if dialog:
                                dialog.processProgressBar.setValue(numberOfPairsToProcess)
                                dialog.processInformationGroupBox.setEnabled(False)
                                dialog.processLineEdit.clear()
                                dialog.processProgressBar.reset()
                                QApplication.processEvents()
                            return str_error, end_date_time, log
                        position_ecef = np.array(position_ecef[0])
                    else:
                        position_ecef = np.array(position.tolist())
                    if at_block.crs_id != at_block.crs_geo3d_id:
                        position_geo3d = [position.tolist()]
                        str_error = self.crs_tools.operation(at_block.crs_id, at_block.crs_geo3d_id,
                                                             position_geo3d)
                        if str_error:
                            str_error += ('Computing rectifying homographies')
                            str_error += ('\nFor image: {} and image: {}'.
                                          format(first_camera.label, second_camera.label))
                            str_error += ('\nFrom CRS: {} to CRS: {}\nfor point: [{:.3f}, {:.3f}]\nerror:\n{}'.
                                         format(at_block.crs_id, at_block.crs_geo3d_id,
                                                position[0][0], position[0][1], str_error))
                            if dialog:
                                dialog.processProgressBar.setValue(numberOfPairsToProcess)
                                dialog.processInformationGroupBox.setEnabled(False)
                                dialog.processLineEdit.clear()
                                dialog.processProgressBar.reset()
                                QApplication.processEvents()
                            return str_error, end_date_time, log
                        position_geo3d = np.array(position_geo3d[0])
                    else:
                        position_geo3d = np.array(position.tolist())
                    position_ecef = np.append(position_ecef, 1.0)
                    position_chunk = np.matmul(at_block.transform_inv, position_ecef)
                    within = None
                    withinAfterUndistortion = None
                    position_first_image = None
                    position_undistorted_first_image = None
                    str_error, within, withinAfterUndistortion, position_first_image, position_undistorted_first_image \
                            = first_camera.from_chunk_to_sensor(position_chunk)
                    if str_error:
                        str_error += ('Computing rectifying homographies')
                        str_error += ('\nFor image: {} and image: {}'.
                                      format(first_camera.label, second_camera.label))
                        str_error += ('\nFrom chunk to first image in point: [{:.3f}, {:.3f}, {:3.f}]\nerror:\n{}'.
                                      format(at_block.crs_id, at_block.crs_geo3d_id,
                                             position_chunk[0][0], position_chunk[0][1], position_chunk[0][2], str_error))
                        if dialog:
                            dialog.processProgressBar.setValue(numberOfPairsToProcess)
                            dialog.processInformationGroupBox.setEnabled(False)
                            dialog.processLineEdit.clear()
                            dialog.processProgressBar.reset()
                            QApplication.processEvents()
                        return str_error, end_date_time, log
                    fImgColumn = position_first_image[0]
                    fImgRow = position_first_image[1]
                    fImgColumnNoD = position_undistorted_first_image[0]
                    fImgRowNoD = position_undistorted_first_image[1]
                    position_second_image = None
                    position_undistorted_second_image = None
                    str_error, within, withinAfterUndistortion, position_second_image, position_undistorted_second_image \
                            = second_camera.from_chunk_to_sensor(position_chunk)
                    if str_error:
                        str_error += ('Computing rectifying homographies')
                        str_error += ('\nFor image: {} and image: {}'.
                                      format(first_camera.label, second_camera.label))
                        str_error += ('\nFrom chunk to second image in point: [{:.3f}, {:.3f}, {:3.f}]\nerror:\n{}'.
                                      format(at_block.crs_id, at_block.crs_geo3d_id,
                                             position_chunk[0][0], position_chunk[0][1], position_chunk[0][2], str_error))
                        if dialog:
                            dialog.processProgressBar.setValue(numberOfPairsToProcess)
                            dialog.processInformationGroupBox.setEnabled(False)
                            dialog.processLineEdit.clear()
                            dialog.processProgressBar.reset()
                            QApplication.processEvents()
                        return str_error, end_date_time, log
                    sImgColumn = position_second_image[0]
                    sImgRow = position_second_image[1]
                    sImgColumnNoD = position_undistorted_second_image[0]
                    sImgRowNoD = position_undistorted_second_image[1]
                    # Calcular los puntos en las homografias a partir de la posicion libre de distorsion
                    fImgDen = fImgColumnNoD * first_camera_H[2, 0] + fImgRowNoD * first_camera_H[2, 1] + 1.0 * first_camera_H[2, 2]
                    fEpiImgColumn = fImgColumnNoD * first_camera_H[0, 0] + fImgRowNoD * first_camera_H[0, 1] + 1.0 * first_camera_H[0, 2]
                    fEpiImgColumn = fEpiImgColumn / fImgDen
                    fEpiImgRow = fImgColumnNoD * first_camera_H[1, 0] + fImgRowNoD * first_camera_H[1, 1] + 1.0 * first_camera_H[1, 2]
                    fEpiImgRow = fEpiImgRow / fImgDen
                    fEpiColumnInt = math.floor(fEpiImgColumn)
                    if (fEpiColumnInt < 0):
                        fEpiColumnInt = 0
                    if (fEpiColumnInt > (first_camera_columns - 1)):
                        fEpiColumnInt = first_camera_columns - 1
                    if (fEpiColumnInt < fImgEpiMinColumn):
                        fImgEpiMinColumn = fEpiColumnInt
                    if (fEpiColumnInt > fImgEpiMaxColumn):
                        fImgEpiMaxColumn = fEpiColumnInt
                    fEpiRowInt = math.floor(fEpiImgRow)
                    if (fEpiRowInt < 0):
                        fEpiRowInt=0
                    if (fEpiRowInt > (first_camera_rows - 1)):
                        fEpiRowInt = first_camera_rows - 1
                    if (fEpiRowInt < fImgEpiMinRow):
                        fImgEpiMinRow = fEpiRowInt
                    if (fEpiRowInt > fImgEpiMaxRow):
                        fImgEpiMaxRow = fEpiRowInt
                    sImgDen = sImgColumnNoD * second_camera_H[2, 0] + sImgRowNoD * second_camera_H[2, 1] + 1.0 * second_camera_H[2, 2]
                    sEpiImgColumn = sImgColumnNoD * second_camera_H[0, 0] + sImgRowNoD * second_camera_H[0, 1] + 1.0 * second_camera_H[0, 2]
                    sEpiImgColumn = sEpiImgColumn / sImgDen
                    sEpiImgRow = sImgColumnNoD * second_camera_H[1, 0] + sImgRowNoD * second_camera_H[1, 1] + 1.0 * second_camera_H[1, 2]
                    sEpiImgRow = sEpiImgRow / sImgDen
                    sEpiColumnInt = math.floor(sEpiImgColumn)
                    if (sEpiColumnInt < 0):
                        sEpiColumnInt = 0
                    if (sEpiColumnInt > (second_camera_columns - 1)):
                        sEpiColumnInt = second_camera_columns - 1
                    if (sEpiColumnInt < sImgEpiMinColumn):
                        sImgEpiMinColumn = sEpiColumnInt
                    if (sEpiColumnInt > sImgEpiMaxColumn):
                        sImgEpiMaxColumn = sEpiColumnInt
                    sEpiRowInt = math.floor(sEpiImgRow)
                    if (sEpiRowInt < 0):
                        sEpiRowInt=0
                    if (sEpiRowInt > (second_camera_rows - 1)):
                        sEpiRowInt = second_camera_rows -1
                    if (sEpiRowInt < sImgEpiMinRow):
                        sImgEpiMinRow = sEpiRowInt
                    if (sEpiRowInt > sImgEpiMaxRow):
                        sImgEpiMaxRow = sEpiRowInt

                    fImgColumnInt = math.floor(fImgColumn)
                    if (fImgColumnInt < 0):
                        fImgColumnInt = 0
                    if (fImgColumnInt > (first_camera_columns - 1)):
                        fImgColumnInt = first_camera_columns - 1

                    fImgRowInt = math.floor(fImgRow)
                    if (fImgRowInt < 0):
                        fImgRowInt = 0
                    if (fImgRowInt > (first_camera_rows - 1)):
                        fImgRowInt = first_camera_rows - 1

                    fImgColumnNoDInt = math.floor(fImgColumnNoD)
                    if (fImgColumnNoDInt < 0):
                        fImgColumnNoDInt = 0
                    if (fImgColumnNoDInt > (first_camera_columns - 1)):
                        fImgColumnNoDInt = first_camera_columns - 1

                    fImgRowNoDInt = math.floor(fImgRowNoD)
                    if (fImgRowNoDInt < 0):
                        fImgRowNoDInt = 0
                    if (fImgRowNoDInt > (first_camera_rows - 1)):
                        fImgRowNoDInt = first_camera_rows - 1

                    sImgColumnInt = math.floor(sImgColumn)
                    if (sImgColumnInt < 0):
                        sImgColumnInt = 0
                    if (sImgColumnInt > (second_camera_columns - 1)):
                        sImgColumnInt = second_camera_columns - 1

                    sImgRowInt = math.floor(sImgRow)
                    if (sImgRowInt < 0):
                        sImgRowInt = 0
                    if (sImgRowInt > (second_camera_rows - 1)):
                        sImgRowInt = second_camera_rows - 1

                    sImgColumnNoDInt = math.floor(sImgColumnNoD)
                    if (sImgColumnNoDInt < 0):
                        sImgColumnNoDInt = 0
                    if (sImgColumnNoDInt > (second_camera_columns - 1)):
                        sImgColumnNoDInt = second_camera_columns - 1

                    sImgRowNoDInt = math.floor(sImgRowNoD)
                    if (sImgRowNoDInt < 0):
                        sImgRowNoDInt = 0
                    if (sImgRowNoDInt > (second_camera_rows - 1)):
                        sImgRowNoDInt = second_camera_rows - 1

                    # paso la fila a negativo para que la geometria se pueda cargar en qgis
                    fImgRowInt = -1 * fImgRowInt
                    fImgRowNoDInt = -1 * fImgRowNoDInt
                    sImgRowInt = -1 * sImgRowInt
                    sImgRowNoDInt = -1 * sImgRowNoDInt
                    firstImageWktGeometry += ("{:.0f}".format(fImgColumnInt))
                    firstImageWktGeometry += " "
                    firstImageWktGeometry += ("{:.0f}".format(fImgRowInt))
                    firstUndistortedImageWktGeometry += ("{:.0f}".format(fImgColumnNoDInt))
                    firstUndistortedImageWktGeometry += " "
                    firstUndistortedImageWktGeometry += ("{:.0f}".format(fImgRowNoDInt))
                    secondImageWktGeometry += ("{:.0f}".format(sImgColumnInt))
                    secondImageWktGeometry += " "
                    secondImageWktGeometry += ("{:.0f}".format(sImgRowInt))
                    secondUndistortedImageWktGeometry += ("{:.0f}".format(sImgColumnNoDInt))
                    secondUndistortedImageWktGeometry += " "
                    secondUndistortedImageWktGeometry += ("{:.0f}".format(sImgRowNoDInt))
                    fEpiRowInt = -1 * fEpiRowInt
                    sEpiRowInt = -1 * sEpiRowInt
                    firstImageEpipolarWktGeometry += ("{:.0f}".format(fEpiColumnInt))
                    firstImageEpipolarWktGeometry += " "
                    firstImageEpipolarWktGeometry += ("{:.0f}".format(fEpiRowInt))
                    secondImageEpipolarWktGeometry += ("{:.0f}".format(sEpiColumnInt))
                    secondImageEpipolarWktGeometry += " "
                    secondImageEpipolarWktGeometry += ("{:.0f}".format(sEpiRowInt))
                    if i == 0:
                        fpFImgColumn = fImgColumnInt
                        fpFImgRow = fImgRowInt
                        fpFUndImgColumn = fImgColumnNoDInt
                        fpFUndImgRow = fImgRowNoDInt
                        fpSImgColumn = sImgColumnInt
                        fpSImgRow = sImgRowInt
                        fpSUndImgColumn = sImgColumnNoDInt
                        fpSUndImgRow = sImgRowNoDInt
                        fpFImgEpiColumn = fEpiColumnInt
                        fpFImgEpiRow = fEpiRowInt
                        fpSImgEpiColumn = sEpiColumnInt
                        fpSImgEpiRow = sEpiRowInt
                    firstImageWktGeometry += ","
                    firstUndistortedImageWktGeometry += ","
                    secondImageWktGeometry += ","
                    secondUndistortedImageWktGeometry += ","
                    firstImageEpipolarWktGeometry += ","
                    secondImageEpipolarWktGeometry += ","
                firstImageWktGeometry += ("{:.0f}".format(fpFImgColumn))
                firstImageWktGeometry += " "
                firstImageWktGeometry += ("{:.0f}".format(fpFImgRow))
                firstUndistortedImageWktGeometry += ("{:.0f}".format(fpFUndImgColumn))
                firstUndistortedImageWktGeometry += " "
                firstUndistortedImageWktGeometry += ("{:.0f}".format(fpFUndImgRow))
                secondImageWktGeometry += ("{:.0f}".format(fpSImgColumn))
                secondImageWktGeometry += " "
                secondImageWktGeometry += ("{:.0f}".format(fpSImgRow))
                secondUndistortedImageWktGeometry += ("{:.0f}".format(fpSUndImgColumn))
                secondUndistortedImageWktGeometry += " "
                secondUndistortedImageWktGeometry += ("{:.0f}".format(fpSUndImgRow))
                firstImageEpipolarWktGeometry += ("{:.0f}".format(fpFImgEpiColumn))
                firstImageEpipolarWktGeometry += " "
                firstImageEpipolarWktGeometry += ("{:.0f}".format(fpFImgEpiRow))
                secondImageEpipolarWktGeometry += ("{:.0f}".format(fpSImgEpiColumn))
                secondImageEpipolarWktGeometry += " "
                secondImageEpipolarWktGeometry += ("{:.0f}".format(fpSImgEpiRow))
                firstImageWktGeometry += "))"
                firstUndistortedImageWktGeometry += "))"
                secondImageWktGeometry += "))"
                secondUndistortedImageWktGeometry += "))"
                firstImageEpipolarWktGeometry += "))"
                secondImageEpipolarWktGeometry += "))"
                firstEpipolarEnvelope = [] # minColum, minRow, maxColum, maxRow
                secondEpipolarEnvelope = [] # minColum, minRow, maxColum, maxRow
                firstEpipolarEnvelope.append(fImgEpiMinColumn)
                firstEpipolarEnvelope.append(fImgEpiMinRow)
                firstEpipolarEnvelope.append(fImgEpiMaxColumn)
                firstEpipolarEnvelope.append(fImgEpiMaxRow)
                secondEpipolarEnvelope.append(sImgEpiMinColumn)
                secondEpipolarEnvelope.append(sImgEpiMinRow)
                secondEpipolarEnvelope.append(sImgEpiMaxColumn)
                secondEpipolarEnvelope.append(sImgEpiMaxRow)
                first_image_geometry = None
                try:
                    first_image_geometry = ogr.CreateGeometryFromWkt(firstImageWktGeometry)
                except Exception as e:
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nComputing geometry for image: {}\nGDAL error:\n{}'
                                  .format(first_camera.label, e.args[0]))
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfPairsToProcess)
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        QApplication.processEvents()
                    return str_error, end_date_time, log
                if not first_image_geometry.IsValid():
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nComputing geometry for image: {}\nInvalid geometry'
                                  .format(first_camera.label))
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfPairsToProcess)
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        QApplication.processEvents()
                    return str_error, end_date_time, log
                first_image_geometry_wkb = None
                try:
                    first_image_geometry_wkb = first_image_geometry.ExportToWkb()
                except Exception as e:
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nExporting to WKB computed geometry for image: {}\nGDAL error:\n{}'
                                  .format(first_camera.label, e.args[0]))
                    if dialog:
                        dialog.processProgressBar.setValue(len(numberOfPairsToProcess))
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                    return str_error, end_date_time, log
                second_image_geometry = None
                try:
                    second_image_geometry = ogr.CreateGeometryFromWkt(secondImageWktGeometry)
                except Exception as e:
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nComputing geometry for image: {}\nGDAL error:\n{}'
                                  .format(second_camera.label, e.args[0]))
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfPairsToProcess)
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        QApplication.processEvents()
                    return str_error, end_date_time, log
                if not second_image_geometry.IsValid():
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nComputing geometry for image: {}\nInvalid geometry'
                                  .format(second_camera.label))
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfPairsToProcess)
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        QApplication.processEvents()
                    return str_error, end_date_time, log
                second_image_geometry_wkb = None
                try:
                    second_image_geometry_wkb = second_image_geometry.ExportToWkb()
                except Exception as e:
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nExporting to WKB computed geometry for image: {}\nGDAL error:\n{}'
                                  .format(second_camera.label, e.args[0]))
                    if dialog:
                        dialog.processProgressBar.setValue(len(numberOfPairsToProcess))
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                    return str_error, end_date_time, log
                first_undistorted_image_geometry = None
                try:
                    first_undistorted_image_geometry = ogr.CreateGeometryFromWkt(firstUndistortedImageWktGeometry)
                except Exception as e:
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nComputing geometry for undistorted image: {}\nGDAL error:\n{}'
                                  .format(first_camera.label, e.args[0]))
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfPairsToProcess)
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        QApplication.processEvents()
                    return str_error, end_date_time, log
                if not first_undistorted_image_geometry.IsValid():
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nComputing geometry for undistorted image: {}\nInvalid geometry'
                                  .format(first_camera.label))
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfPairsToProcess)
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        QApplication.processEvents()
                    return str_error, end_date_time, log
                first_undistorted_image_geometry_wkb = None
                try:
                    first_undistorted_image_geometry_wkb = first_undistorted_image_geometry.ExportToWkb()
                except Exception as e:
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nExporting to WKB computed geometry for undistorted image: {}\nGDAL error:\n{}'
                                  .format(first_camera.label, e.args[0]))
                    if dialog:
                        dialog.processProgressBar.setValue(len(numberOfPairsToProcess))
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                    return str_error, end_date_time, log
                second_undistorted_image_geometry = None
                try:
                    second_undistorted_image_geometry = ogr.CreateGeometryFromWkt(secondUndistortedImageWktGeometry)
                except Exception as e:
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nComputing geometry for undistorted image: {}\nGDAL error:\n{}'
                                  .format(second_camera.label, e.args[0]))
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfPairsToProcess)
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        QApplication.processEvents()
                    return str_error, end_date_time, log
                if not second_undistorted_image_geometry.IsValid():
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nComputing geometry for undistorted image: {}\nInvalid geometry'
                                  .format(second_camera.label))
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfPairsToProcess)
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        QApplication.processEvents()
                    return str_error, end_date_time, log
                second_undistorted_image_geometry_wkb = None
                try:
                    second_undistorted_image_geometry_wkb = second_undistorted_image_geometry.ExportToWkb()
                except Exception as e:
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nExporting to WKB computed geometry for undistorted image: {}\nGDAL error:\n{}'
                                  .format(second_camera.label, e.args[0]))
                    if dialog:
                        dialog.processProgressBar.setValue(len(numberOfPairsToProcess))
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                    return str_error, end_date_time, log
                # report file
                content = "COMPUTING RECTIFYING HOMOGRAPHIES REPORT\n"
                content += "- First image ..........: " + first_camera.label + "\n"
                content += "  Images file content ..: " + str_image1 + "\n"
                content += "- Second image .........: " + second_camera.label + "\n"
                content += "  Images file content ..: " + str_image2 + "\n"
                content += "- Homography matrix, H1 = "
                for row in range(3):
                    if row > 0:
                        content += "                         "
                    for column in range(3):
                        content += ("{:30.16f}".format(first_camera_H[row, column]))
                    content += "\n"
                content += "- Inverse matrix, H1    = "
                for row in range(3):
                    if row > 0:
                        content += "                         "
                    for column in range(3):
                        content += ("{:30.16f}".format(first_camera_invH[row, column]))
                    content += "\n"
                content += "- Homography matrix, H2 = "
                for row in range(3):
                    if row > 0:
                        content += "                         "
                    for column in range(3):
                        content += ("{:30.16f}".format(second_camera_H[row, column]))
                    content += "\n"
                content += "- Inverse matrix, H2    = "
                for row in range(3):
                    if row > 0:
                        content += "                         "
                    for column in range(3):
                        content += ("{:30.16f}".format(second_camera_invH[row, column]))
                    content += "\n"
                content += "- Q =                     "
                for row in range(4):
                    if row > 0:
                        content += "                         "
                    for column in range(4):
                        content += ("{:30.16f}".format(Q[row, column]))
                    content += "\n"
                firstImageEpipolarEnvelopeWkt = "POLYGON(("
                firstImageEpipolarEnvelopeWkt += ("{:.0f}".format(firstEpipolarEnvelope[0]))
                firstImageEpipolarEnvelopeWkt += " "
                firstImageEpipolarEnvelopeWkt += ("{:.0f}".format(-1 * firstEpipolarEnvelope[1]))
                firstImageEpipolarEnvelopeWkt += ","
                firstImageEpipolarEnvelopeWkt += ("{:.0f}".format(firstEpipolarEnvelope[2]))
                firstImageEpipolarEnvelopeWkt += " "
                firstImageEpipolarEnvelopeWkt += ("{:.0f}".format(-1 * firstEpipolarEnvelope[1]))
                firstImageEpipolarEnvelopeWkt += ","
                firstImageEpipolarEnvelopeWkt += ("{:.0f}".format(firstEpipolarEnvelope[2]))
                firstImageEpipolarEnvelopeWkt += " "
                firstImageEpipolarEnvelopeWkt += ("{:.0f}".format(-1 * firstEpipolarEnvelope[3]))
                firstImageEpipolarEnvelopeWkt += ","
                firstImageEpipolarEnvelopeWkt += ("{:.0f}".format(firstEpipolarEnvelope[0]))
                firstImageEpipolarEnvelopeWkt += " "
                firstImageEpipolarEnvelopeWkt += ("{:.0f}".format(-1 * firstEpipolarEnvelope[3]))
                firstImageEpipolarEnvelopeWkt += ","
                firstImageEpipolarEnvelopeWkt += ("{:.0f}".format(firstEpipolarEnvelope[0]))
                firstImageEpipolarEnvelopeWkt += " "
                firstImageEpipolarEnvelopeWkt += ("{:.0f}".format(-1 * firstEpipolarEnvelope[1]))
                firstImageEpipolarEnvelopeWkt += "))"
                secondImageEpipolarEnvelopeWkt = "POLYGON(("
                secondImageEpipolarEnvelopeWkt += ("{:.0f}".format(secondEpipolarEnvelope[0]))
                secondImageEpipolarEnvelopeWkt += " "
                secondImageEpipolarEnvelopeWkt += ("{:.0f}".format(-1 * secondEpipolarEnvelope[1]))
                secondImageEpipolarEnvelopeWkt += ","
                secondImageEpipolarEnvelopeWkt += ("{:.0f}".format(secondEpipolarEnvelope[2]))
                secondImageEpipolarEnvelopeWkt += " "
                secondImageEpipolarEnvelopeWkt += ("{:.0f}".format(-1 * secondEpipolarEnvelope[1]))
                secondImageEpipolarEnvelopeWkt += ","
                secondImageEpipolarEnvelopeWkt += ("{:.0f}".format(secondEpipolarEnvelope[2]))
                secondImageEpipolarEnvelopeWkt += " "
                secondImageEpipolarEnvelopeWkt += ("{:.0f}".format(-1 * secondEpipolarEnvelope[3]))
                secondImageEpipolarEnvelopeWkt += ","
                secondImageEpipolarEnvelopeWkt += ("{:.0f}".format(secondEpipolarEnvelope[0]))
                secondImageEpipolarEnvelopeWkt += " "
                secondImageEpipolarEnvelopeWkt += ("{:.0f}".format(-1 * secondEpipolarEnvelope[3]))
                secondImageEpipolarEnvelopeWkt += ","
                secondImageEpipolarEnvelopeWkt += ("{:.0f}".format(secondEpipolarEnvelope[0]))
                secondImageEpipolarEnvelopeWkt += " "
                secondImageEpipolarEnvelopeWkt += ("{:.0f}".format(-1 * secondEpipolarEnvelope[1]))
                secondImageEpipolarEnvelopeWkt += "))"
                content += "- First image stereo pair WKT geometry ..............: " + firstImageWktGeometry + "\n"
                content += "- First image undistorted stereo pair WKT geometry ..: " + firstUndistortedImageWktGeometry + "\n"
                content += "- Second image stereo pair WKT geometry .............: " + secondImageWktGeometry + "\n"
                content += "- Second image undistorted stereo pair WKT geometry .: " + secondUndistortedImageWktGeometry + "\n"
                content += "- First image epipolar WKT geometry .................: " + firstImageEpipolarWktGeometry + "\n"
                content += "- Second image epipolar WKT geometry ................: " + secondImageEpipolarWktGeometry + "\n"
                content += "- First image epipolar envelope WKT geometry ........: " + firstImageEpipolarEnvelopeWkt + "\n"
                content += "- Second image epipolar envelope WKT geometry .......: " + secondImageEpipolarEnvelopeWkt + "\n"
                first_camera_basename = os.path.basename(first_camera.image_file_path).split('.')[0]
                second_camera_basename = os.path.basename(second_camera.image_file_path).split('.')[0]
                report_file_path = (report_files_output_path +
                                    '/' + first_camera_basename + '_' + second_camera_basename + '.txt')
                report_file_path = os.path.normpath(report_file_path)
                try:
                    with open(report_file_path, "w") as f:
                        f.write(content)
                except Exception as e:
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nError occurred when opening:\n{}\nto write:\n{}'.format(report_file_path, e))
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfPairsToProcess)
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        QApplication.processEvents()
                    return str_error, end_date_time, log
                stereopair_geometry_wkb = None
                try:
                    stereopair_geometry_wkb = stereopair_geometry.ExportToWkb()
                except Exception as e:
                    str_error += ('Computing rectifying homographies')
                    str_error += ('\nFor image: {} and image: {}'.
                                  format(first_camera.label, second_camera.label))
                    str_error += ('\nExporting to WKB stereopair\nGDAL error:\n{}'
                                  .format(e.args[0]))
                    if dialog:
                        dialog.processProgressBar.setValue(len(numberOfPairsToProcess))
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                    return str_error, end_date_time, log
                firstEpipolarEnvelopeStr = ""
                for npp in range(4):
                    firstEpipolarEnvelopeStr += ("{:.0f}".format(firstEpipolarEnvelope[npp]))
                    if npp < 3:
                        firstEpipolarEnvelopeStr += defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR
                secondEpipolarEnvelopeStr = ""
                for npp in range(4):
                    secondEpipolarEnvelopeStr += ("{:.0f}".format(secondEpipolarEnvelope[npp]))
                    if npp < 3:
                        secondEpipolarEnvelopeStr += defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR
                fImgHStr = ""
                sImgHStr = ""
                fImgInvHStr = ""
                sImgInvHStr = ""
                for row in range(3):
                    for col in range(3):
                        fImgHStr += ("{:.16e}".format(first_camera_H[row, col]))
                        sImgHStr += ("{:.16e}".format(second_camera_H[row, col]))
                        fImgInvHStr += ("{:.16e}".format(first_camera_invH[row, col]))
                        sImgInvHStr += ("{:.16e}".format(second_camera_invH[row, col]))
                        if row == 2 and col == 2:
                            continue
                        fImgHStr += defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR
                        sImgHStr += defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR
                        fImgInvHStr += defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR
                        sImgInvHStr += defs_project.PHOTOGRAMMETRY_PROJECT_STRING_SEPARATOR
                if save_rectified_homographies_images:
                    firstHomographyImageFileName = rectified_homographies_images_output_path
                    firstHomographyImageFileName += "/"
                    firstHomographyImageFileName += first_camera_basename
                    firstHomographyImageFileName += "_"
                    firstHomographyImageFileName += second_camera_basename
                    firstHomographyImageFileName += ".jpg"
                    secondHomographyImageFileName = rectified_homographies_images_output_path
                    secondHomographyImageFileName += "/"
                    secondHomographyImageFileName += second_camera_basename
                    secondHomographyImageFileName += "_"
                    secondHomographyImageFileName += first_camera_basename
                    secondHomographyImageFileName += ".jpg"
                    str_error = warp_perspective(first_camera.image_file_path,
                                                 firstHomographyImageFileName,
                                                 first_camera_invH)
                    if str_error:
                        str_error += ('Computing rectifying homographies')
                        str_error += ('\nFor image: {} and image: {}'.
                                      format(first_camera.label, second_camera.label))
                        str_error += ('\nError in warp perspective:\n{}'
                                      .format(str_error))
                        if dialog:
                            dialog.processProgressBar.setValue(len(numberOfPairsToProcess))
                            dialog.processInformationGroupBox.setEnabled(False)
                            dialog.processLineEdit.clear()
                            dialog.processProgressBar.reset()
                        return str_error, end_date_time, log
                    str_error = warp_perspective(second_camera.image_file_path,
                                                 secondHomographyImageFileName,
                                                 second_camera_invH)
                    if str_error:
                        str_error += ('Computing rectifying homographies')
                        str_error += ('\nFor image: {} and image: {}'.
                                      format(second_camera.label, first_camera.label))
                        str_error += ('\nError in warp perspective:\n{}'
                                      .format(str_error))
                        if dialog:
                            dialog.processProgressBar.setValue(len(numberOfPairsToProcess))
                            dialog.processInformationGroupBox.setEnabled(False)
                            dialog.processLineEdit.clear()
                            dialog.processProgressBar.reset()
                        return str_error, end_date_time, log
                    feature = []
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_ID
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_ID]
                    field[defs_gdal.FIELD_VALUE_TAG] = first_camera.id
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_ID
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_ID]
                    field[defs_gdal.FIELD_VALUE_TAG] = second_camera.id
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_WKT
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_WKT]
                    field[defs_gdal.FIELD_VALUE_TAG] = firstImageWktGeometry
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_UND_WKT
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_UND_WKT]
                    field[defs_gdal.FIELD_VALUE_TAG] = firstUndistortedImageWktGeometry
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_EPIPOLAR_ENVELOPE
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_EPIPOLAR_ENVELOPE]
                    field[defs_gdal.FIELD_VALUE_TAG] = firstEpipolarEnvelopeStr
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_HOMOGRAPHY
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_HOMOGRAPHY]
                    field[defs_gdal.FIELD_VALUE_TAG] = fImgHStr
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_INVERSE_HOMOGRAPHY
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_INVERSE_HOMOGRAPHY]
                    field[defs_gdal.FIELD_VALUE_TAG] = fImgInvHStr
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_FILE
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_FILE]
                    field[defs_gdal.FIELD_VALUE_TAG] = firstHomographyImageFileName
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_WKT
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_WKT]
                    field[defs_gdal.FIELD_VALUE_TAG] = secondImageWktGeometry
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_UND_WKT
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_UND_WKT]
                    field[defs_gdal.FIELD_VALUE_TAG] = secondUndistortedImageWktGeometry
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_EPIPOLAR_ENVELOPE
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_EPIPOLAR_ENVELOPE]
                    field[defs_gdal.FIELD_VALUE_TAG] = secondEpipolarEnvelopeStr
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_HOMOGRAPHY
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_HOMOGRAPHY]
                    field[defs_gdal.FIELD_VALUE_TAG] = sImgHStr
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_INVERSE_HOMOGRAPHY
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_INVERSE_HOMOGRAPHY]
                    field[defs_gdal.FIELD_VALUE_TAG] = sImgInvHStr
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_FILE
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_FILE]
                    field[defs_gdal.FIELD_VALUE_TAG] = secondHomographyImageFileName
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FP_GEOM
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
                        defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FP_GEOM]
                    field[defs_gdal.FIELD_VALUE_TAG] = stereopair_geometry_wkb
                    feature.append(field)
                    features.append(feature)
                    if not first_camera.id in self.spObjectGeometryByImagesIds:
                        self.spObjectGeometryByImagesIds[first_camera.id] = {}
                    self.spObjectGeometryByImagesIds[first_camera.id][second_camera.id] = stereopair_geometry
                    if not second_camera.id in self.spObjectGeometryByImagesIds:
                        self.spObjectGeometryByImagesIds[second_camera.id] = {}
                    self.spObjectGeometryByImagesIds[second_camera.id][first_camera.id] = stereopair_geometry
                    if not first_camera.id in self.spImageGeometryByImagesIds:
                        self.spImageGeometryByImagesIds[first_camera.id] = {}
                    self.spImageGeometryByImagesIds[first_camera.id][second_camera.id] = first_image_geometry
                    if not second_camera.id in self.spImageGeometryByImagesIds:
                        self.spImageGeometryByImagesIds[second_camera.id] = {}
                    self.spImageGeometryByImagesIds[second_camera.id][first_camera.id] = second_image_geometry
                    if not first_camera.id in self.spUndistortedImageGeometryByImagesIds:
                        self.spUndistortedImageGeometryByImagesIds[first_camera.id] = {}
                    self.spUndistortedImageGeometryByImagesIds[first_camera.id][
                        second_camera.id] = first_undistorted_image_geometry
                    if not second_camera.id in self.spUndistortedImageGeometryByImagesIds:
                        self.spUndistortedImageGeometryByImagesIds[second_camera.id] = {}
                    self.spUndistortedImageGeometryByImagesIds[second_camera.id][
                        first_camera.id] = second_undistorted_image_geometry
                    if not first_camera.id in self.spEpipolarEnvelopeByImagesIds:
                        self.spEpipolarEnvelopeByImagesIds[first_camera.id] = {}
                    self.spEpipolarEnvelopeByImagesIds[first_camera.id][
                        second_camera.id] = firstEpipolarEnvelope  # minColum,minRow,maxColum,maxRow
                    if not second_camera.id in self.spEpipolarEnvelopeByImagesIds:
                        self.spEpipolarEnvelopeByImagesIds[second_camera.id] = {}
                    self.spEpipolarEnvelopeByImagesIds[second_camera.id][
                        first_camera.id] = secondEpipolarEnvelope  # minColum,minRow,maxColum,maxRow
                    if not first_camera.id in self.homographyMatrixByCamerasId:
                        self.homographyMatrixByCamerasId[first_camera.id] = {}
                    self.homographyMatrixByCamerasId[first_camera.id][second_camera.id] = first_camera_H
                    if not second_camera.id in self.homographyMatrixByCamerasId:
                        self.homographyMatrixByCamerasId[second_camera.id] = {}
                    self.homographyMatrixByCamerasId[second_camera.id][first_camera.id] = second_camera_H
                    if not first_camera.id in self.inverseHomographyMatrixByCamerasId:
                        self.inverseHomographyMatrixByCamerasId[first_camera.id] = {}
                    self.inverseHomographyMatrixByCamerasId[first_camera.id][second_camera.id] = first_camera_invH
                    if not second_camera.id in self.inverseHomographyMatrixByCamerasId:
                        self.inverseHomographyMatrixByCamerasId[second_camera.id] = {}
                    self.inverseHomographyMatrixByCamerasId[second_camera.id][first_camera.id] = second_camera_invH
                    if not first_camera.id in self.epipolarFileNameByCamerasId:
                        self.epipolarFileNameByCamerasId[first_camera.id] = {}
                    self.epipolarFileNameByCamerasId[first_camera.id][second_camera.id] = firstHomographyImageFileName
                    if not second_camera.id in self.epipolarFileNameByCamerasId:
                        self.epipolarFileNameByCamerasId[second_camera.id] = {}
                    self.epipolarFileNameByCamerasId[second_camera.id][first_camera.id] = secondHomographyImageFileName
                    stereopair_multigeometry.AddGeometry(stereopair_geometry)
        if dialog:
            dialog.processProgressBar.setValue(numberOfPairsToProcess)
            dialog.processInformationGroupBox.setEnabled(False)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            QApplication.processEvents()
        features_by_layer = {}
        features_by_layer[defs_project.IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME] = features
        str_error = GDALTools.write_features(self.file_path, features_by_layer)
        if str_error:
            str_error = ('Error storing rectifying homographies:\n{}'.format(str_error))
            return str_error, end_date_time, log
        stereopair_union_geometry = None
        try:
            stereopair_union_geometry = stereopair_multigeometry.UnionCascaded()
        except Exception as e:
            str_error += ('Computing tile')
            str_error += ('\nCreating stereoscopic union geometry GDAL error:\n{}'.format(e.args[0]))
            return str_error, end_date_time, log
        stereopair_union_geometry_wkt = None
        try:
            stereopair_union_geometry_wkt = stereopair_union_geometry.ExportToWkt()
        except Exception as e:
            str_error += ('Computing tile')
            str_error += ('\nExporting stereoscopic union geometry to WKT GDAL error:\n{}'.format(e.args[0]))
            return str_error, end_date_time, log
        minX, maxX, minY, maxY = stereopair_union_geometry.GetEnvelope()
        self.spUnionMinFc = int(np.floor(minX))
        self.spUnionMinSc = int(np.floor(minY))
        self.spUnionMaxFc = int(np.ceil(maxX))
        self.spUnionMaxSc = int(np.ceil(maxY))
        self.stereopair_union_geometry = stereopair_union_geometry
        images_tiles_as_string = defs_project.IMAGES_TILES_VALUES
        for tile_as_string in images_tiles_as_string:
            lodSize = int(tile_as_string)
            tile_table_name = defs_project.IMAGES_TILES_PREFIX_TABLE_NAME + tile_as_string
            self.imagesMaximumRamMBsBySize[lodSize] = 0.
            numberOfTilesInLOD = 0
            minFc = self.spUnionMinFc
            while minFc < self.spUnionMaxFc:
                minSc = self.spUnionMinSc
                while minSc < self.spUnionMaxSc:
                    minSc += lodSize
                    numberOfTilesInLOD = numberOfTilesInLOD + 1
                minFc += lodSize
            if dialog:
                dialog.processInformationGroupBox.setEnabled(True)
                dialog.processLineEdit.clear()
                dialog.processProgressBar.reset()
                text = ('Computing {:.0f} tiles for LOD size: {}'.format(numberOfTilesInLOD, tile_as_string))
                dialog.processLineEdit.setText(text)
                dialog.processLineEdit.adjustSize()
                dialog.processProgressBar.setMaximum(numberOfTilesInLOD)
                dialog.processLineEdit.adjustSize()
                QApplication.processEvents()
            features = []
            numberOfProcessedTiles = 0
            tileX = 0
            minX = self.spUnionMinFc
            minXOverSize = minX - defs_project.IMAGES_TILES_OVERSIZE_VALUE
            while minX < self.spUnionMaxFc:
                maxX = minX + lodSize
                maxXOverSize = maxX + defs_project.IMAGES_TILES_OVERSIZE_VALUE
                tileY = 0
                minY = self.spUnionMinSc
                minYOverSize = minY - defs_project.IMAGES_TILES_OVERSIZE_VALUE
                while minY < self.spUnionMaxSc:
                    numberOfProcessedTiles = numberOfProcessedTiles + 1
                    if dialog:
                        dialog.processProgressBar.setValue(numberOfProcessedTiles)
                        QApplication.processEvents()
                    maxY = minY + lodSize
                    maxYOverSize = maxY + defs_project.IMAGES_TILES_OVERSIZE_VALUE
                    wktGeometry = "POLYGON(("
                    wktGeometry += ("{:.0f}".format(minX))
                    wktGeometry += " "
                    wktGeometry += ("{:.0f}".format(minY))
                    wktGeometry += ","
                    wktGeometry += ("{:.0f}".format(minX))
                    wktGeometry += " "
                    wktGeometry += ("{:.0f}".format(maxY))
                    wktGeometry += ","
                    wktGeometry += ("{:.0f}".format(maxX))
                    wktGeometry += " "
                    wktGeometry += ("{:.0f}".format(maxY))
                    wktGeometry += ","
                    wktGeometry += ("{:.0f}".format(maxX))
                    wktGeometry += " "
                    wktGeometry += ("{:.0f}".format(minY))
                    wktGeometry += ","
                    wktGeometry += ("{:.0f}".format(minX))
                    wktGeometry += " "
                    wktGeometry += ("{:.0f}".format(minY))
                    wktGeometry += "))"
                    tile_geometry = None
                    try:
                        tile_geometry = ogr.CreateGeometryFromWkt(wktGeometry)
                    except Exception as e:
                        str_error += ('Computing tile')
                        str_error += ('\nFor LOD size: {:0f}'.format(lodSize))
                        str_error += ('\nComputing geometry GDAL error:\n{}'.format(e.args[0]))
                        if dialog:
                            dialog.processProgressBar.setValue(numberOfTilesInLOD)
                            dialog.processInformationGroupBox.setEnabled(False)
                            dialog.processLineEdit.clear()
                            dialog.processProgressBar.reset()
                            QApplication.processEvents()
                        return str_error, end_date_time, log
                    if not tile_geometry.IsValid():
                        str_error += ('Computing tile')
                        str_error += ('\nFor LOD size: {:0f}'.format(lodSize))
                        str_error += ('\nComputing geometry get invalid geometry')
                        if dialog:
                            dialog.processProgressBar.setValue(numberOfTilesInLOD)
                            dialog.processInformationGroupBox.setEnabled(False)
                            dialog.processLineEdit.clear()
                            dialog.processProgressBar.reset()
                            QApplication.processEvents()
                        return str_error, end_date_time, log
                    tile_geometry_wkb = None
                    try:
                        tile_geometry_wkb = tile_geometry.ExportToWkb()
                    except Exception as e:
                        str_error += ('Computing tile')
                        str_error += ('\nFor LOD size: {:0f}'.format(lodSize))
                        str_error += ('\nExporting geometry to WKB GDAL error:\n{}'.format(e.args[0]))
                        if dialog:
                            dialog.processProgressBar.setValue(len(numberOfTilesInLOD))
                            dialog.processInformationGroupBox.setEnabled(False)
                            dialog.processLineEdit.clear()
                            dialog.processProgressBar.reset()
                        return str_error, end_date_time, log
                    wktOverSizeGeometry = "POLYGON(("
                    wktOverSizeGeometry += ("{:.1f}".format(minXOverSize))
                    wktOverSizeGeometry += " "
                    wktOverSizeGeometry += ("{:.1f}".format(minYOverSize))
                    wktOverSizeGeometry += ","
                    wktOverSizeGeometry += ("{:.1f}".format(minXOverSize))
                    wktOverSizeGeometry += " "
                    wktOverSizeGeometry += ("{:.1f}".format(maxYOverSize))
                    wktOverSizeGeometry += ","
                    wktOverSizeGeometry += ("{:.1f}".format(maxXOverSize))
                    wktOverSizeGeometry += " "
                    wktOverSizeGeometry += ("{:.1f}".format(maxYOverSize))
                    wktOverSizeGeometry += ","
                    wktOverSizeGeometry += ("{:.1f}".format(maxXOverSize))
                    wktOverSizeGeometry += " "
                    wktOverSizeGeometry += ("{:.1f}".format(minYOverSize))
                    wktOverSizeGeometry += ","
                    wktOverSizeGeometry += ("{:.1f}".format(minXOverSize))
                    wktOverSizeGeometry += " "
                    wktOverSizeGeometry += ("{:.1f}".format(minYOverSize))
                    wktOverSizeGeometry += "))"
                    tile_oversize_geometry = None
                    try:
                        tile_oversize_geometry = ogr.CreateGeometryFromWkt(wktOverSizeGeometry)
                    except Exception as e:
                        str_error += ('Computing tile')
                        str_error += ('\nFor LOD size: {:0f}'.format(lodSize))
                        str_error += ('\nComputing oversize geometry GDAL error:\n{}'.format(e.args[0]))
                        if dialog:
                            dialog.processProgressBar.setValue(numberOfTilesInLOD)
                            dialog.processInformationGroupBox.setEnabled(False)
                            dialog.processLineEdit.clear()
                            dialog.processProgressBar.reset()
                            QApplication.processEvents()
                        return str_error, end_date_time, log
                    if not tile_oversize_geometry.IsValid():
                        str_error += ('Computing tile')
                        str_error += ('\nFor LOD size: {:0f}'.format(lodSize))
                        str_error += ('\nComputing oversize geometry get invalid geometry')
                        if dialog:
                            dialog.processProgressBar.setValue(numberOfTilesInLOD)
                            dialog.processInformationGroupBox.setEnabled(False)
                            dialog.processLineEdit.clear()
                            dialog.processProgressBar.reset()
                            QApplication.processEvents()
                        return str_error, end_date_time, log
                    useTile = False
                    if stereopair_union_geometry.Overlaps(tile_geometry):
                        useTile = True
                    elif stereopair_union_geometry.Contains(tile_geometry):
                        useTile = True
                    if not useTile:
                        minY += lodSize
                        tileY = tileY + 1
                        continue
                    imagesIds = []
                    ramMbs = 0.
                    imagesIdsInTile = ""
                    for camera_id in self.spImageGeometryByImagesIds:
                        if camera_id in imagesIds:
                            continue
                        if not camera_id in geometryImagesInStereopairsByImageId:
                            continue
                        image_geometry = geometryImagesInStereopairsByImageId[camera_id]
                        useImage = False
                        if image_geometry.Overlaps(tile_oversize_geometry):
                            useImage = True
                        elif image_geometry.Contains(tile_oversize_geometry):
                            useImage = True
                        elif image_geometry.Within(tile_oversize_geometry):
                            useImage = True
                        if not useImage:
                            continue
                        camera = at_block.get_camera_from_camera_id(camera_id)
                        sensor = self.at_block_by_label[at_block_label].sensor_by_id[camera.sensor_id]
                        camera_columns = sensor.width
                        camera_rows = sensor.height
                        imageMBytes = camera_columns * camera_rows / 1024. / 1024.
                        ramMbs += imageMBytes
                        strImageId = str(camera_id)
                        if len(imagesIds) > 0:
                            imagesIdsInTile += ";"
                        imagesIdsInTile += strImageId
                        imagesIds.append(camera_id)
                    if len(imagesIds) == 0:
                        minY += lodSize
                        tileY = tileY + 1
                        continue
                    feature = []
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_TILES_FIELD_TILE_X
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[tile_table_name][
                        defs_project.IMAGES_TILES_FIELD_TILE_X]
                    field[defs_gdal.FIELD_VALUE_TAG] = tileX
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_TILES_FIELD_TILE_Y
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[tile_table_name][
                        defs_project.IMAGES_TILES_FIELD_TILE_Y]
                    field[defs_gdal.FIELD_VALUE_TAG] = tileY
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_TILES_IMAGES_ID
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[tile_table_name][
                        defs_project.IMAGES_TILES_IMAGES_ID]
                    field[defs_gdal.FIELD_VALUE_TAG] = imagesIdsInTile
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_TILES_FIELD_RAM_MBS
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[tile_table_name][
                        defs_project.IMAGES_TILES_FIELD_RAM_MBS]
                    field[defs_gdal.FIELD_VALUE_TAG] = ramMbs
                    feature.append(field)
                    field = {}
                    field[defs_gdal.FIELD_NAME_TAG] = defs_project.IMAGES_TILES_FIELD_FP_GEOM
                    field[defs_gdal.FIELD_TYPE_TAG] \
                        = defs_project.fields_by_layer[tile_table_name][
                        defs_project.IMAGES_TILES_FIELD_FP_GEOM]
                    field[defs_gdal.FIELD_VALUE_TAG] = tile_geometry_wkb
                    feature.append(field)
                    features.append(feature)
                    if lodSize in self.imagesMaximumRamMBsBySize:
                        if ramMbs > self.imagesMaximumRamMBsBySize[lodSize]:
                            self.imagesMaximumRamMBsBySize[lodSize] = ramMbs
                        else:
                            self.imagesMaximumRamMBsBySize[lodSize] = ramMbs
                    if not lodSize in self.imagesTileRamMBsBySize:
                        self.imagesTileRamMBsBySize[lodSize] = {}
                    if not tileX in self.imagesTileRamMBsBySize[lodSize]:
                        self.imagesTileRamMBsBySize[lodSize][tileX] = {}
                    self.imagesTileRamMBsBySize[lodSize][tileX][tileY] = ramMbs
                    if not lodSize in self.imagesTilesImagesIdBySize:
                        self.imagesTilesImagesIdBySize[lodSize] = {}
                    if not tileX in self.imagesTilesImagesIdBySize[lodSize]:
                        self.imagesTilesImagesIdBySize[lodSize][tileX] = {}
                    self.imagesTilesImagesIdBySize[lodSize][tileX][tileY] = imagesIds
                    if not lodSize in self.geometryTileBySize:
                        self.geometryTileBySize[lodSize] = {}
                    if not tileX in self.geometryTileBySize[lodSize]:
                        self.geometryTileBySize[lodSize][tileX] = {}
                    self.geometryTileBySize[lodSize][tileX][tileY] = tile_geometry
                    minY += lodSize
                    tileY = tileY + 1
                minX += lodSize
                tileX = tileX + 1
            if dialog:
                dialog.processProgressBar.setValue(numberOfTilesInLOD)
                dialog.processInformationGroupBox.setEnabled(False)
                dialog.processLineEdit.clear()
                dialog.processProgressBar.reset()
                QApplication.processEvents()
            features_by_layer = {}
            features_by_layer[tile_table_name] = features
            str_error = GDALTools.write_features(self.file_path, features_by_layer)
            if str_error:
                str_error = ('Error storing data in tile table name:\n{}'.format(tile_table_name))
                return str_error, end_date_time, log
        # store stereoscopic data into management table
        stereoscopic_object_footprint_geometry_as_dict = {}
        stereoscopic_object_footprint_geometry_as_dict[
            defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_TAG_MINIMUM_FC] = self.spUnionMinFc
        stereoscopic_object_footprint_geometry_as_dict[
            defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_TAG_MINIMUM_SC] = self.spUnionMinSc
        stereoscopic_object_footprint_geometry_as_dict[
            defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_TAG_MAXIMUM_FC] = self.spUnionMaxFc
        stereoscopic_object_footprint_geometry_as_dict[
            defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_TAG_MAXIMUM_SC] = self.spUnionMaxSc
        stereoscopic_object_footprint_geometry_as_dict[
            defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_TAG_WKT_GEOMETRY] = stereopair_union_geometry_wkt
        stereoscopic_object_footprint_geometry_as_json = json.dumps(stereoscopic_object_footprint_geometry_as_dict, indent=4)
        features = []
        feature = []
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_NAME
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_NAME]
        field[defs_gdal.FIELD_VALUE_TAG] = defs_project.STEREOSCOPIC_OBJECT_GEOMETRY_MANAGEMENT_FIELD_NAME
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_CONTENT
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_CONTENT]
        field[defs_gdal.FIELD_VALUE_TAG] = stereoscopic_object_footprint_geometry_as_json
        feature.append(field)
        field = {}
        field[defs_gdal.FIELD_NAME_TAG] = defs_project.MANAGEMENT_FIELD_REMARKS
        field[defs_gdal.FIELD_TYPE_TAG] \
            = defs_project.fields_by_layer[defs_project.MANAGEMENT_LAYER_NAME][defs_project.MANAGEMENT_FIELD_REMARKS]
        field[defs_gdal.FIELD_VALUE_TAG] = ""
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
            str_error = ('Error storing stereocopic data in table name:\n{}'.format(defs_project.MANAGEMENT_LAYER_NAME))
            return str_error, end_date_time, log
        end_date_time = datetime.now()
        return str_error, end_date_time, log

    def process_debug_digitizing(self,
                                 process,
                                 dialog = None):
        str_error = ''
        end_date_time = None
        log = None
        name = process[processes_defs_processes.PROCESS_FIELD_NAME]
        # input json file
        parameters_manager = process[processes_defs_processes.PROCESS_FIELD_PARAMETERS]
        if not (defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_PARAMETER_INPUT_FILE
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_PARAMETER_INPUT_FILE))
            return str_error, end_date_time, log
        parameter_input_file = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_PARAMETER_INPUT_FILE]
        input_file_path = str(parameter_input_file)
        if not input_file_path:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_PARAMETER_INPUT_FILE))
            return str_error, end_date_time, log
        if not os.path.exists(input_file_path):
            str_error = ('Process {} has a not existing file parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_PARAMETER_INPUT_FILE))
            return str_error, end_date_time, log
        # output json file
        if not (defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_PARAMETER_OUTPUT_FILE
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_PARAMETER_OUTPUT_FILE))
            return str_error, end_date_time, log
        parameter_output_file = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_PARAMETER_OUTPUT_FILE]
        parameter_output_file = str(parameter_input_file)
        if not parameter_output_file:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_PARAMETER_OUTPUT_FILE))
            return str_error, end_date_time, log
        # if not os.path.exists(parameter_output_file):
        #     str_error = ('Process {} has a not existing file parameter: {}'.
        #                  format(name,
        #                         defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_PARAMETER_OUTPUT_FILE))
        #     return str_error, end_date_time, log
        self.update_objects_fully_qualified_names()
        with open(input_file_path, "r") as file:
            input_data = json.load(file)
        if not defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_STEPS_TAG in input_data:
            str_error = ('Not exists {} in file:\n'.
                         format(defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_STEPS_TAG,
                                input_file_path))
            return str_error, end_date_time, log
        steps = input_data[defs_processes.PROCESS_FUNCTION_DEBUG_DIGITIZING_STEPS_TAG]
        for i in range(len(steps)):
            step = steps[i]
            if not processes_defs_processes.PROCESS_SRC_ATTRIBUTE_CLASS in step:
                str_error = ("Not exists {} attribute in step position: {} in file:\n{}".
                       format(processes_defs_processes.PROCESS_SRC_ATTRIBUTE_CLASS, str(i+1), input_file_path))
                str_error += ("\nfor proccess: {}".format(name))
                return str_error, end_date_time, log
            if not processes_defs_processes.PROCESS_SRC_ATTRIBUTE_METHOD in step:
                str_error = ("Not exists {} attribute in step position: {} in file:\n{}".
                       format(processes_defs_processes.PROCESS_SRC_ATTRIBUTE_METHOD, str(i+1), input_file_path))
                str_error += ("\nfor proccess: {}".format(name))
                return str_error, end_date_time, log
            object_fully_qualified_name = step[processes_defs_processes.PROCESS_SRC_ATTRIBUTE_CLASS]
            object_method_name = step[processes_defs_processes.PROCESS_SRC_ATTRIBUTE_METHOD]
            object_fully_qualified_name = object_fully_qualified_name.lower()
            # object_method_name = object_method_name.lower()
            if not object_fully_qualified_name in self.object_by_fully_qualified_name:
                str_error = ("Not exists registered object: {}".format(object_fully_qualified_name))
                str_error += ("\nfor proccess: {}".format(name))
                return str_error, end_date_time, log
            object = self.object_by_fully_qualified_name[object_fully_qualified_name]
            if object is None:
                str_error = ("None object: {}".format(object_fully_qualified_name))
                str_error += ("\nfor proccess: {}".format(process_name))
                return str_error, end_date_time, log
            method = None
            try:
                method = getattr(object, object_method_name)
            except AttributeError as e:
                str_error = ("For proccess: {}".format(process_name))
                str_error += ("\nError: {}".format(str(e)))
                return str_error, end_date_time, log
            if method is None:
                str_error = ("No found method: {} in object: {}".format(object_method_name, object_fully_qualified_name))
                str_error += ("\nfor proccess: {}".format(process_name))
                return str_error, end_date_time, log
            method_definition_arguments_names = method.__code__.co_varnames[:method.__code__.co_argcount]
            if not processes_defs_processes.PROCESS_SRC_ATTRIBUTE_ARGUMENTS in step:
                str_error = ("Not exists {} attribute in step position: {} in file:\n{}".
                       format(processes_defs_processes.PROCESS_SRC_ATTRIBUTE_ARGUMENTS, str(i+1), input_file_path))
                str_error += ("\nfor proccess: {}".format(process_name))
                return str_error, end_date_time, log
            arguments = step[processes_defs_processes.PROCESS_SRC_ATTRIBUTE_ARGUMENTS]
            arguments_as_dict = {}
            for j in range(len(arguments)):
                if not processes_defs_processes.PROCESS_SRC_ATTRIBUTE_ARGUMENTS_NAME in arguments[j]:
                    str_error = ("In method: {} not exists {} in attribute position: {} in step position: {} in file:\n{}".
                           format(object_method_name, processes_defs_processes.PROCESS_SRC_ATTRIBUTE_ARGUMENTS_NAME,
                                  str(j + 1), str(i+1), input_file_path))
                    str_error += ("\nfor proccess: {}".format(process_name))
                    return str_error, end_date_time, log
                argument_name = arguments[j][processes_defs_processes.PROCESS_SRC_ATTRIBUTE_ARGUMENTS_NAME]
                if not argument_name in method_definition_arguments_names:
                    str_error = ("In definition of method: {} not exists attribute: {} in step position: {} in file:\n{}".
                           format(object_method_name, argument_name,
                                  str(i + 1), input_file_path))
                    str_error += ("\nfor proccess: {}".format(process_name))
                    return str_error, end_date_time, log
                if not processes_defs_processes.PROCESS_SRC_ATTRIBUTE_ARGUMENTS_VALUE in arguments[j]:
                    str_error = ("In method: {} not exists {} in attribute position: {} in step position: {} in file:\n{}".
                           format(object_method_name, processes_defs_processes.PROCESS_SRC_ATTRIBUTE_ARGUMENTS_VALUE,
                                  str(j + 1), str(i+1), input_file_path))
                    str_error += ("\nfor proccess: {}".format(process_name))
                    return str_error, end_date_time, log
                argument_value = arguments[j][processes_defs_processes.PROCESS_SRC_ATTRIBUTE_ARGUMENTS_VALUE]
                arguments_as_dict[argument_name] = argument_value
            return_values = method(**arguments_as_dict)
            str_error_in_method = ''
            if isinstance(return_values, list):
                str_error_in_method = return_values[0]
            elif isinstance(return_values, str):
                str_error_in_method = return_values
            if str_error:
                str_error = ("Executing method: {} in object: {}".format(object_method_name, object_fully_qualified_name))
                str_error += ("\nfor proccess: {}".format(process_name))
                str_error += ("\nerror: {}".format(str_error_in_method))
                return str_error, end_date_time, log
            yo = 1
            # # str_error = object.run_library_process(process, self)
            # str_error, end_date_time, log = method(process, self)
            # if str_error:
            #     Tools.error_msg(str_error)
            #     return

        end_date_time = datetime.now()
        return str_error, end_date_time, log

    def process_gcps_accuracy_analysis(self,
                                       process,
                                       dialog = None):
        str_error = ''
        end_date_time = None
        log = None
        name = process[processes_defs_processes.PROCESS_FIELD_NAME]
        parameters_manager = process[processes_defs_processes.PROCESS_FIELD_PARAMETERS]
        if not (defs_processes.PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_PARAMETER_OUTPUT_FILE_LABEL
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_PARAMETER_OUTPUT_FILE_LABEL))
            return str_error, end_date_time, log
        parameter_output_file = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_PARAMETER_OUTPUT_FILE_LABEL]
        output_file_path = str(parameter_output_file)
        if not output_file_path:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_GCP_ACCURACY_ANALYSIS_PARAMETER_OUTPUT_FILE_LABEL))
            return str_error, end_date_time, log
        content  = 'GROUND CONTROL POINTS ACCURACY ANALYSIS'
        content += '\n======================================='
        content += '\nProject definition: '
        content += '\n- Name ..........................: ' + self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_NAME]
        content += '\n- Author ........................: ' + self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_AUTHOR]
        content += '\n- CRS id ........................: ' + self.crs_id
        content += '\n  Projected CRS id ..............: ' + self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
        content += '\n- Vertical CRS id ...............: ' + self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS]
        # content += '\n- Metashape markers xml file ....: ' + self.metashape_markers_xml_file
        content += '\n- Number of AT Blocks ...........: ' + str(len(self.at_block_by_label))
        for at_block_label in self.at_block_by_label:
            at_block = self.at_block_by_label[at_block_label]
            str_error, at_block_crs_is_geographic = self.crs_tools.is_geographic(at_block.crs_id)
            if str_error:
                str_error = ('For AT Block: {}, getting is geographic CRS: {}\nError:\n{}'
                             .format(at_block_label, at_block.crs_id, str_error))
                return str_error, end_date_time, log
            gcp_crs2d_precision = 4
            ellipsoid_a = ellipsoid_rf = ellipsoid_b = ellipsoid_e2 = None
            if at_block_crs_is_geographic:
                str_error, ellipsoid = self.crs_tools.get_ellipsoid(at_block.crs_id)
                if str_error:
                    str_error = ('For AT Block: {}, getting ellipsoid from CRS: {}\nError:\n{}'
                                 .format(at_block_label, at_block.crs_id, str_error))
                    return str_error, end_date_time, log
                ellipsoid_a = ellipsoid.semi_major_metre
                ellipsoid_rf = ellipsoid.inverse_flattening
                ellipsoid_b = ellipsoid.semi_minor_metre
                ellipsoid_e2 = ellipsoid.es
                gcp_crs2d_precision = 9
            content += '\nAT Block label ..................: ' + at_block.label
            content += '\n- CRS id ........................: ' + at_block.crs_id
            if self.is_metashape_model:
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
                pc_local = None
                if self.is_metashape_model:
                    pc_local = camera.get_pc_chunk()
                else:
                    pc_local = camera.get_pc_enu()
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
                content += '{:12.4f}'.format(pc_local[0])
                content += '{:12.4f}'.format(pc_local[1])
                content += '{:12.4f}'.format(pc_local[2])
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
                if self.is_metashape_model:
                    content += '{:12.4f}'.format(gcp.position_chunk[0])
                    content += '{:12.4f}'.format(gcp.position_chunk[1])
                    content += '{:12.4f}'.format(gcp.position_chunk[2])
                else:
                    content += '{:12.4f}'.format(gcp.position_enu[0])
                    content += '{:12.4f}'.format(gcp.position_enu[1])
                    content += '{:12.4f}'.format(gcp.position_enu[2])
                content += '  {}'.format(gcp.label)
                if len(gcp.label) > gcp_label_max_length:
                    gcp_label_max_length = len(gcp.label)
            content += '\n- From object space to image space (photogrammetric backward projection), ignoring no pinned image points:'
            content += '\n  GCP.Id    Column       Row   ColumnM      RowM  ErrorC  ErrorR Error2d  Image                              Und.Column   Und.Row  Change  GCP.Id'
            for gcp_id in at_block.image_points_by_gcp_id:
                if not gcp_id in at_block.gcps_by_id:
                    continue
                gcp = at_block.gcps_by_id[gcp_id]
                gcp_local = None
                if self.is_metashape_model:
                    gcp_local = gcp.position_chunk
                else:
                    gcp_local = gcp.position_enu
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
                    within = None
                    withinAfterUndistortion = None
                    position_image = None
                    position_undistorted_image = None
                    if self.is_metashape_model:
                        str_error, within, withinAfterUndistortion, position_image, position_undistorted_image \
                            = camera.from_chunk_to_sensor(gcp_local)
                    else:
                        str_error, within, withinAfterUndistortion, position_image, position_undistorted_image \
                            = camera.from_enu_to_sensor(gcp_local)
                    if str_error:
                        return str_error, end_date_time, log
                    # set undistoted computed as measured for test backwar-forward model
                    image_point.set_measured_undistorted_values(position_undistorted_image)
                    error_column = column_m - position_image[0]
                    error_row = row_m - position_image[1]
                    error_2d = np.sqrt((error_column * error_column) + (error_row * error_row))
                    undistort_change_column = position_undistorted_image[0] - position_image[0]
                    undistort_change_row = position_undistorted_image[1] - position_image[1]
                    undistort_change_2d = np.sqrt(undistort_change_column ** 2. + undistort_change_row ** 2.)
                    content += '\n{:>8s}'.format(str(gcp_id))
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
            if not self.is_metashape_model:
                try:
                    with open(output_file_path, "w") as f:
                        f.write(content)
                except Exception as e:
                    str_error = (
                        'Process {}\nError occurred when opening:\n{}\nto read:\n{}'.format(name, output_file_path, e))
                    return str_error, end_date_time, log
                end_date_time = datetime.now()
                return str_error, end_date_time, log
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
                    return str_error, end_date_time, log
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
                    return str_error, end_date_time, log
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
            str_error = ('Process {}\nError occurred when opening:\n{}\nto write:\n{}'.format(name, output_file_path, e))
            return str_error, end_date_time, log
        end_date_time = datetime.now()
        return str_error, end_date_time, log

    def process_get_image_footprints(self,
                                     process,
                                     dialog):
        str_error = ''
        end_date_time = None
        log = None
        name = process[processes_defs_processes.PROCESS_FIELD_NAME]
        parameters_manager = process[processes_defs_processes.PROCESS_FIELD_PARAMETERS]
        if not defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM in parameters_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM))
            return str_error, end_date_time, log
        parameter_dem_file_path = parameters_manager.parameters[defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM]
        parameter_dem_file_as_dict = json.loads(str(parameter_dem_file_path))
        dem_file_path = parameter_dem_file_as_dict[defs_pars.TAG_FILE_PATH]
        dem_file_path = os.path.normpath(dem_file_path)
        dem_layer_index = parameter_dem_file_as_dict[defs_pars.TAG_LAYER_INDEX]
        dem_file_scale = parameter_dem_file_as_dict[defs_pars.TAG_SCALE]
        dem_file_offset = parameter_dem_file_as_dict[defs_pars.TAG_OFFSET]
        if not dem_file_path:
            str_error = ('Process: {} has a empty parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM))
            return str_error, end_date_time, log
        if not os.path.exists(dem_file_path):
            str_error = ('Process: {} has a parameter: {}\ndoes not exists'.
                         format(name, defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM))
            return str_error, end_date_time, log
        if not defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM_CRS in parameters_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM_CRS))
            return str_error, end_date_time, log
        parameter_dem_crs_id = parameters_manager.parameters[defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM_CRS]
        dem_crs_id = str(parameter_dem_crs_id) # can be empty for use internal of the DEM
        # if not dem_crs_id:
        #     str_error = ('Process: {} has a empty parameter: {}'.
        #                  format(name, defs_project.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_DEM_CRS))
        #     return str_error
        if not defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_NOP in parameters_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_NOP))
            return str_error, end_date_time, log
        parameter_nop = parameters_manager.parameters[defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_NOP]
        str_nop = str(parameter_nop)
        number_of_points_by_side = 3
        try:
            number_of_points_by_side = int(str_nop)
        except ValueError:
            str_error = ('Process: {} does not have a integer parameter: {}, is: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_NOP, str_nop))
            return str_error, end_date_time, log
        if not defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_ENABLED_IMAGES in parameters_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_ENABLED_IMAGES))
            return str_error, end_date_time, log
        parameter_enabled_images = parameters_manager.parameters[defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_ENABLED_IMAGES]
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
                    return str_error, end_date_time, log
            str_error = raster_dem.set_from_file(dem_file_path)
            if str_error:
                str_error = ('Setting raster DEM from file: {}\nError:\n{}'
                             .format(dem_file_path, str_error))
                return str_error, end_date_time, log
            raster_dem.set_check_domain(False) # get solution for out points
            self.raster_dem_by_file_path[dem_file_path] = raster_dem
        else:
            raster_dem = self.raster_dem_by_file_path[dem_file_path]
        str_error = raster_dem.load()
        if str_error:
            str_error = ('Loading in memory raster DEM from file: {}\nError:\n{}'
                         .format(dem_file_path, str_error))
            return str_error, end_date_time, log
        str_error = self.update_enabled_images_from_db()
        if str_error:
            str_error = ('Updating enabled images from file: {}\nError:\n{}'
                         .format(self.file_path, str_error))
            return str_error, end_date_time, log
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
                return str_error, end_date_time, log
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
                return str_error, end_date_time, log
            if not footprint_geometry.IsValid():
                str_error = ('Computing footprint for image: {}\nInvalid geometry'.format(camera.label))
                if dialog:
                    dialog.processProgressBar.setValue(len(cameras_to_process))
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                return str_error, end_date_time, log
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
                return str_error, end_date_time, log
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
                return str_error, end_date_time, log
            if not undistorted_footprint_geometry.IsValid():
                str_error = ('Computing undistorted footprint for image: {}\nInvalid geometry'.format(camera.label))
                if dialog:
                    dialog.processProgressBar.setValue(len(cameras_to_process))
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                return str_error, end_date_time, log
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
                return str_error, end_date_time, log
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
            return str_error, end_date_time, log
        features_by_layer = {}
        features_by_layer[defs_project.IMAGES_UNDISTORTED_FP_TABLE_NAME] = undistorted_features
        str_error = GDALTools.write_features(self.file_path, features_by_layer)
        if str_error:
            str_error = ('Error storing footprints:\n{}'.format(str_error))
            return str_error, end_date_time, log
        end_date_time = datetime.now()
        return str_error, end_date_time, log

    def process_images_to_object_from_ascii_file(self,
                                                 process,
                                                 dialog = None):
        str_error = ''
        end_date_time = None
        log = None
        name = process[processes_defs_processes.PROCESS_FIELD_NAME]
        parameters_manager = process[processes_defs_processes.PROCESS_FIELD_PARAMETERS]
        if not (defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_INPUT_FILE_LABEL
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_INPUT_FILE_LABEL))
            return str_error, end_date_time, log
        parameter_input_file_path = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_INPUT_FILE_LABEL]
        input_file_path = str(parameter_input_file_path)
        if not parameter_input_file_path:
            str_error = ('Process: {} has a empty parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_INPUT_FILE_LABEL))
            return str_error, end_date_time, log
        input_file_path = os.path.normpath(input_file_path)
        if not os.path.exists(input_file_path):
            str_error = ('Process: {} has a parameter: {}\ndoes not exists'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_INPUT_FILE_LABEL))
            return str_error, end_date_time, log
        if not (defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_INPUT_FILE_FORMAT_LABEL
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_GET_IMAGE_FOOTPRINTS_PARAMETER_NOP))
            return str_error, end_date_time, log
        parameter_input_file_format = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_INPUT_FILE_FORMAT_LABEL]
        input_file_format = str(parameter_input_file_format)
        input_file_format = input_file_format.strip()
        if not input_file_format:
            str_error = ('Process: {} has a parameter: {}\ndoes not exists'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_INPUT_FILE_FORMAT_LABEL))
            return str_error, end_date_time, log
        if (input_file_format.casefold()
                != defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FILE_FORMAT_1.casefold()):
            str_error = ('Process: {} has a parameter: {}\ninvalid'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_INPUT_FILE_FORMAT_LABEL))
            return str_error, end_date_time, log
        if not (defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_NO_HEADER_LINES
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_NO_HEADER_LINES))
            return str_error, end_date_time, log
        parameter_nhl = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_NO_HEADER_LINES]
        str_nop = str(parameter_nhl)
        number_of_header_lines = 0
        try:
            number_of_header_lines = int(str_nop)
        except ValueError:
            str_error = ('Process: {} does not have a integer parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_NO_HEADER_LINES,
                                str_nop))
            return str_error, end_date_time, log
        if not (defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_IMAGE_SPACE_TOLERANCE
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_IMAGE_SPACE_TOLERANCE))
            return str_error, end_date_time, log
        parameter_istol = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_IMAGE_SPACE_TOLERANCE]
        str_img_space_tolerance = str(parameter_istol)
        image_space_tolerance = None
        try:
            image_space_tolerance = float(str_img_space_tolerance)
        except ValueError:
            str_error = ('Process: {} does not have a integer parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_IMAGE_SPACE_TOLERANCE,
                                str_nop))
            return str_error, end_date_time, log
        if not (defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_ENABLED_IMAGES
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_ENABLED_IMAGES))
            return str_error, end_date_time, log
        parameter_enabled_images = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_ENABLED_IMAGES]
        str_enabled = str(parameter_enabled_images)
        only_enabled_images = True
        if str_enabled.casefold() == 'false':
            only_enabled_images = False
        if not (defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_FILE_LABEL
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_FILE_LABEL))
            return str_error, end_date_time, log
        parameter_output_file = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_FILE_LABEL]
        output_file_path = str(parameter_output_file)
        if not output_file_path:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_FILE_LABEL))
            return str_error, end_date_time, log
        output_file_path = os.path.normpath(output_file_path)
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
        if os.path.exists(output_file_path):
            msg_error = ('Error removing output file:\n{}'.format(output_file_path))
            str_error = ('Process: {}, parameter: {}:\n{}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_FILE_LABEL,
                                msg_error))
            return str_error, end_date_time, log
        if not (defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_VECTOR_LAYER
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_VECTOR_LAYER))
            return str_error, end_date_time, log
        parameter_vector_layer = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_VECTOR_LAYER]
        vector_layer_as_dict = json.loads(str(parameter_vector_layer))
        if not vector_layer_as_dict:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_VECTOR_LAYER))
            return str_error, end_date_time, log
        if not defs_pars.TAG_FILE_PATH in vector_layer_as_dict:
            str_error = ('Process {} does not has {} in parameter: {}'.
                         format(name, defs_pars.TAG_FILE_PATH,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_VECTOR_LAYER))
            return str_error, end_date_time, log
        vector_layer_file_path = os.path.normpath(vector_layer_as_dict[defs_pars.TAG_FILE_PATH])
        if not defs_pars.TAG_LAYER_NAME in vector_layer_as_dict:
            str_error = ('Process {} does not has {} in parameter: {}'.
                         format(name, defs_pars.TAG_LAYER_NAME,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_VECTOR_LAYER))
            return str_error, end_date_time, log
        vector_layer_layer_name = os.path.normpath(vector_layer_as_dict[defs_pars.TAG_LAYER_NAME])
        # update exisiting file
        # if os.path.exists(geojson_output_file_path):
        #     os.remove(geojson_output_file_path)
        # if os.path.exists(geojson_output_file_path):
        #     msg_error = ('Error removing geojson output file:\n{}'.format(geojson_output_file_path))
        #     str_error = ('Process: {}, parameter: {}:\n{}'.
        #                  format(name,
        #                         defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_GEOJSON_OUTPUT_FILE_LABEL,
        #                         msg_error))
        #     return str_error, end_date_time, log
        content  = 'IMAGES TO OBJECT FROM ASCII FILE'
        content += '\n================================'
        content += '\nProject definition: '
        content += '\n- Name ..........................: ' + self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_NAME]
        content += '\n- Author ........................: ' + self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_AUTHOR]
        content += '\n- CRS id ........................: ' + self.crs_id
        content += '\n  Projected CRS id ..............: ' + self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
        content += '\n- Vertical CRS id ...............: ' + self.project_definition[defs_project_definition.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS]
        # content += '\n- Metashape markers xml file ....: ' + self.metashape_markers_xml_file
        content += '\n- Number of AT Blocks ...........: ' + str(len(self.at_block_by_label))
        content += '\n- Source file ...................: ' + input_file_path
        content += ('\n- Tolerance outliers image space : {:.1f}, pixels'.format(image_space_tolerance))
        try:
            input_file = open(input_file_path, 'r')
        except IOError:
            msg_error = ('Error opening input file:\n{}'.format(input_file_path))
            str_error = ('Process: {}, parameter: {}:\n{}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_FILE_LABEL,
                                msg_error))
            return str_error, end_date_time, log
        measure_by_image_label_by_point_id = {}
        code_by_point_id = {}
        field_names = None
        if (input_file_format.casefold()
                == defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FILE_FORMAT_1.casefold()):
            field_names = defs_processes.process_function_images_to_object_fields_by_format[
                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FILE_FORMAT_1]
        if field_names is None:
            str_error = ('Process: {} has a parameter: {}\ninvalid'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_INPUT_FILE_FORMAT_LABEL))
            return str_error, end_date_time, log
        count = 0
        point_code_max_length = 0
        for line in input_file:
            count += 1
            if count <= number_of_header_lines:
                continue
            if line.strip() == '':
                continue
            line_values = []
            if (input_file_format.casefold()
                    == defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FILE_FORMAT_1.casefold()):
                line_values = line.strip().split(',')
            if line_values is None:
                msg_error = ('Error reading line {} in input file:\n{}'.format(str(count), input_file_path))
                str_error = ('Process: {}, parameter: {}:\n{}'.
                             format(name,
                                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_FILE_LABEL,
                                    msg_error))
                return str_error, end_date_time, log
            if len(field_names) != len(line_values):
                msg_error = ('Invalid fields reading line {} in input file:\n{}'.format(str(count), input_file_path))
                str_error = ('Process: {}, parameter: {}:\n{}'.
                             format(name,
                                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_FILE_LABEL,
                                    msg_error))
                return str_error, end_date_time, log
            values = {}
            for i in range(len(field_names)):
                value = line_values[i].strip()
                if (field_names[i] == defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_IMAGE_COLUMN
                    or field_names[i] == defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_IMAGE_ROW):
                    try:
                        value = float(value)
                    except ValueError:
                        msg_error = (
                            'Invalid float field value: {} reading line {} in input file:\n{}'
                            .format(values[i].trimmed(), str(count), input_file_path))
                        str_error = ('Process: {}, parameter: {}:\n{}'.
                                     format(name,
                                            defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_FILE_LABEL,
                                            msg_error))
                        return str_error, end_date_time, log
                values[field_names[i]] = value
            point_id = values[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_POINT_ID]
            image_label = values[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_IMAGE_LABEL]
            point_code = values[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_POINT_CODE]
            column = values[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_IMAGE_COLUMN]
            row = values[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_IMAGE_ROW]
            if not point_id in measure_by_image_label_by_point_id:
                measure_by_image_label_by_point_id[point_id] = {}
            measure_by_image_label_by_point_id[point_id][image_label] = {}
            measure_by_image_label_by_point_id[point_id][image_label][
                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_IMAGE_COLUMN]= column
            measure_by_image_label_by_point_id[point_id][image_label][
                defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_IMAGE_ROW] = row
            if not point_id in code_by_point_id:
                code_by_point_id[point_id] = point_code
            else:
                if point_code.casefold() != code_by_point_id[point_id].casefold():
                    msg_error = (
                        'Code value: {} different from previous reading line {} in input file:\n{}'
                        .format(point_code, str(count), input_file_path))
                    str_error = ('Process: {}, parameter: {}:\n{}'.
                                 format(name,
                                        defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FAF_PARAMETER_OUTPUT_FILE_LABEL,
                                        msg_error))
                    return str_error, end_date_time, log
            if len(point_code) > point_code_max_length:
                point_code_max_length = len(point_code)
        crs2d_precision_by_at_block_label = {}
        for at_block_label in self.at_block_by_label:
            at_block = self.at_block_by_label[at_block_label]
            str_error, at_block_crs_is_geographic = self.crs_tools.is_geographic(at_block.crs_id)
            if str_error:
                str_error = ('For AT Block: {}, getting is geographic CRS: {}\nError:\n{}'
                             .format(at_block_label, at_block.crs_id, str_error))
                return str_error, end_date_time, log
            crs2d_precision = 4
            if at_block_crs_is_geographic:
                crs2d_precision = 9
            crs2d_precision_by_at_block_label[at_block_label] = crs2d_precision
        log = {}
        log[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_POINTS] = {}
        for point_id in measure_by_image_label_by_point_id:
            measure_by_image_label = measure_by_image_label_by_point_id[point_id]
            at_block_label_by_image_label = {}
            camera_by_image_label = {}
            at_block_labels = []
            number_of_images_measured_by_at_block_label = {}
            image_measured_coordinates_by_camera_id_by_block_label = {}
            for image_label in measure_by_image_label:
                for at_block_label in self.at_block_by_label:
                    at_block = self.at_block_by_label[at_block_label]
                    camera = at_block.get_camera_from_image_label(image_label)
                    if camera == None:
                        continue
                    if not at_block_label in at_block_labels:
                        image_measured_coordinates_by_camera_id_by_block_label[at_block_label]= {}
                        at_block_labels.append(at_block_label)
                        number_of_images_measured_by_at_block_label[at_block_label] = 0
                    number_of_images_measured_by_at_block_label[at_block_label] \
                        = number_of_images_measured_by_at_block_label[at_block_label] + 1
                    camera_by_image_label[image_label] = camera
                    at_block_label_by_image_label[image_label] = at_block_label
                    column = measure_by_image_label[image_label][
                        defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_IMAGE_COLUMN]
                    row = measure_by_image_label[image_label][
                        defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_INPUT_FIELD_IMAGE_ROW]
                    image_measured_coordinates_by_camera_id_by_block_label[at_block_label][camera.id] = [column, row]
            content += "\n- Point .........................: "
            content += point_id
            log_point = {}
            point_code = code_by_point_id[point_id]
            # log_point[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_POINT_ID] = point_id
            log_point[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_POINT_CODE] = point_code
            log_point[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_AT_BLOCKS] = {}
            for at_block_label in image_measured_coordinates_by_camera_id_by_block_label:
                content += "\n  - AT Block ....................: "
                content += at_block_label
                if number_of_images_measured_by_at_block_label[at_block_label] < 2:
                    content += "\n    The point has not been measured in the minimum number of images"
                    continue
                at_block = self.at_block_by_label[at_block_label]
                compute_backward_camera_coordinates = True
                use_distortion = True
                use_ppa = True
                image_measured_coordinates_by_camera_id \
                    = image_measured_coordinates_by_camera_id_by_block_label[at_block_label]
                str_error, position, std_position, image_position_backward_error_by_camera_id \
                    = at_block.from_sensors_to_object(image_measured_coordinates_by_camera_id,
                                                      # at_block.crs_id,
                                                      self.crs_id,
                                                      compute_backward_camera_coordinates,
                                                      use_distortion, use_ppa,
                                                      image_space_tolerance)
                if str_error:
                    return str_error, end_date_time, log
                outliers_camera_ids = at_block.sensors_to_object_outliers_camera_ids
                crs2d_precision = crs2d_precision_by_at_block_label[at_block_label]
                content += "\n                                        "
                if crs2d_precision == 4:
                    content += "      X.GCPsCRS      Y.GCPsCRS      H.GCPsCRS"
                else:
                    content += "   Long.GCPsCRS    Lat.GCPsCRS      H.GCPsCRS"
                content += "\n    - Computed coordinates ......: "
                content += ('').ljust(point_code_max_length)
                if crs2d_precision == 9:
                    content += ("{:15.9f}".format(position[0]))
                    content += ("{:15.9f}".format(position[1]))
                else:
                    content += ("{:15.4f}".format(position[0]))
                    content += ("{:15.4f}".format(position[1]))
                content += ("{:15.4f}".format(position[2]))
                content += "\n    - Std computed coordinates ..: "
                content += ('').ljust(point_code_max_length)
                if crs2d_precision == 9:
                    content += ("{:15.9f}".format(std_position[0]))
                    content += ("{:15.9f}".format(std_position[1]))
                else:
                    content += ("{:15.4f}".format(std_position[0]))
                    content += ("{:15.4f}".format(std_position[1]))
                content += ("{:15.4f}".format(std_position[2]))
                content += "\n     ColumnM      RowM   ColumnC      RowC  ErrorC  ErrorR Error2d  Image"
                log_at_block = {}
                log_at_block[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_OBJECT_SPACE_COORDINATES] \
                    = [position[0], position[1], position[2]]
                log_at_block[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_OBJECT_SPACE_COORDINATES_STD]\
                    = [std_position[0], std_position[1], std_position[2]]
                log_at_block[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_IMAGES_LABEL] = {}
                for camera_id in image_position_backward_error_by_camera_id:
                    measured = image_measured_coordinates_by_camera_id[camera_id]
                    error_computed = image_position_backward_error_by_camera_id[camera_id]
                    error_c = error_computed[0]
                    error_r = error_computed[1]
                    error_2d = np.sqrt(error_c ** 2 + error_r ** 2)
                    camera = at_block.camera_by_id[camera_id]
                    content += '\n{:12.2f}'.format(measured[0])
                    content += '{:10.2f}'.format(measured[1])
                    content += '{:10.2f}'.format(measured[0] - error_c)
                    content += '{:10.2f}'.format(measured[1] - error_r)
                    content += '{:8.2f}'.format(error_c)
                    content += '{:8.2f}'.format(error_r)
                    content += '{:8.2f}'.format(error_2d)
                    content += '  {:s}'.format(camera.label)
                    detected_outlier = False
                    if camera_id in outliers_camera_ids:
                        content += ' **** outlier detected'
                        detected_outlier = True
                    log_image = {}
                    log_image[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_IMAGE_MEASURED_COORDINATES] \
                        = measured
                    log_image[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_IMAGE_COMPUTED_COORDINATES] \
                        = [measured[0] - error_c, measured[1] - error_r]
                    log_image[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_IMAGE_COMPUTED_COORDINATES_ERROR] \
                        = error_computed
                    log_image[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_IMAGE_MEASURED_DETECTED_OUTLIER] \
                        = detected_outlier
                    log_at_block[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_IMAGES_LABEL][camera.label] \
                        = log_image
                log_point[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_AT_BLOCKS][at_block_label] \
                    = log_at_block
            log[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_POINTS][point_id] = log_point
        try:
            with open(output_file_path, "w") as f:
                f.write(content)
        except Exception as e:
            str_error = ('Process {}\nError occurred when opening:\n{}\nto write:\n{}'.format(name, output_file_path, e))
            end_date_time = datetime.now()
            return str_error, end_date_time, log
        # vector layer
        # create output layer
        layers_definition = {}
        layers_definition[vector_layer_layer_name] = {}
        layers_definition[vector_layer_layer_name] \
            = defs_processes.process_function_images_to_object_fields_by_layer[
            defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LAYER_NAME]
        layers_crs_id = {}
        layer_crs_id = self.crs_id
        layers_crs_id[vector_layer_layer_name] = layer_crs_id
        if not os.path.exists(vector_layer_file_path):
            ignore_existing_layers = False  # create new gpkg
            create_options = defs_processes.process_function_images_to_object_create_options
            str_error = GDALTools.create_vector(vector_layer_file_path,
                                                layers_definition,
                                                layers_crs_id,
                                                ignore_existing_layers,
                                                create_options)
            if str_error:
                str_error = (
                    'Creating layer:\n{}\nin file:\n{}\nError:\n{}'.format(vector_layer_layer_name,
                                                                           vector_layer_file_path, str_error))
                end_date_time = datetime.now()
                return str_error, end_date_time, log
        else:
            str_error, exists_layer = GDALTools.exists_layer(vector_layer_file_path, vector_layer_layer_name)
            if str_error:
                str_error = (
                    'Getting if exists layer:\n{}\nin file:\n{}\nError:\n{}'.format(vector_layer_layer_name,
                                                                           vector_layer_file_path, str_error))
                end_date_time = datetime.now()
                return str_error, end_date_time, log
            if not exists_layer:
                ignore_existing_layers = True
                str_error = GDALTools.create_vector(vector_layer_file_path,
                                                    layers_definition,
                                                    layers_crs_id,
                                                    ignore_existing_layers)
                if str_error:
                    str_error = (
                        'Creating layer:\n{}\nin file:\n{}\nError:\n{}'.format(vector_layer_layer_name,
                                                                               vector_layer_file_path, str_error))
                    end_date_time = datetime.now()
                    return str_error, end_date_time, log
        features = []
        for point_id in log[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_POINTS]:
            point = log[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_POINTS][point_id]
            for at_block_label in point[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_AT_BLOCKS]:
                point_at_block = point[defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_AT_BLOCKS][at_block_label]
                feature = []
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_POINT_ID
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_processes.process_function_images_to_object_fields_by_layer[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LAYER_NAME][
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_POINT_ID]
                field[defs_gdal.FIELD_VALUE_TAG] = point_id
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_POINT_CODE
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_processes.process_function_images_to_object_fields_by_layer[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LAYER_NAME][
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_POINT_CODE]
                field[defs_gdal.FIELD_VALUE_TAG] = point[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_POINT_CODE]
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_PHOTOGRAMMETRY_PROJECT_FILE
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_processes.process_function_images_to_object_fields_by_layer[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LAYER_NAME][
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_PHOTOGRAMMETRY_PROJECT_FILE]
                field[defs_gdal.FIELD_VALUE_TAG] = self.file_path
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_AT_BLOCK_LABEL
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_processes.process_function_images_to_object_fields_by_layer[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LAYER_NAME][
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_AT_BLOCK_LABEL]
                field[defs_gdal.FIELD_VALUE_TAG] = at_block_label
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_SPACE_COORDINATES
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_processes.process_function_images_to_object_fields_by_layer[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LAYER_NAME][
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_SPACE_COORDINATES]
                object_space_coordinates = point_at_block[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_OBJECT_SPACE_COORDINATES]
                str_osc = " ".join([str(s) for s in object_space_coordinates])
                field[defs_gdal.FIELD_VALUE_TAG] = str_osc
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_SPACE_COORDINATES_STD
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_processes.process_function_images_to_object_fields_by_layer[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LAYER_NAME][
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_SPACE_COORDINATES_STD]
                object_space_coordinates_std = point_at_block[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_OBJECT_SPACE_COORDINATES_STD]
                str_osc_std = " ".join([str(s) for s in object_space_coordinates_std])
                field[defs_gdal.FIELD_VALUE_TAG] = str_osc_std
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_IMAGES_JSON_DATA
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_processes.process_function_images_to_object_fields_by_layer[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LAYER_NAME][
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_IMAGES_JSON_DATA]
                str_images = json.dumps(point_at_block[
                                            defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LOG_TAG_IMAGES_LABEL])
                field[defs_gdal.FIELD_VALUE_TAG] = str_images
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_REMARKS
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_processes.process_function_images_to_object_fields_by_layer[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LAYER_NAME][
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_REMARKS]
                field[defs_gdal.FIELD_VALUE_TAG] = ''
                feature.append(field)
                field = {}
                field[defs_gdal.FIELD_NAME_TAG] = defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_GEOMETRY
                field[defs_gdal.FIELD_TYPE_TAG] \
                    = defs_processes.process_function_images_to_object_fields_by_layer[
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_LAYER_NAME][
                    defs_processes.PROCESS_FUNCTION_IMAGES_TO_OBJECT_FIELD_GEOMETRY]
                fc = object_space_coordinates[0]
                sc = object_space_coordinates[1]
                tc = object_space_coordinates[2]
                point_geometry = ogr.Geometry(ogr.wkbPoint)
                point_geometry.AddPoint(fc, sc, tc)
                pc_wkb = point_geometry.ExportToWkb()
                field[defs_gdal.FIELD_VALUE_TAG] = pc_wkb
                feature.append(field)
                features.append(feature)
        features_by_layer = {}
        features_by_layer[vector_layer_layer_name] = features
        str_error = GDALTools.write_features(vector_layer_file_path, features_by_layer)
        end_date_time = datetime.now()
        return str_error, end_date_time, log

    def set_digitizing_parameters(self,
                                  process,
                                  dialog = None):
        str_error = ''
        end_date_time = None
        log = None
        name = process[processes_defs_processes.PROCESS_FIELD_NAME]
        parameters_manager = process[processes_defs_processes.PROCESS_FIELD_PARAMETERS]
        # parameter dem
        if not defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM in parameters_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM))
            return str_error, end_date_time, log
        parameter_dem_file_path = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM]
        parameter_dem_file_as_dict = json.loads(str(parameter_dem_file_path))
        dem_file_path = parameter_dem_file_as_dict[defs_pars.TAG_FILE_PATH]
        dem_file_path = os.path.normpath(dem_file_path)
        dem_layer_index = parameter_dem_file_as_dict[defs_pars.TAG_LAYER_INDEX]
        dem_file_scale = parameter_dem_file_as_dict[defs_pars.TAG_SCALE]
        dem_file_offset = parameter_dem_file_as_dict[defs_pars.TAG_OFFSET]
        if not dem_file_path:
            str_error = ('Process: {} has a empty parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM))
            return str_error, end_date_time, log
        if not os.path.exists(dem_file_path):
            str_error = ('Process: {} has a parameter: {}\ndoes not exists'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM))
            return str_error, end_date_time, log
        # parameter dem crs
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM_CRS
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM_CRS))
            return str_error, end_date_time, log
        parameter_dem_crs_id = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM_CRS]
        dem_crs_id = str(parameter_dem_crs_id) # can be empty for use internal of the DEM
        # parameter Ignored sensor percentage
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IGNORED_SENSOR_PERCENTAGE
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IGNORED_SENSOR_PERCENTAGE))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IGNORED_SENSOR_PERCENTAGE]
        str_value = str(parameter_value)
        ignored_sensor_percentage = None
        try:
            ignored_sensor_percentage = float(str_value)
        except ValueError:
            str_error = ('Process: {} does not have a float parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IGNORED_SENSOR_PERCENTAGE,
                                str_value))
            return str_error, end_date_time, log
        # parameter Minimum overlap percentage
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MINIMUM_OVERLAP_PERCENTAGE
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MINIMUM_OVERLAP_PERCENTAGE))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MINIMUM_OVERLAP_PERCENTAGE]
        str_value = str(parameter_value)
        minimum_overlap_percentage = None
        try:
            minimum_overlap_percentage = float(str_value)
        except ValueError:
            str_error = ('Process: {} does not have a float parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MINIMUM_OVERLAP_PERCENTAGE,
                                str_value))
            return str_error, end_date_time, log
        # parameter Save rectified homographies images
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_SAVE_RECTIFIED_HOMOGRAPHIES_IMAGES
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_SAVE_RECTIFIED_HOMOGRAPHIES_IMAGES))
            return str_error, end_date_time, log
        parameter_save_recitified_images = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_SAVE_RECTIFIED_HOMOGRAPHIES_IMAGES]
        str_save_rectified_images = str(parameter_save_recitified_images)
        save_rectified_homographies_images = True
        if str_save_rectified_images.casefold() == 'false':
            save_rectified_homographies_images = False
        # parameter Rectified homographies images output path
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH))
            return str_error, end_date_time, log
        parameter_output_path = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH]
        rectified_homographies_images_output_path = str(parameter_output_path)
        if not rectified_homographies_images_output_path:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH))
            return str_error, end_date_time, log
        rectified_homographies_images_output_path = os.path.normpath(rectified_homographies_images_output_path)
        if not os.path.exists(rectified_homographies_images_output_path):
            str_error = ('Process {} parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH))
            str_error += ('\nnot exists path: {}'.
                         format(rectified_homographies_images_output_path))
            return str_error, end_date_time, log
        # parameter Report files output path
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_REPORT_FILES_OUTPUT_PATH
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_REPORT_FILES_OUTPUT_PATH))
            return str_error, end_date_time, log
        parameter_output_path = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_REPORT_FILES_OUTPUT_PATH]
        report_files_output_path = str(parameter_output_path)
        if not report_files_output_path:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_REPORT_FILES_OUTPUT_PATH))
            return str_error, end_date_time, log
        report_files_output_path = os.path.normpath(report_files_output_path)
        if not os.path.exists(report_files_output_path):
            str_error = ('Process {} parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_REPORT_FILES_OUTPUT_PATH))
            str_error += ('\nnot exists path: {}'.
                         format(report_files_output_path))
            return str_error, end_date_time, log
        # parameter process only enabled images
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_ENABLED_IMAGES
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_ENABLED_IMAGES))
            return str_error, end_date_time, log
        parameter_enabled_images = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_ENABLED_IMAGES]
        str_enabled = str(parameter_enabled_images)
        only_enabled_images = True
        if str_enabled.casefold() == 'false':
            only_enabled_images = False
        # parameter Maximum height separation within Dsm
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_WITHIN_DSM
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_WITHIN_DSM))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_WITHIN_DSM]
        str_value = str(parameter_value)
        maximum_height_separation_within_dsm = None
        try:
            maximum_height_separation_within_dsm = float(str_value)
        except ValueError:
            str_error = ('Process: {} does not have a float parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_WITHIN_DSM,
                                str_value))
            return str_error, end_date_time, log
        # parameter Maximum height separation outside Dsm
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_OUTSIDE_DSM
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_OUTSIDE_DSM))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_OUTSIDE_DSM]
        str_value = str(parameter_value)
        maximum_height_separation_outside_dsm = None
        try:
            maximum_height_separation_outside_dsm = float(str_value)
        except ValueError:
            str_error = ('Process: {} does not have a float parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_OUTSIDE_DSM,
                                str_value))
            return str_error, end_date_time, log
        # parameter Images matches accuracy
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MATCHES_ACCURACY
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MATCHES_ACCURACY))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MATCHES_ACCURACY]
        str_value = str(parameter_value)
        images_matches_accuracy = None
        try:
            images_matches_accuracy = float(str_value)
        except ValueError:
            str_error = ('Process: {} does not have a float parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MATCHES_ACCURACY,
                                str_value))
            return str_error, end_date_time, log
        # parameter Images measurements accuracy
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MEASUREMENTS_ACCURACY
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MEASUREMENTS_ACCURACY))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MEASUREMENTS_ACCURACY]
        str_value = str(parameter_value)
        images_measurements_accuracy = None
        try:
            images_measurements_accuracy = float(str_value)
        except ValueError:
            str_error = ('Process: {} does not have a float parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MEASUREMENTS_ACCURACY,
                                str_value))
            return str_error, end_date_time, log
        # parameter Match maximum epipolar row parallax
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_MAXIMUM_EPIPOLAR_ROW_PARALLAX
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_MAXIMUM_EPIPOLAR_ROW_PARALLAX))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_MAXIMUM_EPIPOLAR_ROW_PARALLAX]
        str_value = str(parameter_value)
        match_maximum_epipolar_row_parallax = None
        try:
            match_maximum_epipolar_row_parallax = int(str_value)
        except ValueError:
            str_error = ('Process: {} does not have an integer parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_MAXIMUM_EPIPOLAR_ROW_PARALLAX,
                                str_value))
            return str_error, end_date_time, log
        # parameter Match OpenCv method
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD))
            return str_error, end_date_time, log
        parameter_match_opencv_method = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD]
        match_opencv_method = str(parameter_match_opencv_method)
        if (match_opencv_method.casefold() !=
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD_ALL.casefold()
                and match_opencv_method.casefold() !=
                PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD_TM_SQDIFF_NORMED
                and match_opencv_method.casefold() !=
                PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD_TM_CCORR_NORMED
                and match_opencv_method.casefold() !=
                PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD_TM_COEFF_NORMED):
            str_error = ('Process: {} parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD))
            str_error += ('\noption: {} not implemented'.
                         format(match_opencv_method))
            return str_error, end_date_time, log
        # parameter Match OpenCv threshold percentage
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_CORRELATION_THRESHOLD_PERCENTAGE
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_CORRELATION_THRESHOLD_PERCENTAGE))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_CORRELATION_THRESHOLD_PERCENTAGE]
        str_value = str(parameter_value)
        match_pencv_threshold_percentage = None
        try:
            match_pencv_threshold_percentage = float(str_value)
        except ValueError:
            str_error = ('Process: {} does not have a float parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_CORRELATION_THRESHOLD_PERCENTAGE,
                                str_value))
            return str_error, end_date_time, log
        # parameter Ram maximum size
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RAM_MAXIMUM_SIZE
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RAM_MAXIMUM_SIZE))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RAM_MAXIMUM_SIZE]
        str_value = str(parameter_value)
        ram_maximum_size = None
        try:
            ram_maximum_size = int(str_value)
        except ValueError:
            str_error = ('Process: {} does not have an integer parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RAM_MAXIMUM_SIZE,
                                str_value))
            return str_error, end_date_time, log
        # parameter Match window size
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_WINDOW_SIZE
                in parameters_manager.parameters):
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_WINDOW_SIZE))
            return str_error, end_date_time, log
        parameter_value = parameters_manager.parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_WINDOW_SIZE]
        str_value = str(parameter_value)
        match_window_size = None
        try:
            match_window_size = int(str_value)
        except ValueError:
            str_error = ('Process: {} does not have an integer parameter: {}, is: {}'.
                         format(name,
                                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_WINDOW_SIZE,
                                str_value))
            return str_error, end_date_time, log

        # dem_file_path
        # dem_crs_id
        # ignored_sensor_percentage
        # minimum_overlap_percentage
        # save_rectified_homographies_images
        # rectified_homographies_images_output_path
        # report_files_output_path
        # only_enabled_images
        # maximum_height_separation_within_dsm
        # maximum_height_separation_outside_dsm
        # images_matches_accuracy
        # images_measurements_accuracy
        # match_maximum_epipolar_row_parallax
        # match_opencv_method
        # match_pencv_threshold_percentage
        # ram_maximum_size
        # match_window_size

        self.digitizing_parameters = {}
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM] \
            = dem_file_path
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_DEM_CRS] \
            = dem_crs_id
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IGNORED_SENSOR_PERCENTAGE] \
            = ignored_sensor_percentage
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MINIMUM_OVERLAP_PERCENTAGE] \
            = minimum_overlap_percentage
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_SAVE_RECTIFIED_HOMOGRAPHIES_IMAGES] \
            = save_rectified_homographies_images
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RECTIFIED_HOMOGRAPHIES_IMAGES_OUTPUT_PATH] \
            = rectified_homographies_images_output_path
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_REPORT_FILES_OUTPUT_PATH] \
            = report_files_output_path
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_ENABLED_IMAGES] \
            = only_enabled_images
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_WITHIN_DSM] \
            = maximum_height_separation_within_dsm
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_OUTSIDE_DSM] \
            = maximum_height_separation_outside_dsm
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MATCHES_ACCURACY] \
            = images_matches_accuracy
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_IMAGES_MEASUREMENTS_ACCURACY] \
            = images_measurements_accuracy
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_MAXIMUM_EPIPOLAR_ROW_PARALLAX] \
            = match_maximum_epipolar_row_parallax
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD] \
            = match_opencv_method
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_CORRELATION_THRESHOLD_PERCENTAGE] \
            = match_pencv_threshold_percentage
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_RAM_MAXIMUM_SIZE] \
            = ram_maximum_size
        self.digitizing_parameters[defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_WINDOW_SIZE] \
            = match_window_size
        end_date_time = datetime.now()
        return str_error, end_date_time, log

    def process_undistort_images(self,
                                 process,
                                 dialog = None):
        str_error = ''
        end_date_time = None
        log = None
        name = process[processes_defs_processes.PROCESS_FIELD_NAME]
        parameters_manager = process[processes_defs_processes.PROCESS_FIELD_PARAMETERS]
        if not defs_processes.PROCESS_FUNCTION_UNDISTORT_IMAGES_OUTPUT_PATH in parameters_manager.parameters:
            str_error = ('Process: {} does not have parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_UNDISTORT_IMAGES_OUTPUT_PATH))
            return str_error, end_date_time, log
        parameter_output_path = parameters_manager.parameters[defs_processes.PROCESS_FUNCTION_UNDISTORT_IMAGES_OUTPUT_PATH]
        output_path = str(parameter_output_path)
        if not output_path:
            str_error = ('Process {} has a empty parameter: {}'.
                         format(name, defs_processes.PROCESS_FUNCTION_UNDISTORT_IMAGES_OUTPUT_PATH))
            return str_error, end_date_time, log
        output_path = os.path.normpath(output_path)
        cameras_to_process = []
        calibration_by_camera_file_path = {}
        for at_block_label in self.at_block_by_label:
            at_block = self.at_block_by_label[at_block_label]
            for camera_id in at_block.camera_by_id:
                camera = at_block.camera_by_id[camera_id]
                camera_enabled = camera.get_enabled() # multisensor ...
                if not camera_enabled:
                    continue
                if not camera.is_usefull():
                    continue
                image_file_path = camera.image_file_path
                if not image_file_path:
                    continue
                if not os.path.exists(image_file_path):
                    str_aux_error = (
                            'For image: {} not exists file path:\n{}'.format(camera.label, image_file_path))
                    str_error = ('Process: {} error:\n{}'.
                                     format(name, str_aux_error))
                    return str_error, end_date_time, log
                sensor_id = camera.sensor_id
                sensor = at_block.sensor_by_id[sensor_id]
                if len(sensor.calibration_by_class) > 1:
                    str_aux_error = (
                            'For image: {} sensor has several calibrations'.format(camera.label))
                    str_error = ('Process: {} error:\n{}'.
                                     format(name, str_aux_error))
                    return str_error, end_date_time, log
                calibration_type = next(iter(sensor.calibration_by_class))
                calibration = sensor.calibration_by_class[calibration_type]
                calibration_by_camera_file_path[image_file_path] = calibration
        if dialog:
            dialog.processInformationGroupBox.setEnabled(True)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            dialog.processLineEdit.setText('Undistorting images ...')
            dialog.processLineEdit.adjustSize()
            dialog.processProgressBar.setMaximum(len(calibration_by_camera_file_path))
            dialog.processLineEdit.adjustSize()
            QApplication.processEvents()
        features = []
        undistorted_features = []
        cont = 0
        for image_file_path in calibration_by_camera_file_path:
            if dialog:
                cont = cont + 1
                dialog.processProgressBar.setValue(cont)
                QApplication.processEvents()
            calibration = calibration_by_camera_file_path[image_file_path]
            undistort_image_file_path = output_path + '/'+ os.path.basename(image_file_path)
            undistort_image_file_path = os.path.normpath(undistort_image_file_path)
            str_error = self.opencv_tools.undistort_image(image_file_path,
                                                          calibration,
                                                          undistort_image_file_path)
            if str_error:
                if dialog:
                    dialog.processProgressBar.setValue(len(calibration_by_camera_file_path))
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                str_error = ('Undistorting image file path: {}\nError:\n{}'
                             .format(image_file_path, str_error))
                return str_error, end_date_time, log
        if dialog:
            dialog.processProgressBar.setValue(len(calibration_by_camera_file_path))
            dialog.processInformationGroupBox.setEnabled(False)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            QApplication.processEvents()
        end_date_time = datetime.now()
        return str_error, end_date_time, log

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

    def save_process(self,
                     process_content,
                     process_author,
                     process_label,
                     process_description,
                     process_log,
                     process_date_time_as_string,
                     process_output,
                     process_remarks):
        return super().save_process(process_content,
                                    process_author,
                                    process_label,
                                    process_description,
                                    process_log,
                                    process_date_time_as_string,
                                    process_output,
                                    process_remarks,
                                    file_path = self.file_path)

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

    def update_objects_fully_qualified_names(self):
        project_fully_qualified_name = type(self).__module__
        project_fully_qualified_name = project_fully_qualified_name.lower()
        if not project_fully_qualified_name in self.object_by_fully_qualified_name:
            self.object_by_fully_qualified_name[project_fully_qualified_name] = self
        return

