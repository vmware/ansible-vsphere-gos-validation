#!/usr/bin/env python3
# Copyright 2024 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
#
# This script can help to query CPU code name from manufacturer website
#
import sys
import requests
import re
import traceback
from lxml import html
from urllib.parse import quote, urlparse, urlunparse
from argparse import ArgumentParser, RawTextHelpFormatter

ARK_INTEL_HOME = "https://ark.intel.com"

def url_encode(input_string):
    encoded_string = quote(input_string)
    return encoded_string

class Processor(object):
    def __init__(self):
        self.cpu_name = None
        self.code_name = None

    def get_cpu_name(self):
        return self.cpu_name

    def get_code_name(self):
        return self.code_name

class IntelProcessor(Processor):
    def __init__(self, cpu_spec_url):
        super().__init__()
        self._parse_cpu_spec(cpu_spec_url)

    def _parse_cpu_spec(self, cpu_spec_url):
        """
        Get CPU details from its specification URL
        For example,
        https://ark.intel.com/content/www/us/en/ark/products/212458/intel-xeon-gold-6330-processor-42m-cache-2-00-ghz.html
        """
        try:
            response = requests.get(cpu_spec_url)
            if response.status_code == 200:
                xml_tree = html.fromstring(response.content)
                product_title = xml_tree.xpath('//div[contains(@class, "product-family-title-text")]/h1')
                if product_title:
                    cpu_name = re.sub(' *Processor *', '', product_title[0].text)
                    cpu_name = cpu_name.replace('®', '(R)')
                    self.cpu_name = cpu_name
                    # Look for code name
                    codename_a = xml_tree.xpath('//span[@data-key="CodeNameText"]/a')
                    if codename_a:
                        self.code_name = codename_a[0].text.replace('Products formerly ', '').strip()
        except Exception as e:
            traceback_str = traceback.format_exc()
            sys.stderr.write(f"Failed to parse CPU specification {cpu_spec_url}\n" + traceback_str)
            sys.exit(1)

def intel_search_cpu(search_name):
    """
    Search for CPU by given CPU name pattern
    """
    cpu_spec_url = None
    # Remove '(R)' from the CPU name
    cpu_name_pattern = re.sub('\(\w+\)', '', search_name)
    # Construct the search query URL
    search_url = f"{ARK_INTEL_HOME}/content/www/us/en/ark/search.html?_charset_=UTF-8&q=" + url_encode(cpu_name_pattern)

    # Send a GET request to the search URL
    response = requests.get(search_url)
    if response.status_code == 200:
        xml_tree = html.fromstring(response.content)
        # Find the CPU search results
        cpu_results = xml_tree.xpath('//h4[@class="result-title"]/a')
        if cpu_results and len(cpu_results) > 0:
            # It searched more than one CPU results
            for cpu_result in cpu_results:
                cpu_name = re.sub(r'(Processor)? *\(.*\)', '', cpu_result.text).strip().replace('®', '(R)')
                # print(f"Found CPU name: {cpu_name}")
                if cpu_name == search_name:
                    cpu_spec_url = ARK_INTEL_HOME + cpu_result.get('href')
                    break
        else:
            # It searched only one CPU result
            search_result = xml_tree.xpath('//div[contains(@class,"textSearch")]/input[@id="FormRedirectUrl"]')
            if search_result and len(search_result) > 0:
                cpu_spec_url = ARK_INTEL_HOME + search_result[0].value

    # print(f"Found CPU spec for {search_name}: {cpu_spec_url}")
    return cpu_spec_url

def intel_query_cpu_code_name(search_name):
    """
    Search CPU and get its code name from CPU specification
    """
    cpu_spec_url = intel_search_cpu(search_name)
    if cpu_spec_url:
        intel_cpu = IntelProcessor(cpu_spec_url)
        cpu_name = intel_cpu.get_cpu_name()
        code_name = intel_cpu.get_code_name()
        if cpu_name and code_name and cpu_name == search_name:
            print(code_name)

def parse_arguments():
    parser = ArgumentParser(description="A tool to query CPU code name by CPU product name",
                            usage='%(prog)s [OPTIONS]',
                            formatter_class=RawTextHelpFormatter)
    parser.add_argument("-n", dest="name", required=True,
                        help="CPU product name\n" +
                             "e.g. Intel(R) Xeon(R) Gold 6330")

    args = parser.parse_args()
    return args

if __name__ == "__main__":
    args = parse_arguments()
    try:
        if 'Intel' in args.name:
            intel_query_cpu_code_name(args.name)
        elif 'AMD' in args.name:
            pass
    except Exception as e:
        traceback_str = traceback.format_exc()
        sys.stderr.write(traceback_str)
        sys.exit(1)
