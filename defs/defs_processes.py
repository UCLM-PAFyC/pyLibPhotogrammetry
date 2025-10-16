# authors:
# David Hernandez Lopez, david.hernandez@uclm.es
import os
import sys

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
# sys.path.insert(0, '..')

PROCESS_PYTHON_PROGRAM = "python"
PROCESSES_PATH = "processes"
GDAL_PATH = "gdal"
CGAL_PATH = "cgal"
LIB_PATH = "lib" # library processes
PROCESSES_SRC_PATH = "src"
PROCESSES_DOC_PATH = "doc"
processes_providers = []
processes_providers.append(GDAL_PATH)
processes_providers.append(CGAL_PATH)
processes_providers.append(LIB_PATH)
PROCESSES_FILES_EXTENSION = ".json"
PROCESSES_SRC_FILES_EXTENSION = ".py"
PROCESSES_DOC_FILES_EXTENSION = ".pdf"
PROCESS_FILE = "file"
PROCESS_SRC = PROCESSES_SRC_PATH
PROCESS_DOC = PROCESSES_DOC_PATH
PROCESSES_MANAGER_DIALOG_TITLE = 'Processes Manager'
PROCESSES_SRC_TYPE_LIBRARY_FUNCTION = "library function"
PROCESS_DOC_FILE_IS_MANDATORY = False

PROCESS_FIELD_NAME = "name"
PROCESS_FIELD_PROVIDER = "provider"
PROCESS_FIELD_CONTRIBUTIONS = "contributions"
PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY = "methodology"
PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE = "software"
PROCESS_FIELD_SRC = "src"
PROCESS_FIELD_DOC = "doc"
PROCESS_FIELD_DESCRIPTION = "description"
PROCESS_FIELD_PARAMETERS = "parameters"
PROCESS_FIELD_FILE = "file"
PROCESS_FIELD_NAME_TAG = "Name"
PROCESS_FIELD_PROVIDER_TAG = "Provider"
PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY_TAG = "Contributions\nMethodology"
PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE_TAG = "Contributions\nSoftware"
PROCESS_FIELD_SRC_TAG = "Source\nCode"
PROCESS_FIELD_DOC_TAG = "Documentation"
PROCESS_FIELD_DESCRIPTION_TAG = "Description"
PROCESS_FIELD_PARAMETERS_TAG = "Parameters"
PROCESS_FIELD_FILE_TAG = "File"
PROCESS_FIELD_NAME_TOOLTIP = "Name"
PROCESS_FIELD_PROVIDER_TOOLTIP = "Provider"
PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY_TOOLTIP = "Contributions\nMethodology"
PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE_TOOLTIP = "Contributions\nSoftware"
PROCESS_FIELD_SRC_TOOLTIP = "Source\nCode"
PROCESS_FIELD_DOC_TOOLTIP = "Documentation"
PROCESS_FIELD_DESCRIPTION_TOOLTIP = "Description"
PROCESS_FIELD_PARAMETERS_TOOLTIP = "Parameters"
PROCESS_FIELD_FILE_TOOLTIP = "File"
processes_manager_dialog_header=[PROCESS_FIELD_NAME_TAG,
                                 PROCESS_FIELD_PROVIDER_TAG,
                                 PROCESS_FIELD_PARAMETERS_TAG,
                                 PROCESS_FIELD_FILE_TAG,
                                 PROCESS_FIELD_DESCRIPTION_TAG,
                                 PROCESS_FIELD_DOC_TAG,
                                 PROCESS_FIELD_SRC_TAG,
                                 PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY_TAG,
                                 PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE_TAG]
processes_manager_dialog_field_by_header_tag = {}
processes_manager_dialog_field_by_header_tag[PROCESS_FIELD_NAME_TAG] = PROCESS_FIELD_NAME
processes_manager_dialog_field_by_header_tag[PROCESS_FIELD_PROVIDER_TAG] = PROCESS_FIELD_PROVIDER
processes_manager_dialog_field_by_header_tag[PROCESS_FIELD_PARAMETERS_TAG] = PROCESS_FIELD_PARAMETERS
processes_manager_dialog_field_by_header_tag[PROCESS_FIELD_FILE_TAG] = PROCESS_FIELD_FILE
processes_manager_dialog_field_by_header_tag[PROCESS_FIELD_DESCRIPTION_TAG] = PROCESS_FIELD_DESCRIPTION
processes_manager_dialog_field_by_header_tag[PROCESS_FIELD_DOC_TAG] = PROCESS_FIELD_DOC
processes_manager_dialog_field_by_header_tag[PROCESS_FIELD_SRC_TAG] = PROCESS_FIELD_SRC
processes_manager_dialog_field_by_header_tag[PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY_TAG] = PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY
processes_manager_dialog_field_by_header_tag[PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE_TAG] = PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE
processes_manager_dialog_tooltip_by_header_tag = {}
processes_manager_dialog_tooltip_by_header_tag[PROCESS_FIELD_NAME_TAG] = PROCESS_FIELD_NAME_TOOLTIP
processes_manager_dialog_tooltip_by_header_tag[PROCESS_FIELD_PROVIDER_TAG] = PROCESS_FIELD_PROVIDER_TOOLTIP
processes_manager_dialog_tooltip_by_header_tag[PROCESS_FIELD_PARAMETERS_TAG] = PROCESS_FIELD_PARAMETERS_TOOLTIP
processes_manager_dialog_tooltip_by_header_tag[PROCESS_FIELD_FILE_TAG] = PROCESS_FIELD_FILE_TOOLTIP
processes_manager_dialog_tooltip_by_header_tag[PROCESS_FIELD_DESCRIPTION_TAG] = PROCESS_FIELD_DESCRIPTION_TOOLTIP
processes_manager_dialog_tooltip_by_header_tag[PROCESS_FIELD_DOC_TAG] = PROCESS_FIELD_DOC_TOOLTIP
processes_manager_dialog_tooltip_by_header_tag[PROCESS_FIELD_SRC_TAG] = PROCESS_FIELD_SRC_TOOLTIP
processes_manager_dialog_tooltip_by_header_tag[PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY_TAG] = PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY_TOOLTIP
processes_manager_dialog_tooltip_by_header_tag[PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE_TAG] = PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE_TOOLTIP

