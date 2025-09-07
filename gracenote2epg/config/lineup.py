"""
gracenote2epg.config.lineup - Lineup management and detection

Handles lineup ID normalization, auto-detection, device type detection,
and validation URL generation for gracenote2epg configurations.
"""

import logging
from typing import Dict, Any, Optional


class LineupManager:
    """Handles lineup ID management and auto-detection"""

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

    def get_lineup_config(self, settings: Dict[str, Any], country: str) -> Dict[str, str]:
        """Get lineup configuration with automatic normalization and detection"""
        lineupid = settings.get("lineupid", "auto")
        postal_code = settings.get("zipcode", "")

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

    def get_auto_lineup_config(self, postal_code: str, country: str) -> Dict[str, str]:
        """Get auto-generated lineup configuration for display purposes"""
        # Generate OTA lineup IDs
        base_lineup = f"OTA{postal_code}"
        tvtv_lineup_id = f"{country}-{base_lineup}"
        api_lineup_id = f"{country}-{base_lineup}-DEFAULT"

        # Generate tvtv.com URL
        if country == "CAN":
            postal_for_url = postal_code.lower()
            tvtv_url = f"https://www.tvtv.ca/qc/saint-jean-sur-richelieu/{postal_for_url}/lu{tvtv_lineup_id}"
        else:
            tvtv_url = f"https://www.tvtv.us/ca/beverly-hills/{postal_code}/lu{tvtv_lineup_id}"

        return {
            "tvtv_lineup_id": tvtv_lineup_id,  # Format for tvtv.com
            "api_lineup_id": api_lineup_id,  # Format for API
            "tvtv_url": tvtv_url,  # Complete tvtv.com URL
            "device_type": "-",  # OTA device type
            "country": country,
            "postal_code": postal_code,
        }

    def generate_gracenote_api_url(self, config: Dict[str, str], timestamp: int) -> str:
        """
        Generate Gracenote API URL for testing
        
        Args:
            config: Lineup configuration from get_auto_lineup_config()
            timestamp: Unix timestamp for the request
            
        Returns:
            Complete API URL for testing
        """
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
        Generate validation URLs for manual verification
        
        Args:
            postal_code: Clean postal code (no spaces)
            country: Country code (USA/CAN)
            
        Returns:
            Dictionary with validation URLs and instructions
        """
        lineup_config = self.get_auto_lineup_config(postal_code, country)
        
        if country == "CAN":
            base_url = "https://www.tvtv.ca/"
            instructions = [
                f"1. Go to {base_url}",
                f"2. Enter postal code: {self._format_postal_for_display(postal_code, country)}",
                f"3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → URL shows lu{lineup_config['tvtv_lineup_id']}",
                f"3b. For Cable/Sat: Select provider → URL shows lu{country}-[ProviderID]-X"
            ]
        else:
            base_url = "https://www.tvtv.us/"
            instructions = [
                f"1. Go to {base_url}",
                f"2. Enter ZIP code: {postal_code}",
                f"3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → URL shows lu{lineup_config['tvtv_lineup_id']}",
                f"3b. For Cable/Sat: Select provider → URL shows lu{country}-[ProviderID]-X"
            ]

        return {
            "auto_generated_url": lineup_config['tvtv_url'],
            "base_url": base_url,
            "instructions": instructions,
            "tvtv_lineup_id": lineup_config['tvtv_lineup_id']
        }

    def _format_postal_for_display(self, postal_code: str, country: str) -> str:
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
        formatted_postal = self._format_postal_for_display(postal_code, country)
        
        return {
            "auto_detection": {
                "zipcode": postal_code,
                "lineupid": "auto",
                "comment": "Simplified configuration (auto-detection)"
            },
            "explicit_ota": {
                "zipcode": postal_code,
                "lineupid": lineup_config['tvtv_lineup_id'],
                "comment": "Alternative: Copy tvtv.com lineup ID directly"
            },
            "cable_satellite_example": {
                "zipcode": postal_code,
                "lineupid": f"{country}-[ProviderID]-X",
                "comment": f"For Cable/Satellite providers",
                "example": f"{country}-0005993-X for Videotron" if country == "CAN" else f"{country}-0012345-X for Comcast"
            }
        }

    def log_lineup_detection(self, original_lineupid: str, final_config: Dict[str, str]):
        """Log lineup detection results for debugging"""
        if final_config["auto_detected"]:
            logging.info(
                "Auto-detected lineupID: %s → %s", 
                original_lineupid, 
                final_config["lineup_id"]
            )
        else:
            logging.info(
                "Normalized lineupID: %s → %s", 
                original_lineupid, 
                final_config["lineup_id"]
            )
        
        logging.debug(
            "Lineup details: device=%s, description='%s'",
            final_config["device_type"],
            final_config["description"]
        )
