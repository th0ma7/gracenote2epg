"""
gracenote2epg.geocoding - Geographic location resolution

Resolves postal/ZIP codes to a city and province/state using a small bundled
GeoNames dataset (gracenote2epg/data/geopostal.csv.gz), read with the standard
library only. This replaces the former pgeocode dependency (which pulled in
pandas/numpy) so the grabber runs on any platform.

The resolution is only used to build the human-friendly tvtv.com validation URL
shown by --show-lineup; it has no effect on the downloaded guide (Gracenote
derives local stations from the postalCode that is sent directly).
"""

import csv
import gzip
import io
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

# App country codes (CAN/USA) -> GeoNames country codes (CA/US)
_COUNTRY_MAP = {"CAN": "CA", "USA": "US"}

_DATA_FILE = Path(__file__).resolve().parent / "data" / "geopostal.csv.gz"

# Lazily-loaded, process-wide cache: {(geonames_country, postal): {fields}}
_POSTAL_DB: Optional[Dict[Tuple[str, str], Dict[str, str]]] = None


def _load_postal_db() -> Dict[Tuple[str, str], Dict[str, str]]:
    """Load and cache the bundled postal dataset (once per process)."""
    global _POSTAL_DB
    if _POSTAL_DB is not None:
        return _POSTAL_DB

    db: Dict[Tuple[str, str], Dict[str, str]] = {}
    try:
        with gzip.open(_DATA_FILE, "rt", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                key = (row["country"], row["postal"])
                db[key] = {
                    "place_name": row.get("place_name", ""),
                    "state_code": row.get("state_code", ""),
                    "state_name": row.get("state_name", ""),
                    "county_name": row.get("county_name", ""),
                    "community_name": row.get("community_name", ""),
                }
    except FileNotFoundError:
        logging.debug("Postal dataset not found at %s - geo resolution disabled", _DATA_FILE)
    except Exception as e:
        logging.warning("Failed to load postal dataset: %s", str(e))

    _POSTAL_DB = db
    return db


class Geocoder:
    """Resolves postal codes to city/province using the bundled GeoNames data."""

    def __init__(self, debug_function=None):
        # Cache to avoid repeated queries
        self._location_cache: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

        # Debug function (can be injected for console debug)
        self._debug = debug_function or self._default_debug

    def _default_debug(self, message, *args):
        """Default debug function using standard logging"""
        if args:
            logging.debug(message, *args)
        else:
            logging.debug(message)

    def resolve_location(self, postal_code: str, country: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve postal code to city and province/state.
        For Canadian postal codes: tries the full code first, then the first 3
        characters (GeoNames stores Canada at the FSA / 3-character level).

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

        city, province = self._lookup(postal_code, country)
        if city and province:
            self._debug("Resolution SUCCESS: %s, %s", city, province)
        else:
            self._debug("Location resolution failed for %s", postal_code)

        result = (city, province) if (city and province) else (None, None)
        self._location_cache[cache_key] = result
        return result

    def _lookup(self, postal_code: str, country: str) -> Tuple[Optional[str], Optional[str]]:
        """Look up the bundled dataset and extract city/province."""
        try:
            geo_country = _COUNTRY_MAP.get(country)
            if geo_country is None:
                self._debug("Unsupported country for geo resolution: %s", country)
                return None, None

            db = _load_postal_db()
            if not db:
                self._debug("Postal dataset unavailable")
                return None, None

            clean_postal = postal_code.replace(" ", "").upper()
            self._debug("Looking up %s/%s", geo_country, clean_postal)

            result = db.get((geo_country, clean_postal))

            # Canada: full 6-character codes are not in the FSA-level data, so
            # fall back to the first 3 characters (the FSA).
            if result is None and country == "CAN" and len(clean_postal) >= 3:
                partial = clean_postal[:3]
                self._debug("Full code not found, trying FSA: %s", partial)
                result = db.get((geo_country, partial))

            if not result:
                self._debug("No match for %s/%s", geo_country, clean_postal)
                return None, None

            if self._is_debug_enabled():
                self._debug("Postal record fields:")
                for key, value in result.items():
                    self._debug("  %s: %s", key, value)

            province_code = result.get("state_code")
            city = self._extract_optimal_city_name(result, country)

            city = city.strip() if (city and city.strip()) else None
            province_code = province_code.strip() if (province_code and province_code.strip()) else None

            if city and province_code:
                self._debug("Resolved %s -> %s, %s", clean_postal, city, province_code)
                return city, province_code

            self._debug("Incomplete data for %s after extraction", clean_postal)

        except Exception as e:
            self._debug("Lookup failed for %s: %s", postal_code, str(e))

        return None, None

    def _is_debug_enabled(self) -> bool:
        """Check if debug mode is enabled (console or logging)"""
        # Check if we have console debug (--show-lineup + --debug)
        args = sys.argv
        has_show_lineup = any('--show-lineup' in arg for arg in args)
        has_debug = any('--debug' in arg for arg in args)
        console_debug = has_show_lineup and has_debug

        # Check if logging debug is enabled
        logging_debug = logging.getLogger().isEnabledFor(logging.DEBUG)

        return console_debug or logging_debug

    def _extract_optimal_city_name(self, result, country: str) -> Optional[str]:
        """
        Extract optimal city name using the GeoNames field hierarchy
        Canada: community_name -> county_name -> place_name (cleaned)
        USA: place_name -> county_name
        """
        def get_field(field_name):
            value = result.get(field_name)
            return value if value and str(value).lower() not in ['nan', 'none', ''] else None

        if country == "CAN":
            # Canada: Try community_name first (most generic)
            city = get_field('community_name')
            if city:
                self._debug("Using community_name: '%s'", city)
                return city

            # Fallback to county_name
            city = get_field('county_name')
            if city:
                self._debug("Using county_name: '%s'", city)
                return city

            # Last resort: clean place_name
            city = get_field('place_name')
            if city:
                cleaned_city = self._extract_generic_city_name(city)
                self._debug("Using cleaned place_name: '%s' -> '%s'", city, cleaned_city)
                return cleaned_city

        else:
            # USA: place_name is usually already generic
            city = get_field('place_name')
            if city:
                self._debug("Using place_name: '%s'", city)
                return city

            # Fallback to county_name if needed
            city = get_field('county_name')
            if city:
                self._debug("Using county_name: '%s'", city)
                return city

        return None

    def _extract_generic_city_name(self, city_name: str) -> str:
        """
        Extract generic city name from detailed place names (fallback only)
        Examples:
        - "Edmonton (North Downtown)" -> "Edmonton"
        - "Saint-Jean-sur-Richelieu Central" -> "Saint-Jean-sur-Richelieu"
        """
        if not city_name:
            return city_name

        # Remove parenthetical descriptions first
        if '(' in city_name:
            city_name = city_name.split('(')[0].strip()

        # Remove common directional/area suffixes
        directional_suffixes = [
            ' East', ' West', ' North', ' South', ' Central',
            ' Northeast', ' Northwest', ' Southeast', ' Southwest',
            ' Downtown', ' Uptown', ' Midtown'
        ]

        for suffix in directional_suffixes:
            if city_name.endswith(suffix):
                city_name = city_name[:-len(suffix)].strip()
                break

        return city_name
