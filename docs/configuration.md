# Configuration Guide

This guide covers all configuration options for gracenote2epg. The script auto-creates a default configuration file on first run.

## Configuration File Locations

gracenote2epg auto-detects your system and uses appropriate directories:

### Linux/Docker
- **Config**: `~/gracenote2epg/conf/gracenote2epg.xml`

### Raspberry Pi
- **Config**: `~/script.module.zap2epg/epggrab/conf/gracenote2epg.xml` (if exists)
- **Fallback**: `~/gracenote2epg/conf/gracenote2epg.xml`

### Synology DSM7
- **Config**: `/var/packages/tvheadend/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`

### Synology DSM6
- **Config**: `/var/packages/tvheadend/target/var/epggrab/gracenote2epg/conf/gracenote2epg.xml`

## Complete Configuration Reference

```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="8">
  <!-- Basic guide settings -->
  <setting id="zipcode">92101</setting>                        <!-- US ZIP or Canadian postal code -->
  <setting id="lineupid">auto</setting>                        <!-- Lineup configuration -->
  <setting id="days">7</setting>                               <!-- Guide duration (1-14 days) -->

  <!-- Station filtering -->
  <setting id="slist"></setting>                               <!-- Comma-separated station IDs (empty=all) -->
  <setting id="stitle">false</setting>                         <!-- Safe titles (replace special chars) -->

  <!-- Extended details and language detection -->
  <setting id="xdetails">true</setting>                        <!-- Use extended data (credits, images, categories) -->
  <setting id="xdesc">true</setting>                           <!-- Use extended descriptions + enhanced info -->
  <setting id="langdetect">true</setting>                      <!-- Enable automatic language detection -->

  <!-- Display options -->
  <setting id="epgenre">3</setting>                            <!-- Genre mode: 0=none, 1=primary, 2=EIT, 3=all -->
  <setting id="epicon">1</setting>                             <!-- Icon mode: 0=none, 1=series+episode, 2=episode only -->

  <!-- TVheadend integration -->
  <setting id="tvhoff">true</setting>                          <!-- Enable TVH integration -->
  <setting id="tvhurl">127.0.0.1</setting>                     <!-- TVH server IP -->
  <setting id="tvhport">9981</setting>                         <!-- TVH port -->
  <setting id="tvhmatch">true</setting>                        <!-- Use TVH channel filtering -->
  <setting id="chmatch">true</setting>                         <!-- Enable channel number matching -->
  <setting id="usern"></setting>                               <!-- TVH username (optional) -->
  <setting id="passw"></setting>                               <!-- TVH password (optional) -->

  <!-- Cache and retention policies -->
  <setting id="redays">7</setting>                             <!-- Cache retention days (must be >= days) -->
  <setting id="refresh">48</setting>                           <!-- Forced refresh first 48 hours (0=disabled) -->
  <setting id="logrotate">true</setting>                       <!-- Log rotation: true(daily)|false|daily|weekly|monthly -->
  <setting id="relogs">30</setting>                            <!-- Log retention: days(number) or weekly|monthly|quarterly -->
  <setting id="rexmltv">7</setting>                            <!-- XMLTV backup retention: days(number) or weekly|monthly|quarterly -->

  <!-- Download performance -->
  <setting id="dlworkers">auto</setting>                       <!-- Parallel download workers: 1=sequential, 2-8=fixed, auto=recommended -->
  <setting id="dlthreshold">auto</setting>                     <!-- Switch to sequential above N pending downloads (avoids 429 wall): auto(~500) or a number -->

  <!-- Image source host (first 'enabled' is used) -->
  <imagesources>
    <source status="enabled">https://tmsimg.fancybits.co/assets</source>
    <source status="disabled">https://www.tvtv.ca/gn/pi/assets</source>
    <source status="disabled">https://zap2it.tmsimg.com/assets</source>
    <source status="disabled">https://dshm.tmsimg.com/assets</source>
  </imagesources>
</settings>
```

> **Schema versions 6 / 7 / 8**: v6 added the `<imagesources>` block, v7 the
> `dlworkers` setting, v8 the `dlthreshold` setting. Older configs are upgraded
> automatically on the next run (a backup is written and the new defaults are
> injected).

## Download Performance

`dlworkers` controls how series details are downloaded:

- `1` — sequential (one request at a time).
- `2`–`8` — a fixed number of parallel keep-alive workers.
- `auto` (default) — a sensible worker count with a self-regulating rate
  governor (starts moderate, speeds up while the server is happy, backs off on
  rate-limit/WAF signals).

