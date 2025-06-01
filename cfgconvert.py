#!/usr/bin/env python3
# 1.0 Rework this to remove the web junk because it's overly complicated. 
# Tear out the auto-detect code and create flags for each configuration type. 
# This is crude 
import os
import sys
import re
import argparse
import logging
import traceback
from xml.etree import ElementTree as ET
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./config_converter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --------------------------
# Conversion Functions
# --------------------------

def junos_to_jinja2(config):
    """Convert JunOS config to Jinja2 template"""
    jinja_config = []
    for line in config.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            jinja_config.append(line)
            continue

        if line.startswith('set'):
            parts = line[4:].split()
            var_path = []
            for part in parts:
                if part.isdigit():
                    var_path.append(f"{{{{ {part}_id }}}}")
                elif '-' in part:
                    var_path.append(f"{{{{ {part.replace('-', '_')} }}}}")
                else:
                    var_path.append(part)
            jinja_config.append(f"set {' '.join(var_path)}")
        else:
            jinja_config.append(line)
    return '\n'.join(jinja_config)

def junos_to_xml(config):
    """Convert JunOS config to XML"""
    root = ET.Element("junos_configuration")
    system = ET.SubElement(root, "system")

    if hostname := re.search(r'set system host-name (\S+)', config):
        ET.SubElement(system, "hostname").text = hostname.group(1)

    interfaces = ET.SubElement(root, "interfaces")
    for intf in re.finditer(r'set interfaces (\S+) unit (\d+)', config):
        intf_elem = ET.SubElement(interfaces, "interface")
        ET.SubElement(intf_elem, "name").text = intf.group(1)
        ET.SubElement(intf_elem, "unit").text = intf.group(2)

        ip_match = re.search(
            r'set interfaces {} unit {} family inet address (\S+)'.format(
                re.escape(intf.group(1)), re.escape(intf.group(2))), 
            config
        )
        if ip_match:
            ET.SubElement(intf_elem, "ip_address").text = ip_match.group(1)

    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

def sros_to_jinja2(config):
    """Convert Nokia SROS config to Jinja2 template"""
    jinja_config = []
    for line in config.splitlines():
        line = line.strip()
        if not line:
            jinja_config.append(line)
            continue

        if line.startswith('configure system name'):
            jinja_config.append('configure system name "{{ system_name }}"')
        elif match := re.match(r'configure interface "([^"]+)"', line):
            jinja_config.append(f'configure interface "{{{{ {match.group(1).replace("-", "_")} }}}}"')
        elif 'address' in line:
            jinja_config.append(re.sub(r'address (\S+)', 'address {{ ip_address }}', line))
        else:
            jinja_config.append(line)
    return '\n'.join(jinja_config)

def sros_to_xml(config):
    """Convert Nokia SROS config to XML"""
    root = ET.Element("sros_configuration")
    system = ET.SubElement(root, "system")

    if name := re.search(r'configure system name "([^"]+)"', config):
        ET.SubElement(system, "name").text = name.group(1)

    interfaces = ET.SubElement(root, "interfaces")
    for intf in re.finditer(r'configure interface "([^"]+)"', config):
        intf_elem = ET.SubElement(interfaces, "interface")
        ET.SubElement(intf_elem, "name").text = intf.group(1)

    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

def ios_to_jinja2(config):
    """Convert Cisco IOS config to Jinja2 template"""
    jinja_config = []
    for line in config.splitlines():
        if line.strip().startswith('!'):
            jinja_config.append(line)
            continue

        line = re.sub(r'hostname (\S+)', 'hostname {{ hostname }}', line)
        if match := re.match(r'(interface\s+)(\S+)', line):
            line = f"{match.group(1)}{{ {match.group(2).replace('/', '_')} }}"
        line = re.sub(r'ip address (\S+) (\S+)', 'ip address {{ ip_address }} {{ subnet_mask }}', line)
        jinja_config.append(line)
    return '\n'.join(jinja_config)

def ios_to_xml(config):
    """Convert Cisco IOS config to XML"""
    root = ET.Element("ios_configuration")

    if hostname := re.search(r'hostname (\S+)', config):
        ET.SubElement(root, "hostname").text = hostname.group(1)

    interfaces = ET.SubElement(root, "interfaces")
    for intf in re.finditer(r'interface (\S+)\n(.*?)(?=\ninterface|\Z)', config, re.DOTALL):
        intf_elem = ET.SubElement(interfaces, "interface")
        ET.SubElement(intf_elem, "name").text = intf.group(1)

        if ip_match := re.search(r'ip address (\S+) (\S+)', intf.group(2)):
            ET.SubElement(intf_elem, "ip_address").text = ip_match.group(1)
            ET.SubElement(intf_elem, "subnet_mask").text = ip_match.group(2)

    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

# [Similar functions for iosxr, eos, mikrotik...]

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Network Config Converter Tool'
    )

    # Required arguments
    parser.add_argument('-f', '--file', required=True,
                      help='Input configuration file')
    parser.add_argument('-o', '--output', required=True,
                      help='Output file')
    parser.add_argument('-t', '--type', required=True,
                      choices=['jinja2', 'xml', 'json'],
                      help='Output format type')

    # OS selection flags
    os_group = parser.add_mutually_exclusive_group(required=True)
    os_group.add_argument('-j', '--junos', action='store_true',
                        help='Juniper JunOS configuration')
    os_group.add_argument('-s', '--sros', action='store_true',
                        help='Nokia SROS configuration')
    os_group.add_argument('-c', '--ios', action='store_true',
                        help='Cisco IOS configuration')
    os_group.add_argument('-x', '--iosxr', action='store_true',
                        help='Cisco IOS-XR configuration')
    os_group.add_argument('-a', '--eos', action='store_true',
                        help='Arista EOS configuration')
    os_group.add_argument('-m', '--mikrotik', action='store_true',
                        help='Mikrotik RouterOS configuration')

    return parser.parse_args()

def main():
    args = parse_arguments()

    try:
        with open(args.file, 'r') as f:
            config = f.read()

        converted = ""
        if args.junos:
            if args.type == 'jinja2':
                converted = junos_to_jinja2(config)
            elif args.type == 'xml':
                converted = junos_to_xml(config)
        elif args.sros:
            if args.type == 'jinja2':
                converted = sros_to_jinja2(config)
            elif args.type == 'xml':
                converted = sros_to_xml(config)
        elif args.ios:
            if args.type == 'jinja2':
                converted = ios_to_jinja2(config)
            elif args.type == 'xml':
                converted = ios_to_xml(config)
        # [Add similar conditions for other platforms...]

        if args.type == 'json':
            os_type = 'junos' if args.junos else \
                     'sros' if args.sros else \
                     'ios' if args.ios else \
                     'iosxr' if args.iosxr else \
                     'eos' if args.eos else \
                     'mikrotik'
            converted = json.dumps({
                "os_type": os_type,
                "config": config.splitlines()
            }, indent=2)

        with open(args.output, 'w') as f:
            f.write(converted)
        logger.info(f"Successfully converted to {args.type} -> {args.output}")
        print(f"Conversion successful. Output written to {args.output}")

    except Exception as e:
        logger.error(f"Conversion failed: {str(e)}\n{traceback.format_exc()}")
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
