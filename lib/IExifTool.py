import os, sys
import exiftool

from PyQt5.QtWidgets import QApplication

# exiftool_file_path = "E:\\dev\\python\\qgis_plugins\\PhotogrammetryTools\\external_tools\\exiftool-13.36_64\\exiftool.exe"
current_path = os.path.dirname(os.path.realpath(__file__))

class IExifTool(object):
    is_initialized = False
    exiftool_file_path = None
    et = None

    @classmethod
    def initialize(self):
        str_error = ''
        parent_path = os.path.dirname(current_path)
        exiftool_file_path = parent_path + "\\external_tools\\exiftool-13.36_64\\exiftool.exe"
        exiftool_file_path = os.path.normpath(exiftool_file_path)
        if not os.path.exists(exiftool_file_path):
            str_error = ("The exiftool path:\n'{}'\ndoes not exist".format(exiftool_file_path))
            return str_error
        try:
            self.et = exiftool.ExifToolHelper(executable=exiftool_file_path)
        except Exception as e:
            str_error = ('EXIFTOOL Error: {}'.format(e.args[0]))
            return str_error
        self.exiftool_file_path = exiftool_file_path

    @classmethod
    def get_metadata_as_dict(self,
                             files,
                             dialog = None):
        str_error = ''
        metadata_by_file_path = {}
        if not self.is_initialized:
            str_error = self.initialize()
            if str_error:
                return str_error, metadata_by_file_path
        cont = 0
        if dialog: # the dialog must content:
            dialog.processInformationGroupBox.setEnabled(True)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            dialog.processLineEdit.setText('Getting metadata from images ...')
            dialog.processLineEdit.adjustSize()
            dialog.processProgressBar.setMaximum(len(files))
            QApplication.processEvents()
        dialog.processLineEdit.adjustSize()
        for file in files:
            if dialog:
                dialog.processProgressBar.setValue(cont)
                QApplication.processEvents()
            # if dialog.was_canceled:
            #     break
            if not os.path.exists(file):
                if dialog:
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                str_error = ("Getting exif metadata, not exists file:\n{}".format(file))
                return str_error
            metadata = None
            try:
                metadata = self.et.get_metadata(file)
            except Exception as e:
                if dialog:
                    dialog.processInformationGroupBox.setEnabled(False)
                    dialog.processLineEdit.clear()
                    dialog.processProgressBar.reset()
                str_error = ('EXIFTOOL Error: {}'.format(e.args[0]))
                return str_error
            metadata_by_file_path[file] = metadata[0]
            cont = cont + 1
        if dialog:
            dialog.processProgressBar.setValue(cont)
            dialog.processInformationGroupBox.setEnabled(False)
            dialog.processLineEdit.clear()
            dialog.processProgressBar.reset()
            QApplication.processEvents()
        return str_error, metadata_by_file_path


