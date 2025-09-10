"""
Argument validation module for gracenote2epg

Handles validation of command-line arguments including days, refresh hours,
postal codes, ZIP codes, and lineup IDs.
"""

import re
from typing import Optional, Tuple


class ArgumentValidator:
    """Validates command-line arguments"""
    
    # Validation patterns
    DAYS_PATTERN = re.compile(r"^[1-9]$|^1[0-4]$")  # 1-14 days
    REFRESH_PATTERN = re.compile(r"^[0-9]+$|^[1-9][0-9]+$")  # 0-999 hours
    CA_CODE_PATTERN = re.compile(r"^[A-Z][0-9][A-Z][ ]?[0-9][A-Z][0-9]$")  # Canadian postal
    US_CODE_PATTERN = re.compile(r"^[0-9]{5}$")  # US ZIP code
    
    @classmethod
    def validate_days(cls, days: Optional[int]) -> Tuple[bool, Optional[str]]:
        """
        Validate days parameter
        
        Args:
            days: Number of days to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if days is None:
            return True, None
            
        if not cls.DAYS_PATTERN.match(str(days)):
            return False, f"Parameter [--days] must be 1-14, got: {days}"
            
        return True, None
    
    @classmethod
    def validate_offset(cls, offset: Optional[int]) -> Tuple[bool, Optional[str]]:
        """
        Validate offset parameter
        
        Args:
            offset: Offset days to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if offset is None:
            return True, None
            
        if not cls.DAYS_PATTERN.match(str(offset)):
            return False, f"Parameter [--offset] must be 1-14, got: {offset}"
            
        return True, None
    
    @classmethod
    def validate_refresh(cls, refresh: Optional[int]) -> Tuple[bool, Optional[str]]:
        """
        Validate refresh parameter
        
        Args:
            refresh: Refresh hours to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if refresh is None:
            return True, None
            
        if refresh < 0 or refresh > 168:  # 0 to 7 days
            return False, f"Parameter [--refresh] must be 0-168 hours, got: {refresh}"
            
        return True, None
    
    @classmethod
    def validate_lineupid(cls, lineupid: Optional[str]) -> Tuple[bool, Optional[str]]:
        """
        Validate lineupid parameter (basic validation)
        
        Args:
            lineupid: Lineup ID to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if lineupid is None:
            return True, None
            
        lineupid = lineupid.strip()
        if not lineupid:
            return False, "Parameter [--lineupid] cannot be empty"
            
        # Additional validation will be done in ConfigManager
        return True, None
    
    @classmethod
    def validate_location_code(cls, location_code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate US ZIP or Canadian postal code
        
        Args:
            location_code: Location code to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not location_code:
            return True, None
            
        # Remove spaces for US ZIP validation
        clean_code = location_code.replace(" ", "")
        
        # Check if valid Canadian or US format
        if cls.CA_CODE_PATTERN.match(location_code) or cls.US_CODE_PATTERN.match(clean_code):
            return True, None
        
        # Normalize display for error message
        display_location = location_code.replace(" ", "")
        return False, (
            f"Invalid location code: {display_location}. "
            "Expected US ZIP (12345) or Canadian postal (A1A1A1)"
        )
    
    @classmethod
    def is_canadian_postal(cls, location_code: str) -> bool:
        """Check if location code is Canadian postal format"""
        return bool(cls.CA_CODE_PATTERN.match(location_code))
    
    @classmethod
    def is_us_zip(cls, location_code: str) -> bool:
        """Check if location code is US ZIP format"""
        clean_code = location_code.replace(" ", "")
        return bool(cls.US_CODE_PATTERN.match(clean_code))
    
    @classmethod
    def validate_all_arguments(cls, args) -> list:
        """
        Validate all arguments at once
        
        Args:
            args: Parsed arguments object
            
        Returns:
            List of error messages (empty if all valid)
        """
        errors = []
        
        # Validate days
        valid, error = cls.validate_days(getattr(args, 'days', None))
        if not valid:
            errors.append(error)
        
        # Validate offset
        valid, error = cls.validate_offset(getattr(args, 'offset', None))
        if not valid:
            errors.append(error)
        
        # Validate refresh
        valid, error = cls.validate_refresh(getattr(args, 'refresh', None))
        if not valid:
            errors.append(error)
        
        # Validate lineupid
        valid, error = cls.validate_lineupid(getattr(args, 'lineupid', None))
        if not valid:
            errors.append(error)
            
        return errors
