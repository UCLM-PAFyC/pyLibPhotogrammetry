# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import math
import pathlib

from PyQt5 import QtCore, QtWidgets
from PyQt5.uic import loadUi
from PyQt5.QtWidgets import (QApplication, QMessageBox, QDialog, QInputDialog,
                             QFileDialog, QPushButton, QComboBox, QPlainTextEdit, QLineEdit,
                             QDialogButtonBox, QVBoxLayout, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import QDir, QFileInfo, QFile, QSize, Qt

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from pyLibPhotogrammetry.defs import defs_project, defs_processes
from pyLibPhotogrammetry.lib.ProcessesManager import ProcessesManager

from pyLibParameters import defs_pars
from pyLibParameters.ParametersManager import ParametersManager
from pyLibParameters.ui_qt.ParametersManagerDialog import ParametersManagerDialog
from pyLibQtTools import Tools
from pyLibQtTools.Tools import SimpleTextEditDialog

class ProcessesManagerDialog(QDialog):
    """Employee dialog."""

    def __init__(self,
                 processes_manager,
                 title,
                 qgis_iface,
                 settings,
                 parent=None):
        super().__init__(parent)
        loadUi(os.path.join(os.path.dirname(__file__), 'ProcessesManagerDialog.ui'), self)
        self.processes_manager = processes_manager
        self.title = title
        self.formats = None
        self.qgis_iface = qgis_iface
        self.settings = settings
        self.initialize(title)

    def initialize(self,
                   title):
        self.setWindowTitle(title)
        headers = defs_processes.processes_manager_dialog_header
        headers_tooltips = defs_processes.processes_manager_dialog_tooltip_by_header_tag
        field_by_header = defs_processes.processes_manager_dialog_field_by_header_tag
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setStyleSheet("QHeaderView::section { color:black; background : lightGray; }")
        for i in range(len(headers)):
            header_item = QTableWidgetItem(headers[i])
            header_tooltip = headers_tooltips[headers[i]]
            header_item.setToolTip(header_tooltip)
            self.tableWidget.setHorizontalHeaderItem(i, header_item)
        self.tableWidget.itemDoubleClicked.connect(self.on_click)
        self.tableWidget.itemClicked.connect(self.on_click)
        self.savePushButton.clicked.connect(self.save)
        self.update_gui()
        return

    @QtCore.pyqtSlot(QtWidgets.QTableWidgetItem)
    def on_click(self, item):
        row = item.row()
        column = item.column()
        current_text = item.text()
        process_name =  self.tableWidget.item(row, 0).text()
        process_provider = self.tableWidget.item(row, 1).text()
        process = self.processes_manager.processes_by_provider[process_provider][process_name]
        label = self.tableWidget.horizontalHeaderItem(column).text()
        tool_tip_text = self.tableWidget.horizontalHeaderItem(column).toolTip()
        if label == defs_processes.PROCESS_FIELD_PARAMETERS_TAG:
            parametes_manager = process[defs_processes.PROCESS_FIELD_PARAMETERS]
            process_file_path = process[defs_processes.PROCESS_FILE]
            title = defs_pars.PARAMETERS_MANAGER_DIALOG_TITLE
            dialog = ParametersManagerDialog(parametes_manager, title, self.qgis_iface, self.settings, self)
            dialog_result = dialog.exec()
            # if dialog_result != QDialog.Accepted:
            #     return str_error
            # Tools.error_msg(str_error)
        elif label == defs_processes.PROCESS_FIELD_FILE_TAG:
            title = "Process: " + process_name
            process_file_path = process[defs_processes.PROCESS_FILE]
            previous_file = self.tableWidget.item(row, column).text()
            previous_file_path = QFileInfo(previous_file).absolutePath()
            title = defs_pars.PARAMETERS_MANAGER_DIALOG_TITLE
            dlg = QFileDialog()
            dlg.setDirectory(previous_file_path)
            dlg.setFileMode(QFileDialog.AnyFile)
            dlg.setNameFilter("Process File (*.json)")
            if dlg.exec_():
                file_names = dlg.selectedFiles()
                file_name = file_names[0]
            else:
                return
            if file_name:
                if pathlib.Path(file_name).suffix != defs_processes.PROCESSES_FILES_EXTENSION:
                    file_name = file_name + defs_processes.PROCESSES_FILES_EXTENSION
                if os.path.exists(file_name):
                    previous_process = self.processes_manager.processes_by_provider[process_provider][process_name]
                    self.processes_manager.processes_by_provider[process_provider].pop(process_name)
                    str_error, process = self.processes_manager.load_process_file(file_name,
                                                                                  process_provider)
                    if str_error:
                        self.processes_manager.processes_by_provider[process_provider][process_name] = previous_process
                        Tools.error_msg(str_error)
                        return
                    self.processes_manager.processes_by_provider[process_provider][process_name] = process
                last_path = QFileInfo(file_name).absolutePath()
                self.settings.setValue("last_path", last_path)
                self.settings.sync()
                self.tableWidget.item(row, column).setText(file_name)
        elif label == defs_processes.PROCESS_FIELD_NAME_TAG:
            str_msg = ('Process name is not editable')
            Tools.info_msg(str_msg)
            return
        elif label == defs_processes.PROCESS_FIELD_PROVIDER_TAG:
            str_msg = ('Process provider is not editable')
            Tools.info_msg(str_msg)
            return
        elif label == defs_processes.PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY_TAG:
            str_msg = ('Process contributors methodology is not editable')
            Tools.info_msg(str_msg)
            return
        elif label == defs_processes.PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE_TAG:
            str_msg = ('Process contributors software is not editable')
            Tools.info_msg(str_msg)
            return
        elif label == defs_processes.PROCESS_FIELD_SRC_TAG:
            # str_msg = ('Process source file is not editable')
            # Tools.info_msg(str_msg)
            # return
            title = "Process: " + process_name
            previous_src_file = process[defs_processes.PROCESS_FIELD_SRC]
            previous_src_file_path = ''
            if os.path.exists(previous_src_file):
                previous_src_file_path = QFileInfo(previous_src_file).absolutePath()
            else:
                process_file_path = process[defs_processes.PROCESS_FILE]
                previous_src_file_path = QFileInfo(process_file_path).absolutePath()
            title = defs_pars.PARAMETERS_MANAGER_DIALOG_TITLE
            dlg = QFileDialog()
            dlg.setDirectory(previous_src_file_path)
            dlg.setFileMode(QFileDialog.ExistingFile)
            dlg.setNameFilter("Source process python file (*.py)")
            if dlg.exec_():
                file_names = dlg.selectedFiles()
                file_name = file_names[0]
            else:
                return
            if file_name:
                last_path = QFileInfo(file_name).absolutePath()
                self.settings.setValue("last_path", last_path)
                self.settings.sync()
                self.tableWidget.item(row, column).setText(file_name)
        elif label == defs_processes.PROCESS_FIELD_DOC_TAG:
            # str_msg = ('Process documentation file is not editable')
            # Tools.info_msg(str_msg)
            # return
            title = "Process: " + process_name
            previous_doc_file = process[defs_processes.PROCESS_FIELD_DOC]
            previous_doc_file_path = ''
            if os.path.exists(previous_doc_file):
                previous_doc_file_path = QFileInfo(previous_doc_file).absolutePath()
            else:
                process_file_path = process[defs_processes.PROCESS_FILE]
                previous_doc_file_path = QFileInfo(process_file_path).absolutePath()
            title = defs_pars.PARAMETERS_MANAGER_DIALOG_TITLE
            dlg = QFileDialog()
            dlg.setDirectory(previous_doc_file_path)
            dlg.setFileMode(QFileDialog.ExistingFile)
            dlg.setNameFilter("Documentation process PDF file (*.pdf)")
            if dlg.exec_():
                file_names = dlg.selectedFiles()
                file_name = file_names[0]
            else:
                return
            if file_name:
                last_path = QFileInfo(file_name).absolutePath()
                self.settings.setValue("last_path", last_path)
                self.settings.sync()
                self.tableWidget.item(row, column).setText(file_name)
        else:
            title = "Process: " + process_name
            current_text = label.replace('\n', ' ') + ':\n\n' + current_text
            dialog = SimpleTextEditDialog(title, current_text, False)
            ret = dialog.exec()
            text = dialog.get_text()
            self.tableWidget.item(row, column).setText(text)
            # if ret == QDialog.Accepted:
            #     text = dialog.get_text()
            #     self.tableWidget.item(row, column).setText(text)
        return

    def save(self):
        for i in range(self.tableWidget.rowCount()):
            process_name = self.tableWidget.item(i, 0).text()
            process_provider = self.tableWidget.item(i, 1).text()
            process_file = self.tableWidget.item(i, 3).text()
            process_description = self.tableWidget.item(i, 4).text()
            process_doc = self.tableWidget.item(i, 5).text()
            process_source = self.tableWidget.item(i, 6).text()
            process_contributions_methodology = self.tableWidget.item(i, 7).text()
            process_contributions_software = self.tableWidget.item(i, 8).text()
            process = self.processes_manager.processes_by_provider[process_provider][process_name]
            # parametes_manager = process[defs_processes.PROCESS_FIELD_PARAMETERS]
            process[defs_processes.PROCESS_FIELD_FILE] = process_file
            process[defs_processes.PROCESS_FIELD_SRC] = process_source
            process[defs_processes.PROCESS_FIELD_DOC] = process_doc
            process[defs_processes.PROCESS_FIELD_DESCRIPTION] = process_description
            # process[defs_processes.PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE] = process_contributions_software
            # process[defs_processes.PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY] = process_contributions_methodology
            str_error = self.processes_manager.save(process_provider, process_name)
            if str_error:
                str_error = ('Saving process provider: {}, name: {}\nError:\n{}'.
                             format(process_provider, process_name, str_error))
                Tools.error_msg(str_error)
                # return
        str_msg = ('Saving of processes has finished')
        Tools.info_msg(str_msg)
        return

    def update_gui(self):
        self.tableWidget.setRowCount(0)
        for process_provider in self.processes_manager.processes_by_provider:
            for process_name in self.processes_manager.processes_by_provider[process_provider]:
                process = self.processes_manager.processes_by_provider[process_provider][process_name]
                # process_name = process[defs_processes.PROCESS_FIELD_NAME]
                process_description = process[defs_processes.PROCESS_FIELD_DESCRIPTION]
                process_contributions = process[defs_processes.PROCESS_FIELD_CONTRIBUTIONS]
                process_contributions_methodology = ''
                for i in range(len(process_contributions[defs_processes.PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY])):
                    if i > 0:
                        process_contributions_methodology += '\n'
                    process_contributions_methodology += (
                        process_contributions)[defs_processes.PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY][i]
                process_contributions_software = ''
                for i in range(len(process_contributions[defs_processes.PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE])):
                    if i > 0:
                        process_contributions_software += '\n'
                    process_contributions_software += (
                        process_contributions)[defs_processes.PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE][i]
                process_file_path = process[defs_processes.PROCESS_FILE]
                process_file = os.path.basename(process_file_path)
                process_src_path = process[defs_processes.PROCESS_FIELD_SRC]
                process_src = os.path.basename(process_src_path)
                process_doc_path = process[defs_processes.PROCESS_FIELD_DOC]
                process_doc = os.path.basename(process_doc_path)
                rowPosition = self.tableWidget.rowCount()
                self.tableWidget.insertRow(rowPosition)
                name_item = QTableWidgetItem(process_name)
                name_item.setTextAlignment(Qt.AlignCenter)
                column_pos = 0
                self.tableWidget.setItem(rowPosition, column_pos, name_item)
                provider_item = QTableWidgetItem(process_provider)
                provider_item.setTextAlignment(Qt.AlignCenter)
                column_pos += 1
                self.tableWidget.setItem(rowPosition, column_pos, provider_item)
                parameters_item = QTableWidgetItem(defs_processes.PROCESS_FIELD_PARAMETERS_TAG)
                parameters_item.setTextAlignment(Qt.AlignCenter)
                column_pos += 1
                self.tableWidget.setItem(rowPosition, column_pos, parameters_item)
                file_item = QTableWidgetItem(process_file_path)
                file_item.setTextAlignment(Qt.AlignCenter)
                column_pos += 1
                self.tableWidget.setItem(rowPosition, column_pos, file_item)
                description_item = QTableWidgetItem(process_description)
                description_item.setTextAlignment(Qt.AlignCenter)
                column_pos += 1
                self.tableWidget.setItem(rowPosition, column_pos, description_item)
                doc_item = QTableWidgetItem(process_doc_path)
                doc_item.setTextAlignment(Qt.AlignCenter)
                column_pos += 1
                self.tableWidget.setItem(rowPosition, column_pos, doc_item)
                src_item = QTableWidgetItem(process_src_path)
                src_item.setTextAlignment(Qt.AlignCenter)
                column_pos += 1
                self.tableWidget.setItem(rowPosition, column_pos, src_item)
                contributions_methodology_item = QTableWidgetItem(process_contributions_methodology)
                contributions_methodology_item.setTextAlignment(Qt.AlignCenter)
                column_pos += 1
                self.tableWidget.setItem(rowPosition, column_pos, contributions_methodology_item)
                contributions_software_item = QTableWidgetItem(process_contributions_software)
                contributions_software_item.setTextAlignment(Qt.AlignCenter)
                column_pos += 1
                self.tableWidget.setItem(rowPosition, column_pos, contributions_software_item)
        self.tableWidget.resizeColumnToContents(0)
        self.tableWidget.resizeColumnToContents(3)
        # self.tableWidget.resizeColumnsToContents()
        return
