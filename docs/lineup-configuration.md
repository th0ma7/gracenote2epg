# LineupID Configuration Guide

This guide explains how to configure the `lineupid` setting in gracenote2epg for optimal TV guide downloads from tvlistings.gracenote.com.

## 🚀 Quick Start

**For most users (Over-the-Air antenna):**
```xml
<setting id="lineupid">auto</setting>
```

**For cable/satellite users:**
1. Visit tvtv.com and find your provider
2. Copy the lineup ID from the URL 
3. Use it in your configuration

## 📋 Understanding LineupID

The `lineupid` setting determines which TV channel lineup gracenote2epg downloads. There are three types:

### 1. **Over-the-Air (OTA) - Antenna** 📡
- **Free channels** received via antenna
- **Device type**: `-` (automatically detected, shown in debug mode)
- **Configuration**: `<setting id="lineupid">auto</setting>`

### 2. **Cable/Satellite Providers** 📺
- **Paid TV services** like cable/satellite companies
- **Device type**: `X` (automatically detected, shown in debug mode)
- **Configuration**: Provider-specific lineup ID

### 3. **Custom Lineup** ⚙️
- **Specific lineup** from tvtv.com
- **Manual selection** for testing or special cases

## 🔧 Configuration Options

### Option 1: Auto-Detection (Recommended)
```xml
<setting id="lineupid">auto</setting>
```
- **Best for**: Over-the-Air (antenna) users
- **Generates**: `USA-OTA90210-DEFAULT` or `CAN-OTAJ3B1M4-DEFAULT`
- **Device**: Automatically detected (shown in debug mode: `--debug`)

### Option 2: Copy from tvtv.com
```xml
<setting id="lineupid">CAN-OTAJ3B1M4</setting>
```
- **Best for**: Manual OTA configuration or testing
- **Auto-normalized**: Automatically adds `-DEFAULT` for API
- **Device**: Automatically detected from lineup format

### Option 3: Cable/Satellite Provider
```xml
<setting id="lineupid">CAN-0005993-X</setting>
```
- **Best for**: Cable/satellite subscribers
- **Complete format**: Used as-is for API calls  
- **Device**: Automatically set to `X` (cable/satellite)

## 🌍 Finding Your LineupID

### Step 1: Visit tvtv.com
- **Canada**: https://www.tvtv.ca/
- **United States**: https://www.tvtv.us/

### Step 2: Enter Your Location
- **Canada**: Enter postal code (e.g., `J3B1M4`)
- **United States**: Enter ZIP code (e.g., `90210`)

### Step 3A: For Over-the-Air (Antenna)
1. Click **"Broadcast"** → **"Local Over the Air"**
2. URL shows: `https://www.tvtv.ca/qc/saint-jean-sur-richelieu/j3b1m4/luCAN-OTAJ3B1M4`
3. **Copy**: `CAN-OTAJ3B1M4` (remove the `lu` prefix)
4. **Use**: `<setting id="lineupid">CAN-OTAJ3B1M4</setting>`

### Step 3B: For Cable/Satellite
1. **Select your provider** (e.g., Videotron, Rogers, Comcast)
2. URL shows: `https://www.tvtv.ca/qc/saint-jean-sur-richelieu/j3b1m4/luCAN-0005993-X`
3. **Copy**: `CAN-0005993-X` (remove the `lu` prefix)
4. **Use**: `<setting id="lineupid">CAN-0005993-X</setting>`

## 🧪 Testing Your Configuration

Use the `--show-lineup` command to test your postal/ZIP code and see what lineup IDs are available:

### Basic Testing
```bash
# Test US ZIP code
tv_grab_gracenote2epg --show-lineup --zip 90210

# Test Canadian postal code (displayed as J3B1M4 in logs)
tv_grab_gracenote2epg --show-lineup --postal J3B1M4
```

**Note**: All postal codes are displayed in normalized format (without spaces) in logs and error messages.

### Detailed Technical Information
```bash
# Debug mode with technical details
tv_grab_gracenote2epg --show-lineup --zip 90210 --debug
```

## 🆕 Enhanced Geographic Resolution

gracenote2epg now includes **intelligent geographic resolution** for more accurate lineup URLs:

### ✅ Automatic Resolution
When `pgeocode` is installed, the system automatically resolves your postal code to the correct city and province:

```bash
# Install with geographic resolution (recommended)
pip install gracenote2epg[full]

# Or install just the geocoding feature
pip install gracenote2epg[geocoding]
```

### 📍 Status Indicators
The `--show-lineup` command now shows the geographic resolution status:

#### ✅ **Successfully Resolved**
```
✅ VALIDATION URLs:
   Direct URL: https://www.tvtv.ca/qc/montreal/h1a1a1/luCAN-OTAH1A1A1
   Status: ✅ Location automatically resolved (Montreal, QC)
```

#### ⚠️ **Manual Lookup Required**
```
✅ VALIDATION URLs:
   Status: ⚠️ Unable to automatically resolve location for H9Z9Z9. Please use manual lookup instructions below.
   Manual lookup required:
     1. Go to https://www.tvtv.ca/
     2. Enter postal code: H9Z 9Z9
     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → Look for 'luCAN-OTAH9Z9Z9' in URL
     ...
```

