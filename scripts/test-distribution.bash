#!/bin/bash
# scripts/test-distribution.bash
#
# Test script for gracenote2epg package distribution
# Tests wheel and source distribution builds, installation, and functionality
#
# Usage:
#   ./scripts/test-distribution.bash [options]
#
# Options:
#   --basic          Basic test (basic functionality only)
#   --full           Full test including translations and extended features (default)
#   --wheel-only     Test wheel distribution only
#   --source-only    Test source distribution only
#   --clean-only     Clean builds without testing
#   --no-color       Disable colored output
#   --help           Show this help

set -e  # Exit on any error

# Colors for output
if [[ "${NO_COLOR:-}" != "1" && -t 1 ]]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    BOLD='\033[1m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    BOLD=''
    NC=''
fi

# Default options
BASIC_TEST=false
TEST_WHEEL=true
TEST_SOURCE=true
CLEAN_ONLY=false

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${BOLD}=== $1 ===${NC}"
}

show_help() {
    cat << EOF
Test script for gracenote2epg package distribution

Usage: $0 [options]

Options:
  --quick          Quick test (basic functionality only)
  --full           Full test including translations and extended features (default)
  --wheel-only     Test wheel distribution only
  --source-only    Test source distribution only
  --clean-only     Clean builds without testing
  --no-color       Disable colored output
  --help           Show this help

Examples:
  $0                    # Full test of both distributions
  $0 --basic           # Basic test
  $0 --wheel-only      # Test wheel only
  $0 --clean-only      # Clean builds only

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --basic)
            BASIC_TEST=true
            shift
            ;;
        --full)
            BASIC_TEST=false
            shift
            ;;
        --wheel-only)
            TEST_WHEEL=true
            TEST_SOURCE=false
            shift
            ;;
        --source-only)
            TEST_WHEEL=false
            TEST_SOURCE=true
            shift
            ;;
        --clean-only)
            CLEAN_ONLY=true
            shift
            ;;
        --no-color)
            RED=''
            GREEN=''
            YELLOW=''
            BLUE=''
            BOLD=''
            NC=''
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check dependencies
check_dependencies() {
    log_step "Checking Dependencies"

    local missing_deps=()

    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi

    if ! python3 -m pip --version &> /dev/null; then
        missing_deps+=("pip")
    fi

    if ! python3 -c "import build" 2>/dev/null; then
        log_warning "python build module not found, installing..."
        pip install build
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi

    log_success "All dependencies available"
}

# Clean old builds
clean_builds() {
    log_step "Cleaning Previous Builds"

    # Exit any existing venv
    if [[ "${VIRTUAL_ENV:-}" ]]; then
        log_info "Exiting current virtual environment: $VIRTUAL_ENV"
        deactivate 2>/dev/null || true
    fi

    # Remove test environments
    for test_env in ~/test_env_wheel ~/test_env_source ~/test_env; do
        if [[ -d "$test_env" ]]; then
            log_info "Removing test environment: $test_env"
            rm -rf "$test_env"
        fi
    done

    # Remove build artifacts
    for dir in build dist *.egg-info; do
        if [[ -d "$dir" ]] || [[ -f "$dir" ]]; then
            log_info "Removing: $dir"
            rm -rf "$dir"
        fi
    done

    log_success "Build cleanup completed"
}

# Build distributions
build_distributions() {
    log_step "Building Distributions"

    log_info "Building wheel and source distributions..."
    python3 -m build

    # Verify files were created
    local wheel_count=$(find dist/ -name "*.whl" | wc -l)
    local source_count=$(find dist/ -name "*.tar.gz" | wc -l)

    if [[ $wheel_count -eq 0 ]]; then
        log_error "No wheel file created"
        exit 1
    fi

    if [[ $source_count -eq 0 ]]; then
        log_error "No source distribution created"
        exit 1
    fi

    log_success "Built $wheel_count wheel(s) and $source_count source distribution(s)"

    # Show file sizes
    log_info "Distribution files:"
    ls -lh dist/
}

# Verify package contents
verify_package_contents() {
    local dist_file="$1"
    local dist_type="$2"

    log_info "Verifying $dist_type contents: $(basename "$dist_file")"

    # Check for locale files (the main issue we're fixing)
    local locale_files
    if [[ "$dist_type" == "wheel" ]]; then
        locale_files=$(python3 -m zipfile -l "$dist_file" | grep -c "locales.*\.po" || echo "0")
    else  # source
        locale_files=$(tar -tzf "$dist_file" | grep -c "locales.*\.po" || echo "0")
    fi

    if [[ $locale_files -gt 0 ]]; then
        log_success "Found $locale_files locale files in $dist_type"
    else
        log_error "No locale files found in $dist_type - translation system will not work"
        return 1
    fi

    # Check for essential files
    local essential_files=("gracenote2epg/__init__.py" "gracenote2epg/main.py" "tv_grab_gracenote2epg")
    for file in "${essential_files[@]}"; do
        if [[ "$dist_type" == "wheel" ]]; then
            if ! python3 -m zipfile -l "$dist_file" | grep -q "$file"; then
                log_error "Missing essential file in wheel: $file"
                return 1
            fi
        else  # source
            if ! tar -tzf "$dist_file" | grep -q "$file"; then
                log_error "Missing essential file in source: $file"
                return 1
            fi
        fi
    done

    log_success "$dist_type package contents verified"
}

