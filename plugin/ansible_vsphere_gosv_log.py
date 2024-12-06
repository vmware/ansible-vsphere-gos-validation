# Copyright 2021-2024 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
""" Ansible vSphere GOS Validation Log Plugin """
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import os
import time
import json
import sys
import importlib
import shutil
import logging
import yaml
import re
from collections import OrderedDict
from textwrap import TextWrapper
from ansible import context
from ansible import constants as C
from ansible.playbook.task_include import TaskInclude
from ansible.plugins.callback import CallbackBase

DOCUMENTATION = '''
    name: ansible_vsphere_gosv_log
    type: notification
    short_description: Write Ansible output and test results to log files
    description:
      - This callback writes detail running log and test results to log file.
'''

if sys.version_info.major == 2:
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    importlib.reload(sys)

def extract_error_msg(json_obj):
    """
    Extract error message from task result
    """
    message = ''
    try:
        for key, value in json_obj.items():
            if key != 'msg':
                continue

            if isinstance(value, str):
                message += value.strip()
                # Extract stderr or stdout from command output when rc != 0
                if 'non-zero return code' in value:
                    if str(json_obj.get('rc','')):
                        message += ': ' + str(json_obj['rc'])
                    if len(json_obj.get('stderr_lines', [])) > 0:
                        message += '\n' + '\n'.join(list(filter(None, json_obj['stderr_lines']))).strip()
                    if len(json_obj.get('stdout_lines', [])) > 0:
                        message += '\n' + '\n'.join(list(filter(None, json_obj['stdout_lines']))).strip()
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

    except TypeError as type_error:
        print("Failed to extract msg from below text as it is not in json format.\n" + str(type_error))

    return message

class vSphereInfo(object):
    def __init__(self, product, hostname):
        self.product = product
        self.hostname = hostname
        self.version = ''
        self.build = ''
        self.model = ''
        self.cpu_model = ''
        self.cpu_codename = ''

    def __str__(self):
        info = {'hostname': self.hostname,
                'version': self.version,
                'build': self.build}
        if self.product.lower() == 'esxi':
            info['model'] = self.model
            info['cpu_model'] = self.cpu_model
            info['cpu_codename'] = self.cpu_codename
        return json.dumps(info, indent=4)

    def update_property(self, p_name, p_value):
        setattr(self, p_name, p_value)

class TestbedInfo(object):
    def __init__(self, vcenter_hostname, esxi_hostname,
                 ansible_gosv_facts):
        """
        Initialize vCenter and ESXi server info with ansible facts
        :param vcenter_hostname:
        :param esxi_hostname:
        :param ansible_gosv_facts:
        """
        self.vcenter_info = vSphereInfo('vCenter', vcenter_hostname)
        self.esxi_info = vSphereInfo('ESXi', esxi_hostname)
        self.set_vcenter_info(ansible_gosv_facts)
        self.set_esxi_info(ansible_gosv_facts)

    def set_vcenter_info(self, ansible_gosv_facts=None):
        """
        Update vCenter server info with ansible facts
        :param ansible_gosv_facts:
        :return:
        """
        if ansible_gosv_facts:
            self.vcenter_info.update_property('version',
                                              ansible_gosv_facts.get('vcenter_version', ''))
            self.vcenter_info.update_property('build',
                                              ansible_gosv_facts.get('vcenter_build', ''))

    def set_esxi_info(self, ansible_gosv_facts=None):
        """
        Update ESXi server info with ansible facts
        :param ansible_gosv_facts:
        :return:
        """
        if ansible_gosv_facts:
            esxi_version = ansible_gosv_facts.get('esxi_version', '')
            esxi_update_version = ansible_gosv_facts.get('esxi_update_version', '')
            if esxi_version and esxi_update_version and esxi_update_version != 'N/A':
                esxi_version += ' U' + esxi_update_version
            self.esxi_info.update_property('version', esxi_version)
            self.esxi_info.update_property('build',
                                           ansible_gosv_facts.get('esxi_build', ''))
            self.esxi_info.update_property('model',
                                           ansible_gosv_facts.get('esxi_model_info', ''))
            self.esxi_info.update_property('cpu_model',
                                           ansible_gosv_facts.get('esxi_cpu_model_info', ''))
            self.esxi_info.update_property('cpu_codename',
                                           ansible_gosv_facts.get('esxi_cpu_code_name', ''))

    def __str__(self):
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
        msg = "Testbed information:\n"
        if ((not self.vcenter_info or not self.vcenter_info.hostname) and
             (not self.esxi_info or not self.esxi_info.hostname)):
            msg += "Not found vCenter or ESXi server information\n"
            return msg

        # Get version column width
        version_col_width = max([len('Version'), len(self.vcenter_info.version), len(self.esxi_info.version)])
        # Get build column width
        build_col_width = max([len('Build'), len(self.vcenter_info.build), len(self.esxi_info.build)])
        # Get hostname or IP column width
        hostname_col_width = max(
            [len('Hostname or IP'), len(self.vcenter_info.hostname), len(self.esxi_info.hostname)])
        # Get server model column width
        esxi_cpu_detail = self.esxi_info.cpu_model
        if self.esxi_info.cpu_codename:
           esxi_cpu_detail += f" ({self.esxi_info.cpu_codename})"

        server_model_col_width = max(
            [len('Server Model'), len(self.esxi_info.model), len(esxi_cpu_detail)])

        # Table width
        table_width = sum([9, version_col_width, build_col_width,
                           hostname_col_width, server_model_col_width]) + 14

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
        if self.vcenter_info.hostname:
            msg += row_format.format("vCenter",
                                     self.vcenter_info.version.ljust(version_col_width),
                                     self.vcenter_info.build.ljust(build_col_width),
                                     self.vcenter_info.hostname.ljust(hostname_col_width),
                                     ''.ljust(server_model_col_width))
            msg += row_border

        # Server row
        if self.esxi_info.hostname:
            msg += row_format.format("ESXi",
                                     self.esxi_info.version.ljust(version_col_width),
                                     self.esxi_info.build.ljust(build_col_width),
                                     self.esxi_info.hostname.ljust(hostname_col_width),
                                     self.esxi_info.model.ljust(server_model_col_width))
            if esxi_cpu_detail:
                msg += row_format.format('',
                                         ''.ljust(version_col_width),
                                         ''.ljust(build_col_width),
                                         ''.ljust(hostname_col_width),
                                         esxi_cpu_detail.ljust(server_model_col_width))
            msg += row_border

        msg += "\n"
        return msg

