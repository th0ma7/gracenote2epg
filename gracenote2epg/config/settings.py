"""
gracenote2epg.config.settings - XML settings parsing and management

Handles XML configuration file parsing, settings processing, type conversion,
and clean XML generation for gracenote2epg configurations.
"""

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class SettingsManager:
    """Handles XML settings parsing and management"""

    # Current config schema version. Bumped to 6 for the <imagesources> block,
    # 7 for the dlworkers (parallel download) setting, 8 for the dlthreshold
    # (parallel→sequential switch) setting, then 9 for the reconf (config backup
    # retention) setting; older files are upgraded automatically on load.
    CONFIG_VERSION = "9"

    # Default configuration template
    DEFAULT_CONFIG = """<?xml version="1.0" encoding="utf-8"?>
<settings version="9">
  <!-- Basic guide settings -->
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">7</setting>

  <!-- Station filtering -->
  <setting id="slist"></setting>
  <setting id="stitle">false</setting>

  <!-- Extended details and language detection -->
  <setting id="xdetails">true</setting>
  <setting id="xdesc">true</setting>
  <setting id="langdetect">true</setting>

  <!-- Display options -->
  <setting id="epgenre">3</setting>
  <setting id="epicon">1</setting>

  <!-- TVheadend integration -->
  <setting id="tvhoff">true</setting>
  <setting id="usern"></setting>
  <setting id="passw"></setting>
  <setting id="tvhurl">127.0.0.1</setting>
  <setting id="tvhport">9981</setting>
  <setting id="tvhmatch">true</setting>
  <setting id="chmatch">true</setting>

  <!-- Cache and retention policies -->
  <setting id="redays">7</setting>
  <setting id="refresh">48</setting>
  <setting id="logrotate">true</setting>
  <setting id="relogs">30</setting>
  <setting id="rexmltv">7</setting>
  <setting id="reconf">10</setting>

  <!-- Download performance -->
  <setting id="dlworkers">auto</setting>
  <setting id="dlthreshold">auto</setting>

  <!-- Image source host (first 'enabled' is used; mirrors serve the same images) -->
  <imagesources>
    <source status="enabled">https://tmsimg.fancybits.co/assets</source>
    <source status="disabled">https://www.tvtv.ca/gn/pi/assets</source>
    <source status="disabled">https://zap2it.tmsimg.com/assets</source>
    <source status="disabled">https://dshm.tmsimg.com/assets</source>
  </imagesources>
</settings>"""

    # Known image hosts (base URLs serving the same TMS asset codes). The first
    # 'enabled' source is used; tvtv.ca is rate-limited so the default enables
    # the fancybits mirror. Used when the config has no <imagesources> block.
    DEFAULT_IMAGE_SOURCES = [
        ("https://tmsimg.fancybits.co/assets", True),
        ("https://www.tvtv.ca/gn/pi/assets", False),
        ("https://zap2it.tmsimg.com/assets", False),
        ("https://dshm.tmsimg.com/assets", False),
    ]
    _DISABLED_STATUSES = {"disabled", "off", "false", "0", "no"}

    # Settings order for clean output
    SETTINGS_ORDER = [
        "zipcode",
        "lineupid",
        "days",
        "slist",
        "stitle",
        "xdetails",
        "xdesc",
        "langdetect",
        "epgenre",
        "epicon",
        "tvhoff",
        "tvhurl",
        "tvhport",
        "tvhmatch",
        "chmatch",
        "usern",
        "passw",
        "redays",
        "refresh",
        "logrotate",
        "relogs",
        "rexmltv",
        "reconf",
        "dlworkers",
        "dlthreshold",
    ]

    def __init__(self):
        self.version: str = "5"

    def create_default_config(self, config_file: Path):
        """Create default configuration file with proper permissions"""
        logging.info("Creating default configuration: %s", config_file)

        # Ensure directory exists with 755 permissions (rwxr-xr-x)
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        except Exception:
            # Fallback: create without mode specification (depends on umask)
            config_file.parent.mkdir(parents=True, exist_ok=True)

        # Write default configuration
        with open(config_file, "w", encoding="utf-8") as f:
            f.write(self.DEFAULT_CONFIG)

    def parse_config_file(self, config_file: Path) -> Tuple[Dict[str, Any], List[str], str]:
        """
        Parse XML configuration file

        Returns:
            tuple: (valid_settings, all_settings_order, version)
        """
        try:
            tree = ET.parse(config_file)
            root = tree.getroot()

            logging.info("Reading configuration from: %s", config_file)

            # Get version - default to version 5 for new unified format
            self.version = root.attrib.get("version", "5")
            logging.info("Configuration version: %s", self.version)

            # Parse settings
            valid_settings = {}
            original_order = []

            for setting in root.findall("setting"):
                setting_id = setting.get("id")
                original_order.append(setting_id)

                # Get value based on version
                if self.version == "2":
                    setting_value = setting.text
                else:
                    # Version 3+: try 'value' attribute first, then text
                    setting_value = setting.get("value")
                    if setting_value is None:
                        setting_value = setting.text
                    if setting_value == "":
                        setting_value = None

                logging.debug("Config setting: %s = %s", setting_id, setting_value)
                valid_settings[setting_id] = setting_value

            return valid_settings, original_order, self.version

        except ET.ParseError as e:
            logging.error("Cannot parse configuration file %s: %s", config_file, e)
            raise
        except Exception as e:
            logging.error("Error reading configuration file %s: %s", config_file, e)
            raise

    def check_ordering_needed(
        self, original_order: List[str], valid_settings: Dict[str, str]
    ) -> bool:
        """Check if configuration settings need to be reordered"""
        # Filter original order to only include valid settings
        current_valid_order = [
            setting_id for setting_id in original_order if setting_id in valid_settings
        ]

        # Get expected order for valid settings
        expected_order = [
            setting_id for setting_id in self.SETTINGS_ORDER if setting_id in valid_settings
        ]

        # Add any valid settings not in SETTINGS_ORDER (alphabetically)
        remaining_settings = sorted(
            [setting_id for setting_id in valid_settings if setting_id not in self.SETTINGS_ORDER]
        )
        expected_order.extend(remaining_settings)

        # Compare orders
        if current_valid_order != expected_order:
            logging.debug("Settings order differs from recommended:")
            logging.debug("  Current:  %s", current_valid_order)
            logging.debug("  Expected: %s", expected_order)
            return True

        return False

    def parse_image_sources(self, config_file: Path) -> List[tuple]:
        """Parse the <imagesources> block; returns a list of (url, enabled).

        Returns [] when the file has no block (callers fall back to the
        default sources).
        """
        try:
            root = ET.parse(config_file).getroot()
        except Exception:
            return []
        block = root.find("imagesources")
        if block is None:
            return []
        sources = []
        for src in block.findall("source"):
            url = (src.text or "").strip()
            if not url:
                continue
            status = (src.get("status") or "enabled").strip().lower()
            sources.append((url, status not in self._DISABLED_STATUSES))
        return sources

    @classmethod
    def active_image_source(cls, sources: List[tuple]) -> str:
        """Return the first enabled source URL, falling back to the default."""
        for url, enabled in sources:
            if enabled:
                return url
        for url, enabled in cls.DEFAULT_IMAGE_SOURCES:
            if enabled:
                return url
        return cls.DEFAULT_IMAGE_SOURCES[0][0]

    def _render_image_sources(self, sources: List[tuple]) -> str:
        """Serialize the <imagesources> block (uses defaults when empty)."""
        if not sources:
            sources = self.DEFAULT_IMAGE_SOURCES
        out = [
            "\n  <!-- Image source host (first 'enabled' is used;"
            " mirrors serve the same images) -->\n",
            "  <imagesources>\n",
        ]
        for url, enabled in sources:
            status = "enabled" if enabled else "disabled"
            out.append(f'    <source status="{status}">{url}</source>\n')
        out.append("  </imagesources>\n")
        return "".join(out)

    def write_clean_config(self, config_file: Path, valid_settings: Dict[str, str]):
        """Write configuration file in proper order with nice formatting"""
        # Preserve any existing <imagesources> block (read before truncating).
        image_sources = self.parse_image_sources(config_file)
        with open(config_file, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="utf-8"?>\n')
            f.write(f'<settings version="{self.CONFIG_VERSION}">\n')

            # Group settings with comments for better readability
            sections = [
                ("Basic guide settings", ["zipcode", "lineupid", "days"]),
                ("Station filtering", ["slist", "stitle"]),
                ("Extended details and language detection", ["xdetails", "xdesc", "langdetect"]),
                ("Display options", ["epgenre", "epicon"]),
                (
                    "TVheadend integration",
                    ["tvhoff", "tvhurl", "tvhport", "tvhmatch", "chmatch", "usern", "passw"],
                ),
                (
                    "Cache and retention policies",
                    ["redays", "refresh", "logrotate", "relogs", "rexmltv", "reconf"],
                ),
                ("Download performance", ["dlworkers", "dlthreshold"]),
            ]

            written_settings = set()

            for section_name, section_settings in sections:
                # Check if this section has any settings to write
                has_settings = any(setting_id in valid_settings for setting_id in section_settings)

                if has_settings:
                    f.write(f"\n  <!-- {section_name} -->\n")

                    for setting_id in section_settings:
                        if setting_id in valid_settings:
                            value = valid_settings[setting_id]
                            if value is not None and str(value).strip():
                                f.write(f'  <setting id="{setting_id}">{value}</setting>\n')
                            else:
                                f.write(f'  <setting id="{setting_id}"></setting>\n')
                            written_settings.add(setting_id)

            # Write any remaining settings not in predefined sections (alphabetically)
            remaining_settings = sorted(
                [setting_id for setting_id in valid_settings if setting_id not in written_settings]
            )

            if remaining_settings:
                f.write("\n  <!-- Other settings -->\n")
                for setting_id in remaining_settings:
                    value = valid_settings[setting_id]
                    if value is not None and str(value).strip():
                        f.write(f'  <setting id="{setting_id}">{value}</setting>\n')
                    else:
                        f.write(f'  <setting id="{setting_id}"></setting>\n')

            # Preserve / inject the image source block
            f.write(self._render_image_sources(image_sources))

            f.write("</settings>\n")

    def set_missing_defaults(
        self, settings: Dict[str, Any], original_settings: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Set default values for settings missing from the original config file.

        Whether a key is "missing" is decided from ``original_settings`` -- the
        config file as parsed, before any command-line overrides -- so a key
        supplied only on the CLI is still recognised as absent from the file and
        persisted with its default (matching the pre-refactor behaviour). Defaults
        are written into ``settings`` for this run without clobbering a CLI value,
        and the added defaults are returned for file persistence.
        """
        # Check if langdetect is available for smart default
        langdetect_available = self._check_langdetect_available()

        defaults = {
            "lineupid": "auto",
            "days": "1",
            "slist": "",
            "stitle": False,
            "xdetails": True,
            "xdesc": True,
            "langdetect": langdetect_available,
            "epgenre": "3",
            "epicon": "1",
            "tvhoff": True,
            "usern": "",
            "passw": "",
            "tvhurl": "127.0.0.1",
            "tvhport": "9981",
            "tvhmatch": True,
            "chmatch": True,
            "redays": "1",
            "refresh": "48",
            "logrotate": "true",
            "relogs": "30",
            "rexmltv": "7",
            "reconf": "10",
            "dlworkers": "auto",
            "dlthreshold": "auto",
        }

        # Decide what is missing from the ORIGINAL file (not the live, possibly
        # CLI-overridden settings); fall back to live settings when no snapshot.
        original = original_settings if original_settings is not None else settings

        settings_to_add = {}
        for key, default_value in defaults.items():
            if key not in original or original[key] is None:
                if key not in settings or settings[key] is None:
                    settings[key] = default_value
                settings_to_add[key] = default_value
                logging.debug("Set default: %s = %s", key, default_value)

        return settings_to_add

    def _check_langdetect_available(self) -> bool:
        """Check if langdetect library is available"""
        try:
            return True
        except ImportError:
            return False

    def get_station_list(self, settings: Dict[str, Any]) -> Optional[List[str]]:
        """Get explicit station list if configured"""
        slist = settings.get("slist", "")
        if slist and slist.strip():
            return [s.strip() for s in slist.split(",") if s.strip()]
        return None

    def needs_extended_download(self, settings: Dict[str, Any]) -> bool:
        """Determine if extended details download is needed"""
        return settings.get("xdetails", False) or settings.get("xdesc", False)