# Test installation and basic functionality
test_installation() {
    local dist_file="$1"
    local dist_type="$2"
    local env_dir="$3"

    log_step "Testing $dist_type Installation"

    # Create virtual environment
    log_info "Creating test environment: $env_dir"
    python3 -m venv "$env_dir"
    source "$env_dir/bin/activate"

    # Upgrade pip
    log_info "Upgrading pip..."
    pip install --upgrade pip --quiet

    # Install package
    log_info "Installing gracenote2epg from $dist_type..."
    if [[ "$BASIC_TEST" == "true" ]]; then
        pip install "$dist_file" --quiet
    else
        pip install "${dist_file}[full]" --quiet
    fi

    # Test basic commands
    log_info "Testing basic commands..."

    # Test version commands
    if ! gracenote2epg --version >/dev/null 2>&1; then
        log_error "gracenote2epg --version failed"
        return 1
    fi

    if ! tv_grab_gracenote2epg --version >/dev/null 2>&1; then
        log_error "tv_grab_gracenote2epg --version failed"
        return 1
    fi

    # Test capabilities
    if ! gracenote2epg --capabilities >/dev/null 2>&1; then
        log_error "gracenote2epg --capabilities failed"
        return 1
    fi

    if ! tv_grab_gracenote2epg --capabilities >/dev/null 2>&1; then
        log_error "tv_grab_gracenote2epg --capabilities failed"
        return 1
    fi

    log_success "Basic commands working"

    # Test imports
    log_info "Testing Python imports..."
    python3 -c "
import gracenote2epg
import gracenote2epg.config
import gracenote2epg.downloader
import gracenote2epg.xmltv
import gracenote2epg.dictionaries
print('Core imports: OK')
"

    # Test translation system if not basic test
    if [[ "$BASIC_TEST" == "false" ]]; then
        log_info "Testing translation system..."
        python3 -c "
import gracenote2epg.dictionaries as gd
print('Translation manager initializing...')
tm = gd.get_translation_manager()
print('Available languages:', tm.get_available_languages())
stats = tm.get_statistics()
print('Translation statistics:', stats)
if len(stats) > 0:
    print('✓ Translations loaded successfully')
else:
    print('⚠ No translations found - but this is non-fatal')
"

        # Test language detection if available
        python3 -c "
try:
    import langdetect
    print('✓ Language detection available')
except ImportError:
    print('ℹ Language detection not available (install with [full])')

try:
    import polib
    print('✓ Translation files support available')
except ImportError:
    print('ℹ Translation files support not available (install with [full])')
"
    fi

    # Test lineup detection
    log_info "Testing lineup detection..."
    if ! gracenote2epg --show-lineup --zip 92101 >/dev/null 2>&1; then
        log_error "Lineup detection test failed"
        return 1
    fi

    log_success "$dist_type installation and functionality test passed"

    # Deactivate environment
    deactivate
}

# Run full test suite
run_tests() {
    # Find distribution files
    local wheel_file
    local source_file

    if [[ "$TEST_WHEEL" == "true" ]]; then
        wheel_file=$(find dist/ -name "*.whl" | head -1)
        if [[ -z "$wheel_file" ]]; then
            log_error "No wheel file found in dist/"
            exit 1
        fi
    fi

    if [[ "$TEST_SOURCE" == "true" ]]; then
        source_file=$(find dist/ -name "*.tar.gz" | head -1)
        if [[ -z "$source_file" ]]; then
            log_error "No source file found in dist/"
            exit 1
        fi
    fi

    # Verify package contents
    if [[ "$TEST_WHEEL" == "true" ]]; then
        verify_package_contents "$wheel_file" "wheel"
    fi

    if [[ "$TEST_SOURCE" == "true" ]]; then
        verify_package_contents "$source_file" "source"
    fi

    # Test installations
    if [[ "$TEST_WHEEL" == "true" ]]; then
        test_installation "$wheel_file" "wheel" ~/test_env_wheel
    fi

    if [[ "$TEST_SOURCE" == "true" ]]; then
        test_installation "$source_file" "source" ~/test_env_source
    fi
}

# Main execution
main() {
    log_step "gracenote2epg Distribution Test"

    if [[ "$BASIC_TEST" == "true" ]]; then
        log_info "Running BASIC test (basic functionality only)"
    else
        log_info "Running FULL test (including translations and extended features)"
    fi

    check_dependencies
    clean_builds

    if [[ "$CLEAN_ONLY" == "true" ]]; then
        log_success "Clean completed successfully"
        exit 0
    fi

    build_distributions
    run_tests

    log_step "Test Summary"
    log_success "All tests completed successfully!"

    if [[ "$TEST_WHEEL" == "true" && "$TEST_SOURCE" == "true" ]]; then
        log_info "Both wheel and source distributions are working correctly"
    elif [[ "$TEST_WHEEL" == "true" ]]; then
        log_info "Wheel distribution is working correctly"
    elif [[ "$TEST_SOURCE" == "true" ]]; then
        log_info "Source distribution is working correctly"
    fi

    log_info "Ready for distribution!"
}

# Run main function
main "$@"
