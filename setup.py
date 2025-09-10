#!/usr/bin/env python3

from setuptools import setup, find_packages
import os


# Read version from __init__.py (single source of truth)
def get_version():
    here = os.path.abspath(os.path.dirname(__file__))
    version_file = os.path.join(here, "gracenote2epg", "__init__.py")

    with open(version_file, encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                # Extract version from line like: __version__ = "1.4.1"
                return line.split('"')[1]

    raise RuntimeError("Unable to find version string in __init__.py")


# Read long description from README
def read_long_description():
    here = os.path.abspath(os.path.dirname(__file__))
    try:
        with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "TV Guide Grabber for North America - gracenote2epg"


setup(
    name="gracenote2epg",
    version=get_version(),  # 🔧 Version read from __init__.py
    description="TV Guide Grabber for North America",
    long_description=read_long_description(),
    long_description_content_type="text/markdown",
    # Author information
    author="th0ma7",
    author_email="th0ma7@gmail.com",
    url="https://github.com/th0ma7/gracenote2epg",
    # License
    license="GPL-3.0",
    # Package discovery
    packages=find_packages(),
    # Python version requirement
    python_requires=">=3.7",
    # Core dependencies (always installed)
    install_requires=[
        "requests>=2.25.0",
    ],
    # Optional dependencies (extras)
    extras_require={
        # Language detection
        "langdetect": [
            "langdetect>=1.0.9",
        ],
        # Support for .po files
        "translations": [
            "polib>=1.1.0",
        ],
        # Geographic resolution for improved lineup URLs
        "geocoding": [
            "pgeocode>=0.4.0",
        ],
        # All functionalities (recommended)
        "full": [
            "langdetect>=1.0.9",
            "polib>=1.1.0",
            "pgeocode>=0.4.0",
        ],
        # Development
        "dev": [
            "langdetect>=1.0.9",
            "polib>=1.1.0",
            "pgeocode>=0.4.0",
            "pytest>=6.0",
            "flake8>=3.8",
            "black>=21.0",
            "mypy>=0.910",
            "autoflake>=1.4",  # Auto-fix imports and variables
            "build>=0.7.0",  # Package building
            "twine>=3.4.0",  # PyPI publishing
        ],
        # Tests only
        "test": [
            "pytest>=6.0",
            "pytest-cov>=2.10",
        ],
    },
    # Command line scripts
    scripts=["tv_grab_gracenote2epg"],
    # Entry points for module execution
    entry_points={
        "console_scripts": [
            "gracenote2epg=gracenote2epg.__main__:main",
        ],
    },
    # Package data
    package_data={
        "gracenote2epg": [
            "locales/*/LC_MESSAGES/*.po",
            "locales/*.pot",
        ],
    },
    # Include package data
    include_package_data=True,
    # Additional files - documentation, config, and wrapper scripts
    data_files=[
        (
            "share/doc/gracenote2epg",
            [
                "docs/installation.md",
                "docs/configuration.md",
                "docs/lineup-configuration.md",
                "docs/cache-retention.md",
                "docs/log-rotation.md",
                "docs/tvheadend.md",
                "docs/troubleshooting.md",
                "docs/development.md",
                "docs/changelog.md",
                "LICENSE",
            ],
        ),
        ("share/gracenote2epg", ["gracenote2epg.xml"]),
        ("bin", ["tv_grab_gracenote2epg"]),
    ],
    # PyPI classifiers
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Environment :: Console",
    ],
    # Keywords for PyPI search
    keywords="xmltv epg tv guide gracenote tvheadend ota cable geocoding",
    # Project URLs
    project_urls={
        "Bug Reports": "https://github.com/th0ma7/gracenote2epg/issues",
        "Source": "https://github.com/th0ma7/gracenote2epg",
        "Documentation": "https://github.com/th0ma7/gracenote2epg/tree/main/docs",
        "TVheadend Guide": "https://github.com/th0ma7/gracenote2epg/blob/main/docs/tvheadend.md",
    },
    # Zip safe
    zip_safe=False,
)