class VmGuestInfo(object):
    def __init__(self, ansible_gosv_facts={}):
        """
        Initialize VM guest info with ansible facts
        :param ansible_gosv_facts:
        """
        self.Guest_OS_Distribution = ansible_gosv_facts.get('vm_guest_os_distribution', '')
        self.ESXi_Version = ansible_gosv_facts.get('esxi_version', '')
        if (self.ESXi_Version and
                ansible_gosv_facts.get('esxi_update_version', '') and
                ansible_gosv_facts['esxi_update_version'] != 'N/A'):
            self.ESXi_Version += ' U' + ansible_gosv_facts['esxi_update_version']
        self.ESXi_Build = ansible_gosv_facts.get('esxi_build', '')
        self.Hardware_Version = ansible_gosv_facts.get('vm_hardware_version','')
        self.VMTools_Version = ansible_gosv_facts.get('guestinfo_vmtools_info', '')
        self.Config_Guest_Id = ansible_gosv_facts.get('vm_guest_id', '')
        self.Guest_Short_Name = ansible_gosv_facts.get('guest_short_name', None)
        self.GuestInfo_Guest_Id = ansible_gosv_facts.get('guestinfo_guest_id', '')
        self.GuestInfo_Guest_Full_Name = ansible_gosv_facts.get('guestinfo_guest_full_name', '')
        self.GuestInfo_Guest_Family = ansible_gosv_facts.get('guestinfo_guest_family', '')
        self.GuestInfo_Detailed_Data = ansible_gosv_facts.get('guestinfo_detailed_data', '')

    def __str__(self):
        """
        Convert guest info into a json formatted string
        """
        guestinfo_in_dict = OrderedDict()
        for attr_name, attr_value in vars(self).items():
            if not attr_name.startswith('__') and attr_value is not None:
                guestinfo_in_dict[attr_name] = attr_value
        return json.dumps(guestinfo_in_dict, indent=4)

