# Development Guide

This guide covers development setup, testing, validation, and contribution guidelines for gracenote2epg.

## Development Environment Setup

### Prerequisites

```bash
# Python 3.7+ required
python3 --version

# Git for version control
git --version

# Recommended: Virtual environment
python3 -m venv gracenote_dev
source gracenote_dev/bin/activate  # Linux/Mac
# gracenote_dev\Scripts\activate   # Windows
```

### Development Dependencies

#### Core Development Tools

The following tools are required for development:

- **Python 3.7+** - Core language
- **build** - Package building
- **black** - Code formatting
- **flake8** - Code linting  
- **autoflake** - Automatic import/variable cleanup
- **twine** - PyPI publishing (optional)

#### Installation Methods

**Ubuntu/Debian (Recommended):**
```bash
# Install system packages (recommended for Ubuntu/Debian)
sudo apt update
sudo apt install python3-pip python3-build black flake8

# Install remaining tools via pip
pip install autoflake twine
```

**Using pip only:**
```bash
# Install all tools via pip
pip install build black flake8 autoflake twine
```

**Development install (includes everything):**
```bash
# Install package in development mode with all dependencies
pip install -e .[dev]
```

#### Tools to AVOID

⚠️ **Do NOT install these packages** - they can cause conflicts:

- `flake8-black` - Causes BLK100 errors and conflicts with our workflow
- `pylint` - Different standards than our flake8 configuration

#### Verification

```bash
# Check tools availability
make check-deps
# or
./scripts/dev-helper.bash check-deps
```

### Installation for Development

```bash
# Clone repository
git clone https://github.com/th0ma7/gracenote2epg.git
cd gracenote2epg

# Install in editable mode with all features
pip install -e .[dev]

# Or install dependencies manually (see Prerequisites section above)
pip install -e .
pip install langdetect polib pytest flake8 black mypy autoflake
```

## Project Structure

```
gracenote2epg/
├── gracenote2epg/           # Main package
│   ├── __init__.py          # Package version and exports
│   ├── __main__.py          # Entry point for -m execution
│   ├── gracenote2epg_*.py   # Core modules
│   └── locales/             # Translation files
├── tv_grab_gracenote2epg    # XMLTV wrapper script
├── gracenote2epg.xml        # Default configuration template
├── Makefile                 # Development task automation
├── docs/                    # Documentation
├── scripts/                 # Development and testing scripts
│   ├── dev-helper.bash      # Development workflow assistant
│   ├── test-distribution.bash # Distribution testing
│   └── README.md            # Scripts documentation
├── tests/                   # Test suite (if present)
├── setup.py                 # Package setup
├── MANIFEST.in              # Distribution file manifest
└── README.md                # Main documentation
```

## Development Workflow

### Makefile - Primary Interface

The project provides a `Makefile` at the root for convenient development task automation:

```bash
# Quick development tasks
make clean               # Clean all artifacts
make autofix             # Auto-fix imports and common issues
make format              # Format code with black  
make lint                # Run linting
make test-basic          # Quick test
make test-full           # Full test (alias: make test)

# Build and install
make build               # Build distributions
make install-dev         # Development installation
make check-deps          # Check dependencies

# Complete workflow
make all                 # Run clean, autofix, format, lint, and test-full
```

### Development Scripts

The Makefile is a wrapper around development scripts located in `scripts/`:

- **`dev-helper.bash`** - Development workflow assistant
- **`test-distribution.bash`** - Distribution testing and validation

**See [Development Scripts README](../scripts/README.md)** for complete documentation of individual scripts, their options, and direct usage.

### Recommended Workflow

```bash
# Daily development cycle
make clean autofix format lint test-basic

# Before committing
make all

# Quick fixes
make autofix format
```

## Code Quality and Standards

### Code Formatting

```bash
# Format code with Black
black gracenote2epg/ tv_grab_gracenote2epg

# Check formatting
black --check gracenote2epg/
```

### Linting

```bash
# Lint with flake8
flake8 gracenote2epg/ tv_grab_gracenote2epg

# Configuration in setup.cfg or .flake8
[flake8]
max-line-length = 100
extend-ignore = E203,W503,F541,F401,F841,E722,W293
exclude = build,dist,*.egg-info,__pycache__
```

### Type Checking

```bash
# Type check with mypy
mypy gracenote2epg/

# Configuration in setup.cfg
[mypy]
python_version = 3.7
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

## Testing and Validation

### Automated Testing with Scripts

The project includes comprehensive testing automation via the Makefile:

```bash
# Quick functionality test
make test-basic

