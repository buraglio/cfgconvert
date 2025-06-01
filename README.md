# Network Config Converter

A tool to convert network device configurations between native format, Jinja2 templates, and XML/JSON.

## Features

- Convert configurations from:
  - Juniper JunOS (`-j`)
  - Nokia SROS (`-s`)
  - Cisco IOS (`-c`)
  - Cisco IOS-XR (`-x`)
  - Arista EOS (`-a`)
  - Mikrotik RouterOS (`-m`)
- Output formats:
  - Jinja2 templates (`-t jinja2`)
  - XML (`-t xml`)
  - JSON (`-t json`)

## Installation

### Linux/macOS

1. **Prerequisites**:
   - Python 3.8+
   - pip

2. **Installation**:
   ```bash
   git clone https://github.com/yourrepo/network-config-converter.git
   cd network-config-converter
   pip install -r requirements.txt
   chmod +x converter.py test_converter.sh

## Usage

```
./converter.py -f input.cfg -o output.j2 -t jinja2 -j  # JunOS to Jinja2
./converter.py -f input.cfg -o output.xml -t xml -s    # SROS to XML
./converter.py -f input.cfg -o output.json -t json -c  # IOS to JSON
```

### Options

```
Flag	Description	Values
-f	Input configuration file	Path to file
-o	Output file	Path to file
-t	Output type	jinja2, xml, or json
-j	Juniper JunOS configuration	N/A
-s	Nokia SROS configuration	N/A
-c	Cisco IOS configuration	N/A
-x	Cisco IOS-XR configuration	N/A
-a	Arista EOS configuration	N/A
-m	Mikrotik RouterOS configuration	N/A
```

## Examples

Convert JunOS to Jinja2:

```
./converter.py -f examples/junos.cfg -o junos_template.j2 -t jinja2 -j
```

Convert SROS to XML:

```
./converter.py -f examples/sros.cfg -o sros_config.xml -t xml -s
```

Run Unit Tests:

```
./test_converter.sh
```