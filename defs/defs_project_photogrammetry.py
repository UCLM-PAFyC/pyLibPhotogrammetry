# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))

# from pyLibCRSs import CRSsDefines as defs_crs
from pyLibGDAL import defs_gdal
# from pyLibProject.defs import defs_project_definition
# from pyLibProject.gui.ProjectDefinitionDialog import ProjectDefinitionDialog
from pyLibProject.defs import defs_project as defs_project_lib

fields_by_layer = defs_project_lib.fields_by_layer

IMAGES_TABLE_NAME = "images"
fields_by_layer[IMAGES_TABLE_NAME] = {}
# IMAGES_FIELD_ID = "id"
# fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_ID] = defs_gdal.type_by_name['int']
IMAGES_FIELD_LABEL = "label"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_LABEL] = defs_gdal.type_by_name['string']
IMAGES_FIELD_FILE = "file"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_FILE] = defs_gdal.type_by_name['string']
# IMAGES_FIELD_XML_FILE_ID_ID = "xml_file_id"
# fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_XML_FILE_ID_ID] = defs_gdal.type_by_name['string']
IMAGES_FIELD_CHUNK_LABEL = "at_block_label"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_CHUNK_LABEL] = defs_gdal.type_by_name['string']
IMAGES_FIELD_CAMERA_ID = "camera_id"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_CAMERA_ID] = defs_gdal.type_by_name['int']
IMAGES_FIELD_ENABLED = "enabled"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_ENABLED] = defs_gdal.type_by_name['int']
IMAGES_FIELD_UNDISTORTED_FILE = "undistorted_file"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_UNDISTORTED_FILE] = defs_gdal.type_by_name['string']
IMAGES_FIELD_STRING_ID = "string_id"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_STRING_ID] = defs_gdal.type_by_name['string']
IMAGES_FIELD_PC_GEOM = defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_PC_GEOM] = defs_gdal.geometry_type_by_name['point']
IMAGES_FIELD_DATE = "date"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_DATE] = defs_gdal.type_by_name['string']
IMAGES_FIELD_UTC = "utc"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_UTC] = defs_gdal.type_by_name['string']
IMAGES_FIELD_SUN_AZIMUTH = "sun_azimuth"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_SUN_AZIMUTH] = defs_gdal.type_by_name['real']
IMAGES_FIELD_SUN_ELEVATION = "sun_elevation"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_SUN_ELEVATION] = defs_gdal.type_by_name['real']
IMAGES_FIELD_SUN_GLINT = "sun_glint"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_SUN_GLINT] = defs_gdal.type_by_name['string']
IMAGES_FIELD_HOTSPOT = "hotspot"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_HOTSPOT] = defs_gdal.type_by_name['string']
IMAGES_FIELD_EXIF = "exif"
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_EXIF] = defs_gdal.type_by_name['string']
IMAGES_FIELD_CONTENT = "content" # json for another data as dictionary
fields_by_layer[IMAGES_TABLE_NAME][IMAGES_FIELD_CONTENT] = defs_gdal.type_by_name['string']

# TABLE: images_rectifying_homographies
IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME = "images_rh"
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME] = {}
# IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_ID = "id"
# fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
#     IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_ID] = defs_gdal.type_by_name['int']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_ID = "first_image_id"
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_ID] = defs_gdal.type_by_name['int']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_ID = "second_image_id"
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_ID] = defs_gdal.type_by_name['int']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_WKT = "first_image_wkt"
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_WKT] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_UND_WKT = "first_image_und_wkt"
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_UND_WKT] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_EPIPOLAR_ENVELOPE = "first_image_epipolar_envelope" # minColum,minRow,maxColum,maxRow
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_EPIPOLAR_ENVELOPE] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_HOMOGRAPHY = "first_image_homography" # by rows
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_HOMOGRAPHY] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_INVERSE_HOMOGRAPHY = "first_image_inverse_homography" # by rows
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_INVERSE_HOMOGRAPHY] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_FILE = "first_image_file"
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FIRST_IMAGE_FILE] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_WKT = "second_image_wkt"
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_WKT] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_UND_WKT = "second_image_und_wkt"
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_UND_WKT] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_EPIPOLAR_ENVELOPE = "second_image_epipolar_envelope" # minColum,minRow,maxColum,maxRow
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_EPIPOLAR_ENVELOPE] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_HOMOGRAPHY = "second_image_homography" # by rows
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_HOMOGRAPHY] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_INVERSE_HOMOGRAPHY = "second_image_inverse_homography" # by rows
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_INVERSE_HOMOGRAPHY] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_FILE = "second_image_file"
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_SECOND_IMAGE_FILE] = defs_gdal.type_by_name['string']
IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FP_GEOM = defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG
fields_by_layer[IMAGES_RECTIFIYING_HOMOGRAPHIES_TABLE_NAME][
    IMAGES_RECTIFIYING_HOMOGRAPHIES_FIELD_FP_GEOM] = defs_gdal.geometry_type_by_name['polygon']

