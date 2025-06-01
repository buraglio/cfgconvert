#!/usr/bin/env python3
# 1.0 Rework this to remove the web junk because it's overly complicated. 
# Tear out the auto-detect code and create flags for each configuration type. 
# This is crude 
import os
import sys
import re
import argparse
import logging
from xml.etree import ElementTree as ET
import json

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

def ios_to_jinja2(config):
    """Convert Cisco IOS config to Jinja2 template"""
    jinja_config = []
    for line in config.splitlines():
        if line.strip().startswith('!'):
            jinja_config.append(line)
            continue

        # Handle hostname replacement
        if line.strip().startswith('hostname'):
            jinja_config.append(re.sub(r'hostname (\S+)', 'hostname {{ hostname }}', line))
            continue

        # Handle interface blocks
        if line.strip().startswith('interface'):
            intf_match = re.match(r'(interface\s+)(\S+)', line)
            if intf_match:
                jinja_config.append("{} {{ {} }}".format(
                    intf_match.group(1),
                    intf_match.group(2).strip('"').replace('-', '_')
                ))
                continue

        # Handle IP addresses
        if 'ip address' in line:
            ip_match = re.match(r'(\s*ip\s+address\s+)(\S+)\s+(\S+)', line)
            if ip_match:
                jinja_config.append("{} {{ ip_address }} {{ subnet_mask }}".format(
                    ip_match.group(1)
                ))
                continue

        # Preserve all other lines as-is
        jinja_config.append(line)

    return '\n'.join(jinja_config)

def iosxr_to_jinja2(config):
    """Convert IOS-XR config to Jinja2 template"""
    jinja_config = []
    for line in config.splitlines():
        if line.strip().startswith('!'):
            jinja_config.append(line)
            continue

        if line.strip().startswith('hostname'):
            jinja_config.append(re.sub(r'hostname (\S+)', 'hostname {{ hostname }}', line))
            continue

        if line.strip().startswith('interface'):
            intf_match = re.match(r'(interface\s+)(\S+)', line)
            if intf_match:
                jinja_config.append("{} {{ {} }}".format(
                    intf_match.group(1),
                    intf_match.group(2).strip('"').replace('-', '_')
                ))
                continue

        if 'ipv4 address' in line:
            ip_match = re.match(r'(\s*ipv4\s+address\s+)(\S+)\s+(\S+)', line)
            if ip_match:
                jinja_config.append("{} {{ ip_address }} {{ subnet_mask }}".format(
                    ip_match.group(1)
                ))
                continue

        jinja_config.append(line)

    return '\n'.join(jinja_config)

def junos_to_jinja2(config):
    """Convert JunOS config to Jinja2 template"""
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

def eos_to_jinja2(config):
    """Convert Arista EOS config to Jinja2 template"""
    jinja_config = []
    for line in config.splitlines():
        if line.strip().startswith('!'):
            jinja_config.append(line)
            continue

        if line.strip().startswith('hostname'):
            jinja_config.append(re.sub(r'hostname (\S+)', 'hostname {{ hostname }}', line))
            continue

        if line.strip().startswith('interface'):
            intf_match = re.match(r'(interface\s+)(\S+)', line)
            if intf_match:
                jinja_config.append("{} {{ {} }}".format(
                    intf_match.group(1),
                    intf_match.group(2).strip('"').replace('-', '_')
                ))
                continue

        if 'ip address' in line:
            ip_match = re.match(r'(\s*ip\s+address\s+)(\S+)\s+(\S+)', line)
            if ip_match:
                jinja_config.append("{} {{ ip_address }} {{ subnet_mask }}".format(
                    ip_match.group(1)
                ))
                continue

        jinja_config.append(line)

    return '\n'.join(jinja_config)

def mikrotik_to_jinja2(config):
    """Convert Mikrotik config to Jinja2 template"""
    jinja_config = []
    for line in config.splitlines():
        if line.strip().startswith('#'):
            jinja_config.append(line)
            continue

        # Handle interface names
        if '/interface' in line and 'add name=' in line:
            match = re.search(r'add name=([^\s]+)', line)
            if match:
                jinja_config.append(line.replace(match.group(1), f"{{{{ {match.group(1).replace('-', '_')} }}}}"))
                continue

        # Handle IP addresses
        if 'add address=' in line:
            match = re.search(r'add address=([^\s]+)', line)
            if match:
                jinja_config.append(line.replace(match.group(1), "{{ ip_address }}"))
                continue

        jinja_config.append(line)

    return '\n'.join(jinja_config)

def ios_to_xml(config):
    """Convert IOS config to XML"""
    root = ET.Element("ios_configuration")

    # Extract hostname
    hostname = re.search(r'hostname (\S+)', config)
    if hostname:
        ET.SubElement(root, "hostname").text = hostname.group(1)

    # Extract interfaces
    interfaces = ET.SubElement(root, "interfaces")
    for intf in re.finditer(r'interface (\S+)\n(.*?)(?=\ninterface|\Z)', config, re.DOTALL):
        intf_elem = ET.SubElement(interfaces, "interface")
        ET.SubElement(intf_elem, "name").text = intf.group(1)

        ip_match = re.search(r'ip address (\S+) (\S+)', intf.group(2))
        if ip_match:
            ET.SubElement(intf_elem, "ip_address").text = ip_match.group(1)
            ET.SubElement(intf_elem, "subnet_mask").text = ip_match.group(2)

    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

