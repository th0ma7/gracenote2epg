# Cache and Retention Policies in gracenote2epg

gracenote2epg uses a unified cache and retention policy system that manages guide cache, log rotation, and XMLTV backup retention with a simplified, consistent configuration.

## Overview

The cache and retention policy system provides a streamlined approach to managing all temporary data and backups:

- **Cache management**: `redays` for guide cache retention and `refresh` for refresh windows
- **Log rotation**: `logrotate` for rotation control  
- **Retention periods**: `relogs` for log retention and `rexmltv` for XMLTV backup retention
- **Consistent behavior**: Same configuration patterns for all retention policies

## Configuration Settings

### Cache and Retention Policies Section

All cache and retention settings are now unified in a single section:

```xml
<!-- Cache and retention policies -->
<setting id="redays">7</setting>                             <!-- Cache retention days (must be >= days) -->
<setting id="refresh">48</setting>                           <!-- Forced refresh first 48 hours (0=disabled) -->
<setting id="logrotate">true</setting>                       <!-- Log rotation: true(daily)|false|daily|weekly|monthly -->
<setting id="relogs">30</setting>                            <!-- Log retention: days(number) or weekly|monthly|quarterly -->
<setting id="rexmltv">7</setting>                            <!-- XMLTV backup retention: days(number) or weekly|monthly|quarterly -->
```

### Individual Settings

#### Guide Cache Management

```xml
<setting id="redays">7</setting>
```
- **Purpose**: Guide cache retention period
- **Requirement**: Must be ≥ `days` setting
- **Values**: Number of days (1-365)

```xml
<setting id="refresh">48</setting>
```
- **Purpose**: Refresh window for recent guide data
- **Values**: Hours (0=disabled, 1-168)

#### Log Rotation Control

```xml
<setting id="logrotate">true</setting>
```
- **Options:**
  - `true` - Enable daily rotation (default)
  - `false` - Disable rotation entirely
  - `daily` - Rotate logs daily at midnight
  - `weekly` - Rotate logs weekly on Sunday at midnight
  - `monthly` - Rotate logs monthly on the 1st at midnight

#### Retention Periods

```xml
<setting id="relogs">30</setting>
<setting id="rexmltv">7</setting>
```

**Retention values can be:**
- **Number (days)**: `7`, `30`, `90` - Keep files for specified number of days
- **Period names**: `weekly`, `monthly`, `quarterly` - Keep files for specified period
- **Unlimited**: `unlimited` or `0` - Never delete old files

## Migration from Old Settings

Old settings are automatically migrated:

| Old Setting | Old Value | New Setting | New Value |
|-------------|-----------|-------------|-----------|
| `logrotate_enabled` | `true` | `logrotate` | `daily` |
| `logrotate_enabled` | `false` | `logrotate` | `false` |
| `logrotate_interval` | `weekly` | `logrotate` | `weekly` |
| `logrotate_keep` | `14` | `relogs` | `98` (14 weeks) |
| `log_rotation` | `daily` | `logrotate` | `daily` |
| `log_retention` | `30` | `relogs` | `30` |
| `xmltv_backup_retention` | `7` | `rexmltv` | `7` |

## Examples

### Standard Home Setup

```xml
<!-- Cache and retention policies -->
<setting id="redays">7</setting>     <!-- 1 week cache retention -->
<setting id="refresh">48</setting>   <!-- Refresh first 48 hours -->
<setting id="logrotate">true</setting>    <!-- Daily log rotation -->
<setting id="relogs">30</setting>    <!-- 30 days log retention -->
<setting id="rexmltv">7</setting>    <!-- 7 days XMLTV backups -->
```

**Result**: 
- Guide cache kept for 7 days
- Recent 48 hours refreshed on each run
- Logs rotate daily, kept for 30 days
- XMLTV backups kept for 7 days

### High-Volume Server

