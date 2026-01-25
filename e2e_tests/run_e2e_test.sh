#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# Parse arguments
TEST_PATTERN="${1:-all}"

echo "=========================================="
echo "HCL Processor E2E Test"
echo "=========================================="
echo ""

# Check AWS credentials
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "ERROR: AWS credentials not configured."
    echo "Please configure AWS credentials using one of the following methods:"
    echo "  - aws configure"
    echo "  - export AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    echo "  - Use AWS SSO (aws sso login)"
    exit 1
fi

echo "AWS credentials verified."
echo ""

run_test() {
    local config_file=$1
    local test_name=$2
    local output_json=$3
    local output_md=$4

    echo "=========================================="
    echo "Running: $test_name"
    echo "Config:  $config_file"
    echo "=========================================="

    # Clean up previous output
    rm -f "$output_json" "$output_md"

    # Run the tool
    if poetry run hcl-processor --config_file "$config_file" --debug; then
        echo ""
        echo "[$test_name] PASSED"
    else
        echo ""
        echo "[$test_name] FAILED!"
        return 1
    fi

    # Check output files
    echo ""
    echo "Checking output files..."

    if [ -f "$output_json" ]; then
        echo "  [OK] $(basename "$output_json") generated"
    else
        echo "  [FAIL] $(basename "$output_json") not found"
        return 1
    fi

    if [ -f "$output_md" ]; then
        echo "  [OK] $(basename "$output_md") generated"
    else
        echo "  [FAIL] $(basename "$output_md") not found"
        return 1
    fi

    echo ""
    return 0
}

FAILED_TESTS=()

case "$TEST_PATTERN" in
    "basic"|"folder")
        echo "Running: Basic (folder) pattern test"
        run_test "e2e_tests/e2e_config.yaml" "Basic (folder)" \
            "e2e_tests/output/output.json" "e2e_tests/output/output.md" || FAILED_TESTS+=("basic")
        ;;

    "files"|"resource")
        echo "Running: Files pattern test"
        run_test "e2e_tests/e2e_config_files.yaml" "Files pattern" \
            "e2e_tests/output/output_files.json" "e2e_tests/output/output_files.md" || FAILED_TESTS+=("files")
        ;;

    "chunk"|"failback")
        echo "Running: Chunk (failback) pattern test"
        run_test "e2e_tests/e2e_config_chunk.yaml" "Chunk (failback)" \
            "e2e_tests/output/output_chunk.json" "e2e_tests/output/output_chunk.md" || FAILED_TESTS+=("chunk")
        ;;

    "all")
        echo "Running all E2E test patterns..."
        echo ""

        # Test 1: Basic (folder) pattern
        run_test "e2e_tests/e2e_config.yaml" "Basic (folder)" \
            "e2e_tests/output/output.json" "e2e_tests/output/output.md" || FAILED_TESTS+=("basic")

        # Test 2: Files pattern
        run_test "e2e_tests/e2e_config_files.yaml" "Files pattern" \
            "e2e_tests/output/output_files.json" "e2e_tests/output/output_files.md" || FAILED_TESTS+=("files")

        # Test 3: Chunk (failback) pattern
        run_test "e2e_tests/e2e_config_chunk.yaml" "Chunk (failback)" \
            "e2e_tests/output/output_chunk.json" "e2e_tests/output/output_chunk.md" || FAILED_TESTS+=("chunk")
        ;;

    *)
        echo "Usage: $0 [basic|files|chunk|all]"
        echo ""
        echo "Test patterns:"
        echo "  basic  - Test folder pattern (resource_data.folder)"
        echo "  files  - Test files pattern (resource_data.files)"
        echo "  chunk  - Test chunk processing (failback enabled)"
        echo "  all    - Run all patterns (default)"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
if [ ${#FAILED_TESTS[@]} -eq 0 ]; then
    echo "All E2E tests passed!"
else
    echo "FAILED TESTS: ${FAILED_TESTS[*]}"
    exit 1
fi
echo "=========================================="
echo ""

# Cleanup
echo "Cleaning up..."
rm -rf "$SCRIPT_DIR/output" "$SCRIPT_DIR/__pycache__"
echo "Done."
