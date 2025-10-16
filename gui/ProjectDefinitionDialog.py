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

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibQtTools import Tools
from pyLibQtTools.Tools import SimpleTextEditDialog

class ProjectDefinitionDialog(QDialog):
    """Employee dialog."""

    def __init__(self,
                 project,
                 title,
                 is_process_creation,
                 parent=None):
        super().__init__(parent)
        loadUi(os.path.join(os.path.dirname(__file__), 'ProjectDefinitionDialog.ui'), self)
        self.project = project
        self.last_path = None
        self.title = title
        self.is_process_creation = is_process_creation
        self.crs_projected_ids = []
        self.crs_vertical_ids = []
        self.active_crs_line_edit_widget = None
        self.is_saved = False
        self.initialize(title)

    def initialize(self, title):
        name = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_NAME]
        tag = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_TAG]
        author = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR]
        description = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_DESCRIPTION]
        output_path = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH]
        crs_projected_id = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
        crs_vertical_id = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS]
        str_start_date = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_START_DATE]
        str_finish_date = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE]
        current_date = QDate.currentDate()
        if not str_start_date:
            start_date = current_date
        else:
            start_date = QDate.fromString(str_start_date, defs_project.QDATE_TO_STRING_FORMAT)
        if not str_finish_date:
            finish_date = QDate.fromJulianDay(current_date.toJulianDay() + 365)
        else:
            finish_date = QDate.fromString(str_finish_date, defs_project.QDATE_TO_STRING_FORMAT)
        self.nameLineEdit.setText(name)
        self.tagLineEdit.setText(tag)
        self.authorLineEdit.setText(author)
        self.descriptionLineEdit.setText(description)
        if output_path:
            if os.path.exists(output_path):
                self.outputPathLineEdit.setText(output_path)
        self.startDateEdit.setDate(start_date)
        self.finishDateEdit.setDate(finish_date)
        self.crsProjectedLineEdit.setText(crs_projected_id)
        self.crsVerticalLineEdit.setText(crs_vertical_id)

        self.last_path = self.project.settings.value("last_path")
        current_dir = QDir.current()
        if not self.last_path:
            self.last_path = QDir.currentPath()
            self.project.settings.setValue("last_path", self.last_path)
            self.project.settings.sync()
        self.setWindowTitle(title)
        self.crs_projected_ids = self.project.crs_tools.get_crs_projected_ids()
        self.crs_vertical_ids = self.project.crs_tools.get_crs_vertical_ids()
        self.crsSearchTextLineEdit.cursorPositionChanged.connect(self.crsSearchTextChanged)
        self.savePushButton.clicked.connect(self.save)
        self.namePushButton.clicked.connect(self.select_name)
        self.tagPushButton.clicked.connect(self.select_tag)
        self.authorPushButton.clicked.connect(self.select_author)
        self.descriptionPushButton.clicked.connect(self.select_description)
        self.outputPathPushButton.clicked.connect(self.select_output_path)

        self.crsTreeWidget.clear()
        self.crsTextEdit.clear()
        self.crsTreeWidget.setColumnCount(1)
        # self.crsTreeWidget.header().hide()
        item_header = self.crsTreeWidget.headerItem()
        item_header.setText(0, 'Select CRS by type')
        self.crs_projected_item = QTreeWidgetItem(self.crsTreeWidget)
        self.crs_projected_item.setText(0, defs_crs.CRS_PROJECTED_LABEL)
        self.crs_projected_item.setFlags(self.crs_projected_item.flags() & ~QtCore.Qt.ItemIsEditable
                                         & ~QtCore.Qt.ItemIsSelectable)
        for crs_id in self.crs_projected_ids:
            str_error, crs_summary = self.project.crs_tools.get_crs_summary(crs_id)
            if str_error:
                str_error = ('Getting summary for CRS: {}, error:\n{}'.format(crs_id, str_error))
                Tools.error_msg(str_error)
                return
            item = QTreeWidgetItem(self.crs_projected_item)
            item.setText(0, crs_summary)
        self.crs_vertical_item = QTreeWidgetItem(self.crsTreeWidget)
        self.crs_vertical_item.setText(0, defs_crs.CRS_VERTICAL_LABEL)
        self.crs_vertical_item.setFlags(self.crs_vertical_item.flags() & ~QtCore.Qt.ItemIsEditable
                                        & ~QtCore.Qt.ItemIsSelectable)
        item = QTreeWidgetItem(self.crs_vertical_item)
        item.setText(0, defs_crs.VERTICAL_ELLIPSOID_TAG)
        for crs_id in self.crs_vertical_ids:
            str_error, crs_summary = self.project.crs_tools.get_crs_summary(crs_id)
            if str_error:
                str_error = ('Getting summary for CRS: {}, error:\n{}'.format(crs_id, str_error))
                Tools.error_msg(str_error)
                return
            item = QTreeWidgetItem(self.crs_vertical_item)
            item.setText(0, crs_summary)
        self.crsTreeWidget.itemSelectionChanged.connect(self.show_crs_details)
        self.crsTreeWidget.expandAll()
        self.update_gui()
        if not self.is_process_creation:
            self.crsGroupBox.setEnabled(False)

    def show_crs_details(self):
        selectedItems = self.crsTreeWidget.selectedItems()
        self.crsTextEdit.clear()
        if len(selectedItems) > 0:
            selected_item = selectedItems[0]
            selected_text = selected_item.text(0)
            if selected_text == defs_crs.VERTICAL_ELLIPSOID_TAG:
                self.crsVerticalLineEdit.setText(selected_text)
                return
            crs_id = selected_text[0: selected_text.index(',')]
            str_error, crs_info_as_dict = self.project.crs_tools.get_crs_info_as_text(crs_id)
            if str_error:
                str_error = ('Getting info for CRS: {}, error:\n{}'.format(crs_id, str_error))
                Tools.error_msg(str_error)
                return
            self.crsTextEdit.setText(crs_info_as_dict)
            if crs_id in self.crs_projected_ids:
                self.crsProjectedLineEdit.setText(crs_id)
            elif crs_id in self.crs_vertical_ids:
                self.crsVerticalLineEdit.setText(crs_id)
        return

    def crsSearchTextChanged(self):
        text = self.crsSearchTextLineEdit.text()
        self.update_crs_tree(text)
        return

    def save(self):
        name = self.nameLineEdit.text()
        tag = self.tagLineEdit.text()
        author = self.authorLineEdit.text()
        description = self.descriptionLineEdit.text()
        output_path = self.outputPathLineEdit.text()
        star_date_as_str = self.startDateEdit.date().toString(defs_project.QDATE_TO_STRING_FORMAT)
        finish_date_as_str = self.finishDateEdit.date().toString(defs_project.QDATE_TO_STRING_FORMAT)
        crs_projected_id = self.crsProjectedLineEdit.text()
        if not crs_projected_id:
            str_error = ('Select Projected CRS')
            Tools.error_msg(str_error)
            return
        crs_vertical_id = self.crsVerticalLineEdit.text()
        if not crs_vertical_id:
            str_error = ('Select Vertical CRS')
            Tools.error_msg(str_error)
            return
        self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_NAME] = name
        self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_TAG] = tag
        self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_AUTHOR] = author
        self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS] = crs_projected_id
        self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS] = crs_vertical_id
        self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_OUTPUT_PATH] = output_path
        self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_DESCRIPTION] = description
        self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_START_DATE] = star_date_as_str
        self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_FINISH_DATE] = finish_date_as_str
        epsg_crs_prefix = defs_crs.EPSG_TAG + ':'
        crs_2d_id = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_PROJECTED_CRS]
        crs_2d_epsg_code = int(crs_2d_id.replace(epsg_crs_prefix, ''))
        self.project.crs_id = epsg_crs_prefix + str(crs_2d_epsg_code)
        crs_vertical_id = self.project.project_definition[defs_project.PROJECT_DEFINITIONS_TAG_VERTICAL_CRS]
        if crs_vertical_id != defs_crs.VERTICAL_ELLIPSOID_TAG:
            crs_vertical_epsg_code = int(crs_vertical_id.replace(epsg_crs_prefix, ''))
            self.project.crs_id += ('+' + str(crs_vertical_epsg_code))
        str_aux_error = self.project.save_management(True)
        if str_aux_error:
            str_error = ('Error updating project definition:\n{}'.
                         format(str_aux_error))
            Tools.error_msg(str_error)
            return
        else:
            str_msg = "Process completed"
            Tools.info_msg(str_msg)
        self.is_saved = True
        return

    def select_author(self):
        current_text = self.authorLineEdit.text()
        text, okPressed = QInputDialog.getText(self, "Author", "Enter author:",
                                               QLineEdit.Normal, current_text)
        if okPressed and text != '':
            self.authorLineEdit.setText(text)

    def select_description(self):
        current_text = self.descriptionLineEdit.text()
        # text, okPressed = QInputDialog.getText(self, "Description", "Enter description:",
        #                                        QLineEdit.Normal, current_text)
        # if okPressed and text != '':
        #     self.descriptionLineEdit.setText(text)
        title = "Enter description"
        dialog = SimpleTextEditDialog(title, current_text, False)
        ret = dialog.exec()
        # if ret == QDialog.Accepted:
        #     text = dialog.get_text()
        #     self.descriptionLineEdit.setText(text)
        text = dialog.get_text()
        if text != current_text:
            self.descriptionLineEdit.setText(text)

    def select_name(self):
        current_text = self.nameLineEdit.text()
        text, okPressed = QInputDialog.getText(self, "Name", "Enter name:",
                                               QLineEdit.Normal, current_text)
        if okPressed and text != '':
            self.nameLineEdit.setText(text)

    def select_output_path(self):
        dialog = QtWidgets.QFileDialog()
        # last_dir = QDir(self.project.last_path)
        last_path = self.project.settings.value("last_path")
        if not last_path:
            last_path = QDir.currentPath()
            self.settings.setValue("last_path", last_path)
            self.settings.sync()
        dialog.setDirectory(last_path)
        path = dialog.getExistingDirectory(self, "Select output path")
        if path:
            self.outputPathLineEdit.setText(path)
            self.project.last_path = path
            self.project.settings.setValue("last_path", self.project.last_path)
            self.project.settings.sync()

    def select_tag(self):
        current_text = self.tagLineEdit.text()
        text, okPressed = QInputDialog.getText(self, "Tag", "Enter tag:",
                                               QLineEdit.Normal, current_text)
        if okPressed and text != '':
            self.tagLineEdit.setText(text)

    def update_crs_tree(self, text):
        if not text:
            return
        for i in range(self.crsTreeWidget.topLevelItemCount()):
            category = self.crsTreeWidget.topLevelItem(i)
            for j in range(category.childCount()):
                item = category.child(j)
                item_text = item.text(0)
                if item_text == defs_crs.VERTICAL_ELLIPSOID_TAG:
                    item.setHidden(False)
                    continue
                if not text.lower() in item_text.lower():
                    item.setHidden(True)
                else:
                    item.setHidden(False)

    def update_gui(self):
        return
