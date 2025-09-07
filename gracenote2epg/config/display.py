"""
gracenote2epg.config.display - Display and testing utilities

Handles lineup detection testing, debug output, validation URL generation,
and configuration recommendation display for gracenote2epg configurations.
"""

import time
from datetime import datetime
from typing import Dict, Any


class ConfigDisplayer:
    """Handles configuration display and testing utilities"""

    def __init__(self, validator, lineup_manager):
        self.validator = validator
        self.lineup_manager = lineup_manager

    def display_lineup_detection_test(self, postal_code: str, debug_mode: bool = False) -> bool:
        """
        Display lineup detection test results - simplified by default, detailed in debug mode

        Args:
            postal_code: Postal/ZIP code to test
            debug_mode: Whether to show detailed debug information

        Returns:
            bool: True if valid postal code, False otherwise
        """
        # Validate postal code format
        is_valid, country, clean_postal = self.validator.validate_postal_code_format(postal_code)

        if not is_valid:
            print(f"❌ ERROR: Invalid postal/ZIP code format: {postal_code}")
            print("   Expected formats:")
            print("   - US ZIP code: 90210")
            print("   - Canadian postal: J3B1M4 or J3B 1M4")
            return False

        # Get country info
        country_name = "United States" if country == "USA" else "Canada"

        # Generate lineup IDs using lineup manager
        auto_lineup_config = self.lineup_manager.get_auto_lineup_config(clean_postal, country)

        # Display results using unified function
        self._display_lineup_output(
            postal_code, clean_postal, country_name, country, auto_lineup_config, debug_mode
        )

        return True

    def _display_lineup_output(self,
                              postal_code: str,
                              clean_postal: str,
                              country_name: str,
                              country: str,
                              lineup_config: Dict,
                              debug_mode: bool = False):
        """
        Display lineup detection output - unified function for both simple and debug modes

        Args:
            postal_code: Original postal code input
            clean_postal: Normalized postal code
            country_name: Full country name
            country: Country code (USA/CAN)
            lineup_config: Auto-generated lineup configuration
            debug_mode: Whether to show debug information
        """
        # Calculate current time rounded to nearest 3-hour block
        now = datetime.now().replace(microsecond=0, second=0, minute=0)
        # Round to nearest 3-hour block (0, 3, 6, 9, 12, 15, 18, 21)
        standard_hour = (now.hour // 3) * 3
        standard_dt = now.replace(hour=standard_hour)
        example_time = str(int(time.mktime(standard_dt.timetuple())))

        # Header (different for debug mode)
        if debug_mode:
            print("=" * 70)
            print("GRACENOTE2EPG - LINEUP DETECTION (DEBUG MODE)")
            print("=" * 70)
            print(f"📍 LOCATION INFORMATION:")
            print(f"   Normalized code:   {clean_postal}")
            print(f"   Detected country:  {country_name} ({country})")
            print()

        # API parameters
        print(f"🌐 GRACENOTE API URL PARAMETERS:")
        print(f"   lineupId={lineup_config['api_lineup_id']}")
        print(f"   country={country}")
        print(f"   postalCode={clean_postal}")
        print()

        # Validation URLs
        print(f"✅ VALIDATION URLs (manual verification):")
        print(f"   Auto-generated: {lineup_config['tvtv_url']}")

        if debug_mode:
            print(
                f"   Note: OTA format is {lineup_config['tvtv_lineup_id']} "
                f"(country + OTA + postal, no -DEFAULT suffix)"
            )
            print(f"   Cable/Satellite providers use different format: {country}-[ProviderID]-X")

        print(f"   Manual lookup:")
        if country == "CAN":
            print(f"     1. Go to https://www.tvtv.ca/")
            print(f"     2. Enter postal code: {clean_postal}")
            print(
                f"     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → "
                f"URL shows lu{lineup_config['tvtv_lineup_id']}"
            )
            print(f"     3b. For Cable/Sat: Select provider → URL shows lu{country}-[ProviderID]-X")
        else:
            print(f"     1. Go to https://www.tvtv.us/")
            print(f"     2. Enter ZIP code: {clean_postal}")
            print(
                f"     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → "
                f"URL shows lu{lineup_config['tvtv_lineup_id']}"
            )
            print(f"     3b. For Cable/Sat: Select provider → URL shows lu{country}-[ProviderID]-X")
        print()

        # API test URL
        test_url = self.lineup_manager.generate_gracenote_api_url(lineup_config, int(example_time))
        print(f"🔗 GRACENOTE API URL FOR TESTING:")

        if debug_mode:
            # Show the human-readable time for debugging
            print(f"   Using current block: {standard_dt.strftime('%Y-%m-%d %H:00')} "
                  f"(timestamp: {example_time})")

        print(f"   {test_url}")
        print()

        # Debug-only sections
        if debug_mode:
            self._display_debug_sections(country, lineup_config, clean_postal, test_url)

        # Documentation link (always shown)
        print("📖 DOCUMENTATION:")
        print("   https://github.com/th0ma7/gracenote2epg/blob/main/docs/lineup-configuration.md")

    def _display_debug_sections(self, country: str, lineup_config: Dict, clean_postal: str, test_url: str):
        """Display debug-only sections for detailed mode"""
        print(f"📊 GRACENOTE API - OTHER COMMON PARAMETERS:")
        print(
            f"   • &device=[-|X]                    "
            f"Device type: - for Over-the-Air, X for cable/satellite"
        )
        print(
            f"   • &pref=16%2C128                   "
            f"Preference codes (16,128): channel lineup preferences"
        )
        print(
            f"   • &timezone=America%2FNew_York     "
            f"User timezone for schedule times (URL-encoded)"
        )
        print(f"   • &languagecode=en-us              Content language: en-us, fr-ca, es-us, etc.")
        print(
            f"   • &TMSID=                          "
            f"Tribune Media Services ID (legacy, usually empty)"
        )
        print(
            f"   • &AffiliateID=lat                 "
            f"Partner/affiliate identifier (lat=local affiliate)"
        )
        print()

        print(f"💾 MANUAL DOWNLOAD:")
        print(f"⚠️  NOTE: Using browser-like headers to bypass AWS WAF")
        print()
        print(
            f'curl -s -H "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            f'AppleWebKit/537.36" \\'
        )
        print(f'     -H "Accept: application/json, text/html, application/xhtml+xml, */*" \\')
        print(f'     "{test_url}" > out.json')
        print()

        print(f"🔧 RECOMMENDED CONFIGURATION:")
        country_full = "Canada" if country == "CAN" else "United States"
        print(f"   <!-- Simplified configuration (auto-detection) -->")
        print(f'   <setting id="zipcode">{clean_postal}</setting>')
        print(f'   <setting id="lineupid">auto</setting>')
        print()
        print(f"   <!-- Alternative: Copy tvtv.com lineup ID directly -->")
        print(f"   <!-- <setting id=\"lineupid\">{lineup_config['tvtv_lineup_id']}</setting> -->")
        print()
        print(f"   <!-- For Cable/Satellite providers: -->")
        print(f'   <!-- <setting id="lineupid">{country}-[ProviderID]-X</setting> -->')
        print(
            f'   <!-- Example: <setting id="lineupid">{country}-0005993-X</setting> '
            f'for Videotron -->'
        )
        print()

        print("=" * 70)
        print("💡 NEXT STEPS:")
        print("1. Verify the validation URLs show your local channels")
        print("2. Update your gracenote2epg.xml with the recommended configuration")
        print("3. Run: tv_grab_gracenote2epg --days 1 --console")
        print("4. Look for 'Auto-detected lineupID' in the logs")
        print("5. Confirm no HTTP 400 errors in download attempts")
        print("=" * 70)
        print()

    def display_config_summary(self, settings: Dict[str, Any], lineup_config: Dict[str, str], 
                              retention_config: Dict[str, Any], config_changes: Dict[str, str]):
        """Display comprehensive configuration summary"""
        print("Configuration Summary:")
        print("=" * 50)
        
        # Enhanced zipcode logging with cleaner format
        zipcode = settings.get("zipcode")
        if "zipcode" in config_changes:
            change_info = config_changes["zipcode"]
            print(f"  zipcode: {change_info}")
        else:
            print(f"  zipcode: {zipcode}")

        # Enhanced lineup configuration logging
        original_lineupid = lineup_config["original_config"]
        final_lineup_id = lineup_config["lineup_id"]

        if "lineupid" in config_changes:
            change_info = config_changes["lineupid"]
            print(f"  lineupid: {change_info}")
        elif lineup_config["auto_detected"]:
            print(f"  lineupid: {original_lineupid} → {final_lineup_id} (auto-detection)")
        else:
            print(f"  lineupid: {original_lineupid} → {final_lineup_id}")

        # Country information
        country = lineup_config["country"]
        country_name = "Canada" if country == "CAN" else "United States of America"
        print(f"  country: {country_name} [{country}] (auto-detected from zipcode)")
        print(f"  description: {lineup_config['description']}")

        # Feature settings
        print(f"  xdetails (download extended data): {settings.get('xdetails')}")
        print(f"  xdesc (use extended descriptions): {settings.get('xdesc')}")
        print(f"  langdetect (automatic language detection): {settings.get('langdetect')}")

        # Cache and retention
        self._display_cache_retention_summary(settings, retention_config)

    def _display_cache_retention_summary(self, settings: Dict[str, Any], retention_config: Dict[str, Any]):
        """Display cache and retention policy summary"""
        from .retention import RetentionManager
        retention_manager = RetentionManager()
        
        refresh_hours = retention_manager.get_refresh_hours(settings)
        redays = retention_manager.get_cache_retention_days(settings)

        print("Cache and retention policies:")
        if refresh_hours == 0:
            print("  refresh: disabled (use all cached data)")
        else:
            print(f"  refresh: {refresh_hours} hours (refresh first {refresh_hours} hours of guide)")

        print(f"  redays: {redays} days (cache retention period)")

        if retention_config["enabled"]:
            print(
                f"  logrotate: enabled ({retention_config['interval']}, "
                f"{retention_config['log_retention_days']} days retention)"
            )
        else:
            print("  logrotate: disabled")

        print(f"  rexmltv: {retention_config['xmltv_retention_days']} days (XMLTV backup retention)")

    def display_feature_logic(self, settings: Dict[str, Any]):
        """Display configuration logic explanation"""
        xdetails = settings.get("xdetails", False)
        xdesc = settings.get("xdesc", False)
        langdetect = settings.get("langdetect", False)

        print("Configuration logic:")
        if xdesc and not xdetails:
            print("  xdesc=true detected - automatically enabling extended details download")
        elif xdetails and not xdesc:
            print("  xdetails=true - downloading extended data but using basic descriptions")
        elif xdetails and xdesc:
            print("  Both xdetails and xdesc enabled - full extended functionality")
        else:
            print("  Extended features disabled - using basic guide data only")

        if langdetect:
            print("  Language detection enabled - will auto-detect French/English/Spanish")
        else:
            print("  Language detection disabled - all content will be marked as English")

    def display_optimization_recommendations(self, settings: Dict[str, Any]):
        """Display optimization recommendations if any"""
        from .retention import RetentionManager
        retention_manager = RetentionManager()
        
        recommendations = retention_manager.optimize_retention_settings(settings)
        
        if recommendations:
            print()
            print("💡 OPTIMIZATION RECOMMENDATIONS:")
            for setting, recommendation in recommendations.items():
                print(f"  {setting}: {recommendation}")