Parallel workers each reuse one persistent connection and share a combined-rate
governor, so a refresh's new-series delta downloads ~3× faster without tripping
the server. There is a single data host (no alternate source to configure).

`dlthreshold` guards the cold-cache case. The Gracenote API enforces a
cumulative-volume wall (HTTP 429) after a few hundred requests, which concurrency
reaches sooner; a single sequential connection is never blocked. So when the
number of series details to fetch reaches `dlthreshold`, the run downloads them
sequentially (slower but reliable); below it, the parallel pool is used.

- `auto` (default) — the observed wall, ~500.
- a positive integer — an explicit batch size to switch at.

As a safety net, even in parallel mode the pool aborts early if the server keeps
returning 429 (instead of crawling), and details are saved as they arrive, so a
partial/aborted run keeps its progress and the rest is fetched on the next run —
the process always terminates on its own.

## Image Source

Program and cast/crew images are referenced by their Gracenote/TMS asset code,
which several mirror hosts serve identically. The `<imagesources>` block selects
which host to write into the guide; the **first `enabled` source wins**. Switch
host by toggling `status` (`enabled` / `disabled`) — no need to retype URLs.

```xml
<imagesources>
  <source status="enabled">https://tmsimg.fancybits.co/assets</source>
  <source status="disabled">https://www.tvtv.ca/gn/pi/assets</source>
</imagesources>
```

- Default host is `tmsimg.fancybits.co` (the `www.tvtv.ca` host is rate-limited).
- You may add your own full base URL as a `<source>`.
- This only affects the image URLs written to the XMLTV; it has no effect on
  which channels/programmes are downloaded.

## Required Settings

### zipcode
**Required**: Your location code
- **US**: 5-digit ZIP code (e.g., `92101`)
- **Canada**: Postal code with or without space (e.g., `J3B1M4` or `J3B 1M4`)

```xml
<setting id="zipcode">92101</setting>          <!-- San Diego, CA -->
<setting id="zipcode">J3B1M4</setting>         <!-- Saint-Jean-sur-Richelieu, QC -->
```

## Lineup Configuration

### lineupid
**Simple lineup configuration** - replaces complex multi-parameter setup

**Values**:
- **`auto`** (default) - Auto-detect Over-the-Air lineup (requires valid zipcode)
- **tvtv.com format** - Copy directly from tvtv.com URL (e.g., `CAN-OTAJ3B1M4`)
- **Complete format** - Cable/Satellite provider (e.g., `CAN-0005993-X`)

```xml
<!-- Over-the-Air (antenna) - Auto-detection -->
<setting id="zipcode">92101</setting>
<setting id="lineupid">auto</setting>

<!-- Copy from tvtv.com (auto-normalized to API format) -->
<setting id="lineupid">CAN-OTAJ3B1M4</setting>

<!-- Cable/Satellite provider -->
<setting id="lineupid">CAN-0005993-X</setting>
```