```xml
<!-- Cache and retention policies -->
<setting id="redays">14</setting>    <!-- 2 weeks cache -->
<setting id="refresh">24</setting>   <!-- Refresh first 24 hours -->
<setting id="logrotate">daily</setting>   <!-- Explicit daily rotation -->
<setting id="relogs">quarterly</setting>  <!-- 90 days log retention -->
<setting id="rexmltv">monthly</setting>   <!-- 30 days XMLTV backups -->
```

**Result**:
- Extended cache for stability
- Aggressive refresh for accuracy
- Long retention for debugging
- Extended XMLTV backup history

### Resource-Constrained System

```xml
<!-- Cache and retention policies -->
<setting id="redays">3</setting>     <!-- Minimal cache -->
<setting id="refresh">12</setting>   <!-- Quick refresh -->
<setting id="logrotate">daily</setting>   <!-- Daily cleanup -->
<setting id="relogs">7</setting>     <!-- 1 week logs -->
<setting id="rexmltv">3</setting>    <!-- 3 days XMLTV backups -->
```

**Result**:
- Minimal disk usage
- Quick operations
- Frequent cleanup
- Short retention periods

### Development/Testing

```xml
<!-- Cache and retention policies -->
<setting id="redays">1</setting>     <!-- Always fresh -->
<setting id="refresh">0</setting>    <!-- No refresh (use cache) -->
<setting id="logrotate">false</setting>   <!-- No rotation (single file) -->
<setting id="relogs">unlimited</setting>  <!-- Keep all logs -->
<setting id="rexmltv">unlimited</setting> <!-- Keep all backups -->
```

**Result**:
- Predictable cache behavior
- No automatic cleanup
- Full history preserved
- Ideal for debugging

### Weekly Operations

```xml
<!-- Cache and retention policies -->
<setting id="redays">14</setting>    <!-- 2 weeks cache -->
<setting id="refresh">168</setting>  <!-- Refresh weekly (168h) -->
<setting id="logrotate">weekly</setting>  <!-- Weekly rotation -->
<setting id="relogs">quarterly</setting>  <!-- Long-term logs -->
<setting id="rexmltv">monthly</setting>   <!-- Monthly XMLTV backups -->
```

**Result**:
- Optimized for weekly guide updates
- Extended refresh window
- Weekly log organization
- Long-term retention

## Implementation Details

### Cache Directory Layout

The cache directory keeps the small, frequently-rotated guide blocks at its
root and stores the many per-series detail files in a `series/` subdirectory:

```
~/gracenote2epg/cache/
├── 2026061412.json.gz      # guide blocks (YYYYMMDDHH, 3-hour spans)
├── 2026061415.json.gz
├── ...
├── xmltv.xml               # generated guide
├── xmltv.xml.2026-06-13... # XMLTV backups
└── series/                 # extended details, one file per series
    ├── SH00012345.json
    ├── MV00067890.json
    └── EP00021161.json
```

Older caches that stored series files directly at the cache root are migrated
automatically on first run (the files are moved into `series/`, so nothing is
re-downloaded).

To inspect:

```bash
ls -la ~/gracenote2epg/cache/*.json.gz      # guide blocks
ls -la ~/gracenote2epg/cache/series/        # series details
```

### Cache Validation

The system validates that `redays >= days`:

```
WARNING  redays (5) must be >= days (7), adjusting redays to 7
```

If `redays < days`, it's automatically adjusted to match `days`.

### Retention Calculation

Retention periods are converted to days internally:

| Period | Days |
|--------|------|
| `weekly` | 7 |
| `monthly` | 30 |
| `quarterly` | 90 |
| `unlimited` | 0 (no cleanup) |

### Refresh Window

The `refresh` setting controls which guide blocks are re-downloaded:

- `0` - No refresh (use all cached data)
- `24` - Refresh first 24 hours
- `48` - Refresh first 48 hours (default)
- `168` - Refresh first week

## Monitoring and Verification

