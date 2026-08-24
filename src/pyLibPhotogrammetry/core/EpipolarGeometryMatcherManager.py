# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
from math import floor, ceil, sqrt
import numpy as np
import cv2

from qgis.PyQt.QtWidgets import QApplication, QDialog

import os, sys
from datetime import datetime
import psutil

from ..defs import defs_project as defs_project
from ..defs import defs_processes
from ..defs import defs_images as defs_img
#from ..core.ProjectPhotogrammetry import ProjectPhotogrammetry
from ..core.ATBlockMetashape import ATBlockMetashape
from ..core.ATBlockGraphos import ATBlockGraphos

EPIPOLARGEOMETRYMATCHERMANAGER_MATCH_WINDOW_RADIUS_FIRST = 5
EPIPOLARGEOMETRYMATCHERMANAGER_MATCH_WINDOW_RADIUS_LAST = 9

class EpipolarGeometryMatcherManager():
    def __init__(self, project):
        self.project = project
        self.at_block = None
        self.tile_size = -1
        self.tile_x = -1
        self.tile_y = -1
        self.load_image_by_id = {}
        self.measuredCamerasId = []
        self.undistortedMeasuredColumns = []
        self.undistortedMeasuredRows = []
        self.matchedCamerasId = []
        self.undistortedMatchedColumns = []
        self.undistortedMatchedRows = []
        self.matchedNames = []
        self.measuredCamerasPc = []
        self.matchedCamerasPc = []
        self.matchedFinds = []
        self.qualitiesValues = []
        self.match_opencv_method = None
        self.match_maximum_epipolar_row_parallax = None
        self.maximum_height_separation_within_dsm = None
        self.maximum_height_separation_outside_dsm = None
        self.match_pencv_threshold_percentage = None
        self.point_height_dem = None
        self.focal_in_pixels = None
        self.point_outside_dem = None
        self.match_window_radius_first = EPIPOLARGEOMETRYMATCHERMANAGER_MATCH_WINDOW_RADIUS_FIRST
        self.match_window_radius_last = EPIPOLARGEOMETRYMATCHERMANAGER_MATCH_WINDOW_RADIUS_LAST

    def load_tile_in_memory(self, tile_size,
                            tile_x, tile_y,
                            dialog = None):
        str_error = ''
        loaded_tile = False
        if tile_size == self.tile_size:
            if tile_x == self.tile_x and tile_y == self.tile_y:
                loaded_tile = True
                return str_error, loaded_tile
        if (not tile_size in self.project.imagesTilesImagesIdBySize
                or not tile_size in self.project.imagesMaximumRamMBsBySize
                or not tile_size in self.project.imagesTileRamMBsBySize):
            str_error = "EpipolarGeometryMatcherManager.load_tile_in_memory"
            str_error += ("Not exists tile size: {}".format(str(tile_size)))
            return str_error, loaded_tile
        # not tile in container but not an error
        if (not tile_x in self.project.imagesTilesImagesIdBySize[tile_size]
                or not tile_x in self.project.imagesTileRamMBsBySize[tile_size]):
            return str_error, loaded_tile
        if (not tile_y in self.project.imagesTilesImagesIdBySize[tile_size][tile_x]
                or not tile_y in self.project.imagesTileRamMBsBySize[tile_size][tile_x]):
            return str_error, loaded_tile
        images_to_load = self.project.imagesTilesImagesIdBySize[tile_size][tile_x][tile_y]
        for image_loaded_id in self.load_image_by_id:
            if not image_loaded_id in images_to_load:
                self.load_image_by_id.pop(image_loaded_id)
        if len(self.project.at_block_by_label) != 1:
            str_error = "EpipolarGeometryMatcherManager.load_tile_in_memory"
            str_error += ("Valid only for project with one ATBlock")
            return str_error, loaded_tile
        at_block_label = next(iter(self.project.at_block_by_label))
        at_block = self.project.at_block_by_label[at_block_label]
        if self.at_block == None:
            self.at_block = at_block
        if dialog:
            dialog.processInformationGroupBox.setEnabled(True)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            dialog.processLineEdit.setText('Loading images for epipolar matching ...')
            dialog.processLineEdit.adjustSize()
            dialog.processProgressBar.setMaximum(len(at_block.camera_by_id))
            dialog.processLineEdit.adjustSize()
            QApplication.processEvents()
        cont = 0
        for camera_id in at_block.camera_by_id:
            cont = cont + 1
            if dialog:
                dialog.processProgressBar.setValue(cont)
                QApplication.processEvents()
            if camera_id in self.load_image_by_id:
                continue
            camera = at_block.camera_by_id[camera_id]
            camera_enabled = camera.get_enabled()  # multisensor ...
            undistorted_image_file_name = camera.undistort_image_file_path
            if undistorted_image_file_name is not None:
                if os.path.exists(undistorted_image_file_name):
                    img = cv2.imread(undistorted_image_file_name, cv2.IMREAD_IGNORE_ORIENTATION | cv2.IMREAD_GRAYSCALE)
                    if img is None:
                        str_error = "EpipolarGeometryMatcherManager.load_tile_in_memory"
                        str_error += ("\nError opening image:\n{}".format(undistorted_image_file_name))
                        dialog.processProgressBar.setValue(len(at_block.camera_by_id))
                        dialog.processInformationGroupBox.setEnabled(False)
                        dialog.processLineEdit.clear()
                        dialog.processProgressBar.reset()
                        return str_error, loaded_tile
                    self.load_image_by_id[camera_id] = img
        if dialog:
            dialog.processProgressBar.setValue(len(at_block.camera_by_id))
            dialog.processInformationGroupBox.setEnabled(False)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            QApplication.processEvents()
        if len(self.load_image_by_id) > 0:
            self.tile_size = tile_size
            self.tile_x = tile_x
            self.tile_y = tile_y
            loaded_tile = True
        return str_error, loaded_tile

    def match_image_rfa(self, position):
        str_error = ""
        matched_find = False
        write_matches_images = False
        measured_camera_id = self.measuredCamerasId[position]
        undistorted_measured_column = self.undistortedMeasuredColumns[position]
        undistorted_measured_row = self.undistortedMeasuredRows[position]
        matched_camera_id = self.matchedCamerasId[position]
        undistorted_matched_column = self.undistortedMatchedColumns[position][0]
        self.undistortedMatchedColumns[position].clear()
        undistorted_matched_row = self.undistortedMatchedRows[position][0]
        self.undistortedMatchedRows[position].clear()
        measured_camera = self.at_block.get_camera_from_camera_id(measured_camera_id)
        matched_camera = self.at_block.get_camera_from_camera_id(matched_camera_id)
        measured_undistorted_image_file_path = measured_camera.undistort_image_file_path
        matched_undistorted_image_file_path = matched_camera.undistort_image_file_path
        mFImgH = self.project.homographyMatrixByImagesId[measured_camera_id][matched_camera_id]
        mSImgH = self.project.homographyMatrixByImagesId[matched_camera_id][measured_camera_id]
        mFImgInvH = self.project.inverseHomographyMatrixByImagesId[measured_camera_id][matched_camera_id]
        mSImgInvH = self.project.inverseHomographyMatrixByImagesId[matched_camera_id][measured_camera_id]
        firstHomographyImageEnvelope = self.project.spEpipolarEnvelopeByImagesIds[measured_camera_id][matched_camera_id]
        secondHomographyImageEnvelope = self.project.spEpipolarEnvelopeByImagesIds[matched_camera_id][measured_camera_id]
        matchWindowSizes = []
        window_radius = self.match_window_radius_first
        while window_radius <= self.match_window_radius_last:
            matchWindowSizes.append(window_radius * 2 + 1)
            window_radius = window_radius + 1
        measuredPcFc = self.measuredCamerasPc[position][0];
        measuredPcSc = self.measuredCamerasPc[position][1];
        measuredPcTc = self.measuredCamerasPc[position][2];
        matchedPcFc = self.matchedCamerasPc[position][0];
        matchedPcSc = self.matchedCamerasPc[position][1];
        matchedPcTc = self.matchedCamerasPc[position][2];
        stereoscopicBase = sqrt((matchedPcFc - measuredPcFc) ** 2.+ (matchedPcSc - measuredPcSc) ** 2.
                                + (matchedPcTc - measuredPcTc) ** 2.)
        # Fotogrametria digital, Toni Schenk, pg 281-282
        incZ = 10.0
        if self.point_outside_dem:
            incZ = self.maximum_height_separation_outside_dsm * 2.
        else:
            incZ = self.maximum_height_separation_within_dsm * 2.
        Zu = self.point_height_dem + incZ / 2
        Zl = self.point_height_dem - incZ / 2
        Hd = (measuredPcTc + matchedPcTc) / 2.
        inzZFactor = incZ / ((Hd - Zl) * (Hd - Zu))
        inzZFactorSb = stereoscopicBase * inzZFactor
        findWindowSize = ceil(self.focal_in_pixels * inzZFactorSb)
        # obtengo la ventana en la homografia de la imagen medida
        xsm = undistorted_measured_column + .5
        ysm = undistorted_measured_row + .5
        denm = xsm * mFImgH[2, 0] + ysm * mFImgH[2, 1] + 1. * mFImgH[2, 2]
        xtm = xsm * mFImgH[0, 0] + ysm * mFImgH[0, 1] + 1. * mFImgH[0, 2]
        ytm = xsm * mFImgH[1, 0] + ysm * mFImgH[1, 1] + 1. * mFImgH[1, 2]
        xtm /= denm
        ytm /= denm
        xtm = xtm - .5
        ytm = ytm - .5
        # obtengo la posicion en la homografia de la aproximacion proyecta
        xsmt = undistorted_matched_column + .5
        ysmt = undistorted_matched_row + .5
        denmt = xsmt * mSImgH[2, 0] + ysmt * mSImgH[2, 1] + 1. * mSImgH[2, 2]
        xtmt = xsmt * mSImgH[0, 0] + ysmt * mSImgH[0, 1] + 1. * mSImgH[0, 2]
        ytmt = xsmt * mSImgH[1, 0] + ysmt * mSImgH[1, 1] + 1. * mSImgH[1, 2]
        xtmt /= denmt
        ytmt /= denmt
        xtmt = xtmt - .5
        ytmt = ytmt - .5
        measured_img = self.load_image_by_id[measured_camera_id]
        measured_img_columns = measured_img.shape[1]
        measured_img_rows = measured_img.shape[0]
        matchMethods = []
        if (self.match_opencv_method.casefold() ==
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD_ALL.casefold()):
            matchMethods.append(
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD_TM_CCORR_NORMED)
            matchMethods.append(
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD_TM_COEFF_NORMED)
            matchMethods.append(
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD_TM_SQDIFF_NORMED)
        else:
            matchMethods.append(self.match_opencv_method)
        undistortedMatchedColumns = []
        undistortedMatchedRows = []
        qValues = []
        pointsInCluster = []
        minDifferences = []
        meanDifferences = []
        maxDifferences = []
        for nws in range(len(matchWindowSizes)):
            matchWindowSizeFromCenter = floor(float(matchWindowSizes[nws]/2.))
            minimumMatchWindowSizeFromCenter = matchWindowSizeFromCenter/2
            findWindowSizeFromCenter = ceil(findWindowSize/2.)
            if findWindowSizeFromCenter < matchWindowSizeFromCenter:
                findWindowSizeFromCenter = findWindowSizeFromCenter + 2
            minimumFindWindowSizeFromCenter = findWindowSizeFromCenter / 2
            sourceReducedHomographyColumn = floor(xtm) - firstHomographyImageEnvelope[0]
            sourceReducedHomographyRow = floor(ytm) - firstHomographyImageEnvelope[1]
            targetReducedHomographyColumn = floor(xtmt) - secondHomographyImageEnvelope[0]
            targetReducedHomographyRow = floor(ytm) - secondHomographyImageEnvelope[1]
            if (sourceReducedHomographyColumn < minimumMatchWindowSizeFromCenter
                    or sourceReducedHomographyRow < minimumMatchWindowSizeFromCenter
                    or sourceReducedHomographyColumn > (firstHomographyImageEnvelope[2] - minimumMatchWindowSizeFromCenter-1)
                    or sourceReducedHomographyRow > (firstHomographyImageEnvelope[3]-minimumMatchWindowSizeFromCenter-1)):
                 continue
            firstReducedHomographyWindow = []
            firstReducedHomographyWindow.append(sourceReducedHomographyColumn-matchWindowSizeFromCenter)
            if firstReducedHomographyWindow[0] < 0:
                firstReducedHomographyWindow[0] = 0
            firstReducedHomographyWindow.append(sourceReducedHomographyRow - matchWindowSizeFromCenter)
            if firstReducedHomographyWindow[1] < 0:
                firstReducedHomographyWindow[1] = 0
            firstReducedHomographyWindow.append(sourceReducedHomographyColumn + matchWindowSizeFromCenter)
            if firstReducedHomographyWindow[2] > (firstHomographyImageEnvelope[2] - 1):
                firstReducedHomographyWindow[2] = firstHomographyImageEnvelope[2] - 1
            firstReducedHomographyWindow.append(sourceReducedHomographyRow + matchWindowSizeFromCenter)
            if firstReducedHomographyWindow[3] > (firstHomographyImageEnvelope[3] - 1):
                firstReducedHomographyWindow[3] = firstHomographyImageEnvelope[3] - 1
            if (targetReducedHomographyRow<minimumMatchWindowSizeFromCenter
                    or targetReducedHomographyRow>(secondHomographyImageEnvelope[2]-minimumMatchWindowSizeFromCenter-1)):
                continue
            if (targetReducedHomographyColumn<minimumFindWindowSizeFromCenter
                    or targetReducedHomographyColumn>(secondHomographyImageEnvelope[2]-minimumFindWindowSizeFromCenter-1)):
                continue
            secondReducedHomographyFindArea = []
            secondReducedHomographyFindArea.append(targetReducedHomographyColumn - findWindowSizeFromCenter)
            if secondReducedHomographyFindArea[0] < 0:
                secondReducedHomographyFindArea[0] = 0
            secondReducedHomographyFindArea.append(targetReducedHomographyRow - matchWindowSizeFromCenter
                                                   - self.match_maximum_epipolar_row_parallax)
            if secondReducedHomographyFindArea[1] < 0:
                secondReducedHomographyFindArea[1] = 0
            secondReducedHomographyFindArea.append(targetReducedHomographyColumn + findWindowSizeFromCenter)
            if secondReducedHomographyFindArea[2] > (secondHomographyImageEnvelope[2] - 1):
                secondReducedHomographyFindArea[2] = secondHomographyImageEnvelope[2] - 1
            secondReducedHomographyFindArea.append(targetReducedHomographyRow + matchWindowSizeFromCenter
                                                   + self.match_maximum_epipolar_row_parallax)
            if secondReducedHomographyFindArea[3] > (secondHomographyImageEnvelope[3] - 1):
                secondReducedHomographyFindArea[3] = secondHomographyImageEnvelope[3] - 1
            measuredTemplateMinColumn = firstReducedHomographyWindow[0] + firstHomographyImageEnvelope[0]
            measuredTemplateMinRow = firstReducedHomographyWindow[1] + firstHomographyImageEnvelope[1]
            measuredTemplateMaxColumn = firstReducedHomographyWindow[2] + firstHomographyImageEnvelope[0]
            measuredTemplateMaxRow = firstReducedHomographyWindow[3] + firstHomographyImageEnvelope[1]
            meauredTemplateColumns = measuredTemplateMaxColumn - measuredTemplateMinColumn + 1 # sourceImg.cols
            measuredTemplateRows = measuredTemplateMaxRow - measuredTemplateMinRow + 1 # sourceImg.cols
            if (meauredTemplateColumns < (matchWindowSizeFromCenter * 2 + 1)
                    or measuredTemplateRows < (matchWindowSizeFromCenter * 2 + 1)):
                continue
            templateMatrix = np.zeros((measuredTemplateRows, meauredTemplateColumns), dtype=np.uint8)
            row = measuredTemplateMinRow
            while row <= measuredTemplateMaxRow:
                column = measuredTemplateMinColumn
                while column <= measuredTemplateMaxColumn:
                    xt = column + .5
                    yt = row + .5
                    targetColumn = floor(xt) - measuredTemplateMinColumn
                    targetRow = floor(yt) - measuredTemplateMinRow
                    den = xt * mFImgInvH[2, 0] + yt * mFImgInvH[2, 1] + 1. * mFImgInvH[2, 2]
                    xs = xt * mFImgInvH[0, 0] + yt * mFImgInvH[0, 1] + 1. * mFImgInvH[0, 2]
                    ys = xt * mFImgInvH[1, 0] + yt * mFImgInvH[1, 1] + 1. * mFImgInvH[1, 2]
                    xs /= den
                    ys /= den
                    xs = xs - .5
                    ys = ys - .5
                    x0 = floor(xs)
                    x1 = x0 + 1
                    y0 = floor(ys)
                    y1 = y0 + 1
                    if x0 < 0 or x1 > (measured_img_columns - 1) or y0 < 0 or y1 > (measured_img_rows - 1):
                        templateMatrix[targetRow, targetColumn] = 0
                        column = column + 1
                        continue
                    dx = xs - x0
                    dy = ys - y0
                    dx_1 = 1 - dx
                    dy_1 = 1 - dy
                    value00 = measured_img[y0, x0]
                    value01 = measured_img[y0, x1]
                    value10 = measured_img[y1, x0]
                    value11 = measured_img[y1, x1]
                    v0 = dx_1 * value00 + dx * value01
                    v1 = dx_1 * value10 + dx * value11
                    v = dy_1 * v0 + dy * v1
                    dnValue = int(np.round(v))
                    if dnValue < 0:
                        dnValue = 0
                    if dnValue > 255:
                        dnValue = 255
                    templateMatrix[targetRow, targetColumn] = dnValue
                    column = column + 1
                row = row + 1
            yo = 1



        return str_error

    def matches_rfa(self,
                    measuredCamerasId,
                    undistortedMeasuredColumns,
                    undistortedMeasuredRows,
                    matchedCamerasId,
                    undistortedMatchedColumns,
                    undistortedMatchedRows,
                    matchedNames,
                    measuredCamerasPc,
                    matchedCamerasPc,
                    pointHeight,
                    focalInPixels,
                    matchedFinds,
                    qualitiesValues,
                    point_outside_dem,
                    dialog = None):
        str_error = ""
        if not self.project.exists_footprints():
            str_error = "EpipolarGeometryMatcherManager.matches_rfa"
            str_error += ('\nImages footprints are not loaded')
            return str_error
        if not self.project.exists_footprints_undistorted():
            str_error = "EpipolarGeometryMatcherManager.matches_rfa"
            str_error += ('\nImages undistorted footprints are not loaded')
            return str_error
        if (len(measuredCamerasId) != len(undistortedMeasuredColumns)
                or len(measuredCamerasId) != len(undistortedMeasuredRows)
                or len(measuredCamerasId) != len(matchedCamerasId)
                or len(measuredCamerasId) != len(undistortedMatchedColumns)
                or len(measuredCamerasId) != len(undistortedMatchedRows)
                or len(measuredCamerasId) != len(matchedNames)
                or len(measuredCamerasId) != len(measuredCamerasPc)
                or len(measuredCamerasId) != len(matchedCamerasPc)
                or len(measuredCamerasId) != len(matchedFinds)
                or len(measuredCamerasId) != len(qualitiesValues)):
            str_error = "EpipolarGeometryMatcherManager.matches_rfa"
            str_error += ('\nInput parameters conteiners must have same size')
            return str_error
        positionsToCompute = []
        for i in range(len(measuredCamerasId)):
            measured_camera_id = measuredCamerasId[i]
            matched_camera_id = matchedCamerasId[i]
            if not measured_camera_id in self.load_image_by_id:
                continue
            if not matched_camera_id in self.load_image_by_id:
                continue
            if not measured_camera_id in self.project.homographyMatrixByImagesId:
                continue
            if not matched_camera_id in self.project.homographyMatrixByImagesId[measured_camera_id]:
                continue
            if not matched_camera_id in self.project.homographyMatrixByImagesId:
                continue
            if not measured_camera_id in self.project.homographyMatrixByImagesId[matched_camera_id]:
                continue
            if not measured_camera_id in self.project.inverseHomographyMatrixByImagesId:
                continue
            if not matched_camera_id in self.project.inverseHomographyMatrixByImagesId[measured_camera_id]:
                continue
            if not matched_camera_id in self.project.inverseHomographyMatrixByImagesId:
                continue
            if not measured_camera_id in self.project.inverseHomographyMatrixByImagesId[matched_camera_id]:
                continue
            if not measured_camera_id in self.project.spEpipolarEnvelopeByImagesIds:
                continue
            if not matched_camera_id in self.project.spEpipolarEnvelopeByImagesIds[measured_camera_id]:
                continue
            if not matched_camera_id in self.project.spEpipolarEnvelopeByImagesIds:
                continue
            if not measured_camera_id in self.project.spEpipolarEnvelopeByImagesIds[matched_camera_id]:
                continue
            positionsToCompute.append(i)
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD
                in self.project.digitizing_parameters):
            str_error = "EpipolarGeometryMatcherManager.matches_rfa"
            str_error += ('\nParameter: {} not exists'.format(
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD))
            return str_error
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_MAXIMUM_EPIPOLAR_ROW_PARALLAX
                in self.project.digitizing_parameters):
            str_error = "EpipolarGeometryMatcherManager.matches_rfa"
            str_error += ('\nParameter: {} not exists'.format(
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_MAXIMUM_EPIPOLAR_ROW_PARALLAX))
            return str_error
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_WITHIN_DSM
                in self.project.digitizing_parameters):
            str_error = "EpipolarGeometryMatcherManager.matches_rfa"
            str_error += ('\nParameter: {} not exists'.format(
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_WITHIN_DSM))
            return str_error
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_OUTSIDE_DSM
                in self.project.digitizing_parameters):
            str_error = "EpipolarGeometryMatcherManager.matches_rfa"
            str_error += ('\nParameter: {} not exists'.format(
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_OUTSIDE_DSM))
            return str_error
        if not (defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_CORRELATION_THRESHOLD_PERCENTAGE
                in self.project.digitizing_parameters):
            str_error = "EpipolarGeometryMatcherManager.matches_rfa"
            str_error += ('\nParameter: {} not exists'.format(
                defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_CORRELATION_THRESHOLD_PERCENTAGE))
            return str_error
        self.measuredCamerasId = measuredCamerasId
        self.undistortedMeasuredColumns = undistortedMeasuredColumns
        self.undistortedMeasuredRows = undistortedMeasuredRows
        self.matchedCamerasId = matchedCamerasId
        self.undistortedMatchedColumns = undistortedMatchedColumns
        self.undistortedMatchedRows = undistortedMatchedRows
        self.matchedNames = matchedNames
        self.measuredCamerasPc = measuredCamerasPc
        self.matchedCamerasPc = matchedCamerasPc
        self.matchedFinds = matchedFinds
        self.qualitiesValues = qualitiesValues
        self.match_opencv_method = self.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_OPENCV_METHOD]
        self.match_maximum_epipolar_row_parallax = self.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_MAXIMUM_EPIPOLAR_ROW_PARALLAX]
        self.maximum_height_separation_within_dsm = self.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_WITHIN_DSM]
        self.maximum_height_separation_outside_dsm = self.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MAXIMUM_HEIGHT_SEPARATION_OUTSIDE_DSM]
        self.match_pencv_threshold_percentage = self.project.digitizing_parameters[
            defs_processes.PROCESS_FUNCTION_SET_DIGITALIZING_PARAMETERS_PARAMETER_MATCH_CORRELATION_THRESHOLD_PERCENTAGE]
        self.point_height_dem = pointHeight
        self.focal_in_pixels = focalInPixels
        self.point_outside_dem = point_outside_dem
        if dialog is not None:
            dialog.processInformationGroupBox.setEnabled(True)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            dialog.processLineEdit.setText('Computing matches ...')
            dialog.processLineEdit.adjustSize()
            dialog.processProgressBar.setMaximum(len(positionsToCompute))
            dialog.processLineEdit.adjustSize()
            QApplication.processEvents()
        cont = 0
        for i in range(len(positionsToCompute)):
            cont = cont + 1
            if dialog is not None:
                dialog.processProgressBar.setValue(cont)
                QApplication.processEvents()
            str_error = self.match_image_rfa(positionsToCompute[i])
            if str_error:
                str_error = "EpipolarGeometryMatcherManager.matches_rfa"
                str_error += ('\nError:\n{}'.format(str_error))
                return str_error
        if dialog is not None:
            dialog.processProgressBar.setValue(len(positionsToCompute))
            dialog.processInformationGroupBox.setEnabled(False)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            QApplication.processEvents()

        return str_error
