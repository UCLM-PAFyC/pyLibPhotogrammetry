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

