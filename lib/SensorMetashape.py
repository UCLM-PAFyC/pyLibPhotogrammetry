# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math
import numpy as np

from osgeo import gdal, osr, ogr

class GdalErrorHandler(object):
    def __init__(self):
        self.err_level = gdal.CE_None
        self.err_no = 0
        self.err_msg = ''

    def handler(self, err_level, err_no, err_msg):
        self.err_level = err_level
        self.err_no = err_no
        self.err_msg = err_msg
err = GdalErrorHandler()
gdal.PushErrorHandler(err.handler)
gdal.UseExceptions()  # Exceptions will get raised on anything >= gdal.CE_Failure
assert err.err_level == gdal.CE_None, 'the error level starts at 0'

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

from pyLibPhotogrammetry.lib.Sensor import Sensor
from pyLibPhotogrammetry.lib.CalibrationMetashape import CalibrationMetashape

SENSOR_INTEGER_NO_VALUE = -9999
SENSOR_DOUBLE_NO_VALUE = -9999.999
SENSOR_GEOMETRY_SIDE_NUMBER_OF_POINTS = 33
SENSOR_GEOMETRY_PRECISION = 6
SENSOR_OUTER_POINT_PERCENTAGE_FOCAL_PLANE_TOLERANCE = 10.0

class SensorMetashape(Sensor):
    def __init__(self,
                 at_block):
        super().__init__(at_block)
        self.normalize_sensitivity = None
        self.layer_index = None
        self.data_type_as_string = None
        self.black_level = None
        self.sensitivity = None
        self.vignetting = {} # self.vignetting[i][j] = value

    def from_camera_to_sensor(self,
                              position_camera):
        str_error = ''
        within = False
        withinAfterUndistortion = False
        position_image = None
        position_undistorted_image = None
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_ADJUSTED in self.calibration_by_class\
                and not defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_INITIAL in self.calibration_by_class:
            str_error = ('For sensor: {} not found calibration class: {}'.
                         format(self.label, defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_ADJUSTED))
            return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image
        calibration = None
        if defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_ADJUSTED in self.calibration_by_class:
            calibration = self.calibration_by_class[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_ADJUSTED]
        else:
            calibration = self.calibration_by_class[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_INITIAL]
        if (calibration.type.casefold() != defs_msm.METASHAPE_CALIBRATION_TYPE_FRAME
                and calibration.type.casefold() != defs_msm.METASHAPE_CALIBRATION_TYPE_FISHEYE):
            str_error = ('For sensor: {} calibration type: {} is not valid\nmust be {} or {}'.
                         format(self.label, calibration.type, defs_msm.METASHAPE_CALIBRATION_TYPE_FRAME,
                                defs_msm.METASHAPE_CALIBRATION_TYPE_FISHEYE))
            return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image
        columns = calibration.width
        rows = calibration.height
        if not self.geometry:
            str_error = self.set_geometry()
            if str_error:
                str_error = ('Setting geometry for sensor: {} error:\n{}'.
                             format(self.label, str_error))
                return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image
        outer_tolerance_columns = SENSOR_OUTER_POINT_PERCENTAGE_FOCAL_PLANE_TOLERANCE / 100. * columns
        outer_tolerance_rows = SENSOR_OUTER_POINT_PERCENTAGE_FOCAL_PLANE_TOLERANCE / 100. * rows
        columns = calibration.width
        rows = calibration.height
        X = position_camera[0]
        Y = position_camera[1]
        Z = position_camera[2]
        if isinstance(self.rotation,np.ndarray):
            rotated_coor = np.zeros(3)
            rotated_coor[0] = X
            rotated_coor[1] = Y
            rotated_coor[2] = Z
            coor = np.dot(self.rotation_inv, rotated_coor)
            X = coor[0]
            Y = coor[1]
            Z = coor[2]
        column = None
        row = None
        columnNd = None
        rowNd = None
        if calibration.type.casefold() == defs_msm.METASHAPE_CALIBRATION_TYPE_FRAME:
            f = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_F_TAG]
            cx = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CX_TAG]
            cy = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CY_TAG]
            b1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B1_TAG]
            b2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B2_TAG]
            k1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K1_TAG]
            k2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K2_TAG]
            k3 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K3_TAG]
            k4 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K4_TAG]
            p1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P1_TAG]
            p2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P2_TAG]
            p3 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P3_TAG]
            p4 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P4_TAG]
            x = X / Z
            y = Y / Z
            columnNd = columns * 0.5 + cx + f * x
            rowNd = rows * 0.5 + cy + y * f
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint(x, y)
            within = True
            if not self.geometry.Contains(point):
                within = False
            withinAfterUndistortion = within
            if not within:
                column = columnNd
                row = rowNd
                if column < (-1. * outer_tolerance_columns) or column > (columns + outer_tolerance_columns) or row < (
                    -1. * outer_tolerance_rows) or row > (rows + outer_tolerance_rows):
                    return str_error
            r = np.sqrt(x * x + y * y)
            r2 = r * r
            r4 = r2 * r2
            r6 = r2 * r4
            r8 = r4 * r4
            x2 = x * x
            y2 = y * y
            xd = x * (1.0 + k1 * r2 + k2 * r4 + k3 * r6 + k4 * r8) + (p1 * (r2 + 2.0 * x2) + 2.0 * p2 * x * y) * (
                        1.0 + p3 * r2 + p4 * r4)
            yd = y * (1.0 + k1 * r2 + k2 * r4 + k3 * r6 + k4 * r8) + (p2 * (r2 + 2.0 * y2) + 2.0 * p1 * x * y) * (
                        1.0 + p3 * r2 + p4 * r4)
            column = columns * 0.5 + cx + f * xd + xd * b1 + yd * b2
            row = rows * 0.5 + cy + yd * f
            if not withinAfterUndistortion and column >= 0 and column < self.width and row >= 0 and row < self.height:
                withinAfterUndistortion = True
        if calibration.type.casefold() == defs_msm.METASHAPE_CALIBRATION_TYPE_FISHEYE:
            f = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_F_TAG]
            cx = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CX_TAG]
            cy = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CY_TAG]
            b1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B1_TAG]
            b2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B2_TAG]
            k1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K1_TAG]
            k2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K2_TAG]
            k3 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K3_TAG]
            k4 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K4_TAG]
            p1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P1_TAG]
            p2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P2_TAG]
            p3 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P3_TAG]
            p4 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P4_TAG]
            x0 = X / Z
            y0 = Y / Z
            r0 = np.sqrt(x0 * x0 + y0 * y0)
            x = x0 * np.arctan(r0) / r0 # x0 * tan - 1 r0 / r0
            y = y0 * np.arctan(r0) / r0 # y0 * tan - 1 r0 / r0
            columnNd = columns * 0.5 + cx + f * x
            rowNd = rows * 0.5 + cy + y * f
            point = ogr.Geometry(ogr.wkbPoint)
            point.AddPoint(x, y)
            within = True
            if not self.geometri.Contains(point):
                within = False
            withinAfterUndistortion = within
            if not within:
                column = columnNd
                row = rowNd
                if column < (-1. * outer_tolerance_columns) or column > (columns + outer_tolerance_columns) or row < (
                    -1. * outer_tolerance_rows) or row > (rows + outer_tolerance_rows):
                    return str_error
            r = np.sqrt(x * x + y * y)
            r2 = r * r
            r4 = r2 * r2
            r6 = r2 * r4
            r8 = r4 * r4
            x2 = x * x
            y2 = y * y
            xd = x * (1.0 + k1 * r2 + k2 * r4 + k3 * r6 + k4 * r8) + (p1 * (r2 + 2.0 * x2) + 2.0 * p2 * x * y) * (
                        1.0 + p3 * r2 + p4 * r4)
            yd = y * (1.0 + k1 * r2 + k2 * r4 + k3 * r6 + k4 * r8) + (p2 * (r2 + 2.0 * y2) + 2.0 * p1 * x * y) * (
                        1.0 + p3 * r2 + p4 * r4)
            column = columns * 0.5 + cx + f * xd + xd * b1 + yd * b2
            row = rows * 0.5 + cy + yd * f
            if not withinAfterUndistortion and column >= 0 and column < self.width and row >= 0 and row < self.height:
                withinAfterUndistortion = True
        position_image = [column, row]
        position_undistorted_image = [columnNd, rowNd]
        return str_error, within, withinAfterUndistortion, position_image, position_undistorted_image

    def from_sensor_to_camera_coordinates_direction(self,
                                                    column,
                                                    row,
                                                    use_distortion = True,
                                                    use_ppa = True):
        str_error = ''
        X = None
        Y = None
        Z = None
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_ADJUSTED in self.calibration_by_class\
                and not defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_INITIAL in self.calibration_by_class:
            str_error = ('For sensor: {} not found calibration class: {}'.
                         format(self.label, defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_ADJUSTED))
            return str_error, X, Y, Z
        calibration = None
        if defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_ADJUSTED in self.calibration_by_class:
            calibration = self.calibration_by_class[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_ADJUSTED]
        else:
            calibration = self.calibration_by_class[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_ATTRIBUTE_CLASS_INITIAL]
        if (calibration.type.casefold() != defs_msm.METASHAPE_CALIBRATION_TYPE_FRAME
                and calibration.type.casefold() != defs_msm.METASHAPE_CALIBRATION_TYPE_FISHEYE):
            str_error = ('For sensor: {} calibration type: {} is not valid\nmust be {} or {}'.
                         format(self.label, calibration.type, defs_msm.METASHAPE_CALIBRATION_TYPE_FRAME,
                                defs_msm.METASHAPE_CALIBRATION_TYPE_FISHEYE))
            return str_error, X, Y, Z
        columns = calibration.width
        rows = calibration.height
        if calibration.type.casefold() == defs_msm.METASHAPE_CALIBRATION_TYPE_FRAME:
            f = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_F_TAG]
            cx = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CX_TAG]
            cy = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CY_TAG]
            b1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B1_TAG]
            b2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B2_TAG]
            x = None
            y = None
            if use_distortion:
                k1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K1_TAG]
                k2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K2_TAG]
                k3 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K3_TAG]
                k4 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K4_TAG]
                p1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P1_TAG]
                p2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P2_TAG]
                p3 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P3_TAG]
                p4 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P4_TAG]
                yd = (row - rows * 0.5 - cy) / f
                xd = (column - columns * 0.5 - cx - yd * b2) / (f + b1)
                x = xd
                y = yd
                control = True
                tolerance = 0.001 / f
                while control:
                    xBefore = x
                    yBefore = y
                    r = np.sqrt(x * x + y * y)
                    r2 = r * r
                    r4 = r2 * r2
                    r6 = r2 * r4
                    r8 = r4 * r4
                    x2 = x * x
                    y2 = y * y
                    x = (xd - (p1 * (r2 + 2.0 * x2) + 2.0 * p2 * x * y) * (1.0 + p3 * r2 + p4 * r4)) / (
                                1.0 + k1 * r2 + k2 * r4 + k3 * r6 + k4 * r8)
                    y = (yd - (p2 * (r2 + 2.0 * y2) + 2.0 * p1 * x * y) * (1.0 + p3 * r2 + p4 * r4)) / (
                                1.0 + k1 * r2 + k2 * r4 + k3 * r6 + k4 * r8)
                    dif_x = x - xBefore
                    dif_y = y - yBefore
                    if np.sqrt(dif_x * dif_x + dif_y * dif_y) < tolerance:
                        control = False
            else:
                b1 = 0.
                b2 = 0.
                if not use_ppa:
                    cx = 0.
                    cy = 0.
                yd = (row - rows * 0.5 - cy) / f
                xd = (column - columns * 0.5 - cx - yd * b2) / (f + b1)
                x = xd
                y = yd
            Z = 1.0 # f
            X = x
            Y = y
        if calibration.type.casefold() == defs_msm.METASHAPE_CALIBRATION_TYPE_FISHEYE:
            f = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_F_TAG]
            cx = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CX_TAG]
            cy = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_CY_TAG]
            b1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B1_TAG]
            b2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_B2_TAG]
            x = None
            y = None
            if use_distortion:
                k1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K1_TAG]
                k2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K2_TAG]
                k3 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K3_TAG]
                k4 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_K4_TAG]
                p1 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P1_TAG]
                p2 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P2_TAG]
                p3 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P3_TAG]
                p4 = calibration.parameters[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_P4_TAG]
                yd = (row - rows * 0.5 - cy) / f
                xd = (column - columns * 0.5 - cx - yd * b2) / (f + b1)
                x = xd
                y = yd
                control = True
                tolerance = 0.001 / f
                while control:
                    xBefore = x
                    yBefore = y
                    r = np.sqrt(x * x + y * y)
                    r2 = r * r
                    r4 = r2 * r2
                    r6 = r2 * r4
                    r8 = r4 * r4
                    x2 = x * x
                    y2 = y * y
                    # x=xd/(1.0+k1*r2+k2*r4+k3*r6+k4*r8)-(p1*(r2+2.0*x2)-2.0*p2*x*y)*(1.0+p3*r2+p4*r4)
                    # y=yd/(1.0+k1*r2+k2*r4+k3*r6+k4*r8)-(p2*(r2+2.0*y2)-2.0*p1*x*y)*(1.0+p3*r2+p4*r4)
                    x = (xd - (p1 * (r2 + 2.0 * x2) + 2.0 * p2 * x * y) * (1.0 + p3 * r2 + p4 * r4)) / (
                                1.0 + k1 * r2 + k2 * r4 + k3 * r6 + k4 * r8)
                    y = (yd - (p2 * (r2 + 2.0 * y2) + 2.0 * p1 * x * y) * (1.0 + p3 * r2 + p4 * r4)) / (
                                1.0 + k1 * r2 + k2 * r4 + k3 * r6 + k4 * r8)
                    dif_x = x - xBefore
                    dif_y = y - yBefore
                    if np.sqrt(dif_x * dif_x + dif_y * dif_y) < tolerance:
                        control = False
            else:
                b1 = 0.
                b2 = 0.
                if not use_ppa:
                    cx = 0.
                    cy = 0.
                yd = (row - rows * 0.5 - cy) / f
                xd = (column - columns * 0.5 - cx - yd * b2) / (f + b1)
                x = xd
                y = yd
            # x = x0 * tan-1r0 / r0
            # y = y0 * tan-1r0 / r0
            # r0 = sqrt(x02 + y02)
            # x0 = X / Z
            # y0 = Y / Z
            # x^2 + y^2 = (x0^2 + y0^2) * atan(r0)^2 / r0^2
            # r^2 = r0^2 * atan(r0)^2 / r0^2
            # r = atan(r0)
            # r0 = tan(r)
            r = np.sqrt(x*x+y*y)
            r0 = np.tan(r)
            x0 = x*r0 / np.arctan(r0)
            y0 = y*r0 / np.arctan(r0)
            Z = 1.0 #f
            X = x0
            Y = y0
        if isinstance(self.rotation,np.ndarray):
            coor = np.zeros(3)
            coor[0] = X
            coor[1] = Y
            coor[2] = Z
            rotated_coor = np.dot(self.rotation, coor)
            X = rotated_coor[0]
            Y = rotated_coor[1]
            Z = rotated_coor[2]
        return str_error, X, Y, Z


    def set_from_metashape_xml(self,
                               xml_element):
        str_error = ''
        #id
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_ATTRIBUTE_ID in xml_element:
            str_error = ('Not exists attribute: {} in sensor in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_ATTRIBUTE_ID, self.at_block.file_path))
            return str_error
        str_id = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_ATTRIBUTE_ID]
        try:
            self.id = int(str_id)
        except ValueError:
            str_error = ('Attribute: {} in sensor in metashape markers XML file:\n{}\n must be an integer: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_ATTRIBUTE_ID, self.at_block.file_path, str_id))
            return str_error
        if self.id in self.at_block.sensor_by_id:
            str_error = ('Exists previous sensor id: {} in sensor in metashape markers XML file:\n{}'.
                         format(str(self.id), self.file_path,))
            return str_error
        # label
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_ATTRIBUTE_LABEL in xml_element:
            str_error = ('Not exists attribute: {} in sensor in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_ATTRIBUTE_LABEL, self.at_block.file_path))
            return str_error
        label = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_ATTRIBUTE_LABEL]
        self.label = label
        # master id
        if defs_msm.METASHAPE_MARKERS_XML_SENSOR_ATTRIBUTE_MASTER_ID in xml_element:
            str_master_id = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_ATTRIBUTE_MASTER_ID]
            try:
                self.master_id = int(str_master_id)
            except ValueError:
                str_error = ('Attribute: {} in sensor: {} in metashape markers XML file:\n{}\n must be an integer: {}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_ATTRIBUTE_MASTER_ID, self.label, self.at_block.file_path, str_id))
                return str_error
            # rotation
            if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_ROTATION_TAG in xml_element:
                str_error = ('Not exists element: {} in sensor: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_ROTATION_TAG, self.label, self.at_block.file_path))
                return str_error
            rotation_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_ROTATION_TAG]
            try:
                rotation_values = [float(x) for x in rotation_element.split()]
            except:
                str_error = ('Not float values in: {} in rotation in sensor: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_ROTATION_TAG, self.label, self.at_block.file_path))
                return str_error
            if len(rotation_values) != 9:
                str_error = ('Not 9 float values in: {} in rotation in sensor: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_ROTATION_TAG, self.label, self.at_block.file_path))
                return str_error
            self.rotation = np.zeros((3, 3))
            for row in range(0, 3):
                for col in range(0, 3):
                    pos = row * 3 + col
                    self.rotation[row, col] = rotation_values[pos]
            u, s, v = np.linalg.svd(self.rotation)
            self.rotation_inv = np.dot(v.transpose(), np.dot(np.diag(s ** -1), u.transpose()))
            # rotation_covariance
            if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_ROTATION_COVARIANCE_TAG in xml_element:
                str_error = ('Not exists element: {} in sensor: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_ROTATION_COVARIANCE_TAG, self.label, self.at_block.file_path))
                return str_error
            rotation_covariance_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_ROTATION_COVARIANCE_TAG]
            try:
                rotation_covariance_values = [float(x) for x in rotation_covariance_element.split()]
            except:
                str_error = ('Not float values in: {} in rotation covariance in sensor: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_ROTATION_COVARIANCE_TAG, self.label, self.at_block.file_path))
                return str_error
            if len(rotation_covariance_values) != 9:
                str_error = (
                    'Not 9 float values in: {} in rotation covariance in sensor: {} in metashape markers XML file:\n{}'.
                    format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_ROTATION_COVARIANCE_TAG, self.label, self.at_block.file_path))
                return str_error
            self.rotation_covariance = np.zeros((3, 3))
            for row in range(0, 3):
                for col in range(0, 3):
                    pos = row + 3 * col
                    self.rotation_covariance[row, col] = rotation_covariance_values[pos]
        # resolution: width and height
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_TAG, self.at_block.file_path))
            return str_error
        resolution_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_TAG]
        if not isinstance(resolution_element, dict):
            str_error = (
                'Element: {} in sensor in metashape markers XML file:\n{}\npmust be a dictionary'.
                format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_TAG, self.at_block.file_path))
            return str_error
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_ATTRIBUTE_WIDTH in resolution_element:
            str_error = ('Not exists attribute: {} in: {} in sensor in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_ATTRIBUTE_WIDTH,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_TAG, self.at_block.file_path))
            return str_error
        str_width = resolution_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_ATTRIBUTE_WIDTH]
        try:
            self.width = int(str_width)
        except ValueError:
            str_error = ('Attribute: {} in: {} in sensor in metashape markers XML file:\n{}\n must be an integer: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_ATTRIBUTE_WIDTH,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_TAG, self.at_block.file_path, str_width))
            return str_error
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_ATTRIBUTE_HEIGHT in resolution_element:
            str_error = ('Not exists attribute: {} in: {} in sensor in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_ATTRIBUTE_HEIGHT,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_TAG, self.at_block.file_path))
            return str_error
        str_height = resolution_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_ATTRIBUTE_HEIGHT]
        try:
            self.height = int(str_height)
        except ValueError:
            str_error = ('Attribute: {} in: {} in sensor in metashape markers XML file:\n{}\n must be an integer: {}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_ATTRIBUTE_HEIGHT,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_RESOLUTION_TAG, self.at_block.file_path, str_height))
            return str_error
        # propierty: pixel width, pixel height, focal
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG in xml_element:
            str_error = ('Not exists attribute: {} in sensor in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG, self.at_block.file_path))
            return str_error
        propierty_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG]
        if not isinstance(propierty_element, list):
            str_error = ('Element: {} in sensor in metashape markers XML file:\n{}\nmust be a list'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG, self.at_block.file_path))
            return str_error
        for i in range(len(propierty_element)):
            propierty = propierty_element[i]
            if not isinstance(propierty, dict):
                str_error = ('Element: {} in sensor in metashape markers XML file:\n{}\npropierty position: {} must be a dictionary'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG, self.at_block.file_path, str(i+1)))
                return str_error
            if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_ATTRIBUTE_NAME in propierty:
                str_error = ('Not exists attribute: {} in element: {}\nin position: {} in sensor in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_ATTRIBUTE_NAME,
                                    defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG,  str(i+1), self.at_block.file_path))
                return str_error
            str_name = propierty[defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_ATTRIBUTE_NAME]
            if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_ATTRIBUTE_VALUE in propierty:
                str_error = ('Not exists attribute: {} in element: {}\nin position: {} in sensor in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_ATTRIBUTE_VALUE,
                                    defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG,  str(i+1), self.at_block.file_path))
                return str_error
            str_value = propierty[defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_ATTRIBUTE_VALUE]
            if str_name.casefold() == defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_PIXEL_WITH_NAME.casefold():
                try:
                    self.pixel_width = float(str_value)
                except ValueError:
                    str_error = (
                        'Attribute: {} in element: {}\nin position: {} in sensor in metashape markers XML file:\n{}\n must be a float'.
                        format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_ATTRIBUTE_NAME,
                               defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG, str(i + 1), self.at_block.file_path))
                    return str_error
            elif str_name.casefold() == defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_PIXEL_HEIGHT_NAME.casefold():
                try:
                    self.pixel_height = float(str_value)
                except ValueError:
                    str_error = (
                        'Attribute: {} in element: {}\nin position: {} in sensor in metashape markers XML file:\n{}\n must be a float'.
                        format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_ATTRIBUTE_NAME,
                               defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG, str(i + 1), self.at_block.file_path))
                    return str_error
            elif str_name.casefold() == defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_FOCAL_LENGTH_NAME.casefold():
                try:
                    self.focal_length = float(str_value)
                except ValueError:
                    str_error = (
                        'Attribute: {} in element: {}\nin position: {} in sensor in metashape markers XML file:\n{}\n must be a float'.
                        format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_ATTRIBUTE_NAME,
                               defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG, str(i + 1), self.at_block.file_path))
                    return str_error
            elif str_name.casefold() == defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_NORMALIZE_SENSITIVITY_NAME.casefold():
                self.normalize_sensitivity = False
                if str_value.casefold() == 'true':
                    self.normalize_sensitivity = True
            elif str_name.casefold() == defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_LAYER_INDEX_NAME.casefold():
                try:
                    self.layer_index = int(str_value)
                except ValueError:
                    str_error = (
                        'Attribute: {} in element: {}\nin position: {} in sensor in metashape markers XML file:\n{}\n must be an integer'.
                        format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_ATTRIBUTE_NAME,
                               defs_msm.METASHAPE_MARKERS_XML_SENSOR_PROPERTY_TAG, str(i + 1), self.at_block.file_path))
                    return str_error
        # bands
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_BANDS_TAG in xml_element:
            str_error = ('Not exists element: {} in sensor in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_BANDS_TAG, self.at_block.file_path))
            return str_error
        bands_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_BANDS_TAG]
        if not isinstance(bands_element, dict):
            str_error = (
                'Element: {} in sensor in metashape markers XML file:\n{}\nmust be a dictionary'.
                format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_BANDS_TAG, self.at_block.file_path))
            return str_error
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_BAND_TAG in bands_element:
            str_error = ('Not exists element: {} in element: {} in sensor in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_BAND_TAG,
                                defs_msm.METASHAPE_MARKERS_XML_SENSOR_BANDS_TAG, self.at_block.file_path))
            return str_error
        bands_element = bands_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_BAND_TAG]
        bands_list = []
        if isinstance(bands_element, list):
            bands_list = bands_element
        else:
            bands_list.append(bands_element)
        for i in range(len(bands_list)):
            band = bands_list[i]
            if not isinstance(band, dict):
                str_error = (
                    'Band position: {} in element: {} in sensor in metashape markers XML file:\n{}\nmust be a dictionary'.
                    format(str(i+1), defs_msm.METASHAPE_MARKERS_XML_SENSOR_BANDS_TAG, self.at_block.file_path))
                return str_error
            if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_BAND_ATTRIBUTE_LABEL in band:
                str_error = (
                    'No attribute: {} in band position: {} in element: {} in sensor in metashape markers XML file:\n{}'.
                    format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_BAND_ATTRIBUTE_LABEL,
                           str(i+1), defs_msm.METASHAPE_MARKERS_XML_SENSOR_BANDS_TAG, self.at_block.file_path))
                return str_error
            band_label = band[defs_msm.METASHAPE_MARKERS_XML_SENSOR_BAND_ATTRIBUTE_LABEL]
            self.band_names.append(band_label)
        # data_type
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_DATA_TYPE_TAG in xml_element:
            str_error = ('Not exists element: {} in sensor in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_DATA_TYPE_TAG, self.at_block.file_path))
            return str_error
        self.data_type_as_string = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_DATA_TYPE_TAG]
        # black_level
        if defs_msm.METASHAPE_MARKERS_XML_SENSOR_BLACK_LEVEL_TAG in xml_element:
            str_black_level = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_BLACK_LEVEL_TAG]
            try:
                self.black_level = float(str_black_level)
            except ValueError:
                str_error = (
                    'Element: {} in sensor in metashape markers XML file:\n{}\n must be a float'.
                    format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_BLACK_LEVEL_TAG, self.at_block.file_path))
                return str_error
        # sensitivity
        if defs_msm.METASHAPE_MARKERS_XML_SENSOR_SENSITIVITY_TAG in xml_element:
            str_black_level = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_SENSITIVITY_TAG]
            try:
                self.sensitivity = float(str_black_level)
            except ValueError:
                str_error = (
                    'Element: {} in sensor in metashape markers XML file:\n{}\n must be a float'.
                    format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_SENSITIVITY_TAG, self.at_block.file_path))
                return str_error
        # vignetting
        if defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG in xml_element:
            vignetting_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG]
            if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG in vignetting_element:
                str_error = ('Not exists element: {} in element: {} in sensor in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG, self.at_block.file_path))
                return str_error
            coeff_elements = vignetting_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG]
            if not isinstance(coeff_elements, list):
                str_error = ('Element: {} in element: {} in sensor in metashape markers XML file:\n{} must be a list'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG, self.at_block.file_path))
                return str_error
            for i in range(len(coeff_elements)):
                coeff_element = coeff_elements[i]
                if not isinstance(coeff_element, dict):
                    str_error = ('Position: {} in element: {} in element: {} in sensor in metashape markers XML file:\n{} must be a dictionary'.
                                 format(str(i+1), defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG,
                                        defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG, self.at_block.file_path))
                    return str_error
                if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_ATTRIBUTE_I in coeff_element:
                    str_error = (
                        'No attribute: {} in position: {} in element: {}\n in element: {} in sensor in metashape markers XML file:\n{}'.
                        format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_ATTRIBUTE_I,
                               str(i + 1), defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG,
                               defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG, self.at_block.file_path))
                    return str_error
                str_i = coeff_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_ATTRIBUTE_I]
                i_pos = None
                try:
                    i_pos = int(str_i)
                except ValueError:
                    str_error = (
                        'Attribute: {} in position: {} in element: {}\n in element: {} in sensor in metashape markers XML file:\n{}\nmust be an integer'.
                        format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_ATTRIBUTE_I,
                               str(i + 1), defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG,
                               defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG, self.at_block.file_path))
                    return str_error
                if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_ATTRIBUTE_J in coeff_element:
                    str_error = (
                        'No attribute: {} in position: {} in element: {}\n in element: {} in sensor in metashape markers XML file:\n{}'.
                        format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_ATTRIBUTE_J,
                               str(i + 1), defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG,
                               defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG, self.at_block.file_path))
                    return str_error
                str_j = coeff_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_ATTRIBUTE_J]
                j_pos = None
                try:
                    j_pos = int(str_j)
                except ValueError:
                    str_error = (
                        'Attribute: {} in position: {} in element: {}\n in element: {} in sensor in metashape markers XML file:\n{}\nmust be an integer'.
                        format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_ATTRIBUTE_J,
                               str(i + 1), defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG,
                               defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG, self.at_block.file_path))
                    return str_error
                if not defs_msm.METASHAPE_MARKERS_XML_TEXT in coeff_element:
                    str_error = (
                        'No attribute: {} in position: {} in element: {}\n in element: {} in sensor in metashape markers XML file:\n{}'.
                        format(defs_msm.METASHAPE_MARKERS_XML_TEXT,
                               str(i + 1), defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG,
                               defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG, self.at_block.file_path))
                    return str_error
                str_value = coeff_element[defs_msm.METASHAPE_MARKERS_XML_TEXT]
                value = None
                try:
                    value = float(str_value)
                except ValueError:
                    str_error = (
                        'Attribute: {} in position: {} in element: {}\n in element: {} in sensor in metashape markers XML file:\n{}\nmust be a float'.
                        format(defs_msm.METASHAPE_MARKERS_XML_TEXT,
                               str(i + 1), defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_COEFF_TAG,
                               defs_msm.METASHAPE_MARKERS_XML_SENSOR_VIGNETTING_TAG, self.at_block.file_path))
                    return str_error
                if not i_pos in self.vignetting:
                    self.vignetting[i_pos] = {}
                self.vignetting[i_pos][j_pos] = value
        # calibrations
        if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_TAG in xml_element:
            str_error = ('Not exists element: {} in sensor: {} in metashape markers XML file:\n{}'.
                         format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_TAG, self.label, self.at_block.file_path))
            return str_error
        calibration_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_TAG]
        calibrations_list = []
        if isinstance(calibration_element, list):
            calibrations_list = calibration_element
        else:
            calibrations_list.append(calibration_element)
        for i in range(len(calibrations_list)):
            calibration_element = calibrations_list[i]
            calibration = CalibrationMetashape(self)
            str_error = calibration.set_from_metashape_xml(calibration_element)
            if str_error:
                str_error = ('Loading calibration position: {}\n in sensor: {} in metashape markers XML file:\n{}'.
                             format(str(i+1), self.label, self.at_block.file_path))
                return str_error
            self.calibration_by_class[calibration.kind] = calibration
        # calibration covariance
        if defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_TAG in xml_element:
            calibration_covariance_element = xml_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_TAG]
            if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_PARAMS_TAG in calibration_covariance_element:
                str_error = ('Not exists element: {} in element: {} in sensor: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_PARAMS_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_TAG, self.label, self.at_block.file_path))
                return str_error
            params_element = calibration_covariance_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_PARAMS_TAG]
            if not defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_COEFFS_TAG in calibration_covariance_element:
                str_error = ('Not exists element: {} in element: {} in sensor: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_COEFFS_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_TAG, self.label, self.at_block.file_path))
                return str_error
            coeffs_element = calibration_covariance_element[defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_COEFFS_TAG]
            try:
                params_values = [str(x) for x in params_element.split()]
            except:
                str_error = ('Not string values in: {} in element: {} in sensor: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_PARAMS_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_TAG, self.label, self.at_block.file_path))
                return str_error
            self.calibration_covariance_params = params_values
            number_of_params = len(params_values)
            try:
                coeffs_values = [float(x) for x in coeffs_element.split()]
            except:
                str_error = ('Not string values in: {} in element: {} in sensor: {} in metashape markers XML file:\n{}'.
                             format(defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_COEFFS_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_TAG, self.label, self.at_block.file_path))
                return str_error
            if len(coeffs_values) != (number_of_params ** 2.):
                str_error = ('Not {} values in: {} in element: {} in sensor: {} in metashape markers XML file:\n{}'.
                             format(str(number_of_params ** 2.), defs_msm.METASHAPE_MARKERS_XML_SENSOR_COVARIANCE_COEFFS_TAG,
                                    defs_msm.METASHAPE_MARKERS_XML_SENSOR_CALIBRATION_TAG, self.label, self.at_block.file_path))
                return str_error
            self.calibration_covariance_values = np.zeros((number_of_params, number_of_params))
            for row in range(0, number_of_params):
                for col in range(0, number_of_params):
                    pos = row + number_of_params * col
                    self.calibration_covariance_values[row, col] = coeffs_values[pos]
        return str_error

    def set_geometry(self):
        str_error = ''
        if self.geometry:
            return
        columns = self.width
        rows = self.height
        numberOfPointsBySide = SENSOR_GEOMETRY_SIDE_NUMBER_OF_POINTS
        columnsIncrement = int(np.floor(float(columns) / float(numberOfPointsBySide - 1.)))
        rowsIncrement = int(np.floor(float(rows) / float(numberOfPointsBySide - 1.)))
        pixelsRows = []
        pixelsColumns = []
        # upper row
        pixelCont = 0
        pixelRow = 0
        pixelColumn = 0
        pixelsRows.append(pixelRow)
        pixelsColumns.append(pixelColumn)
        pixelCont = pixelCont + 1
        while(pixelCont < (numberOfPointsBySide - 1)):
            pixelColumn += columnsIncrement
            pixelsRows.append(pixelRow)
            pixelsColumns.append(pixelColumn)
            pixelCont = pixelCont + 1
        pixelColumn = columns-1
        pixelsRows.append(pixelRow)
        pixelsColumns.append(pixelColumn)
        # right column
        pixelCont = 1
        pixelRow = 0
        pixelColumn = columns-1
        while(pixelCont < (numberOfPointsBySide-1)):
            pixelRow+=rowsIncrement
            pixelsRows.append(pixelRow)
            pixelsColumns.append(pixelColumn)
            pixelCont = pixelCont + 1
        pixelRow = rows-1
        pixelsRows.append(pixelRow)
        pixelsColumns.append(pixelColumn)
        # lower row
        pixelCont = 1
        pixelRow = rows-1
        pixelColumn = columns-1
        while(pixelCont < (numberOfPointsBySide-1)):
            pixelColumn-=columnsIncrement
            pixelsRows.append(pixelRow)
            pixelsColumns.append(pixelColumn)
            pixelCont = pixelCont + 1
        pixelColumn = 0
        pixelsRows.append(pixelRow)
        pixelsColumns.append(pixelColumn)
        # left column
        pixelCont = 1
        pixelRow = rows-1
        pixelColumn = 0
        while(pixelCont < (numberOfPointsBySide-1)):
            pixelRow -= rowsIncrement
            pixelsRows.append(pixelRow)
            pixelsColumns.append(pixelColumn)
            pixelCont = pixelCont + 1
        wkt_geometry = "POLYGON(("
        firstPointX = None
        firstPointY = None
        for i in range(len(pixelsRows)):
            column = float(pixelsColumns[i])
            row = float(pixelsRows[i])
            str_error, X, Y, Z = self.from_sensor_to_camera_coordinates_direction(column,row)
            if str_error:
                str_error = ('In sensor: {}} error getting direction for coordinates: [{},{}]\nError:\n{}}'.
                             format(self.label, str(column), str(row), str_error))
                return str_error
            X = X / Z
            Y = Y / Z
            if i == 0:
                firstPointX = X
                firstPointY = Y
            wkt_geometry += ('{:6f}'.format(X))
            wkt_geometry += " "
            wkt_geometry += ('{:6f}'.format(Y))
            wkt_geometry += ","
        wkt_geometry += ('{:6f}'.format(firstPointX))
        wkt_geometry += " "
        wkt_geometry += ('{:6f}'.format(firstPointY))
        wkt_geometry += "))"
        try:
            self.geometry = ogr.CreateGeometryFromWkt(wkt_geometry)
        except Exception as e:
            # str_error = 'GDAL Error: ' + e.args[0]
            # str_error = ('Setting geometry in sensor: {}\nGDAL error:\n{}}'.
            #              format(self.label, e.args[0]))
            str_error = ('Error setting geometry in sensor: {} from WKT'.
                         format(self.label))
            return str_error
        return str_error