# TABLE: imgs_tiles_
# STEREOPAIRS_TILES_VALUES                 "1;2;5;10;20;50;100;200;500;1000"
IMAGES_TILES_VALUES = ["10", "20", "50", "100"]
IMAGES_TILES_VALUES_STRING_SEPARATOR = ";"
IMAGES_TILES_OVERSIZE_VALUE = 1.0
IMAGES_TILES_IMAGES_SEPARATOR = ";"
IMAGES_TILES_PREFIX_TABLE_NAME = "imgs_tiles_"
for tile_value in IMAGES_TILES_VALUES:
    IMAGES_TILES_TABLE_NAME = IMAGES_TILES_PREFIX_TABLE_NAME + tile_value
    fields_by_layer[IMAGES_TILES_TABLE_NAME] = {}
    # IMAGES_TILES_FIELD_ID = "id"
    # fields_by_layer[IMAGES_TILES_TABLE_NAME][IMAGES_TILES_FIELD_ID] = defs_gdal.type_by_name['int']
    IMAGES_TILES_FIELD_TILE_X = "tile_x"
    fields_by_layer[IMAGES_TILES_TABLE_NAME][IMAGES_TILES_FIELD_TILE_X] = defs_gdal.type_by_name['int']
    IMAGES_TILES_FIELD_TILE_Y = "tile_y"
    fields_by_layer[IMAGES_TILES_TABLE_NAME][IMAGES_TILES_FIELD_TILE_Y] = defs_gdal.type_by_name['int']
    IMAGES_TILES_IMAGES_ID = "imgs_id"
    fields_by_layer[IMAGES_TILES_TABLE_NAME][IMAGES_TILES_IMAGES_ID] = defs_gdal.type_by_name['string']
    IMAGES_TILES_FIELD_RAM_MBS = "ram_mbs"
    fields_by_layer[IMAGES_TILES_TABLE_NAME][IMAGES_TILES_FIELD_RAM_MBS] = defs_gdal.type_by_name['real']
    IMAGES_TILES_FIELD_FP_GEOM = defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG
    fields_by_layer[IMAGES_TILES_TABLE_NAME][IMAGES_TILES_FIELD_FP_GEOM] = defs_gdal.geometry_type_by_name['polygon']

#TABLE: images_fp
IMAGES_FP_TABLE_NAME = "images_fp"
fields_by_layer[IMAGES_FP_TABLE_NAME] = {}
# IMAGES_FP_FIELD_ID = "id"
# fields_by_layer[IMAGES_FP_TABLE_NAME][IMAGES_FP_FIELD_ID] = defs_gdal.type_by_name['int']
IMAGES_FP_FIELD_CHUNK_LABEL = "at_block_label"
fields_by_layer[IMAGES_FP_TABLE_NAME][IMAGES_FP_FIELD_CHUNK_LABEL] = defs_gdal.type_by_name['string']
IMAGES_FP_FIELD_IMAGE_ID = "image_id"
fields_by_layer[IMAGES_FP_TABLE_NAME][IMAGES_FP_FIELD_IMAGE_ID] = defs_gdal.type_by_name['int']
IMAGES_FP_FIELD_IMAGE_FILE_NAME = "image"
fields_by_layer[IMAGES_FP_TABLE_NAME][IMAGES_FP_FIELD_IMAGE_FILE_NAME] = defs_gdal.type_by_name['string']
IMAGES_FP_FIELD_FP_GEOM = defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG
fields_by_layer[IMAGES_FP_TABLE_NAME][IMAGES_FP_FIELD_FP_GEOM] = defs_gdal.geometry_type_by_name['polygon']
IMAGES_FP_LINEAR_PRECISION = 12

#TABLE: undistored_images_fp
IMAGES_UNDISTORTED_FP_TABLE_NAME = "images_undistorted_fp"
fields_by_layer[IMAGES_UNDISTORTED_FP_TABLE_NAME] = {}
# IMAGES_UNDISTORTED_FP_FIELD_ID = "id"
# fields_by_layer[IMAGES_UNDISTORTED_FP_TABLE_NAME][IMAGES_UNDISTORTED_FP_FIELD_ID] = defs_gdal.type_by_name['int']
IMAGES_UNDISTORTED_FP_FIELD_CHUNK_LABEL = "at_block_label"
fields_by_layer[IMAGES_UNDISTORTED_FP_TABLE_NAME][IMAGES_UNDISTORTED_FP_FIELD_CHUNK_LABEL] = defs_gdal.type_by_name['string']
IMAGES_UNDISTORTED_FP_FIELD_IMAGE_ID = "image_id"
fields_by_layer[IMAGES_UNDISTORTED_FP_TABLE_NAME][IMAGES_UNDISTORTED_FP_FIELD_IMAGE_ID] = defs_gdal.type_by_name['int']
IMAGES_UNDISTORTED_FP_FIELD_IMAGE_FILE_NAME = "image"
fields_by_layer[IMAGES_UNDISTORTED_FP_TABLE_NAME][IMAGES_UNDISTORTED_FP_FIELD_IMAGE_FILE_NAME] = defs_gdal.type_by_name['string']
IMAGES_UNDISTORTED_FP_FIELD_FP_GEOM = defs_gdal.LAYERS_GEOMETRY_POSTGIS_TAG
fields_by_layer[IMAGES_UNDISTORTED_FP_TABLE_NAME][IMAGES_UNDISTORTED_FP_FIELD_FP_GEOM] = defs_gdal.geometry_type_by_name['polygon']
IMAGES_UNDISTORTED_FP_LINEAR_PRECISION = 12

METASHAPE_MARKERS_XML_FILE_MANAGEMENT_FIELD_NAME = "Metashape Markers XML File"
RASTER_DEM_PRECISION_CODE = defs_gdal.RASTER_DEM_CENTIMETER_PRECISION_CODE


