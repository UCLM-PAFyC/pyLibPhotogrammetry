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
from Project import Project

from pyLibQtTools import Tools
from pyLibQtTools.Tools import SimpleTextEditDialog, SimpleJSONDialog

class ProjectProcessesDialog(QDialog):
    """Employee dialog."""

    def __init__(self,
                 project,
                 title,
                 settings,
                 parent=None):
        super().__init__(parent)
        loadUi(os.path.join(os.path.dirname(__file__), 'ProjectProcessesDialog.ui'), self)
        # loadUi("lib/InstrumentsDialog.ui", self)
        self.project = project
        self.title = title
        self.formats = None
        self.settings = settings
        self.edited_process_fields_by_original_label = {}
        self.original_process_label_by_row = {}
        self.row_by_original_process_label = {}
        self.column_by_field_name = {}
        self.initialize(title)

    def initialize(self,
                   title):
        self.setWindowTitle(title)
        headers = defs_project.project_processes_dialog_header
        headers_tooltips = defs_project.project_processes_dialog_tooltip_by_header_tag
        field_by_header = defs_project.project_processes_dialog_field_by_header_tag
        self.tableWidget.setColumnCount(len(headers))
        self.tableWidget.setStyleSheet("QHeaderView::section { color:black; background : lightGray; }")
        for i in range(len(headers)):
            header_item = QTableWidgetItem(headers[i])
            header_tooltip = headers_tooltips[headers[i]]
            header_item.setToolTip(header_tooltip)
            self.tableWidget.setHorizontalHeaderItem(i, header_item)
        self.tableWidget.itemDoubleClicked.connect(self.on_click)
        self.tableWidget.itemClicked.connect(self.on_click)
        self.removePushButton.clicked.connect(self.remove)
        self.savePushButton.clicked.connect(self.save)
        self.update_gui()
        return

    @QtCore.pyqtSlot(QtWidgets.QTableWidgetItem)
    def on_click(self, item):
        row = item.row()
        column = item.column()
        current_text = item.text()
        process_label =  self.tableWidget.item(row, 0).text()
        original_process_label = self.original_process_label_by_row[row]
        process = self.project.process_by_label[process_label]
        column_label = self.tableWidget.horizontalHeaderItem(column).text()
        tool_tip_text = self.tableWidget.horizontalHeaderItem(column).toolTip()
        title =  defs_project.PROJECT_PROCESSES_DIALOG_TITLE
        title += (": {}".format(process_label))
        if column_label == defs_project.PROCESESS_FIELD_LABEL_TAG:
            text, ok = QInputDialog().getText(self, title,
                                              "Process label (unique value):", QLineEdit.Normal,
                                              current_text)
            if (ok and text.casefold() != process_label.casefold()
                    and text.casefold() != original_process_label.casefold()):
                exists_label = False
                for process_label in self.project.process_by_label:
                    if text.casefold() == process_label.casefold():
                        exists_label = True
                        break
                if exists_label:
                    str_msg = ('Exists another process with label: {}'.format(text))
                    Tools.info_msg(str_msg)
                    return
                if not original_process_label in self.edited_process_fields_by_original_label:
                    self.edited_process_fields_by_original_label[original_process_label] = []
                process_field_name = defs_project.project_processes_dialog_field_by_header_tag[column_label]
                self.edited_process_fields_by_original_label[original_process_label].append(process_field_name)
                self.tableWidget.item(row, column).setText(text)
        elif column_label == defs_project.PROCESESS_FIELD_DESCRIPTION_TAG\
                or column_label == defs_project.PROCESESS_FIELD_REMARKS_TAG:
            dialog = SimpleTextEditDialog(title, current_text, False)
            ret = dialog.exec()
            text = dialog.get_text()
            if text != current_text:
                process_field_name = defs_project.project_processes_dialog_field_by_header_tag[column_label]
                if not original_process_label in self.edited_process_fields_by_original_label:
                    self.edited_process_fields_by_original_label[original_process_label] = []
                self.edited_process_fields_by_original_label[original_process_label].append(process_field_name)
                self.tableWidget.item(row, column).setText(text)
        elif column_label == defs_project.PROCESESS_FIELD_LOG_TAG:
            dialog = SimpleTextEditDialog(title, current_text, True)
            ret = dialog.exec()
        elif column_label == defs_project.PROCESESS_FIELD_PROCESS_CONTENT_TAG:
            # dialog = SimpleTextEditDialog(title, current_text, True)
            dialog = SimpleJSONDialog(title, current_text, True)
            ret = dialog.exec()
        else:
            str_msg = ('Process {} is not editable'.format(column_label))
            Tools.info_msg(str_msg)
            return
        self.tableWidget.resizeColumnToContents(0)
        self.tableWidget.resizeColumnToContents(3)
        return

    def remove(self):
        process_label_column = self.column_by_field_name[defs_project.PROCESESS_FIELD_LABEL]
        process_labels_to_remove = []
        for i in range(self.tableWidget.rowCount()):
            id_item = self.tableWidget.item(i, 0)
            if id_item.isSelected():
                process_label = self.tableWidget.item(i, process_label_column).text()
                process_labels_to_remove.append(process_label)
        if len(process_labels_to_remove) < 1:
            str_error = "Select processes to remove"
            Tools.error_msg(str_error)
            return
        for i in range(len(process_labels_to_remove)):
            process_label = process_labels_to_remove[i]
            str_error = self.project.remove_process(process_label)
            if str_error:
                str_msg = ('Removing process: {}, error:\n'.format(process_label, str_error))
                Tools.error_msg(str_msg)
                return
        self.update_gui()
        return

    def save(self):
        if not bool(self.edited_process_fields_by_original_label):
            str_msg = ('Nothing to do')
            Tools.info_msg(str_msg)
        for original_label in self.edited_process_fields_by_original_label:
            process_label = original_label
            row = self.row_by_original_process_label[original_label]
            changed_field_names = self.edited_process_fields_by_original_label[original_label]
            if defs_project.PROCESESS_FIELD_LABEL in changed_field_names:
                old_value = self.project.process_by_label.pop(original_label)
                col = self.column_by_field_name[defs_project.PROCESESS_FIELD_LABEL]
                new_value = self.tableWidget.item(row, col).text()
                self.project.process_by_label[new_value] = old_value
                process_label = new_value
            for field_name in changed_field_names:
                col = self.column_by_field_name[field_name]
                new_value = self.tableWidget.item(row, col).text()
                self.project.process_by_label[process_label][field_name] = new_value
            str_aux_error = self.project.update_process(original_label, process_label)
            if str_aux_error:
                str_error = ('Error updating project definition:\n{}'.
                             format(str_aux_error))
                Tools.error_msg(str_error)
                return
        str_msg = "Process completed"
        Tools.info_msg(str_msg)
        return

    def update_gui(self):
        self.tableWidget.setRowCount(0)
        self.original_process_label_by_row = {}
        self.edited_process_fields_by_original_label = {}
        self.row_by_original_process_label = {}
        self.column_by_field_name = {}
        row = 0
        for process_label in self.project.process_by_label:
            # self.process_by_label[process_label][defs_project.PROCESESS_FIELD_LABEL] = process_label
            process_author = self.project.process_by_label[process_label][defs_project.PROCESESS_FIELD_AUTHOR]
            process_description = self.project.process_by_label[process_label][defs_project.PROCESESS_FIELD_DESCRIPTION]
            process_date_time_as_string = self.project.process_by_label[process_label][defs_project.PROCESESS_FIELD_DATE_TIME]
            process_content = self.project.process_by_label[process_label][defs_project.PROCESESS_FIELD_PROCESS_CONTENT]
            process_log = self.project.process_by_label[process_label][defs_project.PROCESESS_FIELD_LOG]
            process_output = self.project.process_by_label[process_label][defs_project.PROCESESS_FIELD_OUTPUT]
            process_remarks = self.project.process_by_label[process_label][defs_project.PROCESESS_FIELD_REMARKS]
            rowPosition = self.tableWidget.rowCount()
            self.tableWidget.insertRow(rowPosition)
            label_item = QTableWidgetItem(process_label)
            label_item.setTextAlignment(Qt.AlignCenter)
            column_pos = 0
            self.column_by_field_name[defs_project.PROCESESS_FIELD_LABEL] = column_pos
            self.tableWidget.setItem(rowPosition, column_pos, label_item)
            author_item = QTableWidgetItem(process_author)
            author_item.setTextAlignment(Qt.AlignCenter)
            column_pos += 1
            self.column_by_field_name[defs_project.PROCESESS_FIELD_AUTHOR] = column_pos
            self.tableWidget.setItem(rowPosition, column_pos, author_item)
            description_item = QTableWidgetItem(process_description)
            description_item.setTextAlignment(Qt.AlignCenter)
            column_pos += 1
            self.column_by_field_name[defs_project.PROCESESS_FIELD_DESCRIPTION] = column_pos
            self.tableWidget.setItem(rowPosition, column_pos, description_item)
            date_time_item = QTableWidgetItem(process_date_time_as_string)
            date_time_item.setTextAlignment(Qt.AlignCenter)
            column_pos += 1
            self.column_by_field_name[defs_project.PROCESESS_FIELD_DATE_TIME] = column_pos
            self.tableWidget.setItem(rowPosition, column_pos, date_time_item)
            content_item = QTableWidgetItem(process_content)
            content_item.setTextAlignment(Qt.AlignCenter)
            column_pos += 1
            self.column_by_field_name[defs_project.PROCESESS_FIELD_PROCESS_CONTENT] = column_pos
            self.tableWidget.setItem(rowPosition, column_pos, content_item)
            log_item = QTableWidgetItem(process_log)
            log_item.setTextAlignment(Qt.AlignCenter)
            column_pos += 1
            self.column_by_field_name[defs_project.PROCESESS_FIELD_LOG] = column_pos
            self.tableWidget.setItem(rowPosition, column_pos, log_item)
            output_item = QTableWidgetItem(process_output)
            output_item.setTextAlignment(Qt.AlignCenter)
            column_pos += 1
            self.column_by_field_name[defs_project.PROCESESS_FIELD_OUTPUT] = column_pos
            self.tableWidget.setItem(rowPosition, column_pos, output_item)
            remarks_item = QTableWidgetItem(process_remarks)
            remarks_item.setTextAlignment(Qt.AlignCenter)
            column_pos += 1
            self.column_by_field_name[defs_project.PROCESESS_FIELD_REMARKS] = column_pos
            self.tableWidget.setItem(rowPosition, column_pos, remarks_item)
            self.original_process_label_by_row[row] = process_label
            self.row_by_original_process_label[process_label] = row
            row = row + 1
        self.tableWidget.resizeColumnToContents(0)
        self.tableWidget.resizeColumnToContents(3)
        return