# TVheadend Integration Guide

This guide covers complete TVheadend integration for gracenote2epg, including migration from other EPG grabbers and troubleshooting.

## 📺 TVheadend EPG Grabber Configuration

### Initial Setup

> **💡 TVheadend Users - Easy Setup**: Most users don't need to edit configuration files! Simply use TVheadend's **Extra arguments** box to add your parameters like `--days 7 --zip 92101 --langdetect false` (Configuration → Channel/EPG → EPG Grabber Modules).

1. **Access TVheadend Web Interface** (usually http://your-server:9981)
2. **Navigate**: Configuration → Channel/EPG → EPG Grabber Modules
3. **Enable gracenote2epg**: 
   - Find **gracenote2epg** - `Internal: XMLTV: North America (tvlistings.gracenote.com using gracenote2epg)`
   - **Add your parameters in Extra arguments** (this overrides the default configuration):
     ```
     --days 14 --postal J3B1M4
     --days 7 --zip 92101 --langdetect false
     --days 7 --zip 90210 --lineupid auto
     ```
   - Select **Only digits** for **Channel numbers (heuristic)**
   - Check ✅ **Enabled**
   - Check ✅ **Scrape credits and extra information**
   - Check ✅ **Alter programme description to include detailed information**
4. **Save Configuration**
5. **Navigate**: Configuration → Channel/EPG → EPG Grabber
6. **Set appropriate Interval**
   - Recommended: every 12 hours (default)
7. **Save Configuration**

> **Important**: Extra arguments override the default configuration file, so you typically don't need to edit `conf/gracenote2epg.xml` manually.

### TVheadend Integration Settings

Configure gracenote2epg for optimal TVheadend integration. Below is the essential parts of the default auto-generated configuration. Note that **Extra arguments** set in **Initial Setup** above will supersede any default configuration value - alternatively you can choose to adjust the default configuration and avoid using **Extra arguments**. Note that TVheadend specific integration parameters requires modifying the configuration file if default doesn't suit your setup.

```xml
<?xml version="1.0" encoding="utf-8"?>
<settings version="6">
  <!-- Basic guide settings -->
  <setting id="zipcode">92101</setting>
  <setting id="lineupid">auto</setting>
  <setting id="days">7</setting>

  <!-- TVheadend integration -->
  <setting id="tvhoff">true</setting>                <!-- Enable TVH integration -->
  <setting id="tvhurl">127.0.0.1</setting>           <!-- TVH server IP -->
  <setting id="tvhport">9981</setting>               <!-- TVH port -->
  <setting id="tvhmatch">true</setting>              <!-- Use TVH channel filtering -->
  <setting id="chmatch">true</setting>               <!-- Channel number matching -->
  
  <!-- TVH authentication (default: anonymous access) -->
  <setting id="usern"></setting>                     <!-- Empty = anonymous access -->
  <setting id="passw"></setting>                     <!-- Empty = anonymous access -->
</settings>
```

> **Default behavior**: The configuration above uses **anonymous access** (empty username/password) which requires the minimal TVheadend permissions described in the Authentication section below.

### TVheadend Authentication Configuration

**Minimal TVheadend permissions for gracenote2epg**:

1. **Configuration** → **Users** → **Access Entries**
2. **Create/Edit user `*`** (anonymous access):
   - **Username**:
     - `*` (anonymous - no authentication)
     - `username` (authenticated named user - requires creating an entry in the **Passwords** tab)
   - **Enabled**: ✅ **Checked**
   - **Change parameters**: Only **Rights** checked
   - **Rights**: Only ✅ **Web interface** (Admin unchecked, streaming unchecked)
   - **Allowed networks**:
     - `127.0.0.0/8` (localhost only)
     - `192.168.0.0/16` (local network)
     - `0.0.0.0/0,::/0` (all networks - less secure)
   - **All other sections**: Leave unchecked (streaming, video recorder, etc.)

3. **Save Configuration**

4. **Create password** → When using authenticated named user you must adjust gracenote2epg configuration accordingly:
   ```xml
   <setting id="usern">username</setting>
   <setting id="passw">password</setting>
   ```

5. **Test access**:
   ```bash
   # Default anonymous channel list access
   curl -s "http://127.0.0.1:9981/api/channel/grid" | head -10
   
   # Default authenticated named user channel list access
   curl -s  --digest -u <username> "http://127.0.0.1:9981/api/channel/grid" | head -10
   Enter host password for user '<username>':

   # Get channel names only
   curl -s "http://127.0.0.1:9981/api/channel/grid" | jq '.entries[].name'

   # Get channel numbers only
   curl -s "http://127.0.0.1:9981/api/channel/grid" | jq '.entries[].number' | sort -V

   # Channel names and numbers together
   curl -s "http://127.0.0.1:9981/api/channel/grid" | jq '.entries[] | {name: .name, number: .number}'
   ```

## 🔄 Migrating EPG Grabbers in TVheadend

### Step 1: Disable Old EPG Grabber

> **💡 Philosophy**: Most EPG grabber migrations work smoothly without special procedures.

1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **EPG Grabber Modules**
2. **Find old grabber** (e.g., `tv_grab_zap2epg`)
3. **Uncheck ❌ Enabled**
4. **Save Configuration**

### Step 2: Enable gracenote2epg

1. **Find `Internal: XMLTV: North America (tvlistings.gracenote.com using gracenote2epg)`** in the EPG grabber list
2. **Check ✅ Enabled** (see **Initial setup** section above for suggested parameters)
3. **Save Configuration**

### Step 3: Test Migration

#### Manually Triggered
1. **Click "Re-run internal EPG grabbers"** in EPG Grabber Modules
2. **Monitor progress** in TVheadend logs
3. **Wait 5-15 minutes** for completion

### Step 4: Verify Success

**Check TVheadend logs** for success indicators:

#### ✅ **Successful Migration**
```
[INFO]:xmltv: grab took 283 seconds
[INFO]:xmltv: parse took 2 seconds  
[INFO]:xmltv: channels   tot=   33 new=    0 mod=    0  ← Channels detected
[INFO]:xmltv: seasons    tot=15249 new=15005 mod=  244  ← Series data ✅
[INFO]:xmltv: episodes   tot=11962 new=11810 mod=  152  ← Episodes ✅
[INFO]:xmltv: broadcasts tot=15682 new=15434 mod=  248  ← Programs ✅
```

#### ❌ **Migration Problems - Troubleshooting Needed**
```
[INFO]:xmltv: grab took 280 seconds
[INFO]:xmltv: parse took 0 seconds  
[INFO]:xmltv: channels   tot=   33 new=    0 mod=    0  ← Channels OK
[INFO]:xmltv: episodes   tot=    0 new=    0 mod=    0  ← No programs! ❌
[INFO]:xmltv: broadcasts tot=    0 new=    0 mod=    0  ← No programs! ❌
```

**If you see the problem pattern above**, proceed to [EPG Database Troubleshooting](#epg-database-troubleshooting).

## 🔧 EPG Database Troubleshooting

### When EPG Database Reset is Required

⚠️ **Use this procedure ONLY if you experience these symptoms:**

1. **Channels appear but no programs** after grabber migration
2. **Silent data rejection**: XMLTV is valid but TVheadend rejects program data
3. **Zero episodes/broadcasts** in logs despite successful grabber run
4. **Corrupted or incomplete program data** in TVheadend interface

### EPG Database Reset Procedure

> **⚠️ Important**: This procedure deletes all EPG data and requires complete re-download.

#### Step 1: Stop TVheadend Service

```bash
# Synology DSM7
sudo synopkg stop tvheadend

# Synology DSM6  
sudo systemctl stop tvheadend

# Standard Linux
sudo systemctl stop tvheadend

# Docker container
docker stop tvheadend_container
```

#### Step 2: Clean EPG Database and Cache

```bash
# Standard Linux (adjust paths for your installation)
sudo rm -f /home/hts/.hts/tvheadend/epgdb.v3
sudo rm -rf /home/hts/.hts/tvheadend/epggrab/xmltv/channels/*

# Synology DSM7
sudo rm -f /var/packages/tvheadend/var/epgdb.v3
sudo rm -rf /var/packages/tvheadend/var/epggrab/xmltv/channels/*

# Synology DSM6
sudo rm -f /var/packages/tvheadend/target/var/epgdb.v3  
sudo rm -rf /var/packages/tvheadend/target/var/epggrab/xmltv/channels/*

# Docker (adjust volume paths as needed)
docker exec tvheadend_container rm -f /config/epgdb.v3
docker exec tvheadend_container rm -rf /config/epggrab/xmltv/channels/*
```

#### Step 3: Start TVheadend Service

```bash
# Standard Linux
sudo systemctl start tvheadend

# Synology DSM7
sudo synopkg start tvheadend

# Docker
docker start tvheadend_container_name
```

#### Step 4: Wait for Channel Detection

- **Wait 2-5 minutes** after TVheadend startup
- **First run detects channels only** (expected behavior):

```
[INFO]:xmltv: grab took 280 seconds
[INFO]:xmltv: channels   tot=   33 new=   33 mod=   33  ← Channels ✅
[INFO]:xmltv: episodes   tot=    0 new=    0 mod=    0  ← No programs (normal)
[INFO]:xmltv: broadcasts tot=    0 new=    0 mod=    0  ← No programs (normal)
```

- **Wait for EPG database save**:
```
[INFO]:epgdb: snapshot start
[INFO]:epgdb: save start  
[INFO]:epgdb: stored (size 79)  ← Small size = channels only
```

#### Step 5: Trigger Program Data Download

1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **EPG Grabber Modules**
2. **Click "Re-run internal EPG grabbers"**
3. **Wait 10-15 minutes** for complete download

#### Step 6: Verify Complete Success

**Second run should show full program data**:

```
[INFO]:xmltv: grab took 283 seconds
[INFO]:xmltv: parse took 2 seconds
[INFO]:xmltv: channels   tot=   33 new=    0 mod=    0  ← Channels stable
[INFO]:xmltv: seasons    tot=15249 new=15005 mod=  244  ← Series ✅
[INFO]:xmltv: episodes   tot=11962 new=11810 mod=  152  ← Episodes ✅
[INFO]:xmltv: broadcasts tot=15682 new=15434 mod=  248  ← Programs ✅
```

**Large EPG database save confirms success**:
```
[INFO]:epgdb: queued to save (size 9816663)  ← Large size = full data ✅
[INFO]:epgdb:   broadcasts 15244             ← Programs saved ✅
[INFO]:epgdb: stored (size 1887624)
```

## 🔄 Rollback Procedures

### Simple Rollback (Try First)

If you need to return to your previous EPG grabber:

1. **Disable gracenote2epg** in TVheadend EPG grabber modules
2. **Enable previous grabber** (e.g., tv_grab_zap2epg)  
3. **Wait for next EPG update** or manually trigger
4. **Monitor logs** for successful program data

### Full Rollback with Database Reset

If simple rollback doesn't work:

1. **Follow EPG Database Reset Procedure** (Steps 1-3 above)
2. **Enable previous grabber** instead of gracenote2epg
3. **Complete reset verification** (Steps 4-6)

## 📊 TVheadend-Specific Monitoring

### Log File Locations

```bash
# Standard Linux
tail -f /var/log/tvheadend/tvheadend.log
# OR
journalctl -f -u tvheadend

# Synology DSM7
tail -f /var/packages/tvheadend/var/log/tvheadend.log

# Synology DSM6
tail -f /var/packages/tvheadend/target/var/log/tvheadend.log

# Docker
docker logs -f tvheadend_container_name
```

### Key Log Patterns to Monitor

#### Successful EPG Update
```
[INFO]:epggrab: grabber tv_grab_gracenote2epg started
[INFO]:xmltv: grab took 283 seconds
[INFO]:xmltv: parse took 2 seconds
[INFO]:xmltv: broadcasts tot=15682 new=15434 mod=248
[INFO]:epgdb: queued to save
```

#### Channel Filtering Working
```
[DEBUG]:xmltv: channel 'NBC-HD' found
[DEBUG]:xmltv: channel 'NBC-HD' enabled, processing
```

#### EPG Database Issues
```
[WARNING]:xmltv: failed to parse
[ERROR]:epggrab: no data received
[INFO]:xmltv: episodes tot=0 new=0 mod=0  ← Problem indicator
```

## 🎛️ Channel Configuration

### Channel Mapping and Filtering

When `tvhmatch=true`, gracenote2epg only processes channels that exist in TVheadend:

1. **Automatic filtering**: Only downloads EPG for channels you've configured
2. **Bandwidth savings**: Skips unused channels
3. **Faster processing**: Reduced XMLTV file size

### Channel Number Matching

When `chmatch=true`, gracenote2epg applies intelligent channel matching:

```
Lineup Channel: "5" → TVheadend Channel: "5.1" ✅ Match
Lineup Channel: "NBC" → TVheadend Channel: "NBC-HD" ✅ Match  
Lineup Channel: "Discovery" → TVheadend Channel: "DISC" ✅ Match
```

### Manual Channel Configuration

If automatic matching doesn't work:

1. **TVheadend Web Interface** → **Configuration** → **Channel/EPG** → **Channels**
2. **Find problematic channel**
3. **Set EPG Source** → **XMLTV**
4. **Set XMLTV channel name** to match gracenote2epg output
5. **Save configuration**

## 🔍 Troubleshooting

### gracenote2epg Not Available in EPG Grabber Modules in TVheadend Interface

If you don't see `gracenote2epg` in **Configuration → Channel/EPG → EPG Grabber Modules** (shows as `Internal: XMLTV: North America (tvlistings.gracenote.com using gracenote2epg)`).  Issue may be due to having installed gracenote2epg from sources elsewhere than into /usr/local/gracenote2epg.  Please make sure you follow **[Installation Guide](installation.md)** relatively to source-based installation.

#### For Standard Linux Installations

**Step 1: Verify Installation and Permissions**
```bash
# Test basic installation from your user
which tv_grab_gracenote2epg        # Shold return /usr/local/bin/tv_grab_gracenote2epg if installed from sources
tv_grab_gracenote2epg --version    # Should return the version

# Test TVheadend user access to gracenote2epg
sudo su -s /bin/bash hts -c 'which tv_grab_gracenote2epg'       # Shold return /usr/local/bin/tv_grab_gracenote2epg if installed from sources
sudo su -s /bin/bash hts -c 'tv_grab_gracenote2epg --version'   # Should return the version
```

**Step 2: Restart TVheadend**

Upon start TVheadend does a test-run of all EPG grabbers to confirm they work as expected.  Confirmation of proper initialization of gracenote2epg can be seen in the logs:
```bash
sudo journalctl -u tvheadend | grep -i gracenote
Aug 23 14:22:22 zap2xml tvheadend[72262]: epggrab: module /usr/local/bin/tv_grab_gracenote2epg created
Aug 23 14:22:22 zap2xml tvheadend[72262]: 2025-08-23 14:22:22.089 [   INFO] epggrab: module /usr/local/bin/tv_grab_gracenote2epg created
```

If TVheadend was installed prior to gracenote2epg it may simply need a restart to re-confirm available EPG:
```
sudo systemctl restart tvheadend
```

**Step 3: Update PATH if Needed**

If TVheadend still can't find gracenote2epg as you may have used a custom installation location, such PATH needs to be added to its startup environment.
```bash
# Validate current TVheadend daemon environement:
systemctl show tvheadend -p Environment    # Should show 'Environment='

# Capture current default PATH for hts user:
sudo su -s /bin/bash hts -c 'echo $PATH'
/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin

# Create a TVheadend systemd service directory
sudo mkdir /etc/systemd/system/tvheadend.service.d/

# Add the environment variable using previously captured PATH and including :<MYPATH> as appropriate
sudo tee /etc/systemd/system/tvheadend.service.d/gracenote2epg.conf << EOF
[Service]
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:<CUSTOM_PATH>"
EOF

# Reload systemd and show the new Environment definition
sudo systemctl daemon-reload
systemctl show tvheadend -p Environment
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:<CUSTOM_PATH>

# Restart TVheadend
sudo systemctl restart tvheadend

# Validate it does now find gracenote2epg
sudo journalctl -u tvheadend | grep -i gracenote
Aug 23 14:45:06 zap2xml tvheadend[72661]: 2025-08-23 14:45:06.293 [   INFO] epggrab: module <CUSTOM_PATH>/tv_grab_gracenote2epg created
Aug 23 14:45:06 zap2xml tvheadend[72661]: epggrab: module <CUSTOM_PATH>/tv_grab_gracenote2epg created
```

### Fix Client Connectivity Issues

⚠️ **Common issue**: Clients unable to connect to TVheadend (unrelated to gracenote2epg)

**Solution - Configure Network Access**:
1. **TVheadend Web Interface** → **Configuration** → **Users** → **Access Entries**
2. **Edit user `*`** (anonymous access):
   - **Allowed networks**: Adjust for your network setup:
     ```
     127.0.0.1/32,192.168.1.0/24        # Local network
     127.0.0.1/32,172.16.16.0/24        # Example Docker network
     0.0.0.0/0,::/0                     # All networks (less secure)
     ```
3. **Save Configuration**


## 📚 Related Documentation

- **[Installation Guide](installation.md)** - Installing gracenote2epg software
- **[Configuration Guide](configuration.md)** - Detailed configuration options
- **[General Troubleshooting](troubleshooting.md)** - Non-TVheadend issues
- **[Cache Configuration](cache-retention.md)** - Optimizing performance

## 🆘 Getting Help

For TVheadend-specific issues:

1. **Enable debug logging**: `tv_grab_gracenote2epg --debug --console`
2. **Collect TVheadend logs**: Include relevant log sections in reports
3. **Test outside TVheadend**: Verify gracenote2epg works independently
4. **[Report issues](https://github.com/th0ma7/gracenote2epg/issues)** with:
   - TVheadend version and platform
   - Complete debug output
   - TVheadend log excerpts
   - Your gracenote2epg configuration (remove passwords)
