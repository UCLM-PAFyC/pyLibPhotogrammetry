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
        self.initialize(title)

    def initialize(self, title):

        return
