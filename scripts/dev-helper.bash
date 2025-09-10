#!/bin/bash
# scripts/dev-helper.bash
#
# Development helper script for gracenote2epg
# Provides common development tasks and shortcuts
#
# Usage:
#   ./scripts/dev-helper.bash <command> [options]
#
# Commands:
#   clean        Clean all build artifacts and caches
#   format       Format code with black
#   autofix      Auto-fix imports and common issues with autoflake
#   lint         Run linting with flake8
#   test-basic   Basic functionality test
#   test-full    Full distribution test
#   install-dev  Install in development mode
#   check-deps   Check and install development dependencies
#   show-dist    Show current distribution files
#   help         Show this help

set -e

# Colors
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'
    BLUE='\033[0;34m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    GREEN='' BLUE='' YELLOW='' RED='' BOLD='' NC=''
fi

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }

show_help() {
    cat << EOF
Development helper script for gracenote2epg

Usage: $0 <command> [options]

Commands:
  clean        Clean all build artifacts and caches
  format       Format code with black
  autofix      Auto-fix imports and common issues with autoflake
  lint         Run linting with flake8
  test-basic   Basic functionality test
  test-full    Full distribution test
  install-dev  Install in development mode
  check-deps   Check and install development dependencies
  show-dist    Show current distribution files
  help         Show this help

Examples:
  $0 clean               # Clean everything
  $0 autofix             # Auto-fix common issues
  $0 format              # Format code
  $0 test-basic          # Quick test
  $0 install-dev         # Install for development

EOF
}

cmd_clean() {
    log_info "Cleaning build artifacts and caches..."

    # Python caches
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    find . -type f -name "*.pyd" -delete 2>/dev/null || true

    # Build artifacts
    rm -rf build/ dist/ *.egg-info/

    # Test environments
    rm -rf ~/test_env ~/test_env_wheel ~/test_env_source

    log_success "Cleanup completed"
}

cmd_autofix() {
    log_info "Auto-fixing imports and common issues with autoflake..."

    # Install autoflake if not present
    if ! command -v autoflake &> /dev/null; then
        log_warning "autoflake not found, installing..."
        pip install autoflake
    fi

    # Remove unused imports and variables
    log_info "Removing unused imports and variables..."
    autoflake --remove-unused-variables --remove-all-unused-imports --recursive --in-place gracenote2epg/
    autoflake --remove-unused-variables --remove-all-unused-imports --in-place tv_grab_gracenote2epg

    log_info "Fixing specific code issues..."
    # Fix bare except clauses
    find gracenote2epg/ -name "*.py" -exec sed -i 's/except:[[:space:]]*$/except Exception:/g' {} \; 2>/dev/null || true
    # Fix whitespace in tv_grab_gracenote2epg
    sed -i 's/[[:space:]]*$//' tv_grab_gracenote2epg 2>/dev/null || true

    log_success "Auto-fixes completed"
}

cmd_format() {
    log_info "Formatting code with black..."

    if ! command -v black &> /dev/null; then
        log_warning "black not found, installing..."
        pip install black
    fi

    # Use same line length as flake8 configuration
    black --line-length 100 gracenote2epg/ tv_grab_gracenote2epg setup.py

    # Verify black made all necessary changes
    if ! black --check --line-length 100 gracenote2epg/ tv_grab_gracenote2epg setup.py; then
        log_warning "Running black again to ensure all changes are applied..."
        black --line-length 100 gracenote2epg/ tv_grab_gracenote2epg setup.py
    fi

    log_success "Code formatting completed"
}

cmd_lint() {
    log_info "Running linting with flake8..."

    if ! command -v flake8 &> /dev/null; then
        log_warning "flake8 not found, installing..."
        pip install flake8
    fi

    # Use explicit configuration to ensure it's applied
    flake8 gracenote2epg/ tv_grab_gracenote2epg \
        --max-line-length=100 \
        --extend-ignore=E203,W503,F541,E501,F401,F841,E722,W293 \
        --exclude=build,dist,*.egg-info,__pycache__,.git,.tox

    log_success "Linting completed"
}

cmd_test_basic() {
    log_info "Running basic test..."
    ./scripts/test-distribution.bash --basic
}

cmd_test_full() {
    log_info "Running full test..."
    ./scripts/test-distribution.bash --full
}

cmd_install_dev() {
    log_info "Installing in development mode..."
    pip install -e .[dev]
    log_success "Development installation completed"
}

cmd_check_deps() {
    log_info "Checking development dependencies..."

    local tools=("python3" "black" "flake8" "autoflake")
    local pip_packages=("build" "twine" "autoflake")
    local missing_tools=()
    local missing_packages=()

    # Check command-line tools (may be system packages or pip)
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done

    # Check Python packages specifically
    for pkg in "${pip_packages[@]}"; do
        if ! python3 -c "import $pkg" 2>/dev/null; then
            missing_packages+=("$pkg")
        fi
    done

    # Report what's missing
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        log_warning "Missing command-line tools: ${missing_tools[*]}"
        log_info "Install with: sudo apt install python3-pip black flake8"
        log_info "Or with pip: pip install ${missing_tools[*]}"
    fi

    if [[ ${#missing_packages[@]} -gt 0 ]]; then
        log_warning "Installing missing Python packages: ${missing_packages[*]}"
        pip install "${missing_packages[@]}"
    fi

    # Check for problematic packages
    if pip list 2>/dev/null | grep -q "flake8-black"; then
        log_warning "Found flake8-black package - this may cause BLK100 errors"
        log_info "Consider removing: pip uninstall flake8-black"
    fi

    # Show what we found
    log_info "Development tools status:"
    for tool in "${tools[@]}"; do
        if command -v "$tool" &> /dev/null; then
            local version=$("$tool" --version 2>/dev/null | head -1)
            log_success "✓ $tool: $version"
        else
            log_warning "✗ $tool: not found"
        fi
    done

    if [[ ${#missing_tools[@]} -eq 0 && ${#missing_packages[@]} -eq 0 ]]; then
        log_success "All development dependencies available"
    fi
}

cmd_show_dist() {
    log_info "Current distribution files:"

    if [[ -d "dist" ]]; then
        ls -lh dist/
        echo

        # Show package contents summary
        for file in dist/*.whl; do
            if [[ -f "$file" ]]; then
                echo "=== $(basename "$file") ==="
                python3 -m zipfile -l "$file" | grep -E "(locales|gracenote2epg)" | head -10
                echo
            fi
        done
    else
        log_warning "No dist/ directory found. Run build first."
    fi
}

# Main execution
case "${1:-help}" in
    clean)
        cmd_clean
        ;;
    autofix)
        cmd_autofix
        ;;
    format)
        cmd_format
        ;;
    lint)
        cmd_lint
        ;;
    test-basic)
        cmd_test_basic
        ;;
    test-full)
        cmd_test_full
        ;;
    install-dev)
        cmd_install_dev
        ;;
    check-deps)
        cmd_check_deps
        ;;
    show-dist)
        cmd_show_dist
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo
        show_help
        exit 1
        ;;
esac
