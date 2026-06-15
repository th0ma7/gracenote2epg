# Program metadata: source fields and XMLTV mapping

Analysis of the fields available in the downloaded Gracenote JSON (guide blocks
and series/overviewDetails) versus what the generated XMLTV currently emits, and
the candidates for enrichment.

## Sources

- **Guide block** (`api/grid`, cached `YYYYMMDDHH.json.gz`): `channels[]` →
  per-channel metadata + `events[]` → per-airing data + `events[].program{}`.
- **Series details** (`api/program/overviewDetails`, cached `series/<id>.json`):
  series-level metadata + `overviewTab.{cast,crew}` + `upcomingEpisodeTab[]`
  (per-episode synopsis, ratings, flags, original air date, …).

## Currently emitted XMLTV

`title`, `sub-title`, `desc`, `credits` (cast only, movies only), `date`,
`category`, `language`, `length`, `icon` (program image), `country`,
`episode-num` ×3, `video`, `audio`, `previously-shown`, `premiere`,
`last-chance`, `new`, `subtitles`, `rating`, `star-rating`.

## Field inventory and status

| Source field | Where | Parsed to | Emitted? | Notes / candidate |
|---|---|---|---|---|
| startTime/endTime/duration | event | epstart/epend/eplength | ✅ | |
| program.title/episodeTitle | event | epshow/eptitle | ✅ | |
| program.season/episode | event | epsn/epen | ✅ | |
| program.releaseYear | event | epyear | ✅ | |
| rating, flag, tags | event | eprating/epflag/eptags | ✅ | |
| filter | event | epfilter | ✅ | |
| shortDesc/longDesc | program | epdesc | ✅ | |
| thumbnail (event) | event | epthumb | ✅ (icon) | also → `<image type="still">` |
| seriesDescription | series | epseriesdesc | ✅ | generic for episodes |
| seriesImage | series | epimage | ✅ (icon) | → `<image type="poster">` |
| **backgroundImage** | series | **epfan** | ❌ **parsed, never emitted** | → `<image type="backdrop">` |
| seriesGenres | series | epgenres | ✅ | |
| **overviewTab.cast** | series | epcredits | ⚠️ **movies only** | enable for TV too |
| **overviewTab.crew** | series | — | ❌ **never captured** | directors/writers/producers |
| **upcomingEpisodeTab[].synopsis** | series | — | ❌ | per-episode desc (more specific) |
| cast/crew[].priority | series | — | ❌ | billing order for credits |
| displayRating | series | — | ❌ | sometimes richer than guide rating |
| programGenres (episode) | series | — | ❌ | episode-specific genres |
| isNew/isLive/isPremier/isFinale | series | — | ❌ | fills gaps in guide flags |
| stationGenres / affiliateCallSign | channel | — | ❌ | (channel DTD has no category) |
| program.isGeneric / program.id | program | — | ❌ | internal use only |

## Images: the DTD-valid way to type them

XMLTV `<icon>` only allows `src`/`width`/`height` — adding `type=` to `<icon>`
**fails** DTD validation. The DTD instead provides a dedicated `<image>` element
(already used for `<image type="person">` in credits):

```
<!ELEMENT image (#PCDATA)>
<!ATTLIST image type ( poster | backdrop | still | person | character ) #IMPLIED>
<!ATTLIST image size ( 1 | 2 | 3 ) #IMPLIED>
<!ATTLIST image orient ( P | L ) #IMPLIED>
```

`<programme>` allows `image*` (at the end of the content model). So:

| Gracenote image | XMLTV |
|---|---|
| seriesImage (poster, `_v_`/`_b_`) | `<image type="poster">…</image>` |
| backgroundImage (16:9, `_i_`/`_k_`) | `<image type="backdrop">…</image>` |
| event thumbnail (episode) | `<image type="still">…</image>` |

Verified DTD-valid (`xmllint --dtdvalid`). Keep the existing `<icon>` for
consumers that only read `<icon>`. Application-level support for `<image>`
(e.g. TVheadend) should be confirmed on the target.

## Recommended PR scope (effort/value)

1. **Credits**: capture `crew` and merge with `cast`; enable for TV series, not
   just movies. Biggest visible win (directors/writers in the guide).
2. **Typed images**: emit `<image type="poster|backdrop|still">` from
   epimage/epfan/epthumb (epfan already parsed). Keep `<icon>`.
3. **Per-episode synopsis**: prefer `upcomingEpisodeTab[].synopsis` over the
   generic series description for episodic `<desc>`.
4. Optional: credit `priority` ordering, `displayRating`.

## Future: configurable image source (separate PR)

`tvtv.ca` (the current host) rate-limits image serving. The image **codes**
(`pNNNNN_x_hN_xx`) are TMS asset IDs served identically by several mirror
hosts, so only the base URL needs to change:

| Base URL | Notes |
|---|---|
| `https://www.tvtv.ca/gn/pi/assets` | current default; rate-limited |
| `https://tmsimg.fancybits.co/assets` | used by zap2epg (current) |
| `https://zap2it.tmsimg.com/assets` | original TMS (zap2epg fallback) |
| `https://dshm.tmsimg.com/assets` | older mirror |

(See zap2epg commit `b8a81f0`, which switched `dshm.tmsimg.com` →
`tmsimg.fancybits.co`.)

Proposed approach for a follow-up PR:

- A config setting (e.g. `imageurl`) holding the base URL — accepting either a
  known alias or a full URL — so the host lives **outside the code** (in the
  config file). Today `ASSETS_BASE_URL` is a single constant in
  `xmltv/generator.py`, so the writers (`<icon>` and `<image>`) only need to
  read the configured value instead.
- Known aliases → base URLs can sit in a small data/config table, not hardcoded
  in the writers.
- **Multiple sources in one XMLTV?** The DTD allows repeating `<icon>`/`<image>`,
  so the same image *could* be emitted from several hosts — but that bloats the
  output and consumers handle duplicates inconsistently. A single configurable
  source is preferable; document the alternatives so users can switch.