# Full distribution test (recommended before commits)
make test-full  # or just: make test

# Complete development workflow
make all  # clean, autofix, format, lint, test-full
```

**For detailed script options and direct usage**, see [Development Scripts README](../scripts/README.md).

### Before Committing

```bash
# Recommended: Complete workflow
make all

# Or step by step:
make clean autofix format lint test-basic
```

### Unit Tests

```bash
# Run tests with pytest
pytest tests/

# Run with coverage
pytest --cov=gracenote2epg tests/

# Run specific test
pytest tests/test_config.py::test_configuration_parsing
```

### Integration Testing

```bash
# Test basic functionality
./tv_grab_gracenote2epg --capabilities

# Test lineup detection (requires internet)
./tv_grab_gracenote2epg --show-lineup --zip 92101

# Test full download (small dataset)
./tv_grab_gracenote2epg --days 1 --zip 92101 --debug --console
```

### XMLTV DTD Validation

```bash
# Download XMLTV DTD for validation
curl -L https://raw.githubusercontent.com/XMLTV/xmltv/master/xmltv.dtd -o xmltv.dtd

# Validate XMLTV output against DTD
xmllint --noout --dtdvalid xmltv.dtd ~/gracenote2epg/cache/xmltv.xml \
        && echo "Validation: DTD valid" \
        || echo "Validation: ERROR"
# Should return: Validation: DTD valid

# Validate encoding
file ~/gracenote2epg/cache/xmltv.xml
# Should show: XML 1.0 document, Unicode text, UTF-8 text, with very long lines (500)
```

## Version Management

### Single Source of Truth

The project uses a centralized version management system:

- **Version location**: `gracenote2epg/__init__.py`
- **Format**: `__version__ = "1.4.2"`
- **Auto-discovery**: `setup.py` automatically reads version from `__init__.py`

### Updating Version

```bash
# Only update the version in one place:
# gracenote2epg/__init__.py

# Example:
__version__ = "1.6.0"

# setup.py will automatically pick up the new version
```

### Version Validation

```bash
# Verify version consistency
python3 -c "
import gracenote2epg
print('Package version:', gracenote2epg.__version__)
"

# Check setup.py version detection
python3 setup.py --version
```

## Building and Distribution

### Automated Building and Testing

```bash
# Build and test distributions automatically
make test-full

# Or build distributions only
make build

# Complete workflow (recommended)
make all
```

**For advanced script options and troubleshooting**, see [Development Scripts README](../scripts/README.md).

### Manual Building

```bash
# Install build tools
pip install build twine

# Clean previous builds
rm -rf build/ dist/ *.egg-info/

# Build source distribution and wheel
python -m build

# Check distribution contents
tar -tzf dist/gracenote2epg-*.tar.gz | head -20
```

### Testing Distribution

```bash
# Test source distribution installation
pip install dist/gracenote2epg-*.tar.gz[full]

# Test wheel installation  
pip install dist/gracenote2epg-*-py3-none-any.whl[full]

