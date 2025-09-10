# Installation Guide

This guide covers all installation methods for gracenote2epg on different platforms.

## 📦 Installation Methods

### Method 1: Install from PyPI (Recommended)

#### With Full Features
```bash
# Install with all features (recommended)
pip install gracenote2epg[full]

# Basic installation (core features only)
pip install gracenote2epg

# Feature-specific installation
pip install gracenote2epg[langdetect]    # Language detection only
pip install gracenote2epg[translations]  # Translation support only
```

### Method 2: Install from GitHub (Alternative)

#### Latest Stable Release
```bash
# Install latest stable release from GitHub
pip install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.6.0"

# Basic installation from GitHub
pip install "gracenote2epg @ git+https://github.com/th0ma7/gracenote2epg.git@v1.6.0"
```

#### Latest Development Version
```bash
# Install latest git snapshot
pip install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git"

# Install latest development version
pip install "gracenote2epg[dev] @ git+https://github.com/th0ma7/gracenote2epg.git"
```

### Method 3: Clone and Install (Development)
```bash
# Clone repository and install (latest version)
git clone https://github.com/th0ma7/gracenote2epg.git
cd gracenote2epg
pip install .[full]  # Install with full features
pip install .        # Basic installation
```

### Method 4: Manual Installation (Source Distribution)
```bash
# Download source from GitHub releases
wget https://github.com/th0ma7/gracenote2epg/archive/v1.6.0.tar.gz -O gracenote2epg-1.6.0.tar.gz

# Install into /usr/local/
sudo tar -xzf gracenote2epg-1.6.0.tar.gz -C /usr/local/

# Create a generic gracenote2epg symbolic link
sudo ln -sf /usr/local/gracenote2epg-1.6.0 /usr/local/gracenote2epg

# Make tv_grab_gracenote2epg available in /usr/local/bin
sudo ln -sf /usr/local/gracenote2epg/tv_grab_gracenote2epg /usr/local/bin

# Validate link exists
ls -la /usr/local/bin/tv_grab_gracenote2epg
lrwxrwxrwx 1 root root 46 Aug 23 14:16 /usr/local/bin/tv_grab_gracenote2epg -> /usr/local/gracenote2epg/tv_grab_gracenote2epg

# Run from installation path
which tv_grab_gracenote2epg       # Should return /usr/local/bin/tv_grab_gracenote2epg
tv_grab_gracenote2epg --version   # Should return its version
```

## Platform-Specific Instructions

### Ubuntu/Debian/RaspberryPi
```bash
# Update and Install Python and pip if not already installed
sudo apt update && apt install -y python3 python3-pip python3-venv python3-langdetect python3-polib

# Install gracenote2epg from PyPI (recommended)
pip3 install gracenote2epg[full]

# Verify installation
pip3 list | grep gracenote2epg
tv_grab_gracenote2epg --version
```

### CentOS/RHEL/Fedora
```bash
# Install Python and pip
sudo dnf update -y && dnf install -y python3 python3-pip python3-virtualenv

# Install gracenote2epg from PyPI (recommended)
pip3 install gracenote2epg[full]

# Verify installation
pip3 list | grep gracenote2epg
tv_grab_gracenote2epg --version
```

### Arch Linux
```bash
# Install dependencies
sudo pacman -Syu python python-pip python-virtualenv python-langdetect python-polib

# Install gracenote2epg from PyPI (recommended)
pip install gracenote2epg[full]

# Verify installation
pip list | grep gracenote2epg
tv_grab_gracenote2epg --version
```

### Synology NAS with TVheadend
```bash
# Prerequisites: TVheadend must already be installed from Package Center

# Install gracenote2epg from PyPI (recommended) in TVheadend environment
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 install gracenote2epg[full]'

# Install a specific version of gracenote2epg from Pypi in TVheadend environment
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 install "gracenote2epg[full]==1.6.0"'

# Install latest git snapshot
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git"'

# Verify installation in TVheadend environment
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/pip3 list | grep gracenote2epg'
sudo su -s /bin/bash sc-tvheadend -c '/var/packages/tvheadend/target/env/bin/tv_grab_gracenote2epg --version'
```

## Package Distribution Types

gracenote2epg is available in two distribution formats:

### 1. Wheel Package (.whl) - For pip install
- Creates both `gracenote2epg` and `tv_grab_gracenote2epg` commands
- Installs in Python site-packages and system bin
- **Recommended for most users**

### 2. Source Distribution (.tar.gz) - For manual installation
- Includes **only** `tv_grab_gracenote2epg` wrapper script in bin/
- Works immediately after extraction (no installation required)
- Useful for systems where pip install isn't preferred

**Important**: The `tv_grab_gracenote2epg` wrapper script is **essential** for *XMLTV Standard Compliance* and *TVheadend Integration* (looks for `tv_grab_*` scripts).

## Available Commands After Installation

```bash
tv_grab_gracenote2epg --capabilities # XMLTV standard wrapper (ESSENTIAL)
gracenote2epg --version              # Alternate command (wheel based installed only)
python -m gracenote2epg --version    # Module execution
```

## Feature Dependencies

### Core Dependencies (Always Installed)
- `requests>=2.25.0` - HTTP requests for downloading guide data

### Optional Dependencies (via extras_require)
- `langdetect>=1.0.9` - Automatic language detection for French/English/Spanish
- `polib>=1.1.0` - Category and term translations using .po files

## Verification

### Test Installation
```bash
# Check if package is installed
pip list | grep gracenote2epg
# Expected output: gracenote2epg    1.6.0

# Check version
tv_grab_gracenote2epg --version

# Show capabilities (XMLTV standard)
tv_grab_gracenote2epg --capabilities

# Test basic functionality
tv_grab_gracenote2epg --show-lineup --zip 92101
```

### Test Features
```bash
# Test language detection
python -c "
try:
    import langdetect
    print('✓ Language detection available')
except ImportError:
    print('✗ Language detection not available - install with [full]')
"

# Test translations
python -c "
try:
    import polib
    print('✓ Translations available')  
except ImportError:
    print('✗ Translations not available - install with [full]')
"
```

## Default Directories

gracenote2epg auto-detects your system and creates appropriate directories:

### Linux/Docker
- **Config**: `~/gracenote2epg/conf/gracenote2epg.xml`
- **Cache**: `~/gracenote2epg/cache/`
- **Logs**: `~/gracenote2epg/log/`

### Raspberry Pi
- **Config**: `~/script.module.zap2epg/epggrab/conf/gracenote2epg.xml` (if exists)
- **Fallback**: `~/gracenote2epg/conf/gracenote2epg.xml`

### Synology (with TVheadend)
- **Config**: `/var/packages/tvheadend/var/epggrab/gracenote2epg/conf/gracenote2epg.xml` (DSM7)
- **Config**: `/var/packages/tvheadend/target/var/epggrab/gracenote2epg/conf/gracenote2epg.xml` (DSM6)

## Troubleshooting Installation

### Common Issues

**Problem**: Permission denied
```bash
# Solution: Install for user only
pip install --user gracenote2epg[full]
```

**Problem**: Package conflicts
```bash
# Solution: Use virtual environment
python3 -m venv gracenote_env
source gracenote_env/bin/activate
pip install gracenote2epg[full]
```

**Problem**: GitHub installation fails
```bash
# Solution: Verify PEP 508 syntax with quotes
pip install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git"
```

### Migration Notes
See the **[TVheadend Guide](tvheadend.md)** if integrating with TVheadend after upgrading.
