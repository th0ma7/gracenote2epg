"""
gracenote2epg.gracenote2epg_tvheadend - TVheadend integration

Handles communication with TVheadend server for automatic channel filtering
and channel number matching.
"""

import logging
from typing import Dict, Optional, Set
import requests
from requests.auth import HTTPDigestAuth


class TvheadendClient:
    """Client for TVheadend server integration"""

    def __init__(
        self,
        url: str,
        port: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 5,
    ):
        self.url = url
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.base_url = f"http://{url}:{port}"
        self.channels: Dict[str, str] = {}  # channel_number -> channel_name

    def fetch_channels(self) -> Dict[str, str]:
        """Fetch enabled channels from TVheadend server"""
        try:
            channels_url = f"{self.base_url}/api/channel/grid"
            params = {
                "all": "1",
                "limit": "999999999",
                "sort": "name",
                "filter": '[{"type":"boolean","value":true,"field":"enabled"}]',
            }

            if self.username and self.password:
                logging.info("TVheadend access using username and password...")
                response = requests.get(
                    channels_url,
                    params=params,
                    auth=HTTPDigestAuth(self.username, self.password),
                    timeout=self.timeout,
                )
            else:
                logging.info("TVheadend anonymous access...")
                response = requests.get(channels_url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                logging.info("Accessing TVheadend channel list from: %s", self.base_url)
                channels_data = response.json()

                for channel in channels_data.get("entries", []):
                    channel_name = channel.get("name", "")
                    channel_number = channel.get("number", "")

                    if channel_number and channel_name:
                        self.channels[str(channel_number)] = channel_name

                logging.info("%d TVheadend channels found...", len(self.channels))
                return self.channels

            else:
                logging.warning("TVheadend returned status code: %d", response.status_code)
                return {}

        except requests.exceptions.ConnectionError as e:
            logging.warning("Cannot connect to TVheadend: Connection error")
            logging.debug("Connection error details: %s", str(e))
            return {}
        except requests.exceptions.Timeout:
            logging.warning("Cannot connect to TVheadend: Timeout after %ds", self.timeout)
            return {}
        except requests.exceptions.RequestException as e:
            logging.warning("Cannot connect to TVheadend: %s", str(e))
            return {}
        except Exception as e:
            logging.warning("Unexpected error connecting to TVheadend: %s", str(e))
            return {}

    def get_channel_numbers(self) -> Set[str]:
        """Get set of channel numbers from TVheadend"""
        return set(self.channels.keys())

    def get_channel_name(self, channel_number: str) -> Optional[str]:
        """Get channel name for given channel number"""
        return self.channels.get(str(channel_number))

    def is_channel_enabled(self, channel_number: str) -> bool:
        """Check if channel number is enabled in TVheadend"""
        return str(channel_number) in self.channels

    def should_process_station(
        self,
        station_data: Dict,
        explicit_station_list: Optional[list] = None,
        use_tvh_matching: bool = True,
        use_channel_matching: bool = True,
    ) -> bool:
        """
        Determine if a station should be processed based on filtering rules

        Args:
            station_data: Station data from guide with channelId, channelNo, callSign
            explicit_station_list: Optional list of specific station IDs
            use_tvh_matching: Whether to use TVheadend channel filtering
            use_channel_matching: Whether to match channel numbers with call signs
        """
        station_id = station_data.get("channelId")

        # Priority 1: Use explicit station list if provided
        if explicit_station_list:
            should_process = station_id in explicit_station_list
            logging.debug(
                "Using explicit station list: %s in list = %s", station_id, should_process
            )
            return should_process

        # Priority 2: Use TVheadend channel filtering if enabled and available
        if use_tvh_matching and self.channels:
            channel_number = station_data.get("channelNo", "")
            call_sign = station_data.get("callSign", "")

            # Generate possible channel number variations
            possible_numbers = [channel_number]

            if "." not in channel_number and use_channel_matching and call_sign:
                # Try to extract subchannel from call sign
                import re

                subchannel_match = re.search(r"(\d+)$", call_sign)
                if subchannel_match:
                    possible_numbers.append(f"{channel_number}.{subchannel_match.group(1)}")
                else:
                    possible_numbers.append(f"{channel_number}.1")

            # Check if any possible number matches TVheadend channels
            for possible_number in possible_numbers:
                if self.is_channel_enabled(possible_number):
                    logging.debug(
                        "Station %s (channel %s->%s) matches TVheadend channel %s (%s)",
                        station_id,
                        channel_number,
                        possible_number,
                        possible_number,
                        self.get_channel_name(possible_number),
                    )
                    return True

            logging.debug(
                "Station %s (channel %s, callsign %s) not found in TVheadend - skipping",
                station_id,
                channel_number,
                call_sign,
            )
            return False

        # Priority 3: No filtering - process all stations
        return True

    def get_matched_channel_number(
        self, station_data: Dict, use_channel_matching: bool = True
    ) -> str:
        """
        Get the matched channel number for a station, with subchannel logic

        Args:
            station_data: Station data with channelNo and callSign
            use_channel_matching: Whether to apply channel matching logic
        """
        channel_number = station_data.get("channelNo", "")
        call_sign = station_data.get("callSign", "")

        if "." not in channel_number and use_channel_matching and call_sign:
            import re

            subchannel_match = re.search(r"(\d+)$", call_sign)
            if subchannel_match:
                return f"{channel_number}.{subchannel_match.group(1)}"
            else:
                return f"{channel_number}.1"

        return channel_number

    def get_tvh_channel_name(self, matched_channel_number: str) -> Optional[str]:
        """Get TVheadend channel name for matched channel number"""
        if self.channels and matched_channel_number in self.channels:
            return self.channels[matched_channel_number]
        return None

    def log_filtering_summary(
        self, explicit_station_list: Optional[list] = None, use_tvh_matching: bool = True
    ):
        """Log summary of channel filtering configuration"""
        if use_tvh_matching and self.channels:
            logging.info(
                "TVheadend channel filtering enabled: %d channels will be used as filter",
                len(self.channels),
            )
            # Show first 10 channels for debug
            channel_sample = list(self.channels.keys())[:10]
            logging.debug("TVheadend channels: %s", channel_sample)
        elif explicit_station_list:
            logging.info(
                "Explicit station list filtering: %d stations configured",
                len(explicit_station_list),
            )
        else:
            logging.info("No channel filtering - all available stations will be processed")
