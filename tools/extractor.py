#!/usr/bin/env python3
# Copyright 2023 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
# This script can help to extract text from an image file or
# error messages from log file
#
import os
import sys
import re
import traceback
import pytesseract
from PIL import Image
from argparse import ArgumentParser, RawTextHelpFormatter

def parse_arguments():
    parser = ArgumentParser(description="A tool to extract text from image file or call trace from log file",
                            usage='%(prog)s [OPTIONS]',
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument("-t", dest="type", choices=["text", "error"], required=True,
                        help="the type to be extracted from file.\n" +
                             "text - Extracting text from image file\n" +
                             "error - Extracting error, failed, exception, call trace, etc from log file")
    parser.add_argument("-f", dest="file", required=True,
                        help='the image or log file path for extracting information')

    args = parser.parse_args()
    return args

def remove_empty_lines(text):
    return '\n'.join(line for line in text.split('\n') if line.strip())

# Escape ANSII code like colors from log file
def escape_ansi(text):
#    ansi_escape = re.compile(r'((?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~])|(\x1b[^m]*m)')
    ansi_escape = re.compile(r'(?:\x1B[@-_]|[\x80-\x9F])[0-?]*[ -/]*[@-~]', flags=re.IGNORECASE)
    return ansi_escape.sub('', text)

def extract_text_from_image(image_path):
    # Open the image file
    img = Image.open(image_path)

    # Use pytesseract to do OCR on the image
    text = pytesseract.image_to_string(img)
    text = remove_empty_lines(text)
    if len(text) > 0:
        print("Extracted text from image:\n" + text)

def extract_calltrace_from_log(log_path):
    calltrace_stack = []

    with open(log_path, 'r') as log_file:
        log_text = log_file.read()
        # Find 'Call Trace:' lines to get the start and end position of call traces
        calltrace_matches = re.finditer('Call Trace:', log_text, flags=re.IGNORECASE)
        if calltrace_matches is None:
            return None

        calltrace_matches = list(calltrace_matches)
        calltrace_count = len(calltrace_matches)
        for calltrace_index, calltrace_match in enumerate(calltrace_matches):
            calltrace_stack.append(calltrace_match.group(0))
            calltrace_start = calltrace_match.end(0)
            if calltrace_index + 1 < calltrace_count:
                calltrace_end = calltrace_matches[calltrace_index + 1].start(0)
            else:
                calltrace_end = len(log_text)

            stack_matches = re.finditer(r'(?<=] ) ([^\s].*\/.*|<\/?.*>)',
                                        log_text[calltrace_start:calltrace_end])
            if stack_matches is None:
                continue
            for stack_match in stack_matches:
                calltrace_stack.append(stack_match.group(0))

    if len(calltrace_stack) > 0:
        print("Found call trace in log file:\n" + "\n".join(calltrace_stack))

def extract_error_from_log(log_path):
    errors = []
    with open(log_path, 'r') as log_file:
        text = remove_empty_lines(log_file.read())
        lines = text.split('\n')
        lines_count = len(lines)

        # Current and next line index
        line_cursor = 0
        next_line_cursor = 0
        while (line_cursor < lines_count):
            line = escape_ansi(lines[line_cursor].rstrip())

            # If line matches Traceback, append following trace stack to error list
            m = re.search(r'Traceback \(most recent call last\):', line, flags=re.IGNORECASE)
            if m:
                char_cursor = m.start()
                errors.append(line)
                # Check whether Traceback is preceded by a match of non-word characters
                left_match = re.search(r'\W+(?=Traceback)', line, flags=re.IGNORECASE)
                if left_match:
                    left_pattern = left_match.group(0)
                    char_cursor = char_cursor - len(left_pattern)
                else:
                    left_pattern = ''

                stack_pattern = f'(?<={left_pattern})(  +.*)'
                next_line_cursor = line_cursor + 1
                while next_line_cursor < lines_count:
                    next_line = escape_ansi(lines[next_line_cursor].rstrip())
                    stack_match = None
                    if char_cursor < len(next_line):
                        stack_match = re.search(stack_pattern, next_line[char_cursor:])

                    if stack_match:
                        # errors.append(stack_match.group(0))
                        errors.append(next_line)
                        line_cursor = next_line_cursor
                        next_line_cursor += 1
                    else:
                        break
            elif re.search('^.*(error|failed|exception):.*', line, flags=re.IGNORECASE):
                # If line has error, failed, exception, append this line to errors
                if line not in errors and not re.search('warning', line, flags=re.IGNORECASE):
                    errors.append(line)

            line_cursor += 1


    if len(errors) > 0:
        print("Found error messages in log file:\n" + "\n".join(errors))


if __name__ == "__main__":
    args = parse_arguments()

    try:
        if not os.path.isfile(args.file):
            raise FileNotFoundError(f"{args.file} doesn't exist or is not a file.")

        if args.type == 'text':
            # Extract text from the image
            extract_text_from_image(args.file)
        elif args.type == 'error':
            extract_calltrace_from_log(args.file)
            extract_error_from_log(args.file)
    except Exception as e:
        traceback_str = traceback.format_exc()
        sys.stderr.write(traceback_str)
        sys.exit(1)
