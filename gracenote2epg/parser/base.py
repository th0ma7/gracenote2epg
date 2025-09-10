"""
Core orchestrator for downloading and parsing

The DataParser now acts as a pure orchestrator that coordinates between:
- Downloaders (handle HTTP and caching logic)  
- Parsers (handle pure data parsing logic)
"""

import logging
from typing import Dict, List, Optional

from ..downloader import OptimizedDownloader, GuideDownloader, SeriesDownloader
from .guide import GuideParser
from .series import SeriesParser


class DataParser:
    """Main orchestrator - coordinates downloading and parsing with separated concerns"""
    
    def __init__(self, cache_manager, tvh_client=None):
        self.cache_manager = cache_manager
        self.tvh_client = tvh_client
        
        # Initialize HTTP engine (shared by all downloaders)
        self.http_engine = OptimizedDownloader(base_delay=0.8, min_delay=0.4)
        
        # Initialize specialized downloaders
        self.guide_downloader = GuideDownloader(self.http_engine, cache_manager)
        self.series_downloader = SeriesDownloader(self.http_engine, cache_manager)
        
        # Initialize pure parsers (no download logic)
        self.guide_parser = GuideParser(tvh_client)
        self.series_parser = SeriesParser()
        
        # Parsed data
        self.schedule: Dict = {}
        
    def download_and_parse_guide(self, grid_time_start: float, day_hours: int,
                                 config_manager, refresh_hours: int = 48) -> bool:
        """
        Download and parse TV guide data with separated download/parse logic
        
        Args:
            grid_time_start: Start time for guide
            day_hours: Number of 3-hour blocks
            config_manager: Configuration manager
            refresh_hours: Hours to refresh
            
        Returns:
            bool: True if successful
        """
        # Get lineup configuration
        lineup_config = config_manager.get_lineup_config()
        
        # PHASE 1: Download guide blocks (delegated to downloader)
        download_success = self.guide_downloader.download_guide_blocks(
            grid_time_start, day_hours, lineup_config, refresh_hours
        )
        
        if not download_success:
            logging.warning("Guide download had issues, continuing with available data")
        
        # PHASE 2: Parse downloaded blocks (pure parsing logic)
        self._parse_guide_blocks(grid_time_start, day_hours)
        
        # Store parsed schedule
        self.schedule = self.guide_parser.get_schedule()
        
        return download_success
    
    def download_and_parse_series_details(self) -> bool:
        """Download and parse extended series details with separated logic"""
        # Extract active series list from parsed schedule
        series_list = self.get_active_series_list()
        
        if not series_list:
            logging.info("No series found for extended details download")
            return True
        
        # PHASE 1: Download series details (delegated to downloader)
        download_success = self.series_downloader.download_series_details(series_list)
        
        if not download_success:
            logging.warning("Extended details download had issues, using basic descriptions")
        
        # PHASE 2: Apply series details to episodes (pure parsing logic)
        self._apply_series_details_to_schedule()
        
        return download_success
    
    def _parse_guide_blocks(self, grid_time_start: float, day_hours: int):
        """Parse all downloaded guide blocks - pure parsing logic"""
        grid_time = grid_time_start
        
        for count in range(day_hours):
            # Generate filename (same logic as downloader)
            from ..utils import TimeUtils
            standard_block_time = TimeUtils.get_standard_block_time(grid_time)
            filename = standard_block_time.strftime("%Y%m%d%H") + ".json.gz"
            
            # Load and parse block (cached data)
            content = self.cache_manager.load_guide_block(filename)
            if content:
                try:
                    logging.debug("Parsing %s", filename)
                    
                    # Parse stations on first block
                    if count == 0:
                        self.guide_parser.parse_stations(content)
                        
                    # Parse episodes
                    self.guide_parser.parse_episodes(content)
                    
                except Exception as e:
                    logging.warning("Parse error for %s: %s", filename, str(e))
            
            grid_time += 10800  # Next 3-hour block
    
    def _apply_series_details_to_schedule(self):
        """Apply downloaded series details to parsed episodes - pure parsing logic"""
        processed_series = set()
        
        for station_id, station_data in self.schedule.items():
            for episode_key, episode_data in station_data.items():
                if episode_key.startswith("ch"):
                    continue  # Skip channel metadata
                    
                series_id = episode_data.get("epseries")
                if not series_id or series_id in processed_series:
                    continue
                    
                # Get cached series details (already downloaded)
                series_details = self.series_downloader.get_cached_series_details(series_id)
                
                if series_details:
                    # Pure parsing - apply details to episode data
                    self.series_parser.parse_series_details(
                        episode_data, series_details, series_id
                    )
                    processed_series.add(series_id)
    
    def get_active_series_list(self) -> List[str]:
        """Extract list of active series from current schedule"""
        active_series = set()
        
        for station_id, station_data in self.schedule.items():
            for episode_key, episode_data in station_data.items():
                if not episode_key.startswith("ch"):
                    series_id = episode_data.get("epseries")
                    if series_id:
                        active_series.add(series_id)
                        
        return list(active_series)
    
    def get_schedule(self) -> Dict:
        """Get the complete parsed schedule"""
        return self.schedule

    def get_downloader_statistics(self) -> Dict:
        """
        Get combined statistics from downloaders and parsers

        Returns:
            Dict: Structured statistics from all components
        """
        stats = {}

        # Get guide downloader statistics
        if hasattr(self, 'guide_downloader'):
            guide_dl_stats = self.guide_downloader.get_downloader_statistics()
            stats['guide'] = guide_dl_stats

        # Get series downloader statistics
        if hasattr(self, 'series_downloader'):
            series_dl_stats = self.series_downloader.get_downloader_statistics()
            stats['series'] = series_dl_stats

        # Get parser statistics
        if hasattr(self, 'guide_parser'):
            parser_stats = self.guide_parser.get_parsing_statistics()
            stats['parser'] = parser_stats

        if hasattr(self, 'series_parser'):
            series_parser_stats = self.series_parser.get_parsing_statistics()
            # Merge series parser stats into parser stats
            if 'parser' in stats:
                stats['parser'].update(series_parser_stats)
            else:
                stats['parser'] = series_parser_stats

        # Get HTTP engine statistics
        if hasattr(self, 'http_engine'):
            http_stats = self.http_engine.get_statistics()
            stats['http_engine'] = http_stats

        return stats
    
    def close(self):
        """Clean shutdown of HTTP engine"""
        if hasattr(self, 'http_engine'):
            self.http_engine.close()
            
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
