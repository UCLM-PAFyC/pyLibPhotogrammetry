# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math
import json

from PyQt5 import QtCore, QtWidgets
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import (QApplication, QMessageBox, QDialog, QTreeWidgetItem,
                             QFileDialog, QPushButton, QComboBox, QPlainTextEdit, QLineEdit,
                             QDialogButtonBox, QVBoxLayout, QTableWidget, QTableWidgetItem, QInputDialog)
from PyQt5.QtCore import QDir, QFileInfo, QFile, QSize, Qt, QDate

current_path = os.path.dirname(os.path.realpath(__file__))
# current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from pyLibPhotogrammetry.defs import defs_project
from pyLibPhotogrammetry.defs import defs_photogrammetry_projects as defs_phprj
from pyLibPhotogrammetry.Project import Project as PhProject

from pyLibCRSs.CompoundProjectedCRSDialog import CompoundProjectedCRSDialog
from pyLibCRSs import CRSsDefines as defs_crs
from pyLibQtTools import Tools
from pyLibQtTools.Tools import SimpleTextEditDialog
from pyLibQtTools.CalendarDialog import CalendarDialog

class PhotogrammetryProjectsDialog(QDialog):
    """Employee dialog."""

    def __init__(self,
                 project,
                 title,
                 parent=None):
        super().__init__(parent)
        loadUi(os.path.join(os.path.dirname(__file__), 'PhotogrammetryProjectsDialog.ui'), self)
        self.project = project
        self.last_path = None
        self.title = title
        self.is_saved = False
        self.setWindowTitle(title)
        self.formats = None
        self.photogrammetry_projects = None
        self.initialize(title)

    def add_project(self):
        format = self.formatComboBox.currentText()
        if format == defs_phprj.CONST_NO_COMBO_SELECT:
            str_msg = ("Select format before")
            Tools.error_msg(str_msg)
            return
        id = self.idLineEdit.text()
        if not id:
            str_msg = ("Select id before")
            Tools.error_msg(str_msg)
            return
        if id in self.photogrammetry_projects:
            str_msg = ("Exists another project with id: {}\nSelect a new id".format(id))
            Tools.error_msg(str_msg)
            return
        str_date = self.dateLineEdit.text()
        if not str_date:
            str_msg = ("Select date before")
            Tools.error_msg(str_msg)
            return
        file_path = ''
        if format == defs_phprj.FORMAT_PHOTOGRAMMETRY_TOOLS:
            file_path = self.fileLineEdit.text()
            if not file_path:
                str_msg = ("Select file before")
                Tools.error_msg(str_msg)
                return
            if not os.path.exists(file_path):
                str_msg = ("Not exists file:\n{}".format(file_path))
                Tools.error_msg(str_msg)
                return
        crs_id = self.crsLineEdit.text()
        if not crs_id:
            str_msg = ("Select CRS before")
            Tools.error_msg(str_msg)
            return
        photogrammetry_project = {}
        photogrammetry_project[defs_phprj.FIELD_ID] = id
        photogrammetry_project[defs_phprj.FIELD_DATE] = str_date
        photogrammetry_project[defs_phprj.FIELD_ENABLED] = 1
        photogrammetry_project[defs_phprj.FIELD_CRS] = crs_id
        photogrammetry_project[defs_phprj.FIELD_DESCRIPTION] = ""
        photogrammetry_project[defs_phprj.FIELD_FILE] = file_path
        photogrammetry_project[defs_phprj.FIELD_ORTHOMOSAIC] = ''
        photogrammetry_project[defs_phprj.FIELD_ORTHOMOSAIC_CRS] = crs_id
        photogrammetry_project[defs_phprj.FIELD_DSM] = ''
        photogrammetry_project[defs_phprj.FIELD_DSM_CRS] = crs_id
        photogrammetry_project[defs_phprj.FIELD_DTM] = ''
        photogrammetry_project[defs_phprj.FIELD_DTM_CRS] = crs_id
        photogrammetry_project[defs_phprj.FIELD_POINT_CLOUD] = ''
        photogrammetry_project[defs_phprj.FIELD_POINT_CLOUD_CRS] = crs_id
        self.photogrammetry_projects[id] = photogrammetry_project
        self.update_gui()
        return

    def disable(self):
        if len(self.photogrammetry_projects) == 0:
            return
        for i in range(self.tableWidget.rowCount()):
            id_item = self.tableWidget.item(i, 0)
            if id_item.isSelected():
                id = id_item.text()
                if self.photogrammetry_projects[id][defs_phprj.FIELD_ENABLED] == 1:
                    enabled_item = self.tableWidget.item(i, 2)
                    enabled_item.setText("False")
                    self.photogrammetry_projects[id][defs_phprj.FIELD_ENABLED] = 0
        return

    def enable(self):
        if len(self.photogrammetry_projects) == 0:
            return
        for i in range(self.tableWidget.rowCount()):
            id_item = self.tableWidget.item(i, 0)
            if id_item.isSelected():
                id = id_item.text()
                if self.photogrammetry_projects[id][defs_phprj.FIELD_ENABLED] == 0:
                    enabled_item = self.tableWidget.item(i, 2)
                    enabled_item.setText("True")
                    self.photogrammetry_projects[id][defs_phprj.FIELD_ENABLED] = 1
        return

    def format_changed(self):
        self.fileLineEdit.clear()
        self.dateLineEdit.clear()
        self.idPushButton.setEnabled(False)
        self.idLineEdit.clear()
        self.crsLineEdit.clear()
        self.selectFilePushButton.setEnabled(False)
        self.fileLineEdit.setEnabled(False)
        self.crsPushButton.setEnabled(False)
        self.crsLineEdit.setEnabled(False)
        self.addProjectPushButton.setEnabled(False)
        format = self.formatComboBox.currentText()
        if format == defs_phprj.CONST_NO_COMBO_SELECT:
            return
        if format == defs_phprj.FORMAT_PHOTOGRAMMETRY_TOOLS:
            # self.crsLineEdit.setText("From project file")
            self.selectFilePushButton.setEnabled(True)
            self.fileLineEdit.setEnabled(True)
            self.idPushButton.setEnabled(True)
            self.datePushButton.setEnabled(True)
            self.addProjectPushButton.setEnabled(True)
            # self.crsLineEdit.setText(defs_phprj.CRS_FROM_PROJECT)
        elif format == defs_phprj.FORMAT_GEOMATIC_PRODUCTS:
            self.idPushButton.setEnabled(True)
            self.datePushButton.setEnabled(True)
            self.addProjectPushButton.setEnabled(True)
            crs_id = self.project.crs_id
            self.crsPushButton.setEnabled(True)
            self.crsLineEdit.setEnabled(True)
            self.crsLineEdit.setText(crs_id)
        return

    def initialize(self, title):
        self.last_path = self.project.settings.value("last_path")
        current_dir = QDir.current()
        if not self.last_path:
            self.last_path = QDir.currentPath()
            self.project.settings.setValue("last_path", self.last_path)
            self.project.settings.sync()
        # deep copy using the dict() constructor
        self.photogrammetry_projects = dict(self.project.photogrammetry_projects)
        if len(defs_phprj.extension_by_format) > 1:
            self.formatComboBox.addItem(defs_phprj.CONST_NO_COMBO_SELECT)
        for format in defs_phprj.extension_by_format:
            self.formatComboBox.addItem(format)
        if len(defs_phprj.extension_by_format) == 1:
            self.formatComboBox.setEnabled(False)
        crs_id = self.project.crs_id
        self.crsLineEdit.setText(crs_id)
        self.selectFilePushButton.clicked.connect(self.select_file)
        self.idPushButton.clicked.connect(self.select_id)
        self.datePushButton.clicked.connect(self.select_date)
        self.crsPushButton.clicked.connect(self.select_crs)
        self.addProjectPushButton.clicked.connect(self.add_project)
        self.savePushButton.clicked.connect(self.save)
        self.tableWidget.itemDoubleClicked.connect(self.on_click)
        self.tableWidget.itemClicked.connect(self.on_click)
        self.removePushButton.clicked.connect(self.remove)
        self.enablePushButton.clicked.connect(self.enable)
        self.disablePushButton.clicked.connect(self.disable)
        headers = defs_phprj.headers
        headers_tooltips = defs_phprj.header_tooltips
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setStyleSheet("QHeaderView::section { color:black; background : lightGray; }")
        for i in range(len(headers)):
            header_item = QTableWidgetItem(headers[i])
            header_tooltip = headers_tooltips[i]
            header_item.setToolTip(header_tooltip)
            self.tableWidget.setHorizontalHeaderItem(i, header_item)
        self.tableWidget.setSizeAdjustPolicy(
            QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.formatComboBox.currentIndexChanged.connect(self.format_changed)
        self.idPushButton.setEnabled(False)
        self.datePushButton.setEnabled(False)
        self.selectFilePushButton.setEnabled(False)
        self.fileLineEdit.setEnabled(False)
        self.crsPushButton.setEnabled(False)
        self.crsLineEdit.setEnabled(False)
        self.addProjectPushButton.setEnabled(False)
        self.format_changed()
        self.update_gui()
        return

    @QtCore.pyqtSlot(QtWidgets.QTableWidgetItem)
    def on_click(self, item):
        row = item.row()
        column = item.column()
        id = self.tableWidget.item(row, 0).text()
        current_text = item.text()
        label = self.tableWidget.horizontalHeaderItem(column).text()
        tool_tip_text = self.tableWidget.horizontalHeaderItem(column).toolTip()
        title = label + ":"
        if label == defs_phprj.HEADER_DESCRIPTION_TAG:
            text = self.photogrammetry_projects[id][defs_phprj.FIELD_DESCRIPTION]
            readOnly = False
            dialog =  SimpleTextEditDialog(title, text, readOnly)
            ret = dialog.exec()
            text = dialog.get_text()
            if text != self.photogrammetry_projects[id][defs_phprj.FIELD_DESCRIPTION]:
                self.photogrammetry_projects[id][defs_phprj.FIELD_DESCRIPTION] = text
            return
        elif label == defs_phprj.HEADER_DATE_TAG:
            # return
            str_date = self.photogrammetry_projects[id][defs_phprj.FIELD_DATE]
            date = QDate.fromString(str_date, defs_phprj.DATE_FORMAT)
            title = "Select Project date"
            dialog = CalendarDialog(self, title, date)
            dialog_result = dialog.exec()
            date = dialog.calendar.selectedDate()
            # if dialog_result == QDialog.Accepted:
            #     return str_error, is_saved
            # return str_error, is_saved
            str_date = date.toString(defs_phprj.DATE_FORMAT)
            self.photogrammetry_projects[id][defs_phprj.FIELD_DATE] = str_date
            item.setText(str_date)
        elif (label == defs_phprj.HEADER_ORTHOMOSAIC_TAG
              or label == defs_phprj.HEADER_DSM_TAG
              or label == defs_phprj.HEADER_DTM_TAG
              or label == defs_phprj.HEADER_POINT_CLOUD_TAG):
            file_extensions = None
            tile = ''
            previous_file_path = ''
            name_filter = ''
            if label == defs_phprj.HEADER_ORTHOMOSAIC_TAG:
                file_extensions = defs_phprj.orthomosaic_file_extensions
                title = "Select Orthomosaic file"
                name_filter = "Orthomosaic file ("
                previous_file_path = self.photogrammetry_projects[id][defs_phprj.FIELD_ORTHOMOSAIC]
            elif label == defs_phprj.HEADER_DSM_TAG or label == defs_phprj.HEADER_DTM_TAG:
                file_extensions = defs_phprj.dem_file_extensions
                if label == defs_phprj.HEADER_DSM_TAG:
                    title = "Select DSM file"
                    name_filter = "DSM file ("
                    previous_file_path = self.photogrammetry_projects[id][defs_phprj.FIELD_DSM]
                else:
                    title = "Select DTM file"
                    name_filter = "DTM file ("
                    previous_file_path = self.photogrammetry_projects[id][defs_phprj.FIELD_DTM]
            else:
                file_extensions = defs_phprj.point_cloud_file_extensions
                title = "Select Point Cloud file"
                name_filter = "Point Cloud file ("
                previous_file_path = self.photogrammetry_projects[id][defs_phprj.FIELD_POINT_CLOUD]
            for i in range(len(file_extensions)):
                file_extension = file_extensions[i]
                if i > 0:
                    name_filter += ' '
                name_filter += '*.' + file_extension
            name_filter += ')'
            if previous_file_path:
                previous_file_path = os.path.normpath(previous_file_path)
            dlg = QFileDialog()
            dlg.setWindowTitle(title)
            dlg.setDirectory(self.last_path)
            dlg.setFileMode(QFileDialog.ExistingFile)
            dlg.setNameFilter(name_filter)
            file_path = ''
            if dlg.exec_():
                file_names = dlg.selectedFiles()
                file_path = file_names[0]
            else:
                return
            # fileName, aux = QFileDialog.getSaveFileName(self, title, self.path, "Project File (*.json)")
            if file_path:
                file_path = os.path.normpath(file_path)
                if previous_file_path and file_path == previous_file_path:
                    return
                if file_path != previous_file_path:
                    if label == defs_phprj.HEADER_ORTHOMOSAIC_TAG:
                        self.photogrammetry_projects[id][defs_phprj.FIELD_ORTHOMOSAIC] = file_path
                    elif label == defs_phprj.HEADER_DSM_TAG:
                        self.photogrammetry_projects[id][defs_phprj.FIELD_DSM] = file_path
                    elif label == defs_phprj.HEADER_DTM_TAG:
                        self.photogrammetry_projects[id][defs_phprj.FIELD_DTM] = file_path
                    elif label == defs_phprj.HEADER_POINT_CLOUD_TAG:
                        self.photogrammetry_projects[id][defs_phprj.FIELD_POINT_CLOUD] = file_path
                    item.setText(file_path)
        elif (label == defs_phprj.HEADER_ORTHOMOSAIC_CRS_TAG
              or label == defs_phprj.HEADER_DSM_CRS_TAG
              or label == defs_phprj.HEADER_DTM_CRS_TAG
              or label == defs_phprj.HEADER_POINT_CLOUD_CRS_TAG):
            tile = ''
            previous_crs_id = ''
            if label == defs_phprj.HEADER_ORTHOMOSAIC_CRS_TAG:
                file_extensions = defs_phprj.orthomosaic_file_extensions
                title = "Select Orthomosaic CRS"
                previous_crs_id = self.photogrammetry_projects[id][defs_phprj.FIELD_ORTHOMOSAIC_CRS]
            elif label == defs_phprj.HEADER_DSM_TAG:
                    title = "Select DSM CRS"
                    previous_crs_id = self.photogrammetry_projects[id][defs_phprj.FIELD_DSM_CRS]
            elif label == defs_phprj.HEADER_DTM_CRS_TAG:
                    title = "Select DTM CRS"
                    previous_crs_id = self.photogrammetry_projects[id][defs_phprj.FIELD_DTM_CRS]
            else:
                title = "Select Point Cloud CRS"
                previous_crs_id = self.photogrammetry_projects[id][defs_phprj.FIELD_POINT_CLOUD_CRS]
            dialog = CompoundProjectedCRSDialog(self.project.crs_tools, previous_crs_id)
            dialog_result = dialog.exec()
            if dialog.is_accepted:
                crs_id = dialog.crs_id
                if crs_id != previous_crs_id:
                    if label == defs_phprj.HEADER_ORTHOMOSAIC_CRS_TAG:
                        self.photogrammetry_projects[id][defs_phprj.FIELD_ORTHOMOSAIC_CRS] = crs_id
                    elif label == defs_phprj.HEADER_DSM_CRS_TAG:
                        self.photogrammetry_projects[id][defs_phprj.FIELD_DSM_CRS] = crs_id
                    elif label == defs_phprj.HEADER_DTM_CRS_TAG:
                        self.photogrammetry_projects[id][defs_phprj.FIELD_DTM_CRS] = crs_id
                    elif label == defs_phprj.HEADER_POINT_CRS_CLOUD_TAG:
                        self.photogrammetry_projects[id][defs_phprj.FIELD_POINT_CLOUD_CRS] = crs_id
                    item.setText(crs_id)
        return

    def remove(self):
        if len(self.photogrammetry_projects) == 0:
            return
        ids_to_remove = []
        for i in range(self.tableWidget.rowCount()):
            id_item = self.tableWidget.item(i, 0)
            if id_item.isSelected():
                ids_to_remove.append(id_item.text())
        if len(ids_to_remove) < 1:
            str_error = "Select rows to remove"
            Tools.error_msg(str_error)
            return
        for i in range(len(ids_to_remove)):
            for j in range(self.tableWidget.rowCount()):
                id_item = self.tableWidget.item(j, 0)
                if id_item.text() == ids_to_remove[i]:
                    self.tableWidget.removeRow(id_item.row())
                    break
        for id in ids_to_remove:
            self.photogrammetry_projects.pop(id)
        return

    def save(self):
        self.project.photogrammetry_projects = dict(self.photogrammetry_projects)
        str_aux_error = self.project.save_to_json()
        if str_aux_error:
            str_error = ('Error saving project:\n{}'.
                         format(str_aux_error))
            Tools.error_msg(str_error)
        else:
            str_msg = "Process completed"
            Tools.info_msg(str_msg)
        return

    def select_crs(self):
        crs_id = self.crsLineEdit.text()
        dialog = CompoundProjectedCRSDialog(self.project.crs_tools, crs_id)
        dialog_result = dialog.exec()
        if dialog.is_accepted:
            crs_id = dialog.crs_id
            self.crsLineEdit.setText(crs_id)
        return

    def select_date(self):
        date = None
        str_date = self.dateLineEdit.text()
        if str_date:
            date = QDate.fromString(str_date, defs_phprj.DATE_FORMAT)
        title = "Select Project date"
        dialog = CalendarDialog(self, title, date)
        dialog_result = dialog.exec()
        date = dialog.calendar.selectedDate()
        # if dialog_result == QDialog.Accepted:
        #     return str_error, is_saved
        # return str_error, is_saved
        str_date = date.toString(defs_phprj.DATE_FORMAT)
        self.dateLineEdit.setText(str_date)
        return

    def select_file(self):
        selected_format = self.formatComboBox.currentText()
        if selected_format == defs_phprj.CONST_NO_COMBO_SELECT:
            str_msg = "Select format before"
            Tools.info_msg(str_msg)
            return
        if selected_format != defs_phprj.FORMAT_PHOTOGRAMMETRY_TOOLS:
            str_msg = "Option not implemented"
            Tools.info_msg(str_msg)
            return
        title = "Select Photogrammetry Project File"
        previous_file_name = self.fileLineEdit.text()
        previous_file_name = os.path.normpath(previous_file_name)
        dlg = QFileDialog()
        dlg.setDirectory(self.last_path)
        dlg.setFileMode(QFileDialog.AnyFile)
        str_content = ('Photogrammetry Project File (*.{})'.format(defs_phprj.extension_by_format[selected_format]))
        dlg.setNameFilter(str_content)
        if dlg.exec_():
            file_names = dlg.selectedFiles()
            file_name = file_names[0]
        else:
            return
        # fileName, aux = QFileDialog.getSaveFileName(self, title, self.path, "Project File (*.json)")
        if file_name:
            file_name = os.path.normpath(file_name)
            if file_name != previous_file_name:
                ph_project = PhProject(self.project.qgis_iface,
                                      self.project.settings)
                str_error = ph_project.load_project(file_name)
                if str_error:
                    str_error = ('Opening Photogrammetry Project:\n{}\nerror:\n{}'.format(file_name, str_error))
                    Tools.error_msg(str_error)
                    return
                # str_error = self.project.load_processes()
                # if str_error:
                #     Tools.error_msg(str_error)
                #     return
                ph_project_crs_id = ph_project.crs_id
                self.crsLineEdit.setText(ph_project_crs_id)
                self.fileLineEdit.setText(file_name)
                self.last_path = QFileInfo(file_name).absolutePath()
                self.project.settings.setValue("last_path", self.last_path)
                self.project.settings.sync()
        return

    def select_id(self):
        current_text = self.idLineEdit.text()
        text, okPressed = QInputDialog.getText(self, "Id", "Enter value (case sensitive):",
                                               QLineEdit.Normal, current_text)
        if okPressed and text != '' and text != current_text:
            # check exists previous id
            if text in self.project.geometric_design_projects:
                str_msg = ("Exists another geometric design project with id: {}\nSelect another id".format(text))
                Tools.info_msg(str_msg)
                return
            self.idLineEdit.setText(text)
        return

    def update_gui(self):
        self.tableWidget.setRowCount(0)
        for id in self.photogrammetry_projects:
            rowPosition = self.tableWidget.rowCount()
            self.tableWidget.insertRow(rowPosition)
            # id
            id_item = QTableWidgetItem(id)
            id_item.setTextAlignment(Qt.AlignCenter)
            column_pos = 0
            self.tableWidget.setItem(rowPosition, column_pos, id_item)
            # date
            str_date = self.photogrammetry_projects[id][defs_phprj.FIELD_DATE]
            date_item = QTableWidgetItem(str_date)
            date_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, date_item)
            # enabled
            str_enabled = 'True'
            if self.photogrammetry_projects[id][defs_phprj.FIELD_ENABLED] == 0:
                str_enabled = 'False'
            enabled_item = QTableWidgetItem(str_enabled)
            enabled_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, enabled_item)
            # crs
            crs_id = self.photogrammetry_projects[id][defs_phprj.FIELD_CRS]
            crs_id_item = QTableWidgetItem(crs_id)
            crs_id_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, crs_id_item)
            # description
            # description = self.geometric_design_projects[id][defs_gdp.FIELD_DESCRIPTION]
            description = defs_phprj.RESUME_CONTENT
            description_item = QTableWidgetItem(description)
            description_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, description_item)
            # file
            file_path = self.photogrammetry_projects[id][defs_phprj.FIELD_FILE]
            file_path_item = QTableWidgetItem(file_path)
            file_path_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, file_path_item)
            # orthomosaic
            orthomosaic = self.photogrammetry_projects[id][defs_phprj.FIELD_ORTHOMOSAIC]
            orthomosaic_item = QTableWidgetItem(orthomosaic)
            orthomosaic_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, orthomosaic_item)
            # orthomosaic crs
            orthomosaic_crs = self.photogrammetry_projects[id][defs_phprj.FIELD_ORTHOMOSAIC_CRS]
            orthomosaic_crs_item = QTableWidgetItem(orthomosaic_crs)
            orthomosaic_crs_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, orthomosaic_crs_item)
            # dsm
            dsm = self.photogrammetry_projects[id][defs_phprj.FIELD_DSM]
            dsm_item = QTableWidgetItem(dsm)
            dsm_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, dsm_item)
            # dsm crs
            dsm_crs = self.photogrammetry_projects[id][defs_phprj.FIELD_DSM_CRS]
            dsm_crs_item = QTableWidgetItem(dsm_crs)
            dsm_crs_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, dsm_crs_item)
            # dtm
            dtm = self.photogrammetry_projects[id][defs_phprj.FIELD_DTM]
            dtm_item = QTableWidgetItem(dtm)
            dtm_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, dtm_item)
            # dtm crs
            dtm_crs = self.photogrammetry_projects[id][defs_phprj.FIELD_DTM_CRS]
            dtm_crs_item = QTableWidgetItem(dtm_crs)
            dtm_crs_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, dtm_crs_item)
            # point cloud
            point_cloud = self.photogrammetry_projects[id][defs_phprj.FIELD_POINT_CLOUD]
            point_cloud_item = QTableWidgetItem(point_cloud)
            point_cloud_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, point_cloud_item)
            # dtm crs
            point_cloud_crs = self.photogrammetry_projects[id][defs_phprj.FIELD_POINT_CLOUD_CRS]
            point_cloud_crs_item = QTableWidgetItem(point_cloud_crs)
            point_cloud_crs_item.setTextAlignment(Qt.AlignCenter)
            column_pos = column_pos + 1
            self.tableWidget.setItem(rowPosition, column_pos, point_cloud_crs_item)
        # self.tableWidget.resizeColumnsToContents()
        self.tableWidget.resizeColumnToContents(0)
        self.tableWidget.resizeColumnToContents(1)
        self.tableWidget.resizeColumnToContents(2)
        self.tableWidget.resizeColumnToContents(3)
        self.tableWidget.resizeColumnToContents(4)
        # self.tableWidget.resizeColumnToContents(5)
        # self.tableWidget.resizeColumnToContents(6)
        self.tableWidget.resizeColumnToContents(7)
        # self.tableWidget.resizeColumnToContents(8)
        self.tableWidget.resizeColumnToContents(9)
        # self.tableWidget.resizeColumnToContents(10)
        self.tableWidget.resizeColumnToContents(11)
        # self.tableWidget.resizeColumnToContents(12)
        self.tableWidget.resizeColumnToContents(13)
        return