def iosxr_to_xml(config):
    """Convert IOS-XR config to XML"""
    root = ET.Element("iosxr_configuration")

    # Extract hostname
    hostname = re.search(r'hostname (\S+)', config)
    if hostname:
        ET.SubElement(root, "hostname").text = hostname.group(1)

    # Extract interfaces
    interfaces = ET.SubElement(root, "interfaces")
    for intf in re.finditer(r'interface (\S+)\n(.*?)(?=\ninterface|\Z)', config, re.DOTALL):
        intf_elem = ET.SubElement(interfaces, "interface")
        ET.SubElement(intf_elem, "name").text = intf.group(1)

        ip_match = re.search(r'ipv4 address (\S+) (\S+)', intf.group(2))
        if ip_match:
            ET.SubElement(intf_elem, "ip_address").text = ip_match.group(1)
            ET.SubElement(intf_elem, "subnet_mask").text = ip_match.group(2)

    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

def junos_to_xml(config):
    """Convert JunOS config to XML"""
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

def eos_to_xml(config):
    """Convert Arista EOS config to XML"""
    root = ET.Element("eos_configuration")

    # Extract hostname
    hostname = re.search(r'hostname (\S+)', config)
    if hostname:
        ET.SubElement(root, "hostname").text = hostname.group(1)

    # Extract interfaces
    interfaces = ET.SubElement(root, "interfaces")
    for intf in re.finditer(r'interface (\S+)\n(.*?)(?=\ninterface|\Z)', config, re.DOTALL):
        intf_elem = ET.SubElement(interfaces, "interface")
        ET.SubElement(intf_elem, "name").text = intf.group(1)

        ip_match = re.search(r'ip address (\S+) (\S+)', intf.group(2))
        if ip_match:
            ET.SubElement(intf_elem, "ip_address").text = ip_match.group(1)
            ET.SubElement(intf_elem, "subnet_mask").text = ip_match.group(2)

    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

def mikrotik_to_xml(config):
    """Convert Mikrotik config to XML"""
    root = ET.Element("mikrotik_configuration")

    # Extract interfaces
    interfaces = ET.SubElement(root, "interfaces")
    for intf in re.finditer(r'/interface\nadd name=([^\s]+)', config):
        intf_elem = ET.SubElement(interfaces, "interface")
        ET.SubElement(intf_elem, "name").text = intf.group(1)

    # Extract IP addresses
    addresses = ET.SubElement(root, "addresses")
    for addr in re.finditer(r'add address=([^\s]+)', config):
        addr_elem = ET.SubElement(addresses, "address")
        addr_elem.text = addr.group(1)

    return ET.tostring(root, encoding='utf-8', method='xml').decode('utf-8')

def parse_arguments():
    """Parse command line arguments with OS-specific flags"""
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

    # OS selection flags (mutually exclusive)
    os_group = parser.add_mutually_exclusive_group(required=True)
    os_group.add_argument('-c', '--cisco', action='store_true',
                        help='Cisco IOS configuration')
    os_group.add_argument('-x', '--iosxr', action='store_true',
                        help='Cisco IOS-XR configuration')
    os_group.add_argument('-j', '--junos', action='store_true',
                        help='Juniper JunOS configuration')
    os_group.add_argument('-a', '--arista', action='store_true',
                        help='Arista EOS configuration')
    os_group.add_argument('-m', '--mikrotik', action='store_true',
                        help='Mikrotik RouterOS configuration')

    return parser.parse_args()

def main():
    args = parse_arguments()

    try:
        with open(args.file, 'r') as f:
            config = f.read()

        # Determine conversion functions based on OS and type
        if args.cisco:
            if args.type == 'jinja2':
                converted = ios_to_jinja2(config)
            elif args.type == 'xml':
                converted = ios_to_xml(config)
        elif args.iosxr:
            if args.type == 'jinja2':
                converted = iosxr_to_jinja2(config)
            elif args.type == 'xml':
                converted = iosxr_to_xml(config)
        elif args.junos:
            if args.type == 'jinja2':
                converted = junos_to_jinja2(config)
            elif args.type == 'xml':
                converted = junos_to_xml(config)
        elif args.arista:
            if args.type == 'jinja2':
                converted = eos_to_jinja2(config)
            elif args.type == 'xml':
                converted = eos_to_xml(config)
        elif args.mikrotik:
            if args.type == 'jinja2':
                converted = mikrotik_to_jinja2(config)
            elif args.type == 'xml':
                converted = mikrotik_to_xml(config)

        if args.type == 'json':
            os_type = 'ios' if args.cisco else \
                     'iosxr' if args.iosxr else \
                     'junos' if args.junos else \
                     'eos' if args.arista else \
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
