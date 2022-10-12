# Copyright 2022 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause

import json

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
                            json_obj['stderr_lines'].remove("")
                            message += '\n' + '\n'.join(json_obj['stderr_lines']).strip()
                        elif 'stdout_lines' in json_obj and len(json_obj['stdout_lines']) > 0:
                            json_obj['stdout_lines'].remove("")
                            message += '\n' + '\n'.join(json_obj['stdout_lines']).strip()

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