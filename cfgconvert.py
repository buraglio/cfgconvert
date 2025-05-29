#!/usr/bin/env python3
import os
import sys
import re
import argparse
import daemon
import lockfile
from flask import Flask, request, render_template, send_file, session
from xml.etree import ElementTree as ET
from io import BytesIO, StringIO
import zipfile
import json
from functools import lru_cache

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Secure random key for production

# ... [Previous OS detection and conversion functions remain unchanged] ...

def convert_config(config, output_format):
    """Handle conversion for both web and CLI interfaces"""
    os_type = detect_os(config)

    if output_format == 'jinja2':
        if os_type == 'ios':
            return ios_to_jinja2(config)
        elif os_type == 'iosxr':
            return iosxr_to_jinja2(config)
        # ... [other OS conversions] ...
    elif output_format == 'xml':
        return to_xml(config, os_type)
    elif output_format == 'json':
        return to_json(config, os_type)
    else:
        raise ValueError(f"Unsupported format: {output_format}")

def run_as_daemon(pid_file):
    """Run the Flask app as a daemon"""
    context = daemon.DaemonContext(
        pidfile=lockfile.FileLock(pid_file),
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    with context:
        app.run(host='0.0.0.0', port=5000)

def handle_cli_conversion(input_file, output_file, output_format):
    """Handle command line conversion"""
    try:
        with open(input_file, 'r') as f:
            config = f.read()

        converted = convert_config(config, output_format)

        if output_file:
            with open(output_file, 'w') as f:
                f.write(converted)
            print(f"Successfully converted to {output_format} -> {output_file}")
        else:
            print(converted)

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Network Config Converter Tool',
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Web server options
    parser.add_argument('-d', '--daemon', 
                        action='store_true',
                        help='Run as daemon with PID file')
    parser.add_argument('-p', '--pid-file',
                        default='/var/run/config_converter.pid',
                        help='PID file location (default: /var/run/config_converter.pid)')

    # CLI conversion options
    parser.add_argument('-f', '--file',
                        help='Input configuration file for CLI conversion')
    parser.add_argument('-o', '--output',
                        help='Output file (default: stdout)')
    parser.add_argument('-t', '--type',
                        choices=['jinja2', 'xml', 'json'],
                        default='jinja2',
                        help='Output format type (default: jinja2)')

    return parser.parse_args()

# ... [Previous Flask routes remain unchanged] ...

if __name__ == '__main__':
    args = parse_arguments()

    if args.file:
        # CLI mode
        handle_cli_conversion(args.file, args.output, args.type)
    elif args.daemon:
        # Daemon mode
        run_as_daemon(args.pid_file)
    else:
        # Interactive web mode
        app.run(host='0.0.0.0', port=5000, debug=True)

