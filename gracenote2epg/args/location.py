"""
Location processing module for gracenote2epg

Handles extraction and validation of location codes (postal/ZIP) from lineup IDs
and ensures consistency between explicit and extracted location codes.
"""

import logging
import re
from typing import Optional, Tuple

from .validator import ArgumentValidator


class LocationProcessor:
    """Processes and validates location codes"""
    
    @staticmethod
    def extract_location_from_lineup(lineupid: str) -> Optional[str]:
        """
        Extract postal/ZIP code from lineup ID if it's in OTA format
        
        Args:
            lineupid: Lineup ID (e.g., 'CAN-OTAJ3B1M4', 'USA-OTA90210')
            
        Returns:
            Extracted location code or None if not extractable
        """
        if not lineupid:
            return None
            
        # Pattern for OTA lineups: COUNTRY-OTA<LOCATION>[-DEFAULT]
        # Examples: CAN-OTAJ3B1M4, USA-OTA90210, CAN-OTAJ3B1M4-DEFAULT
        ota_pattern = re.compile(r"^(CAN|USA)-OTA([A-Z0-9]+)(?:-DEFAULT)?$", re.IGNORECASE)
        
        match = ota_pattern.match(lineupid.strip())
        if match:
            country = match.group(1).upper()
            location = match.group(2).upper()
            
            # Validate extracted location format
            if country == "CAN":
                # Canadian postal: should be A1A1A1 format
                if re.match(r"^[A-Z][0-9][A-Z][0-9][A-Z][0-9]$", location):
                    # Format as A1A 1A1 (with space)
                    return f"{location[:3]} {location[3:]}"
            elif country == "USA":
                # US ZIP: should be 5 digits
                if re.match(r"^[0-9]{5}$", location):
                    return location
                    
        return None
    
    @staticmethod
    def process_lineup_and_location(args) -> Tuple[Optional[str], dict]:
        """
        Process lineup and location arguments with intelligent extraction and validation
        
        Args:
            args: Parsed arguments object
            
        Returns:
            Tuple of (final_location_code, metadata_dict)
        """
        location_code = getattr(args, 'zip', None) or getattr(args, 'postal', None) or getattr(args, 'code', None)
        lineupid = getattr(args, 'lineupid', None)
        
        # Extract postal/ZIP from lineupid if it's an OTA format
        extracted_location = None
        if lineupid:
            extracted_location = LocationProcessor.extract_location_from_lineup(lineupid)
        
        metadata = {
            'location_source': None,
            'original_lineupid': lineupid,
            'extracted_location': extracted_location.replace(" ", "") if extracted_location else None
        }
        
        # Case 1: Both lineupid (with location) and explicit location provided
        if extracted_location and location_code:
            # Verify consistency
            clean_extracted = extracted_location.replace(" ", "").upper()
            clean_provided = location_code.replace(" ", "").upper()
            
            if clean_extracted != clean_provided:
                # Normalize display for error message
                normalized_extracted = extracted_location.replace(" ", "")
                raise ValueError(
                    f"Inconsistent location codes: lineupid contains '{normalized_extracted}' "
                    f"but explicit location is '{location_code}'. They must match."
                )
            
            # Use the explicitly provided format (might have spaces)
            final_location = location_code
            metadata['location_source'] = "explicit"
            
        # Case 2: Only lineupid provided with extractable location
        elif extracted_location and not location_code:
            final_location = extracted_location
            metadata['location_source'] = "extracted"
            logging.debug(f"Extracted location '{extracted_location}' from lineupid '{lineupid}'")
            
        # Case 3: Only explicit location provided
        elif location_code:
            final_location = location_code
            metadata['location_source'] = "explicit"
            
        # Case 4: Neither provided
        else:
            final_location = None
        
        # Validate the final location code if we have one
        if final_location:
            valid, error_msg = ArgumentValidator.validate_location_code(final_location)
            if not valid:
                source = "lineupid" if extracted_location and not location_code else "explicit parameter"
                display_location = final_location.replace(" ", "") if extracted_location and not location_code else final_location
                raise ValueError(f"Invalid location code from {source}: {display_location}. {error_msg}")
            
            # Store normalized version (without spaces)
            final_location = final_location.replace(" ", "")
            
        return final_location, metadata
    
    @staticmethod
    def normalize_langdetect(langdetect: Optional[str]) -> Optional[bool]:
        """
        Normalize langdetect option
        
        Args:
            langdetect: String value 'true' or 'false'
            
        Returns:
            Boolean value or None
        """
        if langdetect:
            return langdetect.lower() == "true"
        return None
    
    @staticmethod
    def normalize_refresh(args) -> Optional[int]:
        """
        Normalize refresh options
        
        Args:
            args: Parsed arguments object
            
        Returns:
            Refresh hours or None
        """
        if getattr(args, 'norefresh', False):
            return 0  # No refresh
        elif getattr(args, 'refresh', None) is not None:
            return args.refresh
        else:
            return None  # Use config default
