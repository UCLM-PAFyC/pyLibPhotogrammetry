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
# from pyLibPhotogrammetry.lib.SensorMetashape import SensorMetashape
# from pyLibPhotogrammetry.lib.CameraMetashape import CameraMetashape
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

        return str_error