class VmDetailInfo(VmGuestInfo):
    def __init__(self, vm_name, ansible_gosv_facts):
        self.Name = vm_name
        if vm_name:
            if not ansible_gosv_facts or not isinstance(ansible_gosv_facts, dict):
                ansible_gosv_facts = {}

            self.Guest_OS_Distribution = ansible_gosv_facts.get('vm_guest_os_distribution', '')
            self.IP = ansible_gosv_facts.get('vm_guest_ip', '')
            self.GUI_Installed = str(ansible_gosv_facts.get('guest_os_with_gui', ''))
            self.CloudInit_Version = ansible_gosv_facts.get('cloudinit_version', '')
            super().__init__(ansible_gosv_facts)

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
        | CloudInit Version         | 20.4.1                            |
        +---------------------------------------------------------------+
        | GUI Installed             | False                             |
        +---------------------------------------------------------------+
        | Hardware Version          | vmx-19                            |
        +---------------------------------------------------------------+
        | VMTools Version           | 11.2.5.26209 (build-17337674)     |
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
        if not self.Name:
            msg += "Not found VM information\n"
            return msg

        wrap_width = 80
        wrapped_vm_info = {}
        # Get column width
        head_col_width = 0
        info_col_width = 0
        for attr_name, attr_value in vars(self).items():
            if not attr_name.startswith('__') and not attr_name.startswith('ESXi') and attr_value is not None:
                head_col_width = max([head_col_width, len(attr_name)])
                if len(str(attr_value)) > wrap_width:
                    if attr_name == 'GuestInfo_Detailed_Data':
                        wrapped_vm_info[attr_name] = self.GuestInfo_Detailed_Data.replace("' ", "'\n").split('\n')
                    else:
                        textwrap = TextWrapper(width=wrap_width)
                        wrapped_vm_info[attr_name] = textwrap.wrap(attr_value)
                elif (attr_name in ['CloudInit_Version', 'GUI_Installed'] and
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

class TestRun(object):
    """
    Data about an individual test case run
    """

    def __init__(self, test_id, test_name):
        self.id = test_id
        self.name = test_name
        self.status = "No Run"
        self.start_time = None
        self.duration = 0
    def __str__(self):
        return str({"id": self.id,
                    "name": self.name,
                    "status": self.status,
                    "start_time": self.start_time,
                    "duration": self.duration})

    def start(self):
        self.start_time = time.time()
        self.status = "Running"
        # print("DEBUG: Test {} is started.".format(self.id))

    def complete(self, status):
        self.duration = int(time.time() - self.start_time)
        self.status = status
        # print("DEBUG: Test {} is completed, result is {}.".format(self.id, self.status))

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
        self.testcases_count = 0
        self.test_runs = OrderedDict()
        self.not_completed_testcases = []

        self._ansible_gosv_facts = {}

        self.start_time = None
        self.end_time = None

        self.plugin_dir = os.path.dirname(os.path.realpath(__file__))
        self.cwd = os.path.dirname(self.plugin_dir)
        self.log_dir = None
        self.current_log_dir = None
        self.full_debug_log = "full_debug.log"
        self.failed_tasks_log = "failed_tasks.log"
        self.known_issues_log = "known_issues.log"
        self.test_results_log = "results.log"
        self.guest_info_json_file = "guest_info.json"
        self.collected_guest_info = {}

        # Testing vars file and testcase list file
        self.testing_vars_file = None
        self.testing_testcase_file = None
        self.testing_vars = {}

        # The play name and path of current playbook
        self._play_name = None
        self._play_path = None

        # The last test case id, composed by <index>_<test_case_name>
        self._last_test_id = None

        # A tasks cache of current play
        self._play_tasks_cache = {}
        self._last_task_uuid = None
        self._last_task_name = None
        self._task_type_cache = {}

        # Set logger
        self.logger_name = "ansible-vsphere-gos-validation"
        self.logger = logging.getLogger(self.logger_name)
        self.logger.setLevel(logging.DEBUG)

        msg = self._banner("PLUGIN [{}]".format(os.path.realpath(__file__)))
        msg += "Project directory: "  + self.cwd
        msg += "\nPlugin directory: "  + self.plugin_dir
        self._display.display(msg, color=C.COLOR_DEBUG)

    def add_logger_file_handler(self, log_file=None):
        """
        Add a file handler to logger with debug level
        """
        if not log_file:
            return

        log_file_path = os.path.join(self.log_dir, log_file)

        for lh in self.logger.handlers:
            if (isinstance(lh, logging.FileHandler) and
                    os.path.realpath(log_file_path) == lh.baseFilename):
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
            if (isinstance(lh, logging.FileHandler) and
                    os.path.realpath(log_file_path) == lh.baseFilename):
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
        formatted_msg = "\n{} | {:<}".format(time.strftime("%Y-%m-%d %H:%M:%S,%03d"),
                                             (msg + " ").ljust(60, '*'))
        if not msg.startswith("Included"):
            formatted_msg += "\n"

        return formatted_msg

    def _print_task_details(self, result,
                            task_status=None,
                            delegated_vars=None,
                            loop_item=None,
                            ignore_errors=False):
        task = result._task
        prefix = self._task_type_cache.get(task._uuid, 'TASK')

        # Use cached task name
        task_name = self._last_task_name
        if task_name is None:
            task_name = task.get_name().strip()

        # Get the current test case name or play name
        current_play = self._play_path
        if self._last_test_id:
            current_play = self._last_test_id
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

        if 'include_vars' in str(task.action):
            # update testing vars with include_vars
            self.testing_vars.update(result._result.get('ansible_facts', {}))

        if ignore_errors:
            task_details += "\n...ignoring"
            log_failed_tasks = False

        if 'known_issue' in task.tags and 'msg' in result._result:
            self._display.display("TAGS: known_issue", color=C.COLOR_WARN)
            log_header = ""
            if 'known_issue' not in self._play_tasks_cache:
                self._play_tasks_cache['known_issue'] = []
                log_header = self._banner("Known Issue in Play [{}]".format(current_play))
                self.write_to_logfile(self.known_issues_log, log_header)

            if task_path and task_path not in self._play_tasks_cache['known_issue']:
                self._play_tasks_cache['known_issue'].append(task_path)
                self.add_logger_file_handler(self.known_issues_log)

        if 'fail_message' in task.tags and 'msg' in result._result:
            self._display.display("TAGS: fail_message", color=C.COLOR_WARN)
            log_failed_tasks = True

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
        if 'known_issue' in task.tags and 'msg' in result._result:
            self.remove_logger_file_handler(self.known_issues_log)

        if log_failed_tasks:
            self.remove_logger_file_handler(self.failed_tasks_log)

    def _load_testing_vars(self, play):
        # Update testing vars with play vars
        play_vars = play.get_vars()
        if play_vars:
            self.testing_vars.update(play_vars)

        # Update testing vars with play vars files
        play_vars_files = play.get_vars_files()
        play_path = self._get_play_path(play)
        if play_vars_files:
            for vars_file in play_vars_files:
                if 'testing_vars_file' in vars_file:
                    # Update testing vars with testing_vars_file
                    if self.testing_vars_file and os.path.exists(self.testing_vars_file):
                        with open(self.testing_vars_file, 'r') as fd:
                            self.testing_vars.update(yaml.load(fd, Loader=yaml.Loader))
                else:
                    vars_file_path = os.path.join(os.path.dirname(play_path), vars_file)
                    if os.path.exists(vars_file_path):
                        with open(vars_file_path, 'r') as fd:
                            self.testing_vars.update(yaml.load(fd, Loader=yaml.Loader))

    # Get all of test cases at play start and set status to "No Run"
    def _get_testcase_list(self, testcase_file_path):
        if not testcase_file_path or not os.path.exists(testcase_file_path):
            self.logger.error("Test cases file {} doesn't exist".format(testcase_file_path))
            return

        with open(testcase_file_path, 'r') as fd:
            playbooks = yaml.load(fd, Loader=yaml.Loader)
            self.testcases_count = len(playbooks)
            for index, playbook in enumerate(playbooks):
                test_name = os.path.basename(playbook['import_playbook']).replace('.yml', '')
                test_id = "{}_{}".format(str(index+1).rjust(len(str(self.testcases_count)), '0'), test_name)
                # print("DEBUG: Get test id: {}".format(test_id))
                self.test_runs[test_id] = TestRun(test_id, test_name)
                self.not_completed_testcases.append(test_name)

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

    def _print_test_results(self):
        """
        Print test results in a table as below

        Test Results (Total: 30, Passed: 27, Skipped: 3, Elapsed Time: 02:22:32)
        +-------------------------------------------------------------------------+
        | ID | Name                                 |   Status        | Exec Time |
        +-------------------------------------------------------------------------+
        | 01 | deploy_vm_efi_paravirtual_vmxnet3    |   Passed        | 00:22:03  |
        | 02 | check_inbox_driver                   |   Passed        | 00:01:17  |
        | 03 | ovt_verify_pkg_install               |   Passed        | 00:26:03  |
        | .. | ...                                  |   ...           | ...       |
        | 30 | ovt_verify_pkg_uninstall             |   Passed        | 00:02:09  |
        +-------------------------------------------------------------------------+
        """
        total_exec_time = ""
        total_count = len(self.test_runs)

        if self.start_time and self.end_time:
            total_exec_time = int(self.end_time - self.start_time)

        # No test run
        if total_count == 0:
            msg = "Test Results (Total: 0, Elapsed Time: {}):\n".format(
                time.strftime("%H:%M:%S", time.gmtime(total_exec_time)))
            self.logger.info(msg)
            self._display.display(msg, color=C.COLOR_VERBOSE)
            return

        # Block test cases when deploy_vm or installing tools failed
        testcase_blocked = False
        if self._play_name == 'env_setup':
            # Test cases are blocked by env_setup failure
            testcase_blocked = True

        blocker_pattern = r'deploy_vm|ovt_verify_.*_install|wintools_complete_install_verify'
        for test_id in self.test_runs:
            if (self.test_runs[test_id].status in ['Failed', 'Blocked'] and
                re.search(blocker_pattern, self.test_runs[test_id].name)):
                testcase_blocked = True
                continue

            # For test cases after blocker, set their status to 'Blocked'
            if testcase_blocked and self.test_runs[test_id].status == 'No Run':
                self.test_runs[test_id].status = 'Blocked'


        # Get the column width
        idx_col_width = max([len(str(total_count)), 2])
        name_col_width = max([len(test_result.name) for test_result in self.test_runs.values()])
        status_col_width = max([(len(test_result.status) + 2)
                                if test_result.status != "Passed"
                                else len(test_result.status)
                                for test_result in self.test_runs.values()])

        status_mark = ""
        if status_col_width > len('passed'):
            status_mark = "  "

        row_border = "+{}+\n".format("".ljust(idx_col_width + name_col_width + status_col_width + 20, "-"))
        row_format = "| {:<} | {:<} | {:<} | {:<9} |\n"

        # Table head
        msg = row_border
        msg += row_format.format("ID",
                                 "Name".ljust(name_col_width),
                                 (status_mark + "Status").ljust(status_col_width),
                                 "Exec Time")
        msg += row_border

        # Set align character for test case index
        if len(str(total_count)) == 1:
            align_char = ' '
        else:
            align_char = '0'

        # Table rows
        status_stats = OrderedDict([('Passed', 0), ('Failed', 0), ('Blocked', 0), ('Skipped', 0), ('No Run', 0)])
        test_idx = 0
        for test_id in self.test_runs:
            test_result = self.test_runs[test_id]
            if (str(self.testing_vars.get('new_vm', False)).lower() == 'true' and
                test_result.name == 'deploy_vm'):
                # Update deploy_vm test case name
                if self.testing_vars.get('vm_deploy_method', '').lower() == 'ova':
                    if self.testing_testcase_file and 'windows' in self.testing_testcase_file:
                        test_result.name = 'deploy_vm_ovf'
                    else:
                        test_result.name = 'deploy_vm_ova'

                elif (self.testing_vars.get('boot_disk_controller') and
                      self.testing_vars.get('firmware') and
                      self.testing_vars.get('network_adapter_type')):
                    test_result.name = "deploy_vm_{}_{}_{}".format(self.testing_vars['firmware'].lower(),
                                                                   self.testing_vars['boot_disk_controller'].lower(),
                                                                   self.testing_vars['network_adapter_type'].lower())

            test_idx += 1
            test_exec_time = time.strftime('%H:%M:%S', time.gmtime(test_result.duration))
            if test_result.status == 'Passed':
                msg += row_format.format(str(test_idx).rjust(idx_col_width, align_char),
                                         test_result.name.ljust(name_col_width),
                                         (status_mark + test_result.status).ljust(status_col_width),
                                         test_exec_time)
                status_stats[test_result.status] += 1
            else:
                msg += row_format.format(str(test_idx).rjust(idx_col_width, align_char),
                                         test_result.name.ljust(name_col_width),
                                         ("* " + test_result.status).ljust(status_col_width),
                                         test_exec_time)
                if test_result.status in ['Failed', 'Blocked', 'No Run']:
                    status_stats[test_result.status] += 1
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
        os_release_info_file = self._ansible_gosv_facts.get('os_release_info_file_path', None)
        if (os_release_info_file and os.path.exists(os_release_info_file)):
            with open(os_release_info_file, 'r') as json_input:
                os_release_info_detail = json.load(json_input,
                                                   object_pairs_hook=OrderedDict)
                # Update cloud-init version or open-vm-tools version in OS releas info
                if os_release_info_detail and len(os_release_info_detail) == 1:
                    data_changed = False
                    if (self._ansible_gosv_facts.get('cloudinit_version','') and
                            'cloud-init' not in os_release_info_detail[0]):
                        os_release_info_detail[0]['cloud-init'] = self._ansible_gosv_facts['cloudinit_version']
                        os_release_info_detail[0].move_to_end('cloud-init', last=False)
                        data_changed = True
                    if (self._ansible_gosv_facts.get('vmtools_info_from_vmtoolsd','') and
                            'open-vm-tools' not in os_release_info_detail[0]):
                        os_release_info_detail[0]['open-vm-tools'] = self._ansible_gosv_facts['vmtools_info_from_vmtoolsd']
                        os_release_info_detail[0].move_to_end('open-vm-tools', last=False)
                        data_changed = True

                    if data_changed:
                        os_release_info_detail[0].move_to_end('Release', last=False)
                        with open(os_release_info_file, 'w') as json_output:
                            json.dump(os_release_info_detail, json_output, indent=4)

    def _get_exception_traceback(self, result):
        msg = ''
        if 'exception' in result:
            msg = "An exception occurred during task execution. "
            msg += "The full traceback is:\n" + str(result['exception'])
            del result['exception']
        return msg

    def v2_runner_on_failed(self, result, ignore_errors=False):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._clean_results(result._result, result._task.action)

        if (not ignore_errors and self._last_test_id and
                self._last_test_id in self.test_runs and
                self.test_runs[self._last_test_id].status == "Running"):
            if 'reason: Blocked' in result._task.name:
                self.test_runs[self._last_test_id].complete('Blocked')
            else:
                self.test_runs[self._last_test_id].complete('Failed')
            # Pop up the completed test case
            self.not_completed_testcases.pop(0)

        if result._task.loop and 'results' in result._result:
            self._process_items(result)
            return

        self._print_task_details(result, 'failed', delegated_vars, ignore_errors=ignore_errors)

    def _dump_guest_info(self):
        """
        Dump collected guest info into a json file
        :return:
        """
        json_file_path = os.path.join(self.log_dir, self.guest_info_json_file)
        if len(self.collected_guest_info) > 0:
            with open(json_file_path, 'w') as json_file:
                json_objs = []
                for guest_info in self.collected_guest_info.values():
                    json_objs.append(json.loads(str(guest_info)))

                json.dump(json_objs, json_file, indent=4)
                self._display.display("VM guest info is dumped into:\n{}".format(json_file_path),
                                      color=C.COLOR_DEBUG)

    def _get_exception_traceback(self, result):
        if 'exception' in result:
            msg = "An exception occurred during task execution. "
            msg += "The full traceback is:\n" + str(result['exception'])
            del result['exception']
            return msg

    def v2_runner_on_failed(self, result, ignore_errors=False):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._clean_results(result._result, result._task.action)

        if (not ignore_errors and self._last_test_id and
                self._last_test_id in self.test_runs and
                self.test_runs[self._last_test_id].status == "Running"):
            if 'reason: Blocked' in result._task.name:
                self.test_runs[self._last_test_id].complete('Blocked')
            else:
                self.test_runs[self._last_test_id].complete('Failed')
            # Pop up the completed test case
            self.not_completed_testcases.pop(0)

        if result._task.loop and 'results' in result._result:
            self._process_items(result)
            return

        self._print_task_details(result, 'failed', delegated_vars, ignore_errors=ignore_errors)

    def _collect_ansible_gosv_facts(self, result):
        task = result._task
        task_result = result._result
        task_args = task.args
        task_file = os.path.basename(task.get_path()).split(':')[0].strip()
        if ((task_file in ["create_local_log_path.yml",
                           "set_current_testcase_facts.yml",
                           "vcenter_get_version_build.yml",
                           "esxi_get_version_build.yml",
                           "esxi_get_model.yml",
                           "vm_get_vm_info.yml",
                           "vm_upgrade_hardware_version.yml",
                           "vm_get_guest_info.yml",
                           "get_linux_system_info.yml",
                           "get_cloudinit_version.yml",
                           "check_guest_os_gui.yml",
                           "get_guest_ovt_version_build.yml",
                           "get_windows_system_info.yml",
                           "win_get_vmtools_version_build.yml",
                           "check_inbox_driver.yml",
                           "check_os_fullname.yml"] or
             "deploy_vm_from" in task_file) and
                str(task.action) == "ansible.builtin.set_fact"):
            ansible_facts = task_result.get('ansible_facts', None)
            if ansible_facts:
                self._ansible_gosv_facts.update(ansible_facts)
                if ("current_testcase_name" in ansible_facts and
                    ansible_facts["current_testcase_name"] and
                    self._last_test_id and
                    self._last_test_id in self.test_runs):
                    # Update deploy_vm test case name
                    self.test_runs[self._last_test_id].name = ansible_facts['current_testcase_name']

                if task_file == 'vm_get_guest_info.yml':
                    esxi_build = self._ansible_gosv_facts.get('esxi_build','')
                    vm_hw_version = self._ansible_gosv_facts.get('vm_hardware_version','')
                    vmtools_version = self._ansible_gosv_facts.get('guestinfo_vmtools_info','')
                    if (esxi_build and vm_hw_version and vmtools_version):
                        guestinfo_hash = str(hash("{}{}{}".format(esxi_build, vm_hw_version, vmtools_version)))
                        if guestinfo_hash not in self.collected_guest_info:
                            # Save guest info
                            vm_guest_info = VmGuestInfo(self._ansible_gosv_facts)
                            self.collected_guest_info[guestinfo_hash] = vm_guest_info

        elif (task_file in ["deploy_vm.yml", "test_setup.yml"] and
              str(task.action) == "ansible.builtin.debug"):
            if 'var' in task_args and task_args['var'] == "vm_guest_ip":
                if task_result["vm_guest_ip"]:
                    self._ansible_gosv_facts["vm_guest_ip"] = task_result["vm_guest_ip"]

    def v2_runner_on_ok(self, result):
        task = result._task
        task_args = task.args

        if isinstance(task, TaskInclude):
            return

        task_result = result._result
        delegated_vars = task_result.get('_ansible_delegated_vars', None)

        if result._task.loop and 'results' in result._result:
            self._process_items(result)
            return

        self._clean_results(result._result, result._task.action)
        if task_result.get('changed', False):
            self._print_task_details(result, "changed", delegated_vars)
        else:
            self._print_task_details(result, "ok", delegated_vars)

        # Collect ansible_facts from set_fact or debug modules
        self._collect_ansible_gosv_facts(result)

        # Set skipped test case result
        task_file = os.path.basename(task.get_path()).split(':')[0].strip()
        if (task_file == "skip_test_case.yml" and
                str(task.action) == "ansible.builtin.debug" and
                "Skip testcase:" in task.name):
            test_status = task.name.split(':')[-1].strip()
            if (self._last_test_id and
                    self._last_test_id in self.test_runs and
                    self.test_runs[self._last_test_id].status == "Running"):
                self.test_runs[self._last_test_id].complete(test_status)
                # Pop up the completed test case
                self.not_completed_testcases.pop(0)

    def v2_runner_on_skipped(self, result):
        self._clean_results(result._result, result._task.action)
        if result._task.loop and 'results' in result._result:
            self._process_items(result)
        else:
            self._print_task_details(result, "skipped")

    def v2_runner_on_unreachable(self, result):
        delegated_vars = result._result.get('_ansible_delegated_vars', None)
        self._print_task_details(result, "unreachable", delegated_vars)

        if (self._last_test_id and
                self._last_test_id in self.test_runs and
                self.test_runs[self._last_test_id].status == "Running"):
            self.test_runs[self._last_test_id].complete('Failed')
            # Pop up the completed test case
            self.not_completed_testcases.pop(0)

    def v2_runner_retry(self, result):
        task_name = result.task_name or result._task
        msg = "FAILED - RETRYING: {} ({} retries left).".format(task_name,
                                                                result._result['retries'] - result._result['attempts'])
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

    def _set_log_dir(self, local_log_path):
        # Set log dir
        if local_log_path and os.path.exists(local_log_path):
            self.log_dir = os.path.join(local_log_path, time.strftime("%Y-%m-%d-%H-%M-%S"))
            self.current_log_dir = os.path.join(local_log_path, "current")
        else:
            self.log_dir = os.path.join(self.cwd, "logs", time.strftime("%Y-%m-%d-%H-%M-%S"))
            self.current_log_dir = os.path.join(self.cwd, "logs/current")

        # Unlink existing symbolic link for current log dir
        if os.path.exists(self.current_log_dir):
            try:
                if os.path.islink(self.current_log_dir):
                    os.unlink(self.current_log_dir)
                else:
                    shutil.rmtree(self.current_log_dir)
            except OSError as os_error:
                self._display.display("Error: {} : {}".format(self.current_log_dir, os_error.strerror),
                                      color=C.COLOR_ERROR)

        # Create new log dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        os.symlink(self.log_dir, self.current_log_dir, target_is_directory=True)

    def v2_playbook_on_start(self, playbook):
        playbook_path = os.path.realpath(playbook._file_name)
        self.start_time = time.time()

        # Parse extra vars
        extra_vars = {}
        if context.CLIARGS and context.CLIARGS['extra_vars']:
            for extra_vars_str in context.CLIARGS['extra_vars']:
                if extra_vars_str:
                    # extra_var_str is tuple
                    extra_vars_list = extra_vars_str.split()
                    for extra_vars_item in extra_vars_list:
                        if extra_vars_item.find("=") != -1:
                            extra_vars[extra_vars_item.split("=")[0].strip()] = extra_vars_item.split("=")[1].strip()

        # Update testing vars file with extra variable
        if 'testing_vars_file' in extra_vars.keys():
            self.testing_vars_file = extra_vars['testing_vars_file']
        else:
            self.testing_vars_file = os.path.join(self.cwd, "vars/test.yml")
        # Load testing vars
        if os.path.exists(self.testing_vars_file):
            with open(self.testing_vars_file, 'r') as fd:
                self.testing_vars.update(yaml.load(fd, Loader=yaml.Loader))

        # Update log dir
        self._set_log_dir(self.testing_vars.get('local_log_path', ''))

        # Get testcase list
        if 'main.yml' in os.path.basename(playbook_path):
            # Update testcase list file with extra variable
            if 'testing_testcase_file' in extra_vars.keys():
                self.testing_testcase_file = extra_vars['testing_testcase_file']
            else:
                self.testing_testcase_file = os.path.join(self.cwd, "linux/gosv_testcase_list.yml")
            self._get_testcase_list(self.testing_testcase_file)

        self.add_logger_file_handler(self.full_debug_log)
        msg = self._banner("PLAYBOOK: {}".format(playbook_path))
        msg += "Positional arguments: {}\n".format(' '.join(context.CLIARGS['args']))
        msg += "Tesing vars file: {}\n".format(self.testing_vars_file)
        msg += "Tesing testcase file: {}\n".format(self.testing_testcase_file)
        msg += "Playbook directory: {}\n".format(self.cwd)
        msg += "Log directory: {}\n".format(self.log_dir)
        msg += "Current log directory: {}\n".format(self.current_log_dir)
        self.logger.info(msg)
        self._display.display(msg, color=C.COLOR_DEBUG)

    def v2_playbook_on_play_start(self, play):
        # Finish the last test case
        if (self._last_test_id and
                self._last_test_id in self.test_runs and
                self.test_runs[self._last_test_id].status == "Running"):
            self.test_runs[self._last_test_id].complete('Passed')
            # Pop up the completed test case
            self.not_completed_testcases.pop(0)

        # Move to new started playbook
        self._last_test_id = None
        self._play_name = play.get_name()
        self._play_path = self._get_play_path(play)
        self._load_testing_vars(play)

        test_index = len(self.test_runs) - len(self.not_completed_testcases)
        # print("DEBUG: Current test index is: {}, play name: {}".format(test_index, self._play_name))
        # Start new test case
        if (test_index < len(self.test_runs) and
            self.not_completed_testcases[0] == self._play_name):
            # Start new test case
            self._last_test_id = "{}_{}".format(str(test_index+1).rjust(len(str(self.testcases_count)), '0'),
                                                self._play_name)

            if self._last_test_id in self.test_runs:
                self.test_runs[self._last_test_id].start()
            else:
                self._last_test_id = None

        if self._last_test_id:
            msg = self._banner("PLAY [{}]".format(self._last_test_id))
        elif self._play_name:
            msg = self._banner("PLAY [{}]".format(self._play_name))
        else:
            msg = self._banner("PLAY")

        if self._play_path:
            msg += "play path: {}".format(self._play_path)

        self.logger.info(msg)

        self.play = play

        # Clear play tasks cache
        self._play_tasks_cache.clear()

    def v2_playbook_on_stats(self, stats):
        self.end_time = time.time()

        # Update the last testcase status
        if (self._last_test_id and
                self._last_test_id in self.test_runs and
                self.test_runs[self._last_test_id].status == "Running"):
            self.test_runs[self._last_test_id].complete('Passed')
            # Pop up the completed test case
            self.not_completed_testcases.pop(0)

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

        # Update open-vm-tools and cloud-init version in inbox driver info file
        self._print_os_release_info()

        # Dump guest info into a json file
        self._dump_guest_info()

        # Debug about ansible facts
        # print("DEBUG: retieved ansible facts\n{}".format(json.dumps(self._ansible_gosv_facts,
        #                                                            indent=4)))

        # Print test summary when there is test run
        if len(self.test_runs) > 0:
            self._display.banner("TEST SUMMARY")
            self.logger.info(self._banner("TEST SUMMARY"))
            self.add_logger_file_handler(self.test_results_log)

            # Print testbed information
            vcenter_hostname = self.testing_vars.get('vcenter_hostname', '')
            esxi_hostname = self.testing_vars.get('esxi_hostname', '')
            testbed_info = TestbedInfo(vcenter_hostname, esxi_hostname, self._ansible_gosv_facts)
            self.logger.info(str(testbed_info))
            self._display.display(str(testbed_info), color=C.COLOR_VERBOSE)

            # Print VM information
            vm_name = self.testing_vars.get('vm_name', None)
            vm_info = VmDetailInfo(vm_name, self._ansible_gosv_facts)
            self.logger.info(str(vm_info))
            self._display.display(str(vm_info), color=C.COLOR_VERBOSE)

            # Print test results
            self._print_test_results()
            self.remove_logger_file_handler(self.test_results_log)

        if ('testrun_log_path' in self._ansible_gosv_facts and
            self._ansible_gosv_facts['testrun_log_path'] and
            self.log_dir != self._ansible_gosv_facts['testrun_log_path']):
            os.system("cp -rf {}/* {}".format(self.log_dir, self._ansible_gosv_facts['testrun_log_path']))
            os.unlink(self.current_log_dir)
            os.system("rm -rf {}".format(self.log_dir))
            os.symlink(self._ansible_gosv_facts['testrun_log_path'], self.current_log_dir, target_is_directory=True)

    def v2_playbook_on_task_start(self, task, is_conditional):
        self._task_start(task, prefix='TASK')

    def v2_playbook_on_include(self, included_file):
        msg = self._banner(
            'Included: {} for {}'.format(included_file._filename, ", ".join([h.name for h in included_file._hosts])))
        label = self._get_item_label(included_file._vars)
        if label:
            msg += " => (item={})".format(label)
        self.logger.info(msg)

    def v2_playbook_on_import_for_host(self, result, imported_file):
        msg = self._banner(
            'Imported: {} for {}'.format(imported_file._filename, ", ".join([h.name for h in imported_file._hosts])))
        label = self._get_item_label(imported_file._vars)
        if label:
            msg += " => (item={})".format(label)
        self.logger.info(msg)