**How to find your lineup**:
1. Visit [tvtv.ca](https://www.tvtv.ca) (Canada) or [tvtv.us](https://www.tvtv.us) (US)
2. Enter your postal/ZIP code
3. **For Over-the-Air**: Click "Broadcast" → "Local Over the Air"
4. **For Cable/Satellite**: Select your provider
5. Copy the lineup ID from the URL (remove the `lu` prefix)

**Test your lineup**:
```bash
tv_grab_gracenote2epg --show-lineup --zip 92101
tv_grab_gracenote2epg --show-lineup --postal J3B1M4 --debug
```

📖 **Detailed guide**: [Lineup Configuration](lineup-configuration.md)

## Core Settings

### days
**Guide duration** (1-14 days)
```xml
<setting id="days">7</setting>         <!-- 7 days of guide data -->
```

### Extended Details Configuration

#### Understanding xdetails vs xdesc

These two settings work **independently** to control different aspects of extended functionality:

**Automatic API Download Logic**: API downloads occur when **either** `xdetails=true` **OR** `xdesc=true`
- `xdetails=true` triggers downloads and uses extended metadata (credits, images, categories)
- `xdesc=true` triggers downloads for enhanced description (year, rating, flags, original air dates)

However, the **usage** of downloaded data depends on the specific setting:

### Configuration Matrix

| xdetails | xdesc | API Downloads | Credits | Extended Categories | Series Images | Description Enhancement |
|----------|-------|---------------|---------|-------------------|---------------|----------------------|
| `false`  | `false` | ❌ No         | ❌ No   | ❌ Basic only      | ❌ Episode only | ❌ Basic guide text  |
| `false`  | `true`  | ✅ Yes*       | ❌ No   | ❌ Basic only      | ❌ Episode only | ✅ Basic + enhancements* |
| `true`   | `false` | ✅ Yes        | ✅ Yes  | ✅ Extended        | ✅ Series     | ❌ Basic guide text  |
| `true`   | `true`  | ✅ Yes        | ✅ Yes  | ✅ Extended        | ✅ Series     | ✅ Extended + enhancements |

*API downloads automatically triggered when `xdesc=true` to gather enhancement data (year, rating, flags, original air dates)
*Enhancement includes: year, rating, flags (NEW/LIVE/PREMIERE), CC/HD tags

**Examples of description differences**:

```
xdesc=true:  "A detective investigates a mysterious case. • 2023 | Rated: TV-14 | NEW | CC"
xdesc=false: "A detective investigates a mysterious case."
```

**Use Cases**:
- **`xdetails=true, xdesc=false`**: Want full metadata (credits, images, categories) but clean, simple descriptions
- **`xdetails=false, xdesc=true`**: Want enhanced descriptions only (API downloads occur for enhancement data, but no credits/extended categories/series images)
- **`xdetails=true, xdesc=true`**: Full functionality (recommended for most users)
- **`xdetails=false, xdesc=false`**: Minimal setup (fastest, lowest bandwidth, no API downloads)

#### langdetect
**Automatic language detection** (requires `langdetect` library)
```xml
<setting id="langdetect">true</setting> <!-- Auto-detect French/English/Spanish -->
```

When enabled:
- Automatically detects French, English, Spanish content
- Translates categories and terms appropriately
- Applies proper capitalization rules per language
- Uses intelligent caching for performance

**Install language detection**:
```bash
pip install gracenote2epg[full]
# OR
pip install langdetect
```

## Display Options

### epgenre
**Genre/category mode**
```xml
<setting id="epgenre">3</setting>      <!-- All genres -->
```

**Values**:
- `0` - No genres
- `1` - Primary genre only
- `2` - EIT categories  
- `3` - All genres (recommended)

### epicon
**Program icon mode**
```xml
<setting id="epicon">1</setting>       <!-- Series + episode icons -->
```

**Values**:
- `0` - No icons
- `1` - Series + episode icons (recommended)
- `2` - Episode icons only

### stitle
**Safe titles** (replace special characters)
```xml
<setting id="stitle">false</setting>   <!-- Keep original titles -->
```

When `true`: Replaces `\/*?:|` with `_` in episode titles (useful for file systems)

## Station Filtering

### slist
**Explicit station list** (comma-separated station IDs)
```xml
<setting id="slist"></setting>         <!-- Empty = all stations -->
<setting id="slist">12345,67890</setting> <!-- Only specific stations -->
```

When empty: Processes all available stations
When specified: Only processes listed station IDs

## TVheadend Integration

### tvhoff
**Enable TVheadend integration**
```xml
<setting id="tvhoff">true</setting>    <!-- Enable TVH integration -->
```

### Connection Settings
```xml
<setting id="tvhurl">127.0.0.1</setting>   <!-- TVH server IP -->
<setting id="tvhport">9981</setting>       <!-- TVH port -->
<setting id="usern"></setting>             <!-- Username (optional) -->
<setting id="passw"></setting>             <!-- Password (optional) -->
```

### Filtering Options
```xml
<setting id="tvhmatch">true</setting>      <!-- Use TVH channel filtering -->
<setting id="chmatch">true</setting>       <!-- Enable channel number matching -->
```

**tvhmatch**: When enabled, only processes channels that exist in TVheadend
**chmatch**: When enabled, applies intelligent channel number matching (e.g., `5` → `5.1`)

## Cache and Retention Policies

📖 **Detailed guide**: [Cache & Retention Policies](cache-retention.md)

### Cache Settings
```xml
<setting id="redays">7</setting>       <!-- Cache retention days (must be >= days) -->
<setting id="refresh">48</setting>     <!-- Refresh first 48 hours (0=disabled) -->
```

**redays**: How long to keep cached guide blocks
**refresh**: How many hours from now to refresh (0 = use all cached data)

### Log Rotation
```xml
<setting id="logrotate">true</setting> <!-- Enable log rotation -->
<setting id="relogs">30</setting>      <!-- Log retention -->
```

**logrotate values**:
- `true` or `daily` - Rotate daily
- `weekly` - Rotate weekly  
- `monthly` - Rotate monthly
- `false` - No rotation

**relogs values**:
- Number - Days to keep (e.g., `30`)
- `weekly` - Keep for 7 days
- `monthly` - Keep for 30 days
- `quarterly` - Keep for 90 days
- `unlimited` - Never delete

### XMLTV Backup Retention
```xml
<setting id="rexmltv">7</setting>      <!-- XMLTV backup retention -->
```

Same format as `relogs` - controls how long to keep XMLTV backup files.

## Configuration Examples

### Standard Home Setup
```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="8">
  <!-- Basic guide settings -->
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">14</setting>

  <!-- Extended features -->
  <setting id="xdetails">true</setting>
  <setting id="xdesc">true</setting>
  <setting id="langdetect">true</setting>

  <!-- Cache and retention -->
  <setting id="redays">14</setting>
  <setting id="refresh">48</setting>
  <setting id="logrotate">true</setting>
  <setting id="relogs">30</setting>
  <setting id="rexmltv">7</setting>
</settings>
```

### Resource-Limited System
```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="8">
  <!-- Minimal resource usage -->
  <setting id="zipcode">J3B1M4</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">3</setting>

  <!-- Basic features only -->
  <setting id="xdetails">false</setting>
  <setting id="xdesc">false</setting>
  <setting id="langdetect">false</setting>
  
  <!-- Cache and retention -->
  <setting id="redays">3</setting>
  <setting id="refresh">12</setting>
  <setting id="logrotate">daily</setting>
  <setting id="relogs">7</setting>
  <setting id="rexmltv">3</setting>
</settings>
```

### Development/Testing
```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="8">
  <!-- Testing configuration -->
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">2</setting>

  <!-- Full debugging -->
  <setting id="xdetails">true</setting>
  <setting id="xdesc">true</setting>
  <setting id="langdetect">true</setting>
  
  <!-- Keep all logs for debugging -->
  <setting id="redays">2</setting>
  <setting id="refresh">0</setting>
  <setting id="logrotate">false</setting>
  <setting id="relogs">unlimited</setting>
  <setting id="rexmltv">unlimited</setting>
</settings>
```

## Command Line Overrides

You can override most configuration options from the command line:

```bash
# Override basic settings
tv_grab_gracenote2epg --days 3 --zip 90210 --lineupid auto

# Override language detection
tv_grab_gracenote2epg --langdetect false --zip 92101

# Override cache settings
tv_grab_gracenote2epg --refresh 24 --zip 92101    # Refresh first 24 hours
tv_grab_gracenote2epg --norefresh --zip 92101     # Use all cached data

# Override output location
tv_grab_gracenote2epg --output custom.xml --zip 92101
```

## Configuration Validation

gracenote2epg validates configuration on startup:

### Common Validation Messages
```
WARNING: redays (5) must be >= days (7), adjusting redays to 7
WARNING: Invalid logrotate value "bad_value", using default "true"
WARNING: Invalid relogs value "invalid", using default "30"
```

### Testing Configuration
```bash
# Test with debug output
tv_grab_gracenote2epg --debug --console --days 1

# Check configuration processing
grep -A 20 "Configuration values processed" ~/gracenote2epg/log/gracenote2epg.log
```

## Configuration Migration

gracenote2epg automatically migrates from older configuration formats:
- Automatic backup of old configuration created
- Migration messages logged at INFO level
- New configuration format provides cleaner organization

## Advanced Configuration

### Custom Base Directory
```bash
# Use custom directory for all files
tv_grab_gracenote2epg --basedir /custom/path/gracenote2epg
```

### Custom Configuration File
```bash
# Use custom configuration file
tv_grab_gracenote2epg --config-file /path/to/custom.xml
```

### Environment-Specific Configurations

You can maintain multiple configurations for different environments:

```bash
# Production configuration
cp gracenote2epg.xml gracenote2epg-prod.xml

# Testing configuration  
cp gracenote2epg.xml gracenote2epg-test.xml

# Use specific configuration
tv_grab_gracenote2epg --config-file gracenote2epg-test.xml
```

## Next Steps

- **[Test your configuration](troubleshooting.md#testing-setup)**
- **[Configure lineup detection](lineup-configuration.md)**  
- **[Optimize cache settings](cache-retention.md)**
- **[Set up TVheadend integration](migration.md)**
