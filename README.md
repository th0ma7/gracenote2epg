# gracenote2epg - TV Guide Grabber for North America

> **📦 PyPI Status**: Now available on PyPI! Install with `pip install gracenote2epg[full]`

A modern Python implementation for downloading TV guide data from tvlistings.gracenote.com with intelligent caching and TVheadend integration.

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI](https://img.shields.io/badge/PyPI-Available-green.svg)](https://pypi.org/project/gracenote2epg/)
[![GitHub](https://img.shields.io/badge/GitHub-Available-green.svg)](https://github.com/th0ma7/gracenote2epg)

## 🌟 Key Features

- **XMLTV Standard Compliant** - Full DTD compliance for maximum compatibility
- **Intelligent Caching** - 95%+ cache efficiency with smart refresh strategies  
- **Multi-language Support** - Automatic French/English/Spanish detection and translations
- **TVheadend Integration** - Seamless channel filtering and matching
- **Unified Cache Management** - Streamlined configuration for all retention policies
- **Platform Agnostic** - Auto-detection for Raspberry Pi, Synology NAS, and Linux

## 🚀 Installation

```bash
# Recommended: Install with all features
pip install gracenote2epg[full]

# Basic installation (core features only)
pip install gracenote2epg

# Alternative: Install from GitHub
pip install "gracenote2epg[full] @ git+https://github.com/th0ma7/gracenote2epg.git@v1.6.0"
```

### 📦 Development Installation

```bash
# Install from GitHub (latest)
pip install "gracenote2epg[dev] @ git+https://github.com/th0ma7/gracenote2epg.git"

# Clone and install for development
git clone https://github.com/th0ma7/gracenote2epg.git
cd gracenote2epg
pip install -e .[dev]
```

## 📋 System Requirements

- **Python**: 3.7 or higher
- **Required**: `requests>=2.25.0`
- **Optional**: `langdetect>=1.0.9` (language detection), `polib>=1.1.0` (translations)

## 🛠️ Quick Examples

### Command Line Examples
```bash
# Show capabilities (XMLTV standard)
tv_grab_gracenote2epg --capabilities

# Download 7 days of guide data
tv_grab_gracenote2epg --days 7 --zip 92101

# Test lineup detection
tv_grab_gracenote2epg --show-lineup --zip 92101

# Canadian postal code with console output
tv_grab_gracenote2epg --days 3 --postal J3B1M4 --console

# Save to custom file with debug info
tv_grab_gracenote2epg --days 7 --zip 92101 --output guide.xml --debug

# Use specific lineup (auto-extracts location)
tv_grab_gracenote2epg --days 7 --lineupid CAN-OTAJ3B1M4

# Disable language detection
tv_grab_gracenote2epg --days 7 --zip 92101 --langdetect false
```

### Configuration

> **💡 TVheadend Users - Easy Setup**: Most users don't need to edit configuration files! Simply use TVheadend's **Extra arguments** box to add your parameters like `--days 7 --zip 92101 --langdetect false` (Configuration → Channel/EPG → EPG Grabber Modules). See **[TVheadend Integration Guide](https://github.com/th0ma7/gracenote2epg/blob/main/docs/tvheadend.md)** for details.

### TVheadend Integration Examples

```bash
# In TVheadend Extra arguments box:
--days 7 --zip 92101
--days 14 --postal J3B1M4 --langdetect false  
--days 7 --zip 90210 --lineupid auto
```

> **Important**: Extra arguments override the default configuration file, so you typically don't need to edit `conf/gracenote2epg.xml` manually.

#### Option 2: Edit Configuration File (Advanced Users)

Also note that the gracenote2epg auto-creates a configuration file on first run. You can then modify as needed:
```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <setting id="zipcode">92101</setting>        <!-- Your ZIP/postal code -->
  <setting id="lineupid">auto</setting>        <!-- Auto-detect lineup -->
  <setting id="days">7</setting>               <!-- Guide duration -->
</settings>
```

## 📚 Documentation

- **[Installation Guide](https://github.com/th0ma7/gracenote2epg/blob/main/docs/installation.md)** - Installation instructions and software migration
- **[Configuration](https://github.com/th0ma7/gracenote2epg/blob/main/docs/configuration.md)** - Complete configuration reference
- **[Lineup Configuration](https://github.com/th0ma7/gracenote2epg/blob/main/docs/lineup-configuration.md)** - Finding and configuring your TV lineup
- **[TVheadend Integration](https://github.com/th0ma7/gracenote2epg/blob/main/docs/tvheadend.md)** - TVheadend setup, EPG migration, and troubleshooting
- **[Troubleshooting](https://github.com/th0ma7/gracenote2epg/blob/main/docs/troubleshooting.md)** - General issues and solutions

## 🛣️ Development & Roadmap

- **[Development Roadmap](https://github.com/th0ma7/gracenote2epg/blob/main/docs/roadmap.md)** - Feature roadmap, upcoming versions, and planned enhancements
- **[Contributing Guide](https://github.com/th0ma7/gracenote2epg/blob/main/docs/development.md)** - Contributing, testing, XMLTV validation, and development setup

### Advanced Topics

- **[Cache & Retention Policies](https://github.com/th0ma7/gracenote2epg/blob/main/docs/cache-retention.md)** - Managing cache and log retention
- **[Log Rotation](https://github.com/th0ma7/gracenote2epg/blob/main/docs/log-rotation.md)** - Built-in log rotation system
- **[Development Scripts](https://github.com/th0ma7/gracenote2epg/blob/main/scripts/README.md)** - Utility scripts for testing and distribution

## 🆘 Need Help?

1. **Check the [troubleshooting guide](https://github.com/th0ma7/gracenote2epg/blob/main/docs/troubleshooting.md)**
2. **Test your lineup**: `tv_grab_gracenote2epg --show-lineup --zip YOUR_CODE`
3. **Enable debug logging**: `tv_grab_gracenote2epg --debug --console`
4. **[Create an issue](https://github.com/th0ma7/gracenote2epg/issues)** with logs

## 📄 License

GPL v3 - Same as original script.module.zap2epg project

## 🙏 Credits

Based on edit4ever's script.module.zap2epg with enhancements and modern Python architecture.

---

**[View Changelog](https://github.com/th0ma7/gracenote2epg/blob/main/docs/changelog.md)** | **[Report Issues](https://github.com/th0ma7/gracenote2epg/issues)** | **[Contribute](https://github.com/th0ma7/gracenote2epg/blob/main/docs/development.md)**
