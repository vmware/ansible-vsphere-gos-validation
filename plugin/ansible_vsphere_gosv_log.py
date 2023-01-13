# Copyright 2021-2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = '''
    name: ansible_vsphere_gosv_log
    type: notification
    short_description: Write Ansible output and test results to log files
    description:
      - This callback writes detail running log and test results to log file.
'''

import os
import time
import json
import sys
import yaml
import re
import importlib
import shutil
import logging
from datetime import datetime
from collections import OrderedDict
from textwrap import TextWrapper

from ansible import context
from ansible import constants as C
from ansible.playbook.task_include import TaskInclude
from ansible.plugins.callback import CallbackBase
from ansible.module_utils._text import to_bytes, to_native, to_text

if sys.version_info.major == 2:
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    importlib.reload(sys)

"""_summary_
Extract error message from task result
"""
def extract_error_msg(json_obj):
    message = ''
    try:
        for key, value in json_obj.items():
            if key == 'msg':
                if isinstance(value, str):
                    message += value.strip()
                    # Extract stderr or stdout from command output when rc != 0
                    if 'non-zero return code' in value:
                        if 'rc' in json_obj and str(json_obj['rc']) != '':
                            message += ': ' + str(json_obj['rc'])
                        if 'stderr_lines' in json_obj and len(json_obj['stderr_lines']) > 0:
                            if "" in json_obj['stderr_lines']:
                                json_obj['stderr_lines'].remove("")
                            message += '\n' + '\n'.join(json_obj['stderr_lines']).strip()
                        elif 'stdout_lines' in json_obj and len(json_obj['stdout_lines']) > 0:
                            if "" in json_obj['stderr_lines']:
                                json_obj['stdout_lines'].remove("")
                            message += '\n' + '\n'.join(json_obj['stdout_lines']).strip()
                    if 'MODULE FAILURE' in value:
                       if 'module_stderr' in json_obj and str(json_obj['module_stderr']) != '':
                             message += '\n' + json_obj['module_stderr'].strip()
                       elif 'module_stdout' in json_obj and str(json_obj['module_stdout']) != '':
                             message += '\n' + json_obj['module_stdout'].strip()

                elif isinstance(value, list):
                    message += '\n'.join(value)
                elif isinstance(value, dict):
                    message += extract_error_msg(value)
                else:
                    message += str(value).strip()

                if message != '' and not message.endswith('\n'):
                    message += '\n'

    except TypeError as e:
        print("Failed to extract msg from below text as it is not in json format.\n" + str(e))
        pass

    return message

class VmInfo(object):
    def __init__(self, vm_name):
        self.Name = vm_name
        self.IP = ''
        self.Guest_OS_Distribution = ''
        self.Hardware_Version = ''
        self.VMTools_Version = ''
        self.CloudInit_Version = ''
        self.GUI_Installed = None
        self.Config_Guest_Id = ''
        self.GuestInfo_Guest_Id = ''
        self.GuestInfo_Guest_Full_Name = ''
        self.GuestInfo_Guest_Family = ''
        self.GuestInfo_Detailed_Data = ''

    def __str__(self):
        """
        Display VM information as below:

        VM information:
        +---------------------------------------------------------------+
        | Name                      | test_vm                           |
        +---------------------------------------------------------------+
        | IP                        | 192.168.10.125                    |
        +---------------------------------------------------------------+
        | Guest OS Distribution     | VMware Photon OS 4.0 x86_64       |
        +---------------------------------------------------------------+
        | Hardware Version          | vmx-19                            |
        +---------------------------------------------------------------+
        | VMTools Version           | 11.2.5.26209 (build-17337674)     |
        +---------------------------------------------------------------+
        | CloudInit Version         | 20.4.1                            |
        +---------------------------------------------------------------+
        | GUI Installed             | False                             |
        +---------------------------------------------------------------+
        | Config Guest Id           | vmwarePhoton64Guest               |
        +---------------------------------------------------------------+
        | GuestInfo Guest Id        | vmwarePhoton64Guest               |
        +---------------------------------------------------------------+
        | GuestInfo Guest Full Name | VMware Photon OS (64-bit)         |
        +---------------------------------------------------------------+
        | GuestInfo Guest Family    | linuxGuest                        |
        +---------------------------------------------------------------+
        | GuestInfo Detailed Data   | architecture='X86'                |
        |                           | bitness='64'                      |
        |                           | distroName='VMware Photon OS'     |
        |                           | distroVersion='4.0'               |
        |                           | familyName='Linux'                |
        |                           | kernelVersion='5.10.61-1.ph4-esx' |
        |                           | prettyName='VMware Photon OS 4.0' |
        +---------------------------------------------------------------+
        """

        # Get VM name from testing vars file and set log dir
        msg = 'VM information:\n'
        wrap_width = 50
        wrapped_vm_info = {}

        # Get column width
        head_col_width = 0
        info_col_width = 0
        for attr_name, attr_value in vars(self).items():
            if not attr_name.startswith('__') and attr_value is not None:
                head_col_width = max([head_col_width, len(attr_name)])
                if len(attr_value) > wrap_width:
                    if attr_name == 'GuestInfo_Detailed_Data':
                        wrapped_vm_info[attr_name] = self.GuestInfo_Detailed_Data.replace("' ", "'\n").split('\n')
                    else:
                        textwrap = TextWrapper(width=wrap_width)
                        wrapped_vm_info[attr_name] = textwrap.wrap(attr_value)
                elif (attr_name == 'CloudInit_Version' and
                      ('windows' in self.Config_Guest_Id.lower() or
                       'windows' in self.Guest_OS_Distribution.lower() or
                       'windows' in self.GuestInfo_Guest_Id.lower())):
                    continue
                else:
                    wrapped_vm_info[attr_name] = [attr_value]

                max_text_line = max([len(line) for line in wrapped_vm_info[attr_name]])
                info_col_width = max([info_col_width, max_text_line])

        # Table width
        table_width = head_col_width + info_col_width + 5

        row_border = '+{}+\n'.format(''.ljust(table_width, '-'))
        row_format = '| {:<} | {:<} |\n'

        # Table content
        msg += row_border
        for attr_name in wrapped_vm_info:
            head_name = attr_name.replace('_', ' ')
            if (len(wrapped_vm_info[attr_name]) == 1 and
                ('GuestInfo' in attr_name or
                len(wrapped_vm_info[attr_name][0]) > 0)):
                msg += row_format.format(head_name.ljust(head_col_width),
                                         wrapped_vm_info[attr_name][0].ljust(info_col_width))
            else:
                msg += row_format.format(head_name.ljust(head_col_width),
                                         wrapped_vm_info[attr_name][0].ljust(info_col_width))
                index = 1
                while index < len(wrapped_vm_info[attr_name]):
                    msg += row_format.format(''.ljust(head_col_width, ' '),
                                             wrapped_vm_info[attr_name][index].ljust(info_col_width))
                    index += 1

            msg += row_border

        msg += "\n"

        return msg

class CallbackModule(CallbackBase):
    CALLBACK_NAME = 'ansible_vsphere_gosv_log'
    CALLBACK_TYPE = 'notification'
    CALLBACK_VERSION = 2.0
    CALLBACK_NEEDS_WHITELIST = False

    def __init__(self):
        super(CallbackModule, self).__init__()
        self.hosts = []
        self.play = None
        self.log_msg = ''
        self.testcases = OrderedDict()

        # Testbed Info
        self.vcenter_info = {'hostname':'',
                             'version':'',
                             'build':''}
        self.esxi_info = {'hostname':'',
                          'version':'',
                          'update_version':'',
                          'build':'',
                          'model':'',
                          'cpu_model':''}
        self.vm_info = None

        self.os_distribution = ""
        self.os_distribution_ver = ""
        self.os_arch = ""
        self.os_cloudinit_version = None
        self.os_ovt_version = None

        self.started_at = None
        self.finished_at = None

        self.testing_vars_file = None
        self.testing_testcase_file = None
        self.testing_vars = {}

        self.plugin_dir = os.path.dirname(os.path.realpath(__file__))
        self.cwd = os.path.dirname(self.plugin_dir)
        self.log_dir = os.path.join(self.cwd, "logs", time.strftime("%Y-%m-%d-%H-%M-%S"))
        self.current_log_dir = os.path.join(self.cwd, "logs/current")
        self.testrun_log_dir = None
        self.full_debug_log = "full_debug.log"
        self.failed_tasks_log = "failed_tasks.log"
        self.known_issues_log = "known_issues.log"
        self.test_results_log = "results.log"
        self.test_results_yml = "test_results.yml"
        self.os_release_info_file = None

        # Plays and Tasks
        self._play_name = None
        self._play_path = None
        self._last_test_name = None
        self._play_tasks_cache = {}

        self._last_task_uuid = None
        self._last_task_name = None
        self._task_type_cache = {}

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        if os.path.exists(self.current_log_dir):
            try:
                if os.path.islink(self.current_log_dir):
                    os.unlink(self.current_log_dir)
                else:
                    shutil.rmtree(self.current_log_dir)
            except OSError as e:
                self._display.display("Error: {} : {}".format(self.current_log_dir, e.strerror), color=C.COLOR_ERROR)

        os.symlink(self.log_dir, self.current_log_dir, target_is_directory=True)

        # Set logger
        self.logger_name = "ansible-vsphere-gos-validation"
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(logging.DEBUG)

        msg = self._banner("PLUGIN [{}]".format(os.path.realpath(__file__)))
        msg += "Plugin directory: {}\nProject directory: {}\nCurrent log directory: {}".format(
            self.plugin_dir, self.cwd, self.current_log_dir)
        self._display.display(msg, color=C.COLOR_VERBOSE)

    def add_logger_file_handler(self, log_file=None):
        """
        Add a file handler to logger with debug level
        """
        if not log_file:
            return

        log_file_path = os.path.join(self.log_dir, log_file)

        for lh in self.logger.handlers:
            if isinstance(lh, logging.FileHandler) and \
                os.path.realpath(log_file_path) == lh.baseFilename:
                return

        log_handler = logging.FileHandler(log_file_path)
        log_handler.setLevel(logging.DEBUG)

        # Set formatter and add it to file and console handlers
        log_format = "%(message)s"
        formatter = logging.Formatter(log_format)
        log_handler.setFormatter(formatter)

        # Add handlers to the logger
        self.logger.addHandler(log_handler)

    def remove_logger_file_handler(self, log_file=None):
        """
        Remove a file handler from logger
        """
        if not log_file:
            return

        log_file_path = os.path.join(self.log_dir, log_file)

        for lh in self.logger.handlers:
            if isinstance(lh, logging.FileHandler) and \
                os.path.realpath(log_file_path) == lh.baseFilename:
                lh.flush()
                lh.close()
                self.logger.removeHandler(lh)
                return

    def _task_start(self, task, prefix=None):
        # Cache output prefix for task if provided
        # This is needed to properly display 'RUNNING HANDLER' and similar
        # when hiding skipped/ok task results
        if prefix is not None:
            self._task_type_cache[task._uuid] = prefix

        # Preserve task name, as all vars may not be available for templating
        # when we need it later
        if self.play and self.play.strategy in ('free', 'host_pinned'):
            # Explicitly set to None for strategy free/host_pinned to account for any cached
            # task title from a previous non-free play
            self._last_task_name = None
        else:
            self._last_task_name = task.get_name().strip()

    def _banner(self, msg):
         if msg.startswith("Included"):
             return "\n{} | {:<}".format(time.strftime("%Y-%m-%d %H:%M:%S,%03d"),
                                         (msg + " ").ljust(60, '*'))
         else:
             return "\n{} | {:<}\n".format(time.strftime("%Y-%m-%d %H:%M:%S,%03d"),
                                           (msg + " ").ljust(60, '*'))

    def _print_task_details(self, result,
                           task_status=None,
                           delegated_vars=None,
                           loop_item=None,
                           ignore_errors=False):
        task = result._task
        task_tags = task.tags
        prefix = self._task_type_cache.get(task._uuid, 'TASK')

        # Use cached task name
        task_name = self._last_task_name
        if task_name is None:
            task_name = task.get_name().strip()

        # Get the current test case name or play name
        current_play = self._play_path
        if self._last_test_name:
            current_play = self._last_test_name
        elif self._play_name:
            current_play = self._play_name

        # Set task banner
        task_banner = self._banner("{} [{}][{}]".format(prefix, current_play, task_name))
        task_path = task.get_path()
        if task_path:
            task_banner += "task path: {}\n".format(task_path)

        task_details = ""
        # Print task banner if the task is changed
        if self._last_task_uuid != task._uuid:
            task_details += task_banner

            # Update last task uuid
            self._last_task_uuid = result._task._uuid

        # Log exception traceback
        if task_status == "failed":
           e_traceback = self._get_exception_traceback(result._result)
           if e_traceback:
               task_details += str(e_traceback)
               task_details += "\n"

        if delegated_vars:
            result_host = "[{} -> {}]".format(result._host.get_name(), delegated_vars['ansible_host'])
        else:
            result_host = "[{}]".format(result._host.get_name())

        log_failed_tasks = False
        # Log task result facts
        if task_status == "ok":
            task_details += "ok: {}".format(result_host)
        elif task_status == "changed":
            task_details += "changed: {}".format(result_host)
        elif task_status == "failed":
            if result._task.loop:
                task_details += "failed: {}".format(result_host)
            else:
                task_details += "fatal: {}: FAILED!".format(result_host)
            log_failed_tasks = True
        elif task_status == "unreachable":
            task_details += "fatal: {}: UNREACHABLE!".format(result_host)
            log_failed_tasks = True
        elif task_status == "skipped":
            task_details += "skipping: {}".format(result_host)
        else:
            task_details += result_host

        if result._task.loop:
            task_details += " => (item={})".format(loop_item)
            if result._task.ignore_errors:
                ignore_errors = True

        task_details += " => {}".format(self._dump_results(result._result, indent=4))

        if ignore_errors:
            task_details += "\n...ignoring"
            log_failed_tasks = False

        if 'known_issue' in str(task_tags) and 'msg' in result._result:
            self._display.display("TAGS: known_issue", color=C.COLOR_VERBOSE)
            log_header = ""
            if 'known_issue' not in self._play_tasks_cache:
                self._play_tasks_cache['known_issue'] = []
                log_header = self._banner("Known Issue in Play [{}]".format(current_play))
                self.write_to_logfile(self.known_issues_log, log_header)

            if task_path and task_path not in self._play_tasks_cache['known_issue']:
                self._play_tasks_cache['known_issue'].append(task_path)
                self.add_logger_file_handler(self.known_issues_log)

        # Add logger handler for failed tasks
        if log_failed_tasks:
            log_header = ""
            if 'failed' not in self._play_tasks_cache:
                self._play_tasks_cache['failed'] = []
                log_header = self._banner("Failed at Play [{}]".format(current_play))

            # If it is a failed item and not the first item, log its task name and path
            # in self.failed_tasks_log as well
            if task_path and task_path not in self._play_tasks_cache['failed']:
                self._play_tasks_cache['failed'].append(task_path)
                if task_path not in task_details:
                    log_header += task_banner

            if log_header:
                self.write_to_logfile(self.failed_tasks_log, log_header)

            # Extract error messages from task result and print it after task details
            result_in_json = json.loads(self._dump_results(result._result, indent=4))
            error_msg = extract_error_msg(result_in_json)
            task_details += "\nerror message:\n" + error_msg

            self.add_logger_file_handler(self.failed_tasks_log)

        self.logger.info(task_details)

        # Remove logger handler for known issues and failed tasks
        if 'known_issue' in str(task_tags) and 'msg' in result._result:
            self.remove_logger_file_handler(self.known_issues_log)

        if log_failed_tasks:
            self.remove_logger_file_handler(self.failed_tasks_log)

    def _get_testing_vars(self):
        if not self.testing_vars_file or not os.path.exists(self.testing_vars_file):
            self.logger.error("Failed to get testing vars file")
            return

        with open(self.testing_vars_file, 'r') as fd:
            self.testing_vars = yaml.load(fd, Loader=yaml.Loader)

    # Get all of test cases at play start and set status to "No Run"
    def _get_testcase_list(self):
        if not self.testing_testcase_file or not os.path.exists(self.testing_testcase_file):
            self.logger.error("Failed to get test cases file")
            return

        with open(self.testing_testcase_file, 'r') as fd:
            lines = yaml.load(fd, Loader=yaml.Loader)
            for line in lines:
                test_name = os.path.basename(line['import_playbook']).replace('.yml', '')
                self.testcases[test_name] = {"status":"No Run",
                                             "started_at": None,
                                             "finished_at": None,
                                             "duration": 0}

    def _get_play_path(self, play):
        path = ""
        if hasattr(play, "_ds") and hasattr(play._ds, "_data_source"):
            path = play._ds._data_source
        return path

    def write_to_logfile(self, log_file, msg):
        log_file_path = os.path.join(self.log_dir, log_file)
        msg = msg.encode('utf-8')
        with open(log_file_path, 'ab') as fd:
            fd.write(msg)
            fd.close()

    def _print_testbed_info(self):
        """
        Print testbed information as below:

        Testbed information:
        +-----------------------------------------------+--------------------------------------------+
        | Product | Version | Build    | Hostname or IP | Server Model                               |
        +-----------------------------------------------+--------------------------------------------+
        | vCenter | 7.0.2   | 17694817 | 192.168.10.10  |                                            | 
        +-----------------------------------------------+--------------------------------------------+
        | ESXi    | 7.0.2   | 17630552 | 192.168.10.11  | Dell Inc. PowerEdge R650                   |
        |         |         |          |                | Intel(R) Xeon(R) Silver 4314 CPU @ 2.40GHz |
        +-----------------------------------------------+--------------------------------------------+
        """

        if (self.testing_vars and
            not self.vcenter_info['hostname'] and
            'vcenter_hostname' in self.testing_vars and
            self.testing_vars['vcenter_hostname']):
            self.vcenter_info['hostname'] = self.testing_vars['vcenter_hostname']
        if (self.testing_vars and
            not self.esxi_info['hostname'] and
            'esxi_hostname' in self.testing_vars and
            self.testing_vars['esxi_hostname']):
            self.esxi_info['hostname'] = self.testing_vars['esxi_hostname']

        msg = "Testbed information:\n"
        if not self.vcenter_info['hostname'] and not self.esxi_info['hostname']:
            msg += "Not found vCenter or ESXi server information\n"
            self.logger.debug(msg)
            self._display.display(msg, color=C.COLOR_VERBOSE)
            return

        # Get version column width
        if self.esxi_info['update_version'] and \
           self.esxi_info['update_version'] != 'N/A' and \
           int(self.esxi_info['update_version']) > 0:
            self.esxi_info['version'] += " Update {}".format(self.esxi_info['update_version'])
        version_col_width = max([len('Version'), len(self.vcenter_info['version']), len(self.esxi_info['version'])])
        # Get build column width
        build_col_width = max([len('Build'), len(self.vcenter_info['build']), len(self.esxi_info['build'])])
        # Get hostname or IP column width
        hostname_col_width = max([len('Hostname or IP'), len(self.vcenter_info['hostname']), len(self.esxi_info['hostname'])])
        # Get server model column width
        server_model_col_width = max([len('Server Model'), len(self.esxi_info['model']), len(self.esxi_info['cpu_model'])])
        
        # Table width
        table_width = sum([9, version_col_width, build_col_width, hostname_col_width, server_model_col_width]) + 14

        row_border = "+{}+\n".format("".ljust(table_width - 2, "-"))
        row_format = "| {:<7} | {:<} | {:<} | {:<} | {:<} |\n"

        # Table head
        msg += row_border
        msg += row_format.format("Product",
                                 "Version".ljust(version_col_width),
                                 "Build".ljust(build_col_width),
                                 "Hostname or IP".ljust(hostname_col_width),
                                 "Server Model".ljust(server_model_col_width))
        msg += row_border

        # vCenter row
        if self.vcenter_info['hostname']:
            msg += row_format.format("vCenter",
                                     self.vcenter_info['version'].ljust(version_col_width),
                                     self.vcenter_info['build'].ljust(build_col_width),
                                     self.vcenter_info['hostname'].ljust(hostname_col_width),
                                     ''.ljust(server_model_col_width))
            msg += row_border

        # Server row
        if self.esxi_info['hostname']:
            msg += row_format.format("ESXi",
                                     self.esxi_info['version'].ljust(version_col_width),
                                     self.esxi_info['build'].ljust(build_col_width),
                                     self.esxi_info['hostname'].ljust(hostname_col_width),
                                     self.esxi_info['model'].ljust(server_model_col_width))
            if self.esxi_info['cpu_model']:
                msg += row_format.format('',
                                         ''.ljust(version_col_width),
                                         ''.ljust(build_col_width),
                                         ''.ljust(hostname_col_width),
                                         self.esxi_info['cpu_model'].ljust(server_model_col_width))
            msg += row_border

        msg += "\n"
        self.logger.info(msg)
        self._display.display(msg, color=C.COLOR_VERBOSE)


    def _print_test_results(self):
        """
        Print test results in a table as below

        Test Results (Total: 3, Failed: 1, No Run: 1, Elapsed Time: 00:18:42):
        +---------------------------------------------+
        | Name                 |   Status | Exec Time |
        +---------------------------------------------+
        | deploy_vm            | * No Run | 00:00:01  |
        +---------------------------------------------+
        | vgauth_check_service |   Passed | 00:03:02  |
        +---------------------------------------------+
        | gosc_cloudinit_dhcp  | * Failed | 00:12:58  |
        +---------------------------------------------+
        """

        total_exec_time = ""
        total_count = len(self.testcases)

        if self.started_at and self.finished_at:
            total_exec_time = int(self.finished_at - self.started_at)

        # No test run
        if total_count == 0:
            msg = "Test Results (Total: 0, Elapsed Time: {}):\n".format(time.strftime("%H:%M:%S", time.gmtime(total_exec_time)))
            self.logger.info(msg)
            self._display.display(msg, color=C.COLOR_VERBOSE)
            return

        # Get the column width
        name_col_width = max([len(testname) for testname in self.testcases.keys()])
        status_col_width = max([(len(test['status']) + 2)
                                if test['status'].lower() != "passed"
                                else len(test['status'])
                                for test in self.testcases.values()])

        status_mark = ""
        if status_col_width > len('passed'):
            status_mark = "  "

        row_border = "+{}+\n".format("".ljust(name_col_width + status_col_width + 17, "-"))
        row_format = "| {:<} | {:<} | {:<9} |\n"

        # Table head
        msg = row_border
        msg += row_format.format("Name".ljust(name_col_width), (status_mark + "Status").ljust(status_col_width), "Exec Time")
        msg += row_border

        # Table rows
        status_stats = OrderedDict([('Passed', 0), ('Failed', 0), ('Blocked', 0), ('Skipped', 0), ('No Run', 0)])
        for testname in self.testcases:
            test_exec_time = time.strftime('%H:%M:%S', time.gmtime(self.testcases[testname]['duration']))
            test_status = self.testcases[testname]['status']
            if test_status == 'Passed':
                msg += row_format.format(testname.ljust(name_col_width), \
                                        (status_mark + test_status).ljust(status_col_width), test_exec_time)
                status_stats[test_status] += 1
            else:
                msg += row_format.format(testname.ljust(name_col_width), \
                                         ("* " + test_status).ljust(status_col_width), test_exec_time)
                if test_status in ['Failed', 'Blocked', 'No Run']:
                    status_stats[test_status] += 1
                else:
                    status_stats['Skipped'] += 1

        msg += row_border

        # Test summary
        test_summary = "Test Results (Total: " + str(total_count)
        for key in status_stats:
             if status_stats[key] > 0:
                test_summary += ", {}: {}".format(key, status_stats[key])

        test_summary += ", Elapsed Time: {})\n".format(time.strftime("%H:%M:%S", time.gmtime(total_exec_time)))

        msg = test_summary + msg
        self.logger.info(msg)
        self._display.display(msg, color=C.COLOR_VERBOSE)

    def _print_os_release_info(self):
        """
        Print OS release information into a JSON file, which includes open-vm-tools version,
        cloud-init version, inbox drivers versions.
        """
        if self.os_release_info_file and os.path.exists(self.os_release_info_file):
            os_release_info_detail = None
            with open(self.os_release_info_file, 'r') as json_input:
                os_release_info_detail = json.load(json_input, object_pairs_hook=OrderedDict)

            # Update cloud-init version or open-vm-tools version in OS releas info
            if os_release_info_detail and len(os_release_info_detail) == 1:
                data_changed = False
                if self.os_cloudinit_version and 'cloud-init' not in os_release_info_detail[0]:
                   os_release_info_detail[0]['cloud-init'] = self.os_cloudinit_version
                   os_release_info_detail[0].move_to_end('cloud-init', last=False)
                   data_changed = True
                if self.os_ovt_version and 'open-vm-tools' not in os_release_info_detail[0]:
                   os_release_info_detail[0]['open-vm-tools'] = self.os_ovt_version
                   os_release_info_detail[0].move_to_end('open-vm-tools', last=False)
                   data_changed = True

                if data_changed:
                    os_release_info_detail[0].move_to_end('Release', last=False)
                    with open(self.os_release_info_file, 'w') as json_output:
                        json.dump(os_release_info_detail, json_output, indent=4)

    def _get_exception_traceback(self, result):
        if 'exception' in result:
            msg = "An exception occurred during task execution. "
            msg += "The full traceback is:\n" + str(result['exception'])
            del result['exception']
            return msg

    def v2_runner_on_failed(self, result, ignore_errors=False):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._clean_results(result._result, result._task.action)

        if not ignore_errors and \
           self._last_test_name in self.testcases and \
           self.testcases[self._last_test_name]['status'] == 'Running':
            if 'reason: Blocked' in result._task.name:
                self.testcases[self._last_test_name]['status'] = 'Blocked'
            else:
                self.testcases[self._last_test_name]['status'] = 'Failed'
            self.testcases[self._last_test_name]['finished_at'] = time.time()
            self.testcases[self._last_test_name]['duration'] = int(self.testcases[self._last_test_name]['finished_at'] -
                                                                   self.testcases[self._last_test_name]['started_at'])
            self.write_to_logfile(self.test_results_yml,
                                  "{}: {}\n".format(self._last_test_name, self.testcases[self._last_test_name]['status']))

        if result._task.loop and 'results' in result._result:
            self._process_items(result)
            return

        self._print_task_details(result, 'failed', delegated_vars, ignore_errors=ignore_errors)


    def v2_runner_on_ok(self, result):
        task = result._task
        if isinstance(task, TaskInclude):
            return

        task_result = result._result
        task_args = task.args
        task_file = os.path.basename(task.get_path()).split(':')[0].strip()
        delegated_vars = task_result.get('_ansible_delegated_vars', None)

        if result._task.loop and 'results' in result._result:
            self._process_items(result)
            return

        self._clean_results(result._result, result._task.action)
        if task_result.get('changed', False):
            self._print_task_details(result, "changed", delegated_vars)
        else:
            self._print_task_details(result, "ok", delegated_vars)

        if str(task.action) == "ansible.builtin.set_fact":
            set_fact_result = task_result.get('ansible_facts', None)
            if set_fact_result:
                # Update deploy_vm test case name if deploy_casename is set
                if self._last_test_name and self._last_test_name.startswith("deploy"):
                    deploy_casename = set_fact_result.get("deploy_casename", None)
                    if self._last_test_name in self.testcases and deploy_casename:
                        old_test_name = self._last_test_name
                        self._last_test_name = deploy_casename
                        self.testcases[self._last_test_name] = self.testcases[old_test_name]
                        del self.testcases[old_test_name]
                        self.testcases.move_to_end(self._last_test_name, last=False)
                if "get_windows_system_info.yml" == task_file or "get_linux_system_info.yml" == task_file:
                    vm_guest_os_distribution = set_fact_result.get("vm_guest_os_distribution", None)
                    if vm_guest_os_distribution and self.vm_info:
                        self.vm_info.Guest_OS_Distribution = vm_guest_os_distribution
                if "vm_get_vm_info.yml" == task_file:
                   if self.vm_info:
                       self.vm_info.Config_Guest_Id = set_fact_result.get("vm_guest_id", '')
                       self.vm_info.Hardware_Version = set_fact_result.get("vm_hardware_version", '')
                if "vm_upgrade_hardware_version.yml" == task_file:
                   if self.vm_info:
                       self.vm_info.Hardware_Version = set_fact_result.get("vm_hardware_version", '')
                if "vm_get_guest_info.yml" == task_file:
                   if self.vm_info:
                       self.vm_info.GuestInfo_Guest_Id = set_fact_result.get("guestinfo_guest_id", '')
                       self.vm_info.GuestInfo_Guest_Full_Name = set_fact_result.get("guestinfo_guest_full_name", '')
                       self.vm_info.GuestInfo_Guest_Family = set_fact_result.get("guestinfo_guest_family", '')
                       self.vm_info.GuestInfo_Detailed_Data = set_fact_result.get("guestinfo_detailed_data", '')
                       self.vm_info.VMTools_Version = set_fact_result.get("guestinfo_vmtools_info", '')
                if "check_guest_os_gui.yml" == task_file:
                   if self.vm_info:
                       self.vm_info.GUI_Installed = str(set_fact_result.get("guest_os_with_gui", ''))

        elif str(task.action) == "ansible.builtin.debug":
            if "skip_test_case.yml" == task_file and "Skip testcase:" in task.name:
                [test_name, test_result] = task.name.split(',')
                test_name = test_name.split(':')[-1].strip()
                test_result = test_result.split(':')[-1].strip()
                if test_name in self.testcases:
                    self.testcases[test_name]['status'] = test_result
                    self.testcases[test_name]['finished_at'] = time.time()
                    self.testcases[test_name]['duration'] = int(self.testcases[test_name]['finished_at'] -
                                                                self.testcases[test_name]['started_at'])
                    self.write_to_logfile(self.test_results_yml,
                                          "{}: {}\n".format(self._last_test_name, self.testcases[self._last_test_name]['status']))
            elif 'var' in task_args:
                debug_var_name = str(task_args['var'])
                debug_var_value = str(task_result[debug_var_name])
                if not self.testrun_log_dir and debug_var_name == 'testrun_log_path':
                    self.testrun_log_dir = debug_var_value
                if "check_inbox_driver.yml" == task_file:
                    if debug_var_name == "os_release_info_file_path":
                        self.os_release_info_file = debug_var_value
                if "deploy_vm.yml" == task_file:
                    if debug_var_name == "vm_guest_ip" and self.vm_info and not self.vm_info.IP:
                        self.vm_info.IP = debug_var_value
                if "test_setup.yml" == task_file:
                    if debug_var_name == "vm_guest_ip" and self.vm_info and not self.vm_info.IP:
                        self.vm_info.IP = debug_var_value
                if ("get_guest_ovt_version_build.yml" == task_file or
                   "win_get_vmtools_version_build.yml" == task_file):
                    if debug_var_name ==  "vmtools_info_from_vmtoolsd" and debug_var_value:
                        if "get_guest_ovt_version_build.yml" == task_file and not self.os_ovt_version:
                            self.os_ovt_version = debug_var_value
                        if (self.vm_info and
                            (not self.vm_info.VMTools_Version or
                             self.vm_info.VMTools_Version != debug_var_value)):
                            self.vm_info.VMTools_Version = debug_var_value
                if "esxi_get_version_build.yml" == task_file:
                    if not self.esxi_info['hostname'] and debug_var_name == "esxi_hostname":
                        self.esxi_info['hostname'] = debug_var_value
                    if not self.esxi_info['version'] and debug_var_name == "esxi_version":
                        self.esxi_info['version'] = debug_var_value
                    if not self.esxi_info['build'] and debug_var_name == "esxi_build":
                        self.esxi_info['build'] = debug_var_value
                    if not self.esxi_info['update_version'] and debug_var_name == "esxi_update_version":
                        self.esxi_info['update_version'] = debug_var_value
                if "esxi_get_model.yml" == task_file:
                    if not self.esxi_info['model'] and debug_var_name == "esxi_model_info":
                        self.esxi_info['model'] = debug_var_value
                    if not self.esxi_info['cpu_model'] and debug_var_name == "esxi_cpu_model_info":
                        self.esxi_info['cpu_model'] = debug_var_value
                if "vcenter_get_version_build.yml" == task_file:
                    if not self.vcenter_info['hostname'] and debug_var_name == "vcenter_hostname":
                        self.vcenter_info['hostname'] = debug_var_value
                    if not self.vcenter_info['version'] and debug_var_name == "vcenter_version":
                        self.vcenter_info['version'] = debug_var_value
                    if not self.vcenter_info['build'] and debug_var_name == "vcenter_build":
                        self.vcenter_info['build'] = debug_var_value
                if "cloudinit_pkg_check.yml" == task_file and debug_var_name == "cloudinit_version":
                    if self.vm_info and not self.vm_info.CloudInit_Version:
                        self.vm_info.CloudInit_Version = debug_var_value
                    if not self.os_cloudinit_version:
                        self.os_cloudinit_version = debug_var_value

    def v2_runner_on_skipped(self, result):
        self._clean_results(result._result, result._task.action)
        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            self._print_task_details(result, "skipped")

    def v2_runner_on_unreachable(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._print_task_details(result, "unreachable", delegated_vars)

        if self._last_test_name in self.testcases and \
           self.testcases[self._last_test_name]['status'] == 'Running':
            self.testcases[self._last_test_name]['status'] = 'Failed'
            self.testcases[self._last_test_name]['finished_at'] = time.time()
            self.testcases[self._last_test_name]['duration'] = int(self.testcases[self._last_test_name]['finished_at'] -
                                                                   self.testcases[self._last_test_name]['started_at'])
            self.write_to_logfile(self.test_results_yml,
                                  "{}: {}\n".format(self._last_test_name, self.testcases[self._last_test_name]['status']))

    def v2_runner_retry(self, result):
        task_name = result.task_name or result._task
        msg = "FAILED - RETRYING: {} ({} retries left).".format(task_name, result._result['retries'] - result._result['attempts'])
        msg += "Result was: %s" % self._dump_results(result._result, indent=4)
        self.logger.debug(msg)

    def v2_runner_item_on_ok(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        if isinstance(result._task, TaskInclude):
            return

        self._clean_results(result._result, result._task.action)
        if result._result.get('changed', False):
            self._print_task_details(result, "changed", delegated_vars, loop_item=self._get_item_label(result._result))
        else:
            self._print_task_details(result, "ok", delegated_vars, loop_item=self._get_item_label(result._result))

    def v2_runner_item_on_failed(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._clean_results(result._result, result._task.action)
        self._print_task_details(result, "failed", delegated_vars, loop_item=self._get_item_label(result._result))

    def v2_runner_item_on_skipped(self, result):
        self._clean_results(result._result, result._task.action)
        self._print_task_details(result, "skipped", loop_item=self._get_item_label(result._result))

    def v2_playbook_on_start(self, playbook):
        playbook_path = os.path.realpath(playbook._file_name)
        self.started_at = time.time()

        # Parse extra vars
        extra_vars = {}
        if context.CLIARGS and context.CLIARGS['extra_vars']:
            for extra_vars_str in context.CLIARGS['extra_vars']:
                if extra_vars_str:
                    #extra_var_str is tuple
                    extra_vars_list = extra_vars_str.split()
                    for extra_vars_item in extra_vars_list:
                        if extra_vars_item.find("=") != -1:
                            extra_vars[extra_vars_item.split("=")[0].strip()] = extra_vars_item.split("=")[1].strip()

        #Use user-defined testing vars file
        if 'testing_vars_file' in extra_vars.keys():
            self.testing_vars_file = extra_vars['testing_vars_file']
        else:
            #Use default testing vars file
            self.testing_vars_file = os.path.join(self.cwd, "vars/test.yml")

        self._get_testing_vars()

        if 'main.yml' in os.path.basename(playbook_path):
            #Use user-defined testcase file
            if 'testing_testcase_file' in extra_vars.keys():
                self.testing_testcase_file = extra_vars['testing_testcase_file']
            else:
                #Use default testing vars file
                self.testing_testcase_file = os.path.join(self.cwd, "linux/gosv_testcase_list.yml")

            self._get_testcase_list()

        if (self.testing_vars and
            'vm_name' in self.testing_vars and
            self.testing_vars['vm_name']):
            self.vm_info = VmInfo(self.testing_vars['vm_name'])

        self.add_logger_file_handler(self.full_debug_log)
        msg = self._banner("PLAYBOOK: {}".format(playbook_path))
        msg += "Positional arguments: {}\n".format(' '.join(context.CLIARGS['args']))
        msg += "Tesing vars file: {}\n".format(self.testing_vars_file)
        msg += "Tesing testcase file: {}\n".format(self.testing_testcase_file)
        msg += "Playbook dir: {}\n".format(self.cwd)
        msg += "Plugin dir: {}\n".format(self.plugin_dir)
        msg += "Log dir: {}".format(self.log_dir)
        self.logger.info(msg)
        self._display.display(msg, color=C.COLOR_VERBOSE)

    def v2_playbook_on_play_start(self, play):
        self._play_name = play.get_name()
        self._play_path = self._get_play_path(play)

        # Update the previous test case result
        if (self._last_test_name and
           self._last_test_name in self.testcases and
           self.testcases[self._last_test_name]['status'] == 'Running'):
            self.testcases[self._last_test_name]['status'] = 'Passed'
            self.testcases[self._last_test_name]['finished_at'] = time.time()
            self.testcases[self._last_test_name]['duration'] = int(self.testcases[self._last_test_name]['finished_at'] -
                                                                   self.testcases[self._last_test_name]['started_at'])
            self.write_to_logfile(self.test_results_yml,
                                  "{}: {}\n".format(self._last_test_name, self.testcases[self._last_test_name]['status']))

        if self._play_name:
            msg = self._banner("PLAY [{}]".format(self._play_name))
        else:
            msg = self._banner("PLAY")

        if self._play_path:
            msg += "play path: {}".format(self._play_path)

        self.logger.info(msg)

        self.play = play

        # Clear play tasks cache
        self._play_tasks_cache.clear()

        # Update testcase status to Running and set its start time
        if self._play_name and self._play_name in self.testcases:
            self.testcases[self._play_name]["status"] = "Running"
            self.testcases[self._play_name]["started_at"] = time.time()
            self._last_test_name = self._play_name

    def v2_playbook_on_stats(self, stats):
        self.finished_at = time.time()

        # Update the last testcase status
        if self._last_test_name and \
           self._last_test_name != self._play_name and \
           self._last_test_name in self.testcases and \
           self.testcases[self._last_test_name]['status'] == 'Running':
            self.testcases[self._last_test_name]['status'] = 'Passed'
            self.testcases[self._last_test_name]['finished_at'] = time.time()
            self.testcases[self._last_test_name]['duration'] = int(self.testcases[self._last_test_name]['finished_at'] -
                                                                   self.testcases[self._last_test_name]['started_at'])
            self.write_to_logfile(self.test_results_yml,
                                  "{}: {}\n".format(self._last_test_name, self.testcases[self._last_test_name]['status']))

        # Log play stats
        msg = self._banner("PLAY RECAP")
        hosts = sorted(stats.processed.keys())
        for h in hosts:
            t = stats.summarize(h)
            msg += "{:<30} :".format(h)
            msg += "  ok={}".format(t['ok'])
            msg += "  changed={}".format(t['changed'])
            msg += "  unreachable={}".format(t['unreachable'])
            msg += "  failed={}".format(t['failures'])
            msg += "  skipped={}".format(t['skipped'])
            msg += "  rescued={}".format(t['rescued'])
            msg += "  ignored={}".format(t['ignored'])

        self.logger.info(msg)

        # Log testcases results
        self._print_os_release_info()

        # Only print test summary when there is test case
        if len(self.testcases) > 0:
            self._display.banner("TEST SUMMARY")
            self.logger.info(self._banner("TEST SUMMARY"))
            self.add_logger_file_handler(self.test_results_log)
            self._print_testbed_info()

            # Print VM information
            if self.vm_info:
                vm_info_str = str(self.vm_info)
            else:
                vm_info_str = "Not found VM information"

            self.logger.info(vm_info_str)
            self._display.display(vm_info_str, color=C.COLOR_VERBOSE)

            self._print_test_results()
            self.remove_logger_file_handler(self.test_results_log)

        if self.testrun_log_dir and self.log_dir != self.testrun_log_dir:
            os.system("cp -rf {}/* {}".format(self.log_dir, self.testrun_log_dir))
            os.unlink(self.current_log_dir)
            os.system("rm -rf {}".format(self.log_dir))
            os.symlink(self.testrun_log_dir, self.current_log_dir, target_is_directory=True)

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._task_start(task, prefix='TASK')

    def v2_playbook_on_include(self, included_file):
        msg = self._banner('Included: {} for {}'.format(included_file._filename, ", ".join([h.name for h in included_file._hosts])))
        label = self._get_item_label(included_file._vars)
        if label:
            msg += " => (item={})".format(label)
        self.logger.info(msg)

    def v2_playbook_on_import_for_host(self, result, imported_file):
        msg = self._banner('Imported: {} for {}'.format(imported_file._filename, ", ".join([h.name for h in imported_file._hosts])))
        label = self._get_item_label(imported_file._vars)
        if label:
            msg += " => (item={})".format(label)
        self.logger.info(msg)
