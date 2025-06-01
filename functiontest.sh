#!/bin/bash
# Initialize counters
passed=0
failed=0

run_test() {
    local os_flag=$1
    local os_name=$2
    local input_file="examples/${os_name}.cfg"

    echo "Testing ${os_name}..."

    # Test Jinja2 conversion
    if ./cfgconvert.py -f "$input_file" -o "output/${os_name}.j2" -t jinja2 $os_flag >/dev/null 2>&1; then
        echo "✅ ${os_name} Jinja2 conversion successful"
        ((passed++))
    else
        echo "❌ ${os_name} Jinja2 conversion failed"
        ((failed++))
    fi

    # Test XML conversion
    if ./cfgconvert.py -f "$input_file" -o "output/${os_name}.xml" -t xml $os_flag >/dev/null 2>&1; then
        echo "✅ ${os_name} XML conversion successful"
        ((passed++))
    else
        echo "❌ ${os_name} XML conversion failed"
        ((failed++))
    fi

    # Test JSON conversion
    if ./cfgconvert.py -f "$input_file" -o "output/${os_name}.json" -t json $os_flag >/dev/null 2>&1; then
        echo "✅ ${os_name} JSON conversion successful"
        ((passed++))
    else
        echo "❌ ${os_name} JSON conversion failed"
        ((failed++))
    fi

    echo ""
}

# Create output directory
mkdir -p output

# Run tests
echo "Starting network config cfgconvert tests..."
echo "========================================"

run_test "-j" "junos"
run_test "-s" "sros"
run_test "-c" "ios"
run_test "-x" "iosxr"
run_test "-a" "eos"
run_test "-m" "mikrotik"

# Summary
echo "Test Summary:"
echo "============="
echo "Total tests passed: ${passed}"
echo "Total tests failed: ${failed}"
echo ""

if [ $failed -eq 0 ]; then
    echo "✅ All tests passed successfully!"
    exit 0
else
    echo "❌ Some tests failed. Check the output for details."
    exit 1
fi