### 🔄 Graceful Fallback
- **Without pgeocode**: Manual lookup instructions are always provided
- **Resolution fails**: Automatic fallback to manual lookup process
- **No breaking changes**: Existing installations continue to work normally

## 📊 Example Output

### Enhanced Normal Mode (with pgeocode)
```
🌍 GRACENOTE API URL PARAMETERS:
   lineupId=CAN-OTAJ3B1M4-DEFAULT
   country=CAN
   postalCode=J3B1M4

✅ VALIDATION URLs:
   Direct URL: https://www.tvtv.ca/qc/saint-jean-sur-richelieu/j3b1m4/luCAN-OTAJ3B1M4
   Status: ✅ Location automatically resolved (Saint-Jean-sur-Richelieu, QC)
     1. Go to https://www.tvtv.ca/
     2. Enter postal code: J3B 1M4
     3a. For OTA: Click 'Broadcast' → 'Local Over the Air' → Look for 'luCAN-OTAJ3B1M4' in URL
     3b. For Cable/Sat: Select your provider → Look for 'luCAN-[ProviderID]-X' in URL
     4. Expected OTA pattern: luCAN-OTAJ3B1M4

🔗 GRACENOTE API URL FOR TESTING:
   https://tvlistings.gracenote.com/api/grid?aid=orbebb&country=CAN&postalCode=J3B1M4&time=1755432000&timespan=3&isOverride=true&userId=-&lineupId=CAN-OTAJ3B1M4-DEFAULT&headendId=lineupId
```

### Legacy Mode (without pgeocode)
```
🌍 GRACENOTE API URL PARAMETERS:
   lineupId=USA-OTA90210-DEFAULT
   country=USA
   postalCode=90210

✅ VALIDATION URLs:
   Status: ⚠️ Unable to automatically resolve location for 90210. Please use manual lookup instructions below.
   Manual lookup required:
     1. Go to https://www.tvtv.us/
     2. Enter ZIP code: 90210
     3. Click 'Broadcast' → 'Local Over the Air'
     4. Look for 'luUSA-OTA90210' in the URL

🔗 GRACENOTE API URL FOR TESTING:
   https://tvlistings.gracenote.com/api/grid?aid=orbebb&country=USA&postalCode=90210&time=1755432000&timespan=3&isOverride=true&userId=-&lineupId=USA-OTA90210-DEFAULT&headendId=lineupId
```

### Debug Mode
Includes additional technical information:
- Geographic resolution process details
- City name normalization for URL compatibility
- Manual download commands with proper headers
- Recommended configuration examples
- Troubleshooting tips

## 📝 LineupID Format Reference

### Over-the-Air (OTA) Format
- **tvtv.com format**: `CAN-OTAJ3B1M4` or `USA-OTA90210`
- **API format**: `CAN-OTAJ3B1M4-DEFAULT` or `USA-OTA90210-DEFAULT`
- **Pattern**: `{Country}-OTA{PostalCode}(-DEFAULT for API)`

### Cable/Satellite Format  
- **tvtv.com format**: `CAN-0005993-X` or `USA-1234567-X`
- **API format**: Same (already complete)
- **Pattern**: `{Country}-{ProviderID}-X`

### Auto-Detection
- **Configuration**: `auto` or empty
- **Generates**: OTA format automatically
- **Based on**: ZIP/postal code in configuration

## 🔄 Automatic Normalization

gracenote2epg automatically converts between formats:

```
Input Configuration    → API Format Used
--------------------     ----------------
auto                   → USA-OTA90210-DEFAULT
CAN-OTAJ3B1M4         → CAN-OTAJ3B1M4-DEFAULT  
CAN-0005993-X         → CAN-0005993-X (unchanged)
```

## 🚨 Common Issues

### Issue: No channels found
**Cause**: Wrong lineup ID for your location
**Solution**: 
1. Use `--show-lineup` to test your postal/ZIP code
2. Verify the lineup ID on tvtv.com
3. Check that your postal/ZIP code is correct

### Issue: Wrong channels shown
**Cause**: Using OTA lineup when you have cable/satellite
**Solution**:
1. Find your cable/satellite provider on tvtv.com
2. Copy the provider lineup ID (ends with `-X`)
3. Update your configuration

### Issue: API errors during download
**Cause**: Invalid lineup ID format
**Solution**:
1. Use `--show-lineup --debug` to see valid formats
2. Ensure you copied the lineup ID correctly from tvtv.com
3. Remove any extra characters or spaces

### Issue: Non-functional validation URLs
**Fixed in v1.5.6**: Validation URLs are now dynamically generated based on actual geographic locations
**Before**: Hardcoded URLs that only worked for specific locations
**After**: Dynamic URLs that work for all valid postal/ZIP codes

