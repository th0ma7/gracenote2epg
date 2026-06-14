# gracenote2epg Enhancement TODO

## VERSION ROADMAP

### Version 2.0 🚀 (Performance & Structure Foundation)
**Focus:** Core performance improvements and code maintainability  
**Timeline:** Next major release

**Priority Features:**
1. **Parallel Series Downloads** ⭐ - Major performance improvement (3-5x faster)
   - **Status:** 🚧 In Progress - [Pull Request #2](https://github.com/th0ma7/gracenote2epg/pull/2)
2. **Split Large Modules** ⭐ - Refactor args.py (800+ lines) & config.py (1000+ lines)
   - Break into logical sub-modules for better maintainability
   - Improve testing capabilities

**Supporting Features:**
- **Unit Testing Framework** - Foundation for safe refactoring
- **Custom Exception Hierarchy** - Better error handling and debugging

**Expected Impact:** Significantly faster downloads, easier code maintenance

---

### Version 2.1 ✨ (XMLTV Enhancements - Quick Wins)  
**Focus:** Immediate user value with simple new features  
**Timeline:** Shortly after 2.0

**Priority Features:**
1. **Enhanced XMLTV Keywords** ⭐ - Quick win, immediate value
   - Add `programGenres`, boolean flags (isNew, isLive, isPremier, isFinale)
   - Extract more meaningful tags beyond CC/HD
2. **Multiple Icon Types** ⭐ - Simple enhancement  
   - Add `backgroundImage`, distinguish series vs episode icons
   - Better visual EPG experience

**Supporting Features:**
- **Extended Credit Photos** - More crew roles with photos
- **Constructed URLs** - Links to program/series information

**Expected Impact:** Richer XMLTV metadata with minimal development risk

---

### Version 2.2 🔧 (Cache & External API Preparation)
**Focus:** Prepare infrastructure for external API integrations  
**Timeline:** Mid-term release

**Priority Features:**
1. **TTL Cache Implementation** ⭐ - Reduce redundant operations
   - Smart caching for language detection, metadata
   - Prepare for external API call optimization
2. **External API Framework** - Foundation architecture
   - Rate limiting, error handling patterns
   - Configuration management for API keys

**Supporting Features:**
- **Dataclasses Migration** - Better type safety for external data
- **Enhanced Configuration** - Settings for external API preferences

**Expected Impact:** Foundation for efficient external API usage

---

### Version 2.3 🌟 (External API Integration - Major Features)
**Focus:** Professional metadata enhancement via external APIs  
**Timeline:** Major feature release

**Priority Features:**
1. **Rotten Tomatoes Integration** ⭐ - Professional ratings  
   - Critics Score and Audience Score in XMLTV
   - Intelligent caching to minimize API calls
2. **IMDB/TMDB Metadata** ⭐ - Correct country origin, enhanced details
   - Fix hardcoded country detection (major accuracy improvement)
   - Production companies, awards, content warnings
3. **Metadata Cross-Referencing** ⭐ - Combine all sources intelligently
   - Conflict resolution algorithms
   - Source attribution and confidence scoring

**Supporting Features:**
- **Enhanced Content Warnings** - Better parental guidance
- **Data Quality Validation** - Verify external metadata integrity

**Expected Impact:** Most comprehensive North American EPG metadata available

---

### Future Versions (2.4+) 🔮 (Architecture & Advanced Features)
**Focus:** Long-term architecture improvements and specialized features  
**Timeline:** To be determined based on user feedback

**Planned Features:**
- **Factory Patterns** - Better extensibility for download strategies
- **Memory Optimizations** - Handle larger datasets (14+ days guides)  
- **Complete Type Hints Coverage** - Full type safety
- **Advanced Language Detection** - ML-enhanced language identification
- **TVheadend Deep Integration** - Channel mapping improvements
- **Cloud Configuration** - Remote configuration management

---

## Quick Reference Summary

### 🆕 New Features - XMLTV Enhancements (High Value)
- **Enhanced Keywords** (programGenres, boolean flags) - *Easy*
- **Multiple Icon Types** (seriesImage, backgroundImage) - *Easy*
- **Constructed URLs** (program/series links) - *Medium*
- **Extended Credit Photos** (more crew roles) - *Easy*
- **Rotten Tomatoes Ratings** (external API integration) - *High*
- **IMDB/TMDB Metadata** (correct country origin, additional details) - *High*

### 🔧 Code Refactoring (Maintainability)
- **Split Large Modules** (args.py 800+, config.py 1000+ lines) - *High Priority*
- **Factory Patterns** (download strategies) - *Medium*
- **Dataclasses** (replace dict structures) - *Medium*
- **Custom Exceptions** (better error handling) - *Low*

### ⚡ Performance Optimizations
- **Parallel Downloads** (series details) - *High Impact*
- **TTL Cache** (language detection, config) - *Medium*
- **Memory Optimization** (large guide processing) - *Low*

### 🧪 Testing & Documentation  
- **Unit Tests** (critical modules) - *High Priority*
- **Type Hints** (full coverage) - *Medium*
- **Configuration Documentation** - *Low*

---

## A. NEW FEATURES - XMLTV ENHANCEMENTS

This section outlines new features and enhancements to the XMLTV output. Includes both internal data improvements and external API integrations for richer metadata.

---

## High Priority (Quick Wins)

### 1. Enhanced Keywords Support
**Status:** Not implemented
**Difficulty:** Low
**JSON Sources:** `programGenres`, `tags`, specialized flags

**Implementation:**
- Add `programGenres` from `upcomingEpisodeTab` entries as keywords
- Extract specialized tags (beyond current CC/HD filtering)
- Convert boolean flags to keywords (isNew, isLive, isPremier, isFinale)

---

## External API Integrations (New Features)

### 1. Rotten Tomatoes Rating Integration ⭐ HIGH VALUE
**Status:** Not implemented
**Difficulty:** High
**JSON Sources:** `epid` (tmsId), `epshow` (title), `epyear` (release year)

**Implementation:**
- Use existing program metadata to query Rotten Tomatoes API
- Add Critics Score and Audience Score to `<star-rating>` elements
- Cache ratings to minimize API calls
- Implement fallback when RT data unavailable

**Benefits:** Professional critics ratings alongside existing metadata

```python
# New XMLTV output:
<star-rating system="Rotten Tomatoes Critics">
    <value>85/100</value>
</star-rating>
<star-rating system="Rotten Tomatoes Audience">
    <value>92/100</value>
</star-rating>
```

**Location:** New module `gracenote2epg/external/rotten_tomatoes.py`

---

### 2. IMDB/TMDB Metadata Enhancement ⭐ HIGH VALUE  
**Status:** Not implemented
**Difficulty:** High
**Current Issue:** Country detection hardcoded and often incorrect

**Implementation:**
- Query IMDB/TMDB using program title, year, and type
- Extract correct country of origin
- Add production companies, budget info (movies)
- Enhance cast/crew with IMDB ratings
- Add content warnings/parental guidance details

**Benefits:** 
- Accurate country codes (currently defaulting to US/CA based on postal code)
- Richer production metadata
- Enhanced parental guidance information

```python
# Enhanced XMLTV output:
<country>GB</country>  <!-- Correct country instead of hardcoded -->
<keyword lang="en">BBC Production</keyword>
<keyword lang="en">Budget: $50M</keyword>

# New production company credits:
<credits>
    <producer>BBC Studios</producer>
    <producer role="Executive Producer">Jane Smith</producer>
</credits>
```

**Priority Data to Extract:**
- **Country of Origin** (fix current hardcoded logic)
- **Production Companies** 
- **Content Warnings** (violence, language, etc.)
- **Box Office Data** (for movies)
- **Awards/Nominations**

**Location:** New module `gracenote2epg/external/imdb_tmdb.py`

---

### 3. Enhanced Metadata Cross-Referencing
**Status:** Not implemented
**Difficulty:** Medium
**Sources:** Combine Gracenote + Rotten Tomatoes + IMDB/TMDB

**Implementation:**
- Create metadata aggregator that combines all sources
- Implement confidence scoring for conflicting data
- Add metadata source attribution
- Priority order: Gracenote (base) → IMDB (details) → RT (ratings)

```python
# Metadata source attribution:
<review type="text" source="Rotten Tomatoes">
    <value>A thrilling adventure with stellar performances...</value>
</review>

<star-rating system="IMDB">
    <value>8.2/10</value>
</star-rating>
```

**Benefits:**
- Most comprehensive metadata possible
- Source transparency for users
- Fallback mechanisms when APIs unavailable

---

### 2. Multiple Icon Types
**Status:** Partially implemented
**Difficulty:** Low
**JSON Sources:** `seriesImage`, `backgroundImage`, existing `epthumb`

**Current:** Only episode thumbnails and series images  
**Enhancement:** Add background images and properly categorize icon types

**Implementation:**
- Add `backgroundImage` as background-type icon
- Distinguish between series vs episode thumbnails
- Add icon type attributes where appropriate

**Location:** `xmltv/media.py` - enhance `_write_program_icons()`

```python
# Available data:
seriesImage = "p12116236_v_h2_aa"        # Series poster
backgroundImage = "p12116236_k_h8_aa"    # Series background
epthumb = "existing_thumb_id"            # Episode thumbnail
```

---

## Medium Priority

### 3. Enhanced Episode Metadata
**Status:** Not implemented
**Difficulty:** Medium
**JSON Sources:** Boolean flags from `upcomingEpisodeTab`

**Implementation:**
- Use `isNew`, `isLive`, `isPremier`, `isFinale` for enhanced metadata
- Improve special episode detection beyond current flag parsing
- Add episode-specific keywords based on boolean indicators

**Benefits:** Better EPG navigation and recording rules

```python
# Available boolean flags:
isNew = true/false
isLive = true/false  
isPremier = true/false
isFinale = true/false
```

---

### 4. Constructed Program URLs
**Status:** Not implemented
**Difficulty:** Medium
**JSON Sources:** `epid` (tmsId), `epseries`

**Implementation:**
- Generate Gracenote program URLs using tmsId
- Create series information URLs using seriesId
- Add conditional URL output (only when extended details enabled)

**Location:** `xmltv/programme.py` - new method `_write_program_urls()`

```python
# URL construction:
program_url = f"https://tvlistings.gracenote.com/program/{tms_id}"
series_url = f"https://tvlistings.gracenote.com/series/{series_id}"
```

---

### 5. Extended Credit Photos
**Status:** Basic implementation exists
**Difficulty:** Low
**JSON Sources:** `assetId` from cast/crew

**Current:** Photos only for actors/directors/presenters  
**Enhancement:** Expand to producers, writers, other crew roles

**Implementation:**
- Extend photo inclusion to more crew roles
- Add error handling for missing asset IDs
- Optimize image URL construction

---

## Low Priority (Nice to Have)

### 6. Smart Genre Deduction
**Status:** Not implemented
**Difficulty:** Medium
**JSON Sources:** `seriesGenres`, `programGenres`, content analysis

**Implementation:**
- Analyze genre combinations for better categorization
- Add content-type keywords (Movie, TV Series, Documentary, etc.)
- Improve EIT genre mapping

**Benefits:** Better content discovery and filtering

---

### 7. Enhanced Rating Systems
**Status:** Basic MPAA implemented
**Difficulty:** Low
**JSON Sources:** `eprating`, `displayRating`

**Implementation:**
- Add Canadian rating system detection
- Support multiple rating sources
- Regional rating system selection based on postal code

---

### 8. Temporal Keywords
**Status:** Not implemented
**Difficulty:** Medium
**JSON Sources:** `originalAirDate`, `releaseYear`

**Implementation:**
- Add decade-based keywords for older content
- Season/holiday detection from air dates
- Anniversary/milestone keywords for significant dates

---

## Technical Considerations

### Code Organization
- Keep enhancements in separate methods for maintainability
- Add configuration flags for new features (backward compatibility)
- Ensure all new features respect the `xdetails`/`xdesc` configuration logic

### Testing Requirements
- Test with different JSON data structures
- Verify DTD compliance with enhanced output
- Performance impact assessment for large guide datasets

### Configuration Integration
- Add new settings to `VALID_SETTINGS` in `config/validation.py`
- Consider grouping related enhancements under feature flags
- Document new configuration options

---

## Implementation Order Recommendation

1. **Enhanced Keywords** (programGenres, specialized tags)
2. **Multiple Icon Types** (seriesImage, backgroundImage)
3. **Constructed URLs** (program/series links)
4. **Extended Credit Photos** (more crew roles)
5. **Enhanced Episode Metadata** (boolean flag utilization)
6. **Smart Genre Deduction** (content-type detection)
7. **Enhanced Rating Systems** (regional systems)
8. **Temporal Keywords** (date-based keywords)

---

## B. CODE REFACTORING & MAINTAINABILITY

### 1. Split Large Modules — ✅ COMPLETED (2.0.0)
The former monolithic modules were split into focused packages: `args/`,
`config/`, `parser/`, `downloader/`, `xmltv/` and `logrotate/`, plus a
dedicated `cache.py`. Behaviour was verified byte-for-byte identical against
the pre-refactor output. The original motivation is kept below for reference.

**Former Issues (resolved):**
- `gracenote2epg_args.py`: 800+ lines (argument parsing, validation, system detection)
- `gracenote2epg_config.py`: 1000+ lines (config management, migration, lineup logic)
- `gracenote2epg_xmltv.py`: `_print_episodes()` method 300+ lines

**Resulting Structure:**
```
gracenote2epg/
├── args/         # base parser, validator, location, path_manager, systems/
├── config/       # base (ConfigManager), validation, settings, migration,
│                 # lineup, retention, display
├── parser/       # base, guide, series
├── downloader/   # base (HTTP + stats mixin), guide, series
├── xmltv/        # generator + stations/programme/descriptions/credits/
│                 # categories/media mixins
├── logrotate/    # handler, manager, periods (pure date math)
├── cache.py      # CacheManager (guide blocks + series/ details)
└── utils.py      # TimeUtils + HtmlUtils
```

**Benefits:** Better maintainability, easier testing, clearer separation of concerns

---

### 2. Factory Pattern for Download Strategies
**Status:** Not implemented
**Difficulty:** Medium
**Current Issue:** Mixed download strategies in single class

**Implementation:**
```python
# gracenote2epg/downloader/strategies.py
class DownloadStrategy(ABC):
    @abstractmethod
    def download(self, url: str, **kwargs) -> Optional[bytes]: pass

class GuideDownloadStrategy(DownloadStrategy):
    """Strategy for guide data (requests with session reuse)"""

class SeriesDownloadStrategy(DownloadStrategy): 
    """Strategy for series details (urllib for compatibility)"""

# gracenote2epg/downloader/factory.py
class DownloaderFactory:
    @staticmethod
    def create_downloader(content_type: str) -> DownloadStrategy:
        return {'guide': GuideDownloadStrategy, 'series': SeriesDownloadStrategy}[content_type]()
```

---

### 3. Replace Dictionaries with Dataclasses
**Status:** Not implemented
**Difficulty:** Medium
**Benefits:** Type safety, better IDE support, easier refactoring

**Priority Models:**
```python
@dataclass
class Episode:
    epid: str
    epstart: str
    epend: Optional[str] = None
    epshow: Optional[str] = None
    eptitle: Optional[str] = None
    epdesc: Optional[str] = None
    epflag: List[str] = field(default_factory=list)

@dataclass 
class Station:
    station_id: str
    chfcc: str
    chnam: str
    chicon: Optional[str] = None

@dataclass
class LineupConfig:
    lineup_id: str
    device_type: Literal['-', 'X']
    country: Literal['USA', 'CAN']
    auto_detected: bool
```

---

### 4. Custom Exception Hierarchy
**Status:** Not implemented
**Difficulty:** Low
**Current Issue:** Generic exceptions make debugging harder

```python
class Gracenote2EPGError(Exception): pass
class ConfigurationError(Gracenote2EPGError): pass
class DownloadError(Gracenote2EPGError): pass
class WAFBlockedError(DownloadError): pass
class TVHeadendConnectionError(Gracenote2EPGError): pass
```

---

## C. PERFORMANCE OPTIMIZATIONS

### 1. Parallel Series Downloads ⭐ HIGH IMPACT
**Status:** Not implemented
**Current Issue:** Sequential downloads for 100+ series (major bottleneck)
**Difficulty:** Medium

**Implementation:**
```python
def download_series_parallel(self, series_list: List[str]) -> Dict[str, bytes]:
    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_series = {
            executor.submit(self.download_series, series_id): series_id 
            for series_id in series_list
        }
        
        results = {}
        for future in as_completed(future_to_series):
            series_id = future_to_series[future]
            try:
                results[series_id] = future.result()
            except Exception as e:
                logging.error(f'Download failed: {series_id}: {e}')
        return results
```

**Expected Impact:** 3-5x faster extended details downloads

---

### 2. TTL Cache Implementation  
**Status:** Basic caching exists
**Difficulty:** Low-Medium
**Enhancement Areas:**
- Language detection cache with TTL
- Configuration cache for repeated accesses
- Series metadata cache across runs

```python
class TTLCache:
    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return value
            del self.cache[key]
        return None
```

---

### 3. Memory Usage Optimization
**Status:** Not implemented
**Difficulty:** Medium
**Target:** Large guide datasets (14+ days)

**Strategies:**
- Streaming XMLTV generation (don't hold full schedule in memory)
- Lazy loading of series details
- Garbage collection hints for large datasets

---

## D. TESTING & DOCUMENTATION

### 1. Unit Testing Framework ⭐ HIGH PRIORITY
**Status:** Not implemented
**Difficulty:** Medium
**Critical Modules to Test:**
- `ConfigManager` (complex logic, multiple code paths)
- `LineupManager` (postal code validation, normalization)
- `LanguageDetector` (caching, fallback logic)
- `CacheManager` (retention policies, cleanup)

**Test Structure:**
```
tests/
├── fixtures/           # Sample JSON data, configs
├── unit/
│   ├── test_config_manager.py
│   ├── test_lineup_manager.py  
│   ├── test_language_detector.py
│   └── test_cache_manager.py
└── integration/
    ├── test_full_workflow.py
    └── test_xmltv_output.py
```

---

### 2. Complete Type Hints Coverage
**Status:** Partial
**Difficulty:** Low
**Current:** ~60% coverage, missing complex types

**Priority Areas:**
```python
# Complex return types
def get_lineup_config(self) -> LineupConfig: ...
def parse_episodes(self, content: bytes) -> CheckTBAResult: ...

# Union types for API responses  
ApiResponse = Union[Dict[str, Any], List[Dict[str, Any]], None]

# Callback types
ProgressCallback = Callable[[int, int, str], None]
```

---

### 3. Configuration Documentation
**Status:** Basic
**Enhancement:** Auto-generated config reference from code

---

## E. INFRASTRUCTURE IMPROVEMENTS

### 1. Centralized Constants
**Status:** Scattered throughout code
**Implementation:**
```python
# gracenote2epg/constants.py
class API:
    BASE_URL = 'http://tvlistings.gracenote.com/api/grid'
    DETAILS_URL = 'https://tvlistings.gracenote.com/api/program/overviewDetails'
    
class Timeouts:
    DEFAULT = 6
    EXTENDED = 15
    WAF_BACKOFF = (3, 8)

class Cache:
    GUIDE_RETENTION_DAYS = 7
    SERIES_RETENTION_DAYS = 30
    LOG_RETENTION_DAYS = 30
```

---

### 2. Centralized Logging Configuration
**Status:** Distributed across modules
**Enhancement:**
```python
class LogManager:
    FORMATS = {
        'file': '%(asctime)s %(levelname)-8s %(message)s',
        'console': '%(levelname)s: %(message)s'
    }
    
    @staticmethod
    def log_progress(current: int, total: int, message: str):
        percent = (current / total * 100) if total > 0 else 0
        logging.info(f'Progress: {current}/{total} ({percent:.1f}%) - {message}')
```

---



## MIGRATION STRATEGY

- **Backward Compatibility:** All changes must maintain existing API compatibility
- **Feature Flags:** New features should be configurable/optional initially  
- **Progressive Rollout:** Implement in isolated modules first
- **Extensive Testing:** Each phase should include regression testing
- **Documentation Updates:** Keep user-facing docs current with changes

---

## MEASUREMENT CRITERIA

### Performance Metrics
- **Download Time:** Current vs optimized (target: 50% reduction for series downloads)
- **Memory Usage:** Peak memory during large guide processing
- **Cache Hit Rates:** Language detection, configuration, series metadata
- **External API Response Times:** RT/IMDB/TMDB integration performance
- **Metadata Accuracy:** Country detection, rating consistency

### Code Quality Metrics  
- **Test Coverage:** Target 80%+ for critical modules
- **Cyclomatic Complexity:** Reduce high-complexity methods
- **Module Size:** No single module >500 lines
- **Type Coverage:** 95%+ type hint coverage

### Feature Quality Metrics
- **Data Enrichment Rate:** % of programs with enhanced metadata
- **External API Success Rate:** % of successful RT/IMDB queries
- **Metadata Conflict Resolution:** Accuracy of cross-referenced data
- **User Value:** Improvement in EPG richness and accuracy

---

## TECHNICAL CONSIDERATIONS

### External API Integration
- **Rate Limiting:** Implement proper rate limiting for RT/IMDB/TMDB APIs
- **API Key Management:** Secure storage and rotation of API credentials
- **Fallback Strategies:** Graceful degradation when external services unavailable
- **Data Caching:** Aggressive caching to minimize external API calls (especially for country data)
- **Error Handling:** Specific exceptions for different API failure modes
- **Content Matching:** Fuzzy matching algorithms for program identification across APIs
- **Country Code Standardization:** ISO 3166-1 alpha-2 vs alpha-3 code handling

### Configuration Extensions
- **External API Settings:** New config section for API keys, rate limits
- **Metadata Preferences:** User choice of external data sources priority
- **Feature Toggles:** Ability to disable external integrations per user preference

### Data Quality Assurance
- **Conflict Resolution:** Algorithm for handling contradictory data from multiple sources
- **Data Validation:** Verification of external data before integration
- **Source Attribution:** Clear indication of metadata source for transparency
- **Confidence Scoring:** Quality metrics for cross-referenced data

---

## Notes
- **New Features:** Focus on user value and data accuracy improvements
- **External Dependencies:** Plan for API changes and service unavailability
- Prioritize changes that improve both performance and maintainability
- Consider user impact when planning breaking changes
- Maintain extensive logging during refactoring phases
- Test with both Canadian and US content throughout development
- **Privacy Considerations:** Ensure external API calls don't leak user data
