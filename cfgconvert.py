#!/usr/bin/env python3
import os
import sys
import re
import argparse
import logging
from xml.etree import ElementTree as ET
import json
from io import BytesIO

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/config_converter.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def detect_os(config):
    """Enhanced OS detection with better pattern matching"""
    if re.search(r'^!!\s+TiMOS-', config, re.MULTILINE):
        return 'sros'
    elif re.search(r'^## Last commit:', config, re.MULTILINE) or 'version junos' in config.lower():
        return 'junos'
    elif re.search(r'^!Command:.*IOS-XR', config, re.MULTILINE):
        return 'iosxr'
    elif 'hostname' in config.lower() or 'interface' in config.lower():
        return 'ios'
    return 'unknown'

def junos_to_jinja2(config):
    """Proper JunOS to Jinja2 conversion with hierarchical support"""
    jinja_config = []
    current_path = []

    for line in config.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            jinja_config.append(line)
            continue

        if line.startswith('set'):
            parts = line[4:].split()
            if not parts:
                continue

            # Handle hierarchical paths
            path_parts = []
            i = 0
            while i < len(parts):
                if parts[i] == 'set':
                    i += 1
                    continue
                path_parts.append(parts[i])
                i += 1

            # Convert variables
            var_path = []
            for part in path_parts:
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

def sros_to_jinja2(config):
    """Proper SROS to Jinja2 conversion with quoted strings"""
    jinja_config = []
    in_interface = False

    for line in config.splitlines():
        line = line.strip()
        if not line:
            jinja_config.append(line)
            continue

        # Handle system name
        if line.startswith('configure system name'):
            jinja_config.append('configure system name "{{ system_name }}"')
            continue

        # Handle interfaces
        if line.startswith('configure interface'):
            match = re.match(r'configure interface "([^"]+)"', line)
            if match:
                intf_name = match.group(1).replace('-', '_')
                jinja_config.append(f'configure interface "{{{{ {intf_name} }}}}"')
                in_interface = True
                continue

        # Handle IP addresses
        if in_interface and 'address' in line:
            match = re.match(r'address (\S+)', line)
            if match:
                jinja_config.append('address {{ ip_address }}')
                continue

        jinja_config.append(line)

    return '\n'.join(jinja_config)

def junos_to_xml(config):
    """Proper JunOS to XML conversion with hierarchy"""
    root = ET.Element("junos_configuration")

    # Extract system info
    system = ET.SubElement(root, "system")
    hostname = re.search(r'set system host-name (\S+)', config)
    if hostname:
        ET.SubElement(system, "hostname").text = hostname.group(1)

    # Extract interfaces
    interfaces = ET.SubElement(root, "interfaces")
    for intf in re.finditer(r'set interfaces (\S+) unit (\d+)', config):
        intf_elem = ET.SubElement(interfaces, "interface")
        ET.SubElement(intf_elem, "name").text = intf.group(1)
        ET.SubElement(intf_elem, "unit").text = intf.group(2)

        # Find IP address
        ip_match = re.search(
            r'set interfaces {} unit {} family inet address (\S+)'.format(
                re.escape(intf.group(1)), 
                re.escape(intf.group(2))
            ), 
            config
        )
        if ip_match:
            ET.SubElement(intf_elem, "ip_address").text = ip_match.group(1)

    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

def sros_to_xml(config):
    """Proper SROS to XML conversion with quoted strings"""
    root = ET.Element("sros_configuration")

    # Extract system info
    system = ET.SubElement(root, "system")
    name = re.search(r'configure system name "([^"]+)"', config)
    if name:
        ET.SubElement(system, "name").text = name.group(1)

    # Extract interfaces
    interfaces = ET.SubElement(root, "interfaces")
    for intf in re.finditer(r'configure interface "([^"]+)"', config):
        intf_elem = ET.SubElement(interfaces, "interface")
        ET.SubElement(intf_elem, "name").text = intf.group(1)

        # Find IP address
        ip_match = re.search(
            r'configure router interface "{}"\s+address (\S+)'.format(
                re.escape(intf.group(1))
            ), 
            config
        )
        if ip_match:
            ET.SubElement(intf_elem, "ip_address").text = ip_match.group(1)

    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Network Config Converter Tool'
    )
    parser.add_argument('-f', '--file', required=True,
                      help='Input configuration file')
    parser.add_argument('-o', '--output', required=True,
                      help='Output file')
    parser.add_argument('-t', '--type', required=True,
                      choices=['jinja2', 'xml', 'json'],
                      help='Output format type')
    return parser.parse_args()

def main():
    args = parse_arguments()

    try:
        with open(args.file, 'r') as f:
            config = f.read()

        os_type = detect_os(config)
        logger.info(f"Detected OS type: {os_type}")

        if args.type == 'jinja2':
            if os_type == 'junos':
                converted = junos_to_jinja2(config)
            elif os_type == 'sros':
                converted = sros_to_jinja2(config)
            else:
                raise ValueError(f"Unsupported OS type for Jinja2: {os_type}")
        elif args.type == 'xml':
            if os_type == 'junos':
                converted = junos_to_xml(config)
            elif os_type == 'sros':
                converted = sros_to_xml(config)
            else:
                raise ValueError(f"Unsupported OS type for XML: {os_type}")
        elif args.type == 'json':
            converted = json.dumps({
                "os_type": os_type,
                "config": config.splitlines()
            }, indent=2)
        else:
            raise ValueError(f"Unsupported output format: {args.type}")

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
