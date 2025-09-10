"""
gracenote2epg.gracenote2epg_lineup - Lineup management and geographic resolution

Handles lineup ID management, auto-detection, geographic location resolution
for accurate URL generation, and validation URL generation for gracenote2epg configurations.
"""

import logging
import re
import sys
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

# Geographic resolution support
try:
    import pgeocode

    PGEOCODE_AVAILABLE = True
except ImportError:
    PGEOCODE_AVAILABLE = False
    logging.debug("pgeocode not available - geographic resolution disabled")


class Geocoder:
    """Handles geographic location resolution using pgeocode"""

    def __init__(self, debug_function=None):
        # Cache to avoid repeated queries
        self._location_cache = {}

        # Debug function (can be injected for console debug)
        self._debug = debug_function or self._default_debug

        # Initialize pgeocode geolocators if available
        self._ca_geocoder = None
        self._us_geocoder = None

        if PGEOCODE_AVAILABLE:
            try:
                self._ca_geocoder = pgeocode.Nominatim("CA")
                self._us_geocoder = pgeocode.Nominatim("US")
                self._debug("pgeocode initialized successfully")
            except Exception as e:
                self._debug("Failed to initialize pgeocode: %s", str(e))
                logging.warning("Failed to initialize pgeocode: %s", str(e))

    def _default_debug(self, message, *args):
        """Default debug function using standard logging"""
        if args:
            logging.debug(message, *args)
        else:
            logging.debug(message)

    def resolve_location(
        self, postal_code: str, country: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve postal code to city and province/state using pgeocode
        For Canadian postal codes: tries full code first, then first 3 characters

        Args:
            postal_code: Postal/ZIP code to resolve
            country: Country code (CAN/USA)

        Returns:
            Tuple of (city, province_code) or (None, None) if not found
        """
        # Check cache first
        cache_key = f"{postal_code}_{country}"
        if cache_key in self._location_cache:
            cached_result = self._location_cache[cache_key]
            self._debug("Using cached result for %s: %s", cache_key, cached_result)
            return cached_result

        city, province = None, None

        # Try pgeocode (offline, no dependencies)
        if PGEOCODE_AVAILABLE:
            self._debug("Trying pgeocode for %s", postal_code)
            city, province = self._try_pgeocode(postal_code, country)
            if city and province:
                self._debug("pgeocode SUCCESS: %s, %s", city, province)
                self._location_cache[cache_key] = (city, province)
                return city, province
            else:
                self._debug("pgeocode failed or returned incomplete data")
        else:
            self._debug("pgeocode not available")

        # Cache the failure to avoid repeated attempts
        self._debug("Location resolution failed for %s", postal_code)
        self._location_cache[cache_key] = (None, None)
        return None, None

    def _try_pgeocode(self, postal_code: str, country: str) -> Tuple[Optional[str], Optional[str]]:
        """Use pgeocode to resolve postal code to city/province"""
        try:
            geocoder = self._ca_geocoder if country == "CAN" else self._us_geocoder
            if geocoder is None:
                self._debug("No pgeocode geocoder available for country %s", country)
                return None, None

            # Query postal code
            clean_postal = postal_code.replace(" ", "")
            self._debug("pgeocode querying %s", clean_postal)

            result = geocoder.query_postal_code(clean_postal)

            # For Canadian postal codes, if full code fails, try first 3 characters
            if (
                (result is None or result.empty or self._is_result_invalid(result))
                and country == "CAN"
                and len(clean_postal) >= 3
            ):
                partial_postal = clean_postal[:3]
                self._debug("pgeocode full code failed, trying partial code: %s", partial_postal)
                result = geocoder.query_postal_code(partial_postal)

            if result is not None and hasattr(result, "empty") and not result.empty:
                # Get state/province code directly from pgeocode
                province_code = (
                    result.get("state_code")
                    if hasattr(result, "get")
                    else getattr(result, "state_code", None)
                )

                # Extract city using optimal hierarchy based on country
                city = self._extract_optimal_city_name(result, country)

                self._debug(
                    "pgeocode raw result - city: %s, province_code: %s", city, province_code
                )

                # Clean up the results
                if city and isinstance(city, str) and city.strip() and str(city).lower() != "nan":
                    city = city.strip()
                else:
                    city = None

                if (
                    province_code
                    and isinstance(province_code, str)
                    and province_code.strip()
                    and str(province_code).lower() != "nan"
                ):
                    province_code = province_code.strip()
                else:
                    province_code = None

                if city and province_code:
                    self._debug(
                        "pgeocode cleaned result - city: %s, province_code: %s", city, province_code
                    )
                    return city, province_code
                else:
                    self._debug("pgeocode returned incomplete data after cleaning")
            else:
                self._debug("pgeocode returned empty or invalid result")

        except Exception as e:
            self._debug("pgeocode lookup failed for %s: %s", postal_code, str(e))

        return None, None

    def _extract_optimal_city_name(self, result, country: str) -> Optional[str]:
        """
        Extract optimal city name using pgeocode's hierarchy
        Canada: community_name → county_name → place_name (cleaned)
        USA: place_name → county_name
        """

        def get_field(field_name):
            value = (
                result.get(field_name)
                if hasattr(result, "get")
                else getattr(result, field_name, None)
            )
            return value if value and str(value).lower() not in ["nan", "none", ""] else None

        if country == "CAN":
            # Canada: Try community_name first (most generic)
            city = get_field("community_name")
            if city:
                self._debug("Using community_name: '%s'", city)
                return city

            # Fallback to county_name
            city = get_field("county_name")
            if city:
                self._debug("Using county_name: '%s'", city)
                return city

            # Last resort: clean place_name
            city = get_field("place_name")
            if city:
                cleaned_city = self._extract_generic_city_name(city)
                self._debug("Using cleaned place_name: '%s' → '%s'", city, cleaned_city)
                return cleaned_city

        else:
            # USA: place_name is usually already generic
            city = get_field("place_name")
            if city:
                self._debug("Using place_name: '%s'", city)
                return city

            # Fallback to county_name if needed
            city = get_field("county_name")
            if city:
                self._debug("Using county_name: '%s'", city)
                return city

        return None

    def _extract_generic_city_name(self, city_name: str) -> str:
        """
        Extract generic city name from detailed place names (fallback only)
        Examples:
        - "Edmonton (North Downtown)" → "Edmonton"
        - "Saint-Jean-sur-Richelieu Central" → "Saint-Jean-sur-Richelieu"
        """
        if not city_name:
            return city_name

        # Remove parenthetical descriptions first
        if "(" in city_name:
            city_name = city_name.split("(")[0].strip()

        # Remove common directional/area suffixes
        directional_suffixes = [
            " East",
            " West",
            " North",
            " South",
            " Central",
            " Northeast",
            " Northwest",
            " Southeast",
            " Southwest",
            " Downtown",
            " Uptown",
            " Midtown",
        ]

        for suffix in directional_suffixes:
            if city_name.endswith(suffix):
                city_name = city_name[: -len(suffix)].strip()
                break

        return city_name

    def _is_result_invalid(self, result) -> bool:
        """Check if pgeocode result is invalid (contains only NaN values)"""
        try:
            if not hasattr(result, "get") and not hasattr(result, "place_name"):
                return True

            city = (
                result.get("place_name")
                if hasattr(result, "get")
                else getattr(result, "place_name", None)
            )
            province_code = (
                result.get("state_code")
                if hasattr(result, "get")
                else getattr(result, "state_code", None)
            )
            province_name = (
                result.get("state_name")
                if hasattr(result, "get")
                else getattr(result, "state_name", None)
            )

            # If all important fields are NaN or None, consider invalid
            city_invalid = not city or str(city).lower() in ["nan", "none", ""]
            province_code_invalid = not province_code or str(province_code).lower() in [
                "nan",
                "none",
                "",
            ]
            province_name_invalid = not province_name or str(province_name).lower() in [
                "nan",
                "none",
                "",
            ]

            return city_invalid and province_code_invalid and province_name_invalid

        except Exception:
            return True

    def clear_cache(self):
        """Clear the location cache"""
        self._location_cache.clear()

    def get_cache_stats(self) -> Dict:
        """Get cache statistics for debugging"""
        return {
            "cache_size": len(self._location_cache),
            "cached_locations": list(self._location_cache.keys()),
        }


class LineupManager:
    """Handles lineup ID management and auto-detection"""

    def __init__(self):
        # Debug output control for --show-lineup mode
        self._console_debug = False
        self._check_console_debug_mode()

        # Initialize geocoder with appropriate debug function
        self._geocoder = Geocoder(debug_function=self._debug)

    def _check_console_debug_mode(self):
        """Check if we should output debug to console (--show-lineup + --debug)"""
        # Check if we're in show-lineup mode with debug
        args = sys.argv
        has_show_lineup = any("--show-lineup" in arg for arg in args)
        has_debug = any("--debug" in arg for arg in args)

        # Check if logging has console handlers configured
        root_logger = logging.getLogger()
        has_console_handler = any(
            isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout
            for handler in root_logger.handlers
        )

        # Enable console debug if show-lineup + debug but no console logging configured
        self._console_debug = has_show_lineup and has_debug and not has_console_handler

        if self._console_debug:
            self._debug("Console debug mode enabled for --show-lineup")

    def _debug(self, message, *args):
        """Smart debug output - console for --show-lineup, logging otherwise"""
        if self._console_debug:
            # Format message like logging would
            if args:
                formatted_message = message % args
            else:
                formatted_message = message
            print(f"DEBUG: {formatted_message}")
        else:
            # Use normal logging
            if args:
                logging.debug(message, *args)
            else:
                logging.debug(message)

    def _normalize_city_for_url(self, city: str) -> str:
        """Convert city name to tvtv URL format"""
        if not city:
            return ""

        # Convert to lowercase and replace spaces/apostrophes with hyphens
        normalized = city.lower()
        normalized = re.sub(r"['\s]+", "-", normalized)
        # Remove accents and special characters
        normalized = self._remove_accents(normalized)
        # Remove any non-alphanumeric characters except hyphens
        normalized = re.sub(r"[^a-z0-9-]", "", normalized)
        # Remove multiple consecutive hyphens
        normalized = re.sub(r"-+", "-", normalized)
        # Remove leading/trailing hyphens
        normalized = normalized.strip("-")

        return normalized

    def _remove_accents(self, text: str) -> str:
        """Remove French accents for URL normalization"""
        accent_map = {
            "à": "a",
            "á": "a",
            "â": "a",
            "ã": "a",
            "ä": "a",
            "è": "e",
            "é": "e",
            "ê": "e",
            "ë": "e",
            "ì": "i",
            "í": "i",
            "î": "i",
            "ï": "i",
            "ò": "o",
            "ó": "o",
            "ô": "o",
            "õ": "o",
            "ö": "o",
            "ù": "u",
            "ú": "u",
            "û": "u",
            "ü": "u",
            "ç": "c",
            "ñ": "n",
        }

        for accented, unaccented in accent_map.items():
            text = text.replace(accented, unaccented)

        return text

    def _get_province_code_for_url(self, province_code: str, country: str) -> str:
        """Convert province code to tvtv URL format (lowercase)"""
        if not province_code:
            return "qc" if country == "CAN" else "ca"

        # For URL, we need lowercase
        return province_code.lower()

    def get_auto_lineup_config(self, postal_code: str, country: str) -> Dict[str, str]:
        """Get auto-generated lineup configuration with geocoding support"""
        self._debug("Attempting automatic resolution for %s, %s", postal_code, country)

        # Generate OTA lineup IDs
        base_lineup = f"OTA{postal_code}"
        tvtv_lineup_id = f"{country}-{base_lineup}"
        api_lineup_id = f"{country}-{base_lineup}-DEFAULT"

        # Try to resolve city/province automatically using geocoder
        city, province_code = self._geocoder.resolve_location(postal_code, country)

        if city and province_code:
            # SUCCESS: Generate dynamic URL
            province_code_url = self._get_province_code_for_url(province_code, country)
            city_url = self._normalize_city_for_url(city)
            postal_for_url = postal_code.lower().replace(" ", "")

            if country == "CAN":
                tvtv_url = f"https://www.tvtv.ca/{province_code_url}/{city_url}/{postal_for_url}/lu{tvtv_lineup_id}"
            else:
                tvtv_url = f"https://www.tvtv.us/{province_code_url}/{city_url}/{postal_code}/lu{tvtv_lineup_id}"

            status = "auto_resolved"
            self._debug("Resolution successful - %s, %s → %s", city, province_code, tvtv_url)

        else:
            # FAILURE: Unable to resolve location automatically
            if country == "CAN":
                base_url = "https://www.tvtv.ca/"
            else:
                base_url = "https://www.tvtv.us/"

            tvtv_url = base_url
            status = "unable_to_resolve"
            self._debug("Unable to resolve location for %s - manual lookup required", postal_code)

        return {
            "tvtv_lineup_id": tvtv_lineup_id,
            "api_lineup_id": api_lineup_id,
            "tvtv_url": tvtv_url,
            "device_type": "-",
            "country": country,
            "postal_code": postal_code,
            "resolved_city": city,
            "resolved_province": province_code,
            "location_source": status,
            # Always provide manual lookup instructions as fallback
            "manual_lookup_message": f"Unable to automatically resolve location for {postal_code}. Please use manual lookup instructions below.",
        }

    def normalize_lineup_id(self, lineupid: str, country: str, postal_code: str) -> str:
        """
        Normalize lineup ID to API format

        Args:
            lineupid: Raw lineup ID from config (auto, tvtv format, or complete)
            country: Country code (USA/CAN)
            postal_code: Postal/ZIP code

        Returns:
            Normalized lineup ID for API use
        """
        if not lineupid or lineupid.lower() == "auto":
            # Auto-generate OTA lineup ID
            return f"{country}-OTA{postal_code}-DEFAULT"

        elif not lineupid.endswith("-DEFAULT") and not lineupid.endswith("-X"):
            # Format from tvtv.com (e.g. CAN-OTAJ3B1M4) → Add -DEFAULT for API
            return f"{lineupid}-DEFAULT"

        else:
            # Already complete format (e.g. CAN-OTAJ3B1M4-DEFAULT or CAN-0005993-X)
            return lineupid

    def detect_device_type(self, normalized_lineup_id: str) -> str:
        """
        Auto-detect device type from lineup ID

        Args:
            normalized_lineup_id: Normalized lineup ID

        Returns:
            Device type: "-" for OTA, "X" for cable/satellite
        """
        if "OTA" in normalized_lineup_id:
            return "-"  # Over-the-Air
        elif normalized_lineup_id.endswith("-X"):
            return "X"  # Cable/Satellite
        else:
            return "-"  # Default to OTA

    def generate_description(self, normalized_lineup_id: str, country: str) -> str:
        """
        Auto-generate description from lineup ID

        Args:
            normalized_lineup_id: Normalized lineup ID
            country: Country code

        Returns:
            Human-readable description
        """
        country_name = "United States" if country == "USA" else "Canada"

        if "OTA" in normalized_lineup_id:
            return f"Local Over the Air Broadcast ({country_name})"
        elif normalized_lineup_id.endswith("-X"):
            return f"Cable/Satellite Provider ({country_name})"
        else:
            return f"TV Lineup ({country_name})"

    def get_lineup_config(self, lineupid: str, postal_code: str, country: str) -> Dict[str, str]:
        """Get lineup configuration with automatic normalization and detection"""
        # Normalize lineup ID
        normalized_lineup_id = self.normalize_lineup_id(lineupid, country, postal_code)

        # Auto-detect device type
        device_type = self.detect_device_type(normalized_lineup_id)

        # Auto-generate description
        description = self.generate_description(normalized_lineup_id, country)

        # Determine if this was auto-detected
        auto_detected = not lineupid or lineupid.lower() == "auto"

        return {
            "lineup_id": normalized_lineup_id,  # Full API format
            "headend_id": "lineupId",  # Always literal 'lineupId' for API
            "device_type": device_type,  # Auto-detected device type
            "description": description,  # Auto-generated description
            "auto_detected": auto_detected,
            "original_config": lineupid,  # Original config value
            "country": country,
            "postal_code": postal_code,
        }

    def generate_gracenote_api_url(self, config: Dict[str, str], timestamp: int = None) -> str:
        """
        Generate Gracenote API URL for testing

        Args:
            config: Lineup configuration from get_auto_lineup_config()
            timestamp: Unix timestamp for the request (optional, uses current time)

        Returns:
            Complete API URL for testing
        """
        if timestamp is None:
            # Calculate current time rounded to nearest 3-hour block
            now = datetime.now().replace(microsecond=0, second=0, minute=0)
            # Round to nearest 3-hour block (0, 3, 6, 9, 12, 15, 18, 21)
            standard_hour = (now.hour // 3) * 3
            standard_dt = now.replace(hour=standard_hour)
            timestamp = int(time.mktime(standard_dt.timetuple()))

        return (
            f"https://tvlistings.gracenote.com/api/grid?"
            f"aid=orbebb&"
            f"country={config['country']}&"
            f"postalCode={config['postal_code']}&"
            f"time={timestamp}&"
            f"timespan=3&"
            f"isOverride=true&"
            f"userId=-&"
            f"lineupId={config['api_lineup_id']}&"
            f"headendId=lineupId"
        )

    def generate_validation_urls(self, postal_code: str, country: str) -> Dict[str, str]:
        """
        Generate validation URLs that always work

        Args:
            postal_code: Clean postal code (no spaces)
            country: Country code (USA/CAN)

        Returns:
            Dictionary with validation URLs and instructions
        """
        lineup_config = self.get_auto_lineup_config(postal_code, country)

        if country == "CAN":
            base_url = "https://www.tvtv.ca/"
            formatted_postal = self._format_postal_for_display(postal_code, country)
            instructions = [
                f"1. Go to {base_url}",
                f"2. Enter postal code: {formatted_postal}",
                f"3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → Look for 'lu{lineup_config['tvtv_lineup_id']}' in URL",
                f"3b. For Cable/Sat: Select your provider → Look for 'lu{country}-[ProviderID]-X' in URL",
                f"4. Expected OTA pattern: lu{lineup_config['tvtv_lineup_id']}",
            ]
        else:
            base_url = "https://www.tvtv.us/"
            instructions = [
                f"1. Go to {base_url}",
                f"2. Enter ZIP code: {postal_code}",
                f"3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → Look for 'lu{lineup_config['tvtv_lineup_id']}' in URL",
                f"3b. For Cable/Sat: Select your provider → Look for 'lu{country}-[ProviderID]-X' in URL",
                f"4. Expected OTA pattern: lu{lineup_config['tvtv_lineup_id']}",
            ]

        return {
            "base_url": base_url,
            "auto_generated_url": lineup_config["tvtv_url"],
            "instructions": instructions,
            "tvtv_lineup_id": lineup_config["tvtv_lineup_id"],
            "expected_pattern": f"lu{lineup_config['tvtv_lineup_id']}",
        }

    def _format_postal_for_display(self, postal_code: str, country: str = None) -> str:
        """Format postal code for display (with space for Canadian postal codes)"""
        if country == "CAN" and len(postal_code) == 6:
            return f"{postal_code[:3]} {postal_code[3:]}"
        return postal_code

    def generate_config_recommendations(self, postal_code: str, country: str) -> Dict[str, str]:
        """
        Generate configuration recommendations for user

        Args:
            postal_code: Clean postal code
            country: Country code

        Returns:
            Dictionary with configuration recommendations
        """
        lineup_config = self.get_auto_lineup_config(postal_code, country)
        self._format_postal_for_display(postal_code, country)

        return {
            "auto_detection": {
                "zipcode": postal_code,
                "lineupid": "auto",
                "description": "Recommended: Uses automatic detection",
            },
            "manual_tvtv": {
                "zipcode": postal_code,
                "lineupid": lineup_config["tvtv_lineup_id"],
                "description": f"Manual: Copy lineup ID from tvtv.com",
            },
            "manual_api": {
                "zipcode": postal_code,
                "lineupid": lineup_config["api_lineup_id"],
                "description": "Advanced: Complete API format",
            },
        }

    def validate_postal_code_format(self, postal_code: str) -> Tuple[bool, str, str]:
        """
        Validate postal code format and return country info

        Args:
            postal_code: Raw postal code input

        Returns:
            tuple: (is_valid, country_code, clean_postal)
        """
        clean_postal = postal_code.replace(" ", "").upper()

        if clean_postal.isdigit() and len(clean_postal) == 5:
            return True, "USA", clean_postal
        elif re.match(r"^[A-Z][0-9][A-Z][0-9][A-Z][0-9]$", clean_postal):
            return True, "CAN", clean_postal
        else:
            return False, "", clean_postal

    def log_lineup_detection_results(self, original_lineupid: str, final_config: Dict[str, str]):
        """Log lineup detection results for debugging"""
        if final_config["auto_detected"]:
            logging.info(
                "Auto-detected lineupID: %s → %s", original_lineupid, final_config["lineup_id"]
            )
        else:
            logging.info(
                "Normalized lineupID: %s → %s", original_lineupid, final_config["lineup_id"]
            )

        logging.debug(
            "Lineup details: device=%s, description='%s'",
            final_config["device_type"],
            final_config["description"],
        )

    def display_lineup_detection_test(self, postal_code: str, debug_mode: bool = False) -> bool:
        """
        Display lineup detection test results - with enhanced geocoding support

        Args:
            postal_code: Postal/ZIP code to test
            debug_mode: Whether to show detailed debug information

        Returns:
            bool: True if valid postal code, False otherwise
        """
        # Validate postal code format
        is_valid, country, clean_postal = self.validate_postal_code_format(postal_code)

        if not is_valid:
            print(f"❌ ERROR: Invalid postal/ZIP code format: {postal_code}")
            print("   Expected formats:")
            print("   - US ZIP code: 90210")
            print("   - Canadian postal: J3B1M4 or J3B 1M4")
            return False

        # Get country info
        country_name = "United States" if country == "USA" else "Canada"

        # Generate lineup IDs using enhanced method with geocoding
        auto_lineup_config = self.get_auto_lineup_config(clean_postal, country)

        # Display results
        self._display_lineup_output(
            postal_code, clean_postal, country_name, country, auto_lineup_config, debug_mode
        )

        return True

    def _display_lineup_output(
        self,
        postal_code: str,
        clean_postal: str,
        country_name: str,
        country: str,
        lineup_config: Dict,
        debug_mode: bool = False,
    ):
        """
        Display lineup detection output - enhanced version with geocoding status
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
        print(f"🌍 GRACENOTE API URL PARAMETERS:")
        print(f"   lineupId={lineup_config['api_lineup_id']}")
        print(f"   country={country}")
        print(f"   postalCode={clean_postal}")
        print()

        # Validation URLs - ENHANCED VERSION
        print(f"✅ VALIDATION URLs:")

        # Check if location was resolved automatically
        if lineup_config.get("location_source") == "auto_resolved":
            print(f"   Direct URL: {lineup_config['tvtv_url']}")
            print(
                f"   Status: ✅ Location automatically resolved ({lineup_config.get('resolved_city')}, {lineup_config.get('resolved_province')})"
            )
        else:
            print(
                f"   Status: ⚠️  {lineup_config.get('manual_lookup_message', 'Unable to automatically resolve location')}"
            )
            print(f"   Manual lookup required:")

        # Always show manual lookup steps
        try:
            validation_urls = self.generate_validation_urls(clean_postal, country)
            for instruction in validation_urls["instructions"]:
                print(f"     {instruction}")
        except Exception:
            # Fallback manual instructions
            if country == "CAN":
                print(f"     1. Go to https://www.tvtv.ca/")
                print(f"     2. Enter postal code: {clean_postal}")
            else:
                print(f"     1. Go to https://www.tvtv.us/")
                print(f"     2. Enter ZIP code: {clean_postal}")
            print(f"     3. Click 'Broadcast' → 'Local Over the Air'")
            print(f"     4. Look for 'lu{lineup_config['tvtv_lineup_id']}' in the URL")

        print()

        if debug_mode:
            print(
                f"   Note: OTA format is {lineup_config['tvtv_lineup_id']} "
                f"(country + OTA + postal, no -DEFAULT suffix)"
            )
            print(f"   Cable/Satellite providers use different format: {country}-[ProviderID]-X")

        # API test URL
        print(f"🔗 GRACENOTE API URL FOR TESTING:")

        if debug_mode:
            # Show the human-readable time for debugging
            print(
                f"   Using current block: {standard_dt.strftime('%Y-%m-%d %H:00')} "
                f"(timestamp: {example_time})"
            )

        test_url = self.generate_gracenote_api_url(lineup_config, int(example_time))
        print(f"   {test_url}")
        print()

        # Debug-only sections
        if debug_mode:
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
            print(
                f"   • &languagecode=en-us              Content language: en-us, fr-ca, es-us, etc."
            )
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
            print(f"   <!-- Simplified configuration (auto-detection) -->")
            print(f'   <setting id="zipcode">{clean_postal}</setting>')
            print(f'   <setting id="lineupid">auto</setting>')
            print()
            print(f"   <!-- Alternative: Copy tvtv.com lineup ID directly -->")
            print(
                f"   <!-- <setting id=\"lineupid\">{lineup_config['tvtv_lineup_id']}</setting> -->"
            )
            print()
            print(f"   <!-- For Cable/Satellite providers: -->")
            print(f'   <!-- <setting id="lineupid">{country}-[ProviderID]-X</setting> -->')
            print(
                f'   <!-- Example: <setting id="lineupid">{country}-0005993-X</setting> '
                f"for Videotron -->"
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

        # Documentation link (always shown)
        print("📖 DOCUMENTATION:")
        print("   https://github.com/th0ma7/gracenote2epg/blob/main/docs/lineup-configuration.md")