### Issue: Inconsistent location codes
**Error message**: `"Inconsistent location codes: lineupid contains 'J3B1M4' but explicit location is 'J3B2M4'"`
**Cause**: Postal codes don't match (note: all codes displayed without spaces)
**Solution**: Ensure consistency between lineup and explicit location
**Example**: `--lineupid CAN-OTAJ3B1M4 --zip 90210` is invalid (J3B1M4 ≠ 90210)

## 🔗 Provider Examples

### Canada
- **Over-the-Air**: `CAN-OTAJ3B1M4`
- **Videotron**: `CAN-0005993-X`
- **Rogers**: `CAN-0006147-X`
- **Bell**: `CAN-0006148-X`

### United States
- **Over-the-Air**: `USA-OTA90210`
- **Comcast**: `USA-1234567-X`
- **DIRECTV**: `USA-2345678-X`
- **Spectrum**: `USA-3456789-X`

*Note: Provider IDs are examples and vary by location. Always check tvtv.com for your specific area.*

## 🛠️ Advanced Usage

### Testing Different Lineups
```bash
# Test multiple postal codes
tv_grab_gracenote2epg --show-lineup --postal J3B1M4
tv_grab_gracenote2epg --show-lineup --postal H3H2N1  
tv_grab_gracenote2epg --show-lineup --zip 90210
tv_grab_gracenote2epg --show-lineup --zip 10001
```

### Downloading with Custom LineupID
```bash
# Use specific lineup for testing
tv_grab_gracenote2epg --days 1 --zip 90210 --console
```

### Validation Against tvtv.com
1. Configure your `lineupid` 
2. Run `--show-lineup` to see the validation URL
3. Visit the validation URL and compare channels
4. If channels match, your configuration is correct

## 📄 Configuration Template

```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="5">
  <!-- Basic guide settings -->
  <setting id="days">2</setting>
  <setting id="zipcode">92101</setting>                        <!-- Your postal/ZIP code -->
  
  <!-- LineupID configuration (choose one) -->
  <setting id="lineupid">auto</setting>                        <!-- Auto-detect OTA -->
  <!-- <setting id="lineupid">CAN-OTAJ3B1M4</setting> -->      <!-- Manual OTA -->
  <!-- <setting id="lineupid">CAN-0005993-X</setting> -->      <!-- Cable/Satellite -->
  
  <!-- Other settings... -->
</settings>
```

## 🔍 Configuration Logging and Debug Information

The application provides clear logging to help you understand what's happening:

### Normal Mode Logging
```
Configuration values processed:
  zipcode: J3B1M4 (extracted from CAN-OTAJ3B1M4-DEFAULT)
  lineupid: auto → CAN-OTAJ3B1M4-DEFAULT (auto-detection)
  country: Canada [CAN] (auto-detected from zipcode)
  description: Local Over the Air Broadcast (Canada)
```

### Debug Mode Logging
Use `--debug` to see additional technical information:
```bash
tv_grab_gracenote2epg --debug --console --days 1 --lineupid CAN-OTAJ3B1M4
```

Debug mode includes:
- Device type detection: `device: - (auto-detected for optional &device= URL parameter)`
- Geographic resolution status and process details
- Detailed URL parameter explanations
- Technical API information
- Postal code normalization details

### Postal Code Normalization
All postal codes are displayed consistently without spaces:
- **Canadian**: `J3B1M4` (not `J3B 1M4`)
- **US ZIP**: `90210` (unchanged)
- **Error messages**: Always show normalized format
- **Log entries**: Consistent formatting throughout

## 📚 Related Documentation

- **[README.md](README.md)** - Main documentation and installation guide
- **[CHANGELOG.md](CHANGELOG.md)** - Version history and release notes  
- **Configuration file**: `gracenote2epg.xml` - Complete configuration example

## 🆘 Getting Help

If you're still having issues with lineup configuration:

1. **Test first**: `tv_grab_gracenote2epg --show-lineup --zip YOUR_CODE`
2. **Check geographic resolution**: Look for ✅ or ⚠️ status indicators
3. **Check logs**: Look for lineup-related messages in the log files
4. **Validate**: Visit the tvtv.com URLs shown in `--show-lineup` output
5. **Debug**: Use `--debug` flag for detailed technical information
6. **Check normalization**: Ensure postal codes match exactly (no spaces)

### Debug Commands for Troubleshooting
```bash
# Basic lineup test with geographic resolution
tv_grab_gracenote2epg --show-lineup --zip 92101

# Detailed debug information
tv_grab_gracenote2epg --show-lineup --zip 92101 --debug

# Test actual download with console output
tv_grab_gracenote2epg --days 1 --zip 92101 --debug --console

# Test configuration consistency
tv_grab_gracenote2epg --lineupid CAN-OTAJ3B1M4 --debug --console
```

### Geographic Resolution Troubleshooting
```bash
# Check if pgeocode is installed
python -c "import pgeocode; print('pgeocode available')"

# Install geographic resolution support
pip install gracenote2epg[geocoding]

# Test geographic resolution
tv_grab_gracenote2epg --show-lineup --postal J3B1M4 --debug
```

The `--show-lineup` command with enhanced geographic resolution is your best friend for lineup configuration troubleshooting! 🚀