### Log Messages

The system provides clear feedback about cache and retention policies:

```
INFO     Cache and retention policies:
INFO       refresh: 48 hours (refresh first 48 hours of guide)
INFO       redays: 7 days (cache retention period)
INFO       logrotate: enabled (daily, 30 days retention)
INFO       rexmltv: 7 days (XMLTV backup retention)
```

### Checking Current Configuration

View your current cache and retention settings in the unified section:

```bash
grep -A10 "Cache and retention policies" ~/gracenote2epg/conf/gracenote2epg.xml
```

Or check individual settings:

```bash
grep -E "(redays|refresh|logrotate|relogs|rexmltv)" ~/gracenote2epg/conf/gracenote2epg.xml
```

### Verifying Results

Check guide cache:
```bash
ls -la ~/gracenote2epg/cache/*.json.gz
```

Check log backups:
```bash
ls -la ~/gracenote2epg/log/gracenote2epg.log.*
```

Check XMLTV backups:
```bash
ls -la ~/gracenote2epg/cache/xmltv.xml.*
```

## Troubleshooting

### Validation Errors

Common validation issues and fixes:

1. **redays too small**:
   ```
   WARNING  redays (3) must be >= days (7), adjusting redays to 7
   ```
   **Fix**: Increase `redays` to at least match `days`.

2. **Invalid retention value**:
   ```
   WARNING  Invalid relogs value "bad_value", using default "30"
   ```
   **Fix**: Use valid retention values (number or period names).

### Cache Issues

If cache isn't working as expected:

1. **Check redays vs days**:
   ```bash
   grep -E "(days|redays)" ~/gracenote2epg/conf/gracenote2epg.xml
   ```

2. **Verify refresh window**:
   ```bash
   grep "refresh" ~/gracenote2epg/conf/gracenote2epg.xml
   ```

3. **Check cache directory**:
   ```bash
   ls -la ~/gracenote2epg/cache/
   ```

### Disk Space Management

To quickly free up space:

```xml
<!-- Aggressive cleanup -->
<setting id="redays">1</setting>     <!-- Minimal cache -->
<setting id="refresh">6</setting>    <!-- 6-hour refresh -->
<setting id="logrotate">daily</setting>   <!-- Daily rotation -->
<setting id="relogs">7</setting>     <!-- 1 week logs -->
<setting id="rexmltv">1</setting>    <!-- 1 day XMLTV backups -->
```

Then run gracenote2epg once to apply the new policy.

## Best Practices

### Standard Home Use

```xml
<setting id="redays">7</setting>
<setting id="refresh">48</setting>
<setting id="logrotate">true</setting>
<setting id="relogs">30</setting>
<setting id="rexmltv">7</setting>
```

### Server Deployment

```xml
<setting id="redays">14</setting>
<setting id="refresh">24</setting>
<setting id="logrotate">daily</setting>
<setting id="relogs">quarterly</setting>
<setting id="rexmltv">monthly</setting>
```

### Development Environment

```xml
<setting id="redays">1</setting>
<setting id="refresh">0</setting>
<setting id="logrotate">false</setting>
<setting id="relogs">unlimited</setting>
<setting id="rexmltv">unlimited</setting>
```

### Resource-Limited Systems

```xml
<setting id="redays">2</setting>
<setting id="refresh">12</setting>
<setting id="logrotate">daily</setting>
<setting id="relogs">weekly</setting>
<setting id="rexmltv">3</setting>
```

## Performance Impact

- **Minimal overhead**: All cleanup happens during startup
- **Intelligent caching**: Only refreshes data within refresh window
- **Efficient analysis**: Optimized file operations and regex parsing
- **Non-blocking**: Cleanup operations don't interfere with normal operation
- **Fail-safe**: Errors in cleanup don't prevent normal operation

The unified cache and retention system provides comprehensive control over all temporary data and backups while maintaining excellent performance and reliability.
