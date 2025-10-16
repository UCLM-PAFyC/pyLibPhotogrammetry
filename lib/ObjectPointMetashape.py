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

from pyLibPhotogrammetry.lib.ObjectPoint import ObjectPoint

class ObjectPointMetashape(ObjectPoint):
    def __init__(self,
                 at_block):
        super().__init__(at_block)
        self.position_chunk = None

    def set_from_metashape_xml(self,
                               xml_element):
        str_error = ''
        #id
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_ID in xml_element:
            str_error = ('Not exists attribute: {} in marker in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_ID, self.file_path))
            return str_error
        str_id = xml_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_ID]
        try:
            self.id = int(str_id)
        except ValueError:
            str_error = ('Attribute: {} in marker in metashape markers XML file:\n{}\n must be an integer: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_ID, self.file_path, str_id))
            return str_error
        if self.id in self.at_block.gcps_by_id:
            str_error = ('Exists previous marker id: {} in marker in metashape markers XML file:\n{}'.
                         format(str(self.id), self.file_path,))
            return str_error
        # label
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_LABEL in xml_element:
            str_error = ('Not exists attribute: {} in marker in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_LABEL, self.file_path))
            return str_error
        label = xml_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_ATTRIBUTE_LABEL]
        self.label = label
        # reference
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG in xml_element:
            str_error = ('Not exists attribute: {} in marker: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        reference_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG]
        # x
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_FIRST_COORDINATE in reference_element:
            str_error = ('Not exists attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_FIRST_COORDINATE,
                                defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        str_reference_x = reference_element[defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_FIRST_COORDINATE]
        try:
            reference_x = float(str_reference_x)
        except ValueError:
            str_error = (
                'Attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}\nmust be a float'.
                format(defs_msm.METASHAPE_MARKERS_XML_CAMERA_REFERENCE_ATTRIBUTE_FIRST_COORDINATE,
                       defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        # y
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_SECOND_COORDINATE in reference_element:
            str_error = ('Not exists attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_SECOND_COORDINATE,
                                defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        str_reference_y = reference_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_SECOND_COORDINATE]
        try:
            reference_y = float(str_reference_y)
        except ValueError:
            str_error = (
                'Attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}\nmust be a float'.
                format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_SECOND_COORDINATE,
                       defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        # z
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_THIRD_COORDINATE in reference_element:
            str_error = ('Not exists attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_THIRD_COORDINATE,
                                defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        str_reference_z = reference_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_THIRD_COORDINATE]
        try:
            reference_z = float(str_reference_z)
        except ValueError:
            str_error = (
                'Attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}\nmust be a float'.
                format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_THIRD_COORDINATE,
                       defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        # enabled
        if not defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_ENABLED in reference_element:
            str_error = ('Not exists attribute: {} in element: {} in marker: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_ENABLED,
                                defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_TAG, self.label, self.file_path))
            return str_error
        position_crs_source = [reference_x, reference_y, reference_z]
        str_enabled = reference_element[defs_msm.METASHAPE_MARKERS_XML_MARKERS_MARKER_REFERENCE_ATTRIBUTE_ENABLED]
        self.enabled = True
        if str_enabled.casefold() == 'false':
            self.enabled = False
        self.position_crs_source = np.array(position_crs_source)
        if self.at_block.crs_id != self.at_block.gcps_crs_id:
            position = [[reference_x, reference_y, reference_z]]
            str_error = self.crs_tools.operation(self.at_block.gcps_crs_id, self.at_block.crs_id, position)
            if str_error:
                str_error = ('In GCP: {} in metashape markers XML file:\n{}\nError in CRSs operation:\n{}'.
                             format(self.label, self.file_path, str_error))
                return str_error
            self.position = np.array(position[0])
        else:
            self.position = np.array([reference_x, reference_y, reference_z])
        if self.at_block.crs_id != self.at_block.crs_ecef_id:
            position_ecef = [self.position.tolist()]
            str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_ecef_id, position_ecef)
            if str_error:
                str_error = ('In GCP: {} in metashape markers XML file:\n{}\nError in CRSs operation:\n{}'.
                             format(self.label, self.file_path, str_error))
                return str_error
            self.position_ecef = np.array(position_ecef[0])
        else:
            self.position_ecef = np.array(self.position.tolist())
        if self.at_block.crs_id != self.at_block.crs_geo3d_id:
            position_geo3d = [self.position.tolist()]
            str_error = self.crs_tools.operation(self.at_block.crs_id, self.at_block.crs_geo3d_id, position_geo3d)
            if str_error:
                str_error = ('In GCP: {} in metashape markers XML file:\n{}\nError in CRSs operation:\n{}'.
                             format(self.label, self.file_path, str_error))
                return str_error
            self.position_geo3d = np.array(position_geo3d[0])
        else:
            self.position_geo3d = np.array(self.position.tolist())
        position_ecef = np.append(self.position_ecef, 1.0)
        self.position_chunk = np.matmul(self.at_block.transform_inv, position_ecef)
        return str_error


