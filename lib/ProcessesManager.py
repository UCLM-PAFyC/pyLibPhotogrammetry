# authors:
# David Hernandez Lopez, david.hernandez@uclm.es

import os
import sys
import pathlib
import math
import random
import re
import json

current_path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(current_path, '..'))
sys.path.append(os.path.join(current_path, '../..'))
# sys.path.insert(0, '..')
# sys.path.insert(0, '../..')

from pyLibPhotogrammetry.defs import defs_project, defs_processes

from pyLibParameters import defs_pars
from pyLibParameters.ParametersManager import ParametersManager
from pyLibQtTools import Tools

class ProcessesManager:
    def __init__(self):
        self.path = None
        self.processes_by_provider ={}

    def initialize(self,
                   # processes_path,
                   process_path_by_provider):
        str_error = ''
        processes_by_provider = {}
        # # lib processes
        # parent_path = os.path.dirname(current_path)
        # lib_processes_path = parent_path + '/' + defs_processes.PROCESSES_PATH
        # lib_processes_path = os.path.normpath(lib_processes_path)
        # if not os.path.exists(lib_processes_path):
        #     str_error = ('Not exists lib processes path:\n{}'.format(lib_processes_path))
        #     return str_error
        # for provider in defs_processes.processes_providers:
        #     provider_processes_path = (lib_processes_path + '/' + provider)
        #     provider_processes_path = os.path.normpath(provider_processes_path)
        #     if not os.path.exists(processes_path):
        #         str_error = ('Not exists {}} processes path:\n{}'.format(provider, provider_processes_path))
        #         return str_error
        #     provider_processes_src_path = (provider_processes_path + '/' + defs_processes.PROCESSES_SRC_PATH)
        #     provider_processes_src_path = os.path.normpath(provider_processes_src_path)
        #     if not os.path.exists(provider_processes_src_path):
        #         str_error = ('Not exists {} processes SRC path:\n{}'.format(provider, provider_processes_src_path))
        #         return str_error
        #     provider_processes_doc_path = (provider_processes_path + '/' + defs_processes.PROCESSES_DOC_PATH)
        #     provider_processes_doc_path = os.path.normpath(provider_processes_doc_path)
        #     if not os.path.exists(provider_processes_doc_path):
        #         str_error = ('Not exists {} processes SRC path:\n{}'.format(provider, provider_processes_doc_path))
        #         return str_error
        #     processes_files = []
        #     for file in os.listdir(provider_processes_path):
        #         if file.endswith(defs_processes.PROCESSES_FILES_EXTENSION):
        #             file_path = os.path.normcase(provider_processes_path + '/' + file)
        #             processes_files.append(file_path)
        #     processes_src_files = []
        #     for file in os.listdir(provider_processes_src_path):
        #         if file.endswith(defs_processes.PROCESSES_SRC_FILES_EXTENSION):
        #             processes_src_files.append(file)
        #     processes_doc_files = []
        #     for file in os.listdir(provider_processes_doc_path):
        #         if file.endswith(defs_processes.PROCESSES_DOC_FILES_EXTENSION):
        #             processes_doc_files.append(file)
        #     processes = {}
        #     for process_file in processes_files:
        #         str_error, process = self.load_process_file(process_file,
        #                                                     provider,
        #                                                     processes_src_files,
        #                                                     provider_processes_src_path,
        #                                                     processes_doc_files,
        #                                                     provider_processes_doc_path)
        #         if str_error:
        #             return str_error
        #         process_name = process[defs_processes.PROCESS_FIELD_NAME]
        #         processes[process_name] = process
        #     processes_by_provider[provider] = processes
        # # processes argument
        parent_path = os.path.dirname(current_path)
        lib_processes_path = parent_path + '/' + defs_processes.PROCESSES_PATH
        lib_processes_path = os.path.normpath(lib_processes_path)
        if not os.path.exists(lib_processes_path):
            str_error = ('Not exists lib processes path:\n{}'.format(lib_processes_path))
            return str_error
        # processes_path = os.path.normpath(processes_path)
        # if not os.path.exists(lib_processes_path):
        #     str_error = ('Not exists processes path:\n{}'.format(processes_path))
        #     return str_error
        for provider in defs_processes.processes_providers:
            if provider in process_path_by_provider:
                processes_path = process_path_by_provider[provider]
            else:
                processes_path = lib_processes_path
            provider_processes_path = (processes_path + '/' + provider)
            provider_processes_path = os.path.normpath(provider_processes_path)
            if not os.path.exists(provider_processes_path):
                str_error = ('Not exists {}} processes path:\n{}'.format(provider, provider_processes_path))
                return str_error
            provider_processes_src_path = (provider_processes_path + '/' + defs_processes.PROCESSES_SRC_PATH)
            provider_processes_src_path = os.path.normpath(processes_path)
            if not os.path.exists(provider_processes_src_path):
                str_error = ('Not exists {} processes SRC path:\n{}'.format(provider, provider_processes_src_path))
                return str_error
            provider_processes_doc_path = (provider_processes_path + '/' + defs_processes.PROCESSES_DOC_PATH)
            provider_processes_doc_path = os.path.normpath(provider_processes_doc_path)
            if not os.path.exists(provider_processes_doc_path):
                str_error = ('Not exists {} processes DOC path:\n{}'.format(provider, provider_processes_doc_path))
                return str_error
            processes_files = []
            for file in os.listdir(provider_processes_path):
                if file.endswith(defs_processes.PROCESSES_FILES_EXTENSION):
                    file_path = os.path.normcase(provider_processes_path + '/' + file)
                    processes_files.append(file_path)
            processes_src_files = []
            for file in os.listdir(provider_processes_src_path):
                if file.endswith(defs_processes.PROCESSES_SRC_FILES_EXTENSION):
                    processes_src_files.append(file)
            processes_doc_files = []
            for file in os.listdir(provider_processes_doc_path):
                if file.endswith(defs_processes.PROCESSES_DOC_FILES_EXTENSION):
                    processes_doc_files.append(file)
            processes = {}
            for process_file in processes_files:
                str_error, process = self.load_process_file(process_file,
                                                            provider,
                                                            processes_src_files,
                                                            provider_processes_src_path,
                                                            processes_doc_files,
                                                            provider_processes_doc_path)
                if str_error:
                    return str_error
                process_name = process[defs_processes.PROCESS_FIELD_NAME]
                processes[process_name] = process
            processes_by_provider[provider] = processes
        self.processes_by_provider = processes_by_provider
        return str_error

    def load_process_file(self, process_file, provider,
                          processes_src_files = None,
                          provider_processes_src_path = '',
                          processes_doc_files = None,
                          provider_processes_doc_path = '',
                          ):
        str_error = ''
        need_save = False
        process = None
        try:
            with open(process_file, 'r') as file:
                try:
                    json_content = json.load(file)
                except json.JSONDecodeError as e:
                    str_error = ('Loading file:\n{}\nError:\n{}'.format(process_file, e))
                    return str_error, process
        except:
            str_error = ('Error opening file:\n{}'.format(process_file))
            return str_error, process
        if not defs_processes.PROCESS_FIELD_NAME in json_content:
            str_error = ('ProcessesManager.load_process_file\n')
            str_error += ("No field {} in process from file:\n{}".
                          format(defs_processes.PROCESS_FIELD_NAME, process_file))
            return str_error, process
        process_name = json_content[defs_processes.PROCESS_FIELD_NAME]
        if provider in self.processes_by_provider:
            if process_name in self.processes_by_provider[provider]:
                str_error = ('ProcessesManager.load_process_file\n')
                str_error += ("Exists several process named: {},\nreading process from file:\n{}".
                              format(process_name, process_file))
                return str_error, process
        if not defs_processes.PROCESS_FIELD_CONTRIBUTIONS in json_content:
            str_error = ('ProcessesManager.load_process_file\n')
            str_error += ("No field {} in process from file:\n{}".
                          format(defs_processes.PROCESS_FIELD_CONTRIBUTIONS, process_file))
            return str_error, process
        contributions = json_content[defs_processes.PROCESS_FIELD_CONTRIBUTIONS]
        if not defs_processes.PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY in contributions:
            str_error = ('ProcessesManager.load_process_file\n')
            str_error += ("No field {} in process from file:\n{}".
                          format(defs_processes.PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY, process_file))
            return str_error, process
        if not defs_processes.PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE in contributions:
            str_error = ('ProcessesManager.load_process_file\n')
            str_error += ("No field {} in process from file:\n{}".
                          format(defs_processes.PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE, process_file))
            return str_error, process
        process_contributions = {}
        process_contributions[defs_processes.PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY] \
            = contributions[defs_processes.PROCESS_FIELD_CONTRIBUTIONS_METHODOLOGY]
        process_contributions[defs_processes.PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE] \
            = contributions[defs_processes.PROCESS_FIELD_CONTRIBUTIONS_SOFTWARE]
        if not defs_processes.PROCESS_FIELD_DESCRIPTION in json_content:
            str_error = ('ProcessesManager.load_process_file\n')
            str_error += ("No field {} in process from file:\n{}".
                          format(defs_processes.PROCESS_FIELD_DESCRIPTION, process_file))
            return str_error, process
        process_description = json_content[defs_processes.PROCESS_FIELD_DESCRIPTION]
        if not defs_processes.PROCESS_FIELD_PARAMETERS in json_content:
            str_error = ('ProcessesManager.load_process_file\n')
            str_error += ("No field {} in process from file:\n{}".
                          format(defs_processes.PROCESS_FIELD_PARAMETERS, process_file))
            return str_error, process
        parameters_dictionary_list = json_content[defs_processes.PROCESS_FIELD_PARAMETERS]
        process_parameters_manager = ParametersManager()
        str_aux_error = process_parameters_manager.initialize(parameters_dictionary_list)
        if str_aux_error:
            # str_error = ('ProcessesManager.load_process_file\n')
            # str_error += ("\nIn process from file:\n{}".format(process_file))
            # str_error += ('\nError:\n{}'.format(str_aux_error))
            # Tools.error_msg(str_error)
            str_error = ('ProcessesManager.load_process_file\n')
            str_error += ("No field {} in process from file:\n{}".
                          format(defs_processes.PROCESS_FIELD_PARAMETERS, process_file))
            str_error += ("\nError:\n{}".
                          format(str_aux_error))
            return str_error, process
        if not defs_processes.PROCESS_FIELD_SRC in json_content:
            str_error = ('ProcessesManager.load_process_file\n')
            str_error += ("No field {} in process from file:\n{}".
                          format(defs_processes.PROCESS_FIELD_SRC, process_file))
            return str_error, process
        src_file_name = json_content[defs_processes.PROCESS_FIELD_SRC]
        if not defs_processes.PROCESS_FIELD_DOC in json_content:
            str_error = ('ProcessesManager.load_process_file\n')
            str_error += ("No field {} in process from file:\n{}".
                          format(defs_processes.PROCESS_FIELD_DOC, process_file))
            return str_error, process
        doc_file_name = json_content[defs_processes.PROCESS_FIELD_DOC]
        # process_base_name = pathlib.Path(process_file).stem
        process_src_file = ''
        if src_file_name.casefold() == defs_processes.PROCESSES_SRC_TYPE_LIBRARY_FUNCTION.casefold():
            process_src_file = src_file_name
        else:
            if src_file_name:
                if not os.path.exists(src_file_name):
                    src_file_basename = os.path.basename(src_file_name)
                    for file_basename in processes_src_files:
                        # file_base_name = pathlib.Path(file).stem
                        if file_basename.casefold() == src_file_basename.casefold():
                            file_path = os.path.normcase(provider_processes_src_path + '/' + file_basename)
                            process_src_file = file_path
                            need_save = True
                            break
                else:
                    process_src_file = src_file_name
        if not process_src_file:
            str_error = ('ProcessesManager.load_process_file\n')
            str_error += ("\nIn process from file:\n{}".format(process_file))
            str_error += ('\nProcess source file is empty')
            Tools.error_msg(str_error)
        if process_src_file.casefold() != defs_processes.PROCESSES_SRC_TYPE_LIBRARY_FUNCTION.casefold():
            if not os.path.exists(process_src_file):
                str_error = ('ProcessesManager.load_process_file\n')
                str_error += ("\nIn process from file:\n{}".format(process_file))
                str_error += ('\nNot exists process source file:\n{}'.format(src_file_name))
                Tools.error_msg(str_error)
                process_src_file = ''
        if not process_src_file:
            dialog_title = 'Select process source python file'
            previous_file = None
            previous_path = self.path
            file_types = [defs_processes.PROCESSES_SRC_FILES_EXTENSION]
            file_mode = defs_pars.FILE_MODE_READ
            mandatory = True
            str_error, process_src_file = Tools.get_file(dialog_title, previous_file, previous_path,
                                                         file_types, file_mode,mandatory)
            if str_error:
                Tools.error_msg(str_error)
                return str_error, process
            need_save = True
        process_doc_file = ''
        if doc_file_name:
            if not os.path.exists(doc_file_name):
                doc_file_basename = os.path.basename(doc_file_name)
                for file_basename in processes_doc_files:
                    # file_base_name = pathlib.Path(file).stem
                    if file_basename.casefold() == doc_file_basename.casefold():
                        file_path = os.path.normcase(provider_processes_doc_path + '/' + file_basename)
                        process_doc_file = file_path
                        need_save = True
                        break
            else:
                process_doc_file = doc_file_name
        if defs_processes.PROCESS_DOC_FILE_IS_MANDATORY:
            if not process_doc_file:
                str_error = ('ProcessesManager.load_process_file\n')
                str_error += ("\nIn process from file:\n{}".format(process_file))
                str_error += ('\nDocumentation file is empty')
                Tools.error_msg(str_error)
            elif not os.path.exists(process_doc_file):
                str_error = ('ProcessesManager.load_process_file\n')
                str_error += ("\nIn process from file:\n{}".format(process_file))
                str_error += ('\nNot exists documentation file:\n{}'.format(process_doc_file))
                Tools.error_msg(str_error)
                process_doc_file = ''
            if not process_doc_file:
                dialog_title = 'Select process documentation pdf file'
                previous_file = None
                previous_path = self.path
                file_types = [defs_processes.PROCESSES_DOC_FILES_EXTENSION]
                file_mode = defs_pars.FILE_MODE_READ
                mandatory = False
                str_error, process_doc_file = Tools.get_file(dialog_title, previous_file, previous_path,
                                                             file_types, file_mode,mandatory)
                if str_error:
                    Tools.error_msg(str_error)
                    return str_error, process
                need_save = True
        process = {}
        process[defs_processes.PROCESS_FILE] = process_file
        process[defs_processes.PROCESS_FIELD_NAME] = process_name
        process[defs_processes.PROCESS_FIELD_CONTRIBUTIONS] = process_contributions
        process[defs_processes.PROCESS_FIELD_DESCRIPTION] = process_description
        process[defs_processes.PROCESS_FIELD_PARAMETERS] = process_parameters_manager
        # process[defs_processes.PROCESS_FILE] = process_file
        process[defs_processes.PROCESS_SRC] = process_src_file
        process[defs_processes.PROCESS_DOC] = process_doc_file
        if need_save:
            as_dict = {}
            as_dict[defs_processes.PROCESS_FIELD_NAME] = process[defs_processes.PROCESS_FIELD_NAME]
            as_dict[defs_processes.PROCESS_FIELD_CONTRIBUTIONS] = process[defs_processes.PROCESS_FIELD_CONTRIBUTIONS]
            as_dict[defs_processes.PROCESS_FIELD_SRC] = process[defs_processes.PROCESS_FIELD_SRC]
            as_dict[defs_processes.PROCESS_FIELD_DESCRIPTION] = process[defs_processes.PROCESS_FIELD_DESCRIPTION]
            as_dict[defs_processes.PROCESS_FIELD_DOC] = process[defs_processes.PROCESS_DOC]
            as_dict[defs_processes.PROCESS_FIELD_PARAMETERS] \
                = process[defs_processes.PROCESS_FIELD_PARAMETERS].parameters_as_list_of_dict
            json_object = json.dumps(as_dict, indent=4, ensure_ascii=False)
            with open(process_file, "w") as outfile:
                outfile.write(json_object)
        return str_error, process

    def get_process_arguments(self, provider, name):
        str_error = ""
        arguments = []
        if not provider in self.processes_by_provider:
            str_error = ('ProcessesManager.get_process_arguments\n')
            str_error += ('Not exists processes provider: {}'.format(provider))
            return str_error, arguments
        if not name in self.processes_by_provider[provider]:
            str_error = ('ProcessesManager.get_process_arguments\n')
            str_error += ('Not exists process name: {} for provider: {}'.format(name, provider))
            return str_error, arguments
        process = self.processes_by_provider[provider][name]
        process_src_file_path = process[defs_processes.PROCESS_FIELD_SRC]
        if not process_src_file_path:
            str_error = ('ProcessesManager.get_process_arguments\n')
            str_error += ('Source file is not selected')
            return str_error, arguments
        if not os.path.exists(process_src_file_path):
            str_error = ('ProcessesManager.get_process_arguments\n')
            str_error += ('Not exists source file:\n{}'.format(process_src_file_path))
            return str_error, arguments
        process_src_file_path = os.path.normcase(process_src_file_path)
        parametes_manager = process[defs_processes.PROCESS_FIELD_PARAMETERS]
        str_error, parameters_arguments = parametes_manager.get_process_arguments()
        if str_error:
            return str_error, arguments
        arguments.append(process_src_file_path)
        for i in range(len(parameters_arguments)):
            arguments.append(parameters_arguments[i])
        # if dialog_result != QDialog.Accepted:
        #     return str_error
        return str_error, arguments

    def get_process_output_arguments(self, provider, name):
        str_error = ""
        output_arguments = []
        if not provider in self.processes_by_provider:
            str_error = ('ProcessesManager.get_process_output_arguments\n')
            str_error += ('Not exists processes provider: {}'.format(provider))
            return str_error, output_arguments
        if not name in self.processes_by_provider[provider]:
            str_error = ('ProcessesManager.get_process_output_arguments\n')
            str_error += ('Not exists process name: {} for provider: {}'.format(name, provider))
            return str_error, output_arguments
        process = self.processes_by_provider[provider][name]
        parametes_manager = process[defs_processes.PROCESS_FIELD_PARAMETERS]
        str_error, output_arguments = parametes_manager.get_process_output_arguments()
        if str_error:
            return str_error, output_arguments
        return str_error, output_arguments


    def save(self, provider, name):
        str_error = ""
        if not provider in self.processes_by_provider:
            str_error = ('ProcessesManager.save\n')
            str_error += ('Not exists processes provider: {}'.format(provider))
            return str_error
        if not name in self.processes_by_provider[provider]:
            str_error = ('ProcessesManager.save\n')
            str_error += ('Not exists process name: {} for provider: {}'.format(name, provider))
            return str_error
        process = self.processes_by_provider[provider][name]
        file_name = process[defs_processes.PROCESS_FIELD_FILE]
        as_dict = {}
        as_dict[defs_processes.PROCESS_FIELD_NAME] = process[defs_processes.PROCESS_FIELD_NAME]
        as_dict[defs_processes.PROCESS_FIELD_CONTRIBUTIONS] = process[defs_processes.PROCESS_FIELD_CONTRIBUTIONS]
        as_dict[defs_processes.PROCESS_FIELD_SRC] = process[defs_processes.PROCESS_FIELD_SRC]
        as_dict[defs_processes.PROCESS_FIELD_DESCRIPTION] = process[defs_processes.PROCESS_FIELD_DESCRIPTION]
        as_dict[defs_processes.PROCESS_FIELD_DOC] = process[defs_processes.PROCESS_DOC]
        as_dict[defs_processes.PROCESS_FIELD_PARAMETERS] \
            = process[defs_processes.PROCESS_FIELD_PARAMETERS].parameters_as_list_of_dict
        json_object = json.dumps(as_dict, indent=4, ensure_ascii=False)
        with open(file_name, "w") as outfile:
            outfile.write(json_object)
        return str_error

