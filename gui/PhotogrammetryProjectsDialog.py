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

from pyLibCRSs import CRSsDefines as defs_crs
from pyLibQtTools import Tools
from pyLibQtTools.Tools import SimpleTextEditDialog

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
        return

    def disable(self):
        return

    def enable(self):
        return

    def format_changed(self):
        self.fileLineEdit.clear()
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
        elif format == defs_phprj.FORMAT_PHOTOGRAMMETRY_TOOLS:
            # self.crsLineEdit.setText("From project file")
            self.selectFilePushButton.setEnabled(True)
            self.fileLineEdit.setEnabled(True)
            self.idPushButton.setEnabled(True)
            self.addProjectPushButton.setEnabled(True)
        elif format == defs_phprj.FORMAT_GEOMATIC_PRODUCTS:
            self.idPushButton.setEnabled(True)
            self.addProjectPushButton.setEnabled(True)
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
        self.selectFilePushButton.setEnabled(False)
        self.fileLineEdit.setEnabled(False)
        self.crsPushButton.setEnabled(False)
        self.crsLineEdit.setEnabled(False)
        self.addProjectPushButton.setEnabled(False)
        self.format_changed()
        self.update_gui()
        return

    def on_click(self):
        return

    def remove(self):
        return

    def save(self):
        return

    def select_crs(self):
        return

    def select_file(self):
        return

    def select_id(self):
        return

    def update_gui(self):
        return