# Verify commands work
tv_grab_gracenote2epg --capabilities
gracenote2epg --version
```

### Publishing to PyPI

```bash
# Test upload to TestPyPI first
python -m twine upload --repository testpypi dist/*

# Install from TestPyPI to verify
pip install --index-url https://test.pypi.org/simple/ gracenote2epg[full]

# Upload to production PyPI
python -m twine upload dist/*
```

## Debugging and Troubleshooting

### Debug Mode

```bash
# Enable all debug output
./tv_grab_gracenote2epg --debug --console --days 1 --zip 92101

# Specific debug areas (modify source as needed)
# - Configuration parsing
# - Lineup detection  
# - Download progress
# - Cache operations
# - XMLTV generation
```

### Log Analysis

```bash
# Real-time log monitoring
tail -f ~/gracenote2epg/log/gracenote2epg.log

# Search for specific issues
grep -i error ~/gracenote2epg/log/gracenote2epg.log
grep -i warning ~/gracenote2epg/log/gracenote2epg.log

# Performance analysis
grep "took.*seconds" ~/gracenote2epg/log/gracenote2epg.log
grep "cache efficiency" ~/gracenote2epg/log/gracenote2epg.log
```

### Common Development Issues

#### Import Errors
```bash
# Check package installation
pip show gracenote2epg

# Verify Python path
python -c "import sys; print(sys.path)"

# Test module import
python -c "import gracenote2epg; print('OK')"
```

#### Configuration Issues
```bash
# Test configuration parsing
python -c "
from gracenote2epg.gracenote2epg_config import ConfigManager
config = ConfigManager()
print('Configuration loaded successfully')
"
```

#### Distribution Issues
```bash
# Debug packaging problems
./scripts/test-distribution.bash --clean-only
python3 -m build --verbose

# Check locale files inclusion
python3 -m zipfile -l dist/*.whl | grep locales
```

#### Development Tools Issues

**flake8-black conflicts:**
If you see `BLK100` errors during linting:
```bash
# Remove the conflicting plugin
pip uninstall flake8-black

# Check what's installed
pip list | grep flake8
```

The `flake8-black` plugin is **not needed** for this project and causes conflicts.

**Mixed system/pip installations:**
The scripts handle mixed installations (Ubuntu apt + pip) gracefully:
```bash
# Check what you have installed
./scripts/dev-helper.bash check-deps

# Typical Ubuntu setup (recommended):
# - black, flake8: via apt
# - autoflake, build, twine: via pip
```

**Tool version conflicts:**
If you encounter tool conflicts:
```bash
# Option 1: Use virtual environment
python3 -m venv dev-env
source dev-env/bin/activate
pip install -e .[dev]

# Option 2: Check tool versions
black --version        # Should be 20.8b1+
flake8 --version       # Should be 3.8.0+
autoflake --version    # Should be 1.4+
```

## Contributing Guidelines

### Code Style

- **Follow PEP 8** with Black formatting
- **Line length**: 100 characters (increased from 88 for readability)
- **Type hints**: Required for new code
- **Docstrings**: Use Google style docstrings

### Commit Guidelines

```bash
# Commit message format
feat: add new feature
fix: bug fix
docs: documentation changes
style: formatting changes
refactor: code refactoring
test: add tests
chore: maintenance
```

### Pull Request Process

1. **Fork repository** and create feature branch
2. **Make changes** with appropriate tests
3. **Run quality checks**: `make autofix format lint`
4. **Test distributions**: `./scripts/test-distribution.bash`
5. **Update documentation** if needed
6. **Submit pull request** with clear description

### Testing Requirements

- **Unit tests** for new functionality
- **Integration tests** for major features
- **XMLTV validation** for output changes
- **Distribution testing** with provided scripts
- **Performance testing** for cache/network changes

## Architecture Notes

### Core Components

- **Configuration**: XML-based with auto-migration
- **Cache System**: Intelligent block-based caching
- **Download Engine**: WAF-aware with retry logic
- **XMLTV Generator**: Standards-compliant output
- **TVheadend Integration**: Optional channel filtering
- **Translation System**: Multi-language support with .po files

### Design Principles

- **Backward compatibility** with zap2epg configurations
- **Graceful degradation** when optional features unavailable
- **Intelligent caching** for 95%+ cache efficiency
- **Robust error handling** with automatic retries
- **Platform agnostic** auto-detection
- **Single source of truth** for version management

## Release Process

### Pre-Release Checklist

1. **Update version** in `gracenote2epg/__init__.py` only
2. **Run full test suite** including distribution tests
   ```bash
   make all
   ```
3. **Update CHANGELOG.md** with new features/fixes
4. **Update documentation** if needed

### Release Steps

```bash
# 1. Verify version is updated in __init__.py
grep "__version__" gracenote2epg/__init__.py

# 2. Build and test distributions
make all

# 3. Create Git tag
git tag -a v$(python3 -c "import gracenote2epg; print(gracenote2epg.__version__)") -m "Release version $(python3 -c "import gracenote2epg; print(gracenote2epg.__version__)")"
git push origin v$(python3 -c "import gracenote2epg; print(gracenote2epg.__version__)")

# 4. Upload to PyPI
python -m twine upload dist/*
```

### Post-Release

1. **Update installation instructions** in documentation
2. **Verify PyPI publication**
3. **Update README.md** PyPI status if this is the first publication

## Getting Help

### Development Support

- **[GitHub Issues](https://github.com/th0ma7/gracenote2epg/issues)** - Bug reports and feature requests
- **[GitHub Discussions](https://github.com/th0ma7/gracenote2epg/discussions)** - Development questions
- **[Development Scripts](../scripts/README.md)** - Testing and distribution tools
- **Code Review** - Submit pull requests for feedback

### Resources

- **[XMLTV DTD](http://xmltv.cvs.sourceforge.net/viewvc/*checkout*/xmltv/xmltv/xmltv.dtd)** - XMLTV standard
- **[Python Packaging](https://packaging.python.org/)** - Distribution guidelines
- **[TVheadend API](https://tvheadend.org/projects/tvheadend/wiki/Httpapi)** - Integration reference
