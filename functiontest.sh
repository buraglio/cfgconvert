#!/bin/bash

# Test functions of all flags
run_test() {
    local os_flag=$1
    local os_name=$2
    local input_file="examples/${os_name}.cfg"

    echo "Testing ${os_name}..."

    # Test Jinja2 conversion
    ./converter.py -f "$input_file" -o "output/${os_name}.j2" -t jinja2 "${os_flag}"
    if [ $? -eq 0 ]; then
        echo "✅ ${os_name} Jinja2 conversion successful"
    else
        echo "❌ ${os_name} Jinja2 conversion failed"
    fi

    # Test XML conversion
    ./converter.py -f "$input_file" -o "output/${os_name}.xml" -t xml "${os_flag}"
    if [ $? -eq 0 ]; then
        echo "✅ ${os_name} XML conversion successful"
    else
        echo "❌ ${os_name} XML conversion failed"
    fi

    # Test JSON conversion
    ./converter.py -f "$input_file" -o "output/${os_name}.json" -t json "${os_flag}"
    if [ $? -eq 0 ]; then
        echo "✅ ${os_name} JSON conversion successful"
    else
        echo "❌ ${os_name} JSON conversion failed"
    fi

    echo ""
}

# Create output directory
mkdir -p output

# Run tests
run_test "-j" "junos"
run_test "-s" "sros"
run_test "-c" "ios"
run_test "-x" "iosxr"
run_test "-a" "eos"
run_test "-m" "mikrotik"

echo "All tests completed. Check output/ directory for results."
