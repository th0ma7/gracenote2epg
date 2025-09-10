"""
gracenote2epg.geocoding - Geographic location resolution

Handles postal code resolution to city and province/state using pgeocode,
with intelligent fallbacks and caching for gracenote2epg configurations.
"""

import logging
import sys
from typing import Dict, Optional, Tuple

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
                self._ca_geocoder = pgeocode.Nominatim('CA')
                self._us_geocoder = pgeocode.Nominatim('US')
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

    def resolve_location(self, postal_code: str, country: str) -> Tuple[Optional[str], Optional[str]]:
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
            if (result is None or result.empty or self._is_result_invalid(result)) and country == "CAN" and len(clean_postal) >= 3:
                partial_postal = clean_postal[:3]
                self._debug("pgeocode full code failed, trying partial code: %s", partial_postal)
                result = geocoder.query_postal_code(partial_postal)
            
            if result is not None and hasattr(result, 'empty') and not result.empty:
                # DIAGNOSTIC: Show all available fields in debug mode
                if self._is_debug_enabled():
                    self._debug("pgeocode available fields:")
                    if hasattr(result, 'keys'):
                        for key in result.keys():
                            value = result.get(key) if hasattr(result, 'get') else getattr(result, key, None)
                            self._debug("  %s: %s", key, value)
                    elif hasattr(result, '__dict__'):
                        for key, value in result.__dict__.items():
                            self._debug("  %s: %s", key, value)
                    else:
                        self._debug("  result type: %s", type(result))
                        self._debug("  result dir: %s", str(dir(result)[:10]))  # First 10 attributes
                
                # Get state/province code directly from pgeocode
                province_code = result.get('state_code') if hasattr(result, 'get') else getattr(result, 'state_code', None)
                
                # Extract city using optimal hierarchy based on country
                city = self._extract_optimal_city_name(result, country)
                
                self._debug("pgeocode raw result - city: %s, province_code: %s", city, province_code)
                
                # Clean up the results
                if city and isinstance(city, str) and city.strip() and str(city).lower() != 'nan':
                    city = city.strip()
                else:
                    city = None
                    
                if province_code and isinstance(province_code, str) and province_code.strip() and str(province_code).lower() != 'nan':
                    province_code = province_code.strip()
                else:
                    province_code = None
                
                if city and province_code:
                    self._debug("pgeocode cleaned result - city: %s, province_code: %s", city, province_code)
                    return city, province_code
                else:
                    self._debug("pgeocode returned incomplete data after cleaning")
            else:
                self._debug("pgeocode returned empty or invalid result")
                
        except Exception as e:
            self._debug("pgeocode lookup failed for %s: %s", postal_code, str(e))
        
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
        Extract optimal city name using pgeocode's hierarchy
        Canada: community_name → county_name → place_name (cleaned)
        USA: place_name → county_name
        """
        def get_field(field_name):
            value = result.get(field_name) if hasattr(result, 'get') else getattr(result, field_name, None)
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
                self._debug("Using cleaned place_name: '%s' → '%s'", city, cleaned_city)
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
        - "Edmonton (North Downtown)" → "Edmonton"
        - "Saint-Jean-sur-Richelieu Central" → "Saint-Jean-sur-Richelieu"
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

    def _is_result_invalid(self, result) -> bool:
        """Check if pgeocode result is invalid (contains only NaN values)"""
        try:
            if not hasattr(result, 'get') and not hasattr(result, 'place_name'):
                return True
                
            city = result.get('place_name') if hasattr(result, 'get') else getattr(result, 'place_name', None)
            province_code = result.get('state_code') if hasattr(result, 'get') else getattr(result, 'state_code', None)
            province_name = result.get('state_name') if hasattr(result, 'get') else getattr(result, 'state_name', None)
            
            # If all important fields are NaN or None, consider invalid
            city_invalid = not city or str(city).lower() in ['nan', 'none', '']
            province_code_invalid = not province_code or str(province_code).lower() in ['nan', 'none', '']
            province_name_invalid = not province_name or str(province_name).lower() in ['nan', 'none', '']
            
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
            "cached_locations": list(self._location_cache.keys())
        }
