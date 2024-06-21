#!/usr/bin/env python
# Copyright 2024 VMware, Inc.
# SPDX-License-Identifier: BSD-2-Clause
"""
This is a script to test host verified SAML token by reading guest OS environment variables.
"""

import os
import ssl
import argparse
import sys
import base64
import logging
import traceback
import xml.dom.minidom
import xml.etree.ElementTree as ET
from OpenSSL import crypto
from pyVmomi import vim, SoapStubAdapter
from pyVim import sso
from pyVim.connect import SmartConnect, Disconnect

logger = None
log_dir = None

def get_logger(debug=False, log_file=None):
    """
    Get logger object
    :param debug: True to print debug message in console
    :param log_file: The log file path
    :return:
    """
    global log_dir
    logger = logging.getLogger()
    if debug:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO

    logger.setLevel(logging.DEBUG)

    logFormat = '%(asctime)s|%(levelname)5s| %(message)s'

    formatter = logging.Formatter(logFormat)
    if log_file is not None:
        log_dir = os.path.dirname(os.path.abspath(log_file))
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        lh = logging.FileHandler(log_file)
        lh.setLevel(logging.DEBUG)
        lh.setFormatter(formatter)
        logger.addHandler(lh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(log_level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", dest="verbose", action="store_true", default=False,
                        help="print debug messages to console output")
    parser.add_argument("-l", dest="log",
                        help="log file path")
    parser.add_argument("-H", dest="host", required=True,
                        help="vCenter Server hostname or IP address")
    parser.add_argument("-d", dest="domain", default="vsphere.local",
                        help="vCenter Server user domain")
    parser.add_argument("-vm", dest="vm_name", required=True,
                        help="VM name")
    parser.add_argument("-au", dest="admin_user",
                        default='Administrator',
                        help="VC admin username without domain name. Default is Administrator")
    parser.add_argument("-ap", dest="admin_pwd", required=True,
                        help="VC admin password")
    parser.add_argument("-tu", dest="test_user",
                        default='vcuser',
                        help="VC test username without domain name. Default is vcuser")
    parser.add_argument("-tp", dest="test_pwd",
                        default='VP@ssw0rd',
                        help="VC test password. Default is VP@ssw0rd")
    parser.add_argument("-gu", dest="guest_user", default="gosuser",
                        help="guest username. Default is gosuser")
    parser.add_argument("-gp", dest="guest_pwd", default='GP@ssw0rd',
                        help="guest user password. Default is GP@ssw0rd")
    parser.add_argument("-o", dest="operation",
                        required=True,
                        choices = ['ListGuestAlias',
                                   'AddGuestAlias',
                                   'RemoveGuestAlias',
                                   'PerformGuestOps'],
                        help="guest operations")
    args = parser.parse_args()
    for kwarg in args._get_kwargs():
        if(kwarg[0] in ['domain', 'guest_user'] and kwarg[1] == ''):
            parser.error(f"{kwarg[0]} can't be empty.")
        if(kwarg[0] in ['admin_user', 'test_user'] and len(kwarg[1].split('@')) > 1):
            parser.error(f"{kwarg[0]} can't include domain name.")

    if args.operation != 'PerformGuestOps' and not args.test_pwd:
        parser.error(f"test_pwd is required for {args.operation}")
    return args

def get_unverified_context():
    """
    Get an unverified ssl context. Used to disable the server certificate
    verification.
    @return: unverified ssl context.
    """
    context = None
    if hasattr(ssl, '_create_unverified_context'):
        context = ssl._create_unverified_context()
    return context

def prettify_xml(xml_string):
    """
    Print XML string in pretty format
    :param xml_string:
    :return:
    """
    dom = xml.dom.minidom.parseString(xml_string)
    pretty_xml = dom.toprettyxml(indent="  ")
    return pretty_xml

def get_sso_saml_token(host, username, password, domain='vsphere.local', context=None):
    """
    Get Single Sign-On SAML token for VC domain user
    :param host: vCenter Server hostname
    :param username: VC user name without domain
    :param password: VC user password
    :param domain: VC user domain
    :param context: SSL context
    :return: SSO user SAML token in XML
    """
    sso_url = 'https://{}/sts/STSService/{}'.format(host, domain)
    logger.debug("The SSO URL is " + sso_url)
    auth = sso.SsoAuthenticator(sso_url)

    user = f"{username}@{domain}"
    logger.debug(f'Retrieving the SAML bearer token from SSO for VC user {user}.')
    saml_token = auth.get_bearer_saml_assertion(user, password,
                                                delegatable=True,
                                                # renewable=True,
                                                ssl_context=context)
    pretty_xml = prettify_xml(saml_token)
    # logger.debug("The SSO SAML token is:\n" + pretty_xml)
    saml_token_file = f"{username}_saml_token.xml"
    if log_dir is not None and log_dir:
        saml_token_file = os.path.join(log_dir, saml_token_file)
    with open(saml_token_file, 'w') as f:
        f.write(pretty_xml)
    logger.debug(f"SAML token for VC domain {user} is saved to: {saml_token_file}")
    return saml_token

def extract_x509_cert_from_token(saml_token):
    """
    Extract X.509 certificate from SAML token
    :param saml_token: VC SSO user SAML token string
    :return: The X.509 certificate in PEM format
    """
    namespace = {'ds': 'http://www.w3.org/2000/09/xmldsig#'}
    root = ET.fromstring(saml_token)
    x509_cert_element = root.find('.//ds:X509Certificate', namespace)

    if x509_cert_element is not None and x509_cert_element.text:
        x509_cert =  x509_cert_element.text.strip()

    # Extract the X.509 certificate
    if x509_cert != '':
        x509_cert = "\n".join([x509_cert[i:i+64] for i in range(0, len(x509_cert), 64)])
        # X.509 certificate string
        x509_cert = f"-----BEGIN CERTIFICATE-----\n{x509_cert}\n-----END CERTIFICATE-----\n"

        # File path to write the certificate
        cert_file_path = "x509_pem.crt.txt"
        if log_dir is not None and log_dir:
            cert_file_path = os.path.join(log_dir, cert_file_path)
        # Write the certificate string into the file
        with open(cert_file_path, "w") as file:
            file.write(x509_cert)
        logger.debug(f"X.509 certification in PEM format is saved to {cert_file_path}")

    return x509_cert

def get_base64_cert_from_token(saml_token):
    """
    Retrieve X.509 certificate from SSO user SAML token with base64 encoded
    :param saml_token:
    :return:
    """
    x509_cert = extract_x509_cert_from_token(saml_token)
    # Convert X.509 certificate in PEM to DER format
    cert_pem = crypto.load_certificate(crypto.FILETYPE_PEM, x509_cert)
    cert_der = crypto.dump_certificate(crypto.FILETYPE_ASN1, cert_pem)
    base64_cert = base64.b64encode(cert_der).decode('utf-8')
    # logger.debug("Base64 encoded X.509 certificate:\n" + str(base64_cert))
    return base64_cert

def find_vm_by_name(service_instance, vm_name):
    """
    Find a virtual machine object
    :param service_instance:
    :param vm_name:
    :return:
    """
    content = service_instance.RetrieveContent()
    container_view = content.viewManager.CreateContainerView(content.rootFolder,
                                                             [vim.VirtualMachine], True)
    for vm in container_view.view:
        if vm.name == vm_name:
            logger.debug(f"Find VM {vm_name}: " + str(vm))
            return vm
    return None

def list_guest_alias(args, service_instance, vm):
    """
    List VC SSO users mapping to a guest user
    """
    # Get guest user alias manager
    guest_ops_manager = service_instance.content.guestOperationsManager
    alias_manager = guest_ops_manager.aliasManager

    # Add a guest authentication object with SAML token
    guest_auth = vim.vm.guest.NamePasswordAuthentication()
    guest_auth.username = args.guest_user
    guest_auth.password = args.guest_pwd

    logger.debug(f"Retrieving guest user alias for guest user '{args.guest_user}'")
    alias_mappings = alias_manager.ListGuestAliases(vm, guest_auth, args.guest_user)
    sso_users = []
    for mapping in alias_mappings:
        if (mapping.aliases and len(mapping.aliases) > 0 and
            mapping.aliases[0].subject):
            sso_users.append(mapping.aliases[0].subject.name)
    logger.info(f"SSO users mapping to guest user '{args.guest_user}': " + ','.join(sso_users))
    return sso_users

def add_guest_alias(args, service_instance, vm, base64_cert):
    """
    Add a guest user mapping from VC SSO user to guest user
    """
    # Get guest user alias manager
    guest_ops_manager = service_instance.content.guestOperationsManager
    alias_manager = guest_ops_manager.aliasManager

    # Create a guest user name specification
    guest_auth = vim.vm.guest.NamePasswordAuthentication()
    guest_auth.username = args.guest_user
    guest_auth.password = args.guest_pwd

    # Create a guest alias mapping
    alias_info = vim.vm.guest.AliasManager.GuestAuthAliasInfo()
    guest_auth_subject = vim.vm.guest.AliasManager.GuestAuthNamedSubject()
    vc_user = f"{args.test_user}@{args.domain}"
    guest_auth_subject.name = vc_user
    alias_info.subject = guest_auth_subject
    alias_info.comment = "Guest user mapping for testing host verified SAML token"

    # Add the alias mapping
    logger.debug(f"Adding user alias for guest user {args.guest_user}: {vc_user}")
    alias_manager.AddGuestAlias(vm=vm, auth=guest_auth, username=args.guest_user,
                                mapCert=True, base64Cert=base64_cert, aliasInfo=alias_info)

    sso_users = list_guest_alias(args, service_instance, vm)
    if vc_user in sso_users:
        logger.info(f"Successfuly added guest user mapping: {args.guest_user}:{vc_user}")
    else:
        raise Exception(f"Failed to add guest user mapping: {args.guest_user}:{vc_user}")

def remove_guest_alias(args, service_instance, vm, base64_cert):
    """
    Remove a guest user mapping from VC SSO user to guest user
    """
    # Get guest user alias manager
    guest_ops_manager = service_instance.content.guestOperationsManager
    alias_manager = guest_ops_manager.aliasManager

    # Add a guest authentication object with SAML token
    guest_auth = vim.vm.guest.NamePasswordAuthentication()
    guest_auth.username = args.guest_user
    guest_auth.password = args.guest_pwd

    guest_auth_subject = vim.vm.guest.AliasManager.GuestAuthNamedSubject()

    vc_user = f"{args.test_user}@{args.domain}"
    guest_auth_subject.name = vc_user

    # Remove guest user alias
    logger.debug(f"Removing user alias for guest user {args.guest_user}: {vc_user}")
    alias_manager.RemoveGuestAlias(vm=vm, auth=guest_auth, username=args.guest_user,
                                   base64Cert=base64_cert, subject=guest_auth_subject)

    sso_users = list_guest_alias(args, service_instance, vm)
    if vc_user not in sso_users:
        logger.info(f"Successfuly removed guest user mapping: {args.guest_user}:{vc_user}")
    else:
        raise Exception(f"Failed to remove guest user mapping: {args.guest_user}:{vc_user}")

    return sso_users

def perform_guest_ops(args, service_instance, vm, context=None):
    """
    Perform guest operation with VC SSO user
    E.g. ReadEnvironmentVariableInGuest in this sample
    :param args:
    :param service_instance:
    :param vm:
    :param context:
    :return:
    """
    # Create a GuestAuth object for test user with the acquired SAML token
    saml_token = get_sso_saml_token(args.host, args.test_user, args.test_pwd, args.domain, context)
    guest_auth = vim.vm.guest.SAMLTokenAuthentication()
    guest_auth.username = args.guest_user
    guest_auth.token = saml_token

    # Get GuestProcessManager object
    guest_ops_manager = service_instance.content.guestOperationsManager
    process_manager = guest_ops_manager.processManager

    # List guest environment variables
    guest_envs = process_manager.ReadEnvironmentVariableInGuest(vm, guest_auth)
    logger.info("Guest user's environment variables are:\n" + '\n'.join(guest_envs))

# Two ways to get service instance, each of them works
def get_si_with_token(host, saml_token, context=None):
    """
    Get VC service instance by SSO log in with SAML token
    """
    logger.debug("SSO Log in with SAML token and get service instance")
    return SmartConnect(host=host, token=saml_token, tokenType='saml', sslContext=context)

def get_si_with_usernam_password(host, user, password, context=None):
    """
    Get VC service instance by SSO log in with username and password
    """
    logger.debug("SSO Log in with username and password and get service instance")
    return SmartConnect(host=host, user=user, pwd=password, sslContext=context)

def main():
    global logger
    args = parse_arguments()
    logger = get_logger(debug=args.verbose, log_file=args.log)

    # Connect to vCenter Server with SAML token
    service_instance = None
    try:
        context = get_unverified_context()
        admin_saml_token = get_sso_saml_token(args.host, args.admin_user, args.admin_pwd, args.domain, context)
        # Get service instance by SSO log in with SAML token
        service_instance = get_si_with_token(args.host, admin_saml_token, context)

        # Find the virtual machine
        vm = find_vm_by_name(service_instance, args.vm_name)
        if vm is None:
            raise Exception(f"Failed to find VM with name {args.vm_name}")

        base64_cert = get_base64_cert_from_token(admin_saml_token)

        if args.operation == "ListGuestAlias":
            list_guest_alias(args, service_instance, vm)
        elif args.operation == "AddGuestAlias":
            add_guest_alias(args, service_instance, vm, base64_cert)
        elif args.operation == "RemoveGuestAlias":
            remove_guest_alias(args, service_instance, vm, base64_cert)
        elif args.operation == "PerformGuestOps":
            perform_guest_ops(args, service_instance, vm, context)

        return 0
    except Exception as ex:
        logger.error(str(ex) +  "\n" + traceback.format_exc())
        return 1
    finally:
        if service_instance:
            # Disconnect from vCenter Server
            Disconnect(service_instance)

# Main Execution point
if __name__ == "__main__":
    sys.exit(main())
