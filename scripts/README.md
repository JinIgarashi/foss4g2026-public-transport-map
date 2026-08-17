# Tile pipeline

Turns MLIT's railway, bus route and bus stop data, plus a curated IC-card
acceptance table and English names gathered from OpenStreetMap and Wikidata,
into the four PMTiles archives the web map reads.

```bash
cd scripts
uv run build_tiles.py                 # reuse cached downloads
uv run build_tiles.py --refresh       # re-download from MLIT, OSM and Wikidata first
uv run build_tiles.py --skip-bus      # railways only — a ~30s loop instead of ~8min
uv run build_tiles.py --offline-names # no network for names: transliterate everything
```

Requires [tippecanoe](https://github.com/felt/tippecanoe) on `PATH`
(`brew install tippecanoe`) and [uv](https://docs.astral.sh/uv/).

Outputs, all overwritten in place:

| Path                           | Size    | Contents                                    |
| ------------------------------ | ------- | ------------------------------------------- |
| `static/tiles/railway.pmtiles` | ~4 MB   | 21,933 railway sections                     |
| `static/tiles/station.pmtiles` | ~3 MB   | 9,046 stations, interchanges merged         |
| `static/tiles/bus.pmtiles`     | ~25 MB  | 353,453 routes dissolved to ~1,750 features |
| `static/tiles/busstop.pmtiles` | ~24 MB  | 278,515 bus stops, one per stop × operator  |
| `src/lib/data/operators.json`  | ~250 KB | Operator index for the highlight control    |
| `src/lib/data/datasets.json`   | ~1 KB   | Editions and sources for the About dialog   |
| `data/name-en.generated.yaml`  | ~40 KB  | Line-name review aid — never a build input  |

`--skip-bus` leaves `operators.json` untouched: the index is built from the
feature counts of the run that writes it, so a railways-only run would drop the
1,400 bus operators out of the map's filter while their routes are still on it.

**The PMTiles are committed to the repository.** They change roughly once a year
and rebuilding them needs a 320 MB download, so a checkout that can serve the map
beats a smaller repository. Regenerate them only when the data or the coverage
table actually changes, and say why in the commit message.

## Data sources

- **N02 railway data** — ships a UTF-8 GeoJSON next to the shapefile, in
  EPSG:6668 with lon/lat ordering, so `n02_railway.py` reads it directly.
- **N07 bus route data** — GML only, and GDAL reads _zero_ layers from it: routes
  reference their geometry by `xlink:href` rather than inlining it, and none of
  the `GML_SKIP_RESOLVE_ELEMS` modes handle that shape. `n07_bus.py` therefore
  streams the XML with `iterparse`; at 280 MB expanded, building a DOM would need
  several gigabytes.

- **P11 bus stop data** — a ZIP of 47 prefectural ZIPs, each a GML shaped like
  N07: the stop points are inline but referenced by id, so `p11_busstop.py`
  streams them the same way. FY2022, the same edition as N07, which is why the
  operator names in the two datasets match without extra aliasing.

All three are published by MLIT under CC BY 4.0.

## English names

MLIT publishes none, so `english.py` resolves every English string, in this
order: `data/name-en.yaml` (hand-curated), `name:en` from OpenStreetMap, English
labels of railway lines from Wikidata, and finally Hepburn transliteration by
pykakasi. Responses are cached under `.cache/names/` and re-used until
`--refresh`; if a source is unreachable and uncached the build says so and falls
back to transliteration rather than failing.

`data/name-en.generated.yaml` lists every line name with the English we resolved
and where it came from. It is a review aid in the mould of
`ic-coverage.generated.yaml` — entries still marked `source: romaji` are the
ones worth correcting into `data/name-en.yaml`.

## The acceptance table

`data/ic-coverage.yaml` is the part of this pipeline that cannot be derived, and
the file worth reviewing carefully. It says, per operator, whether the ten
mutually usable IC cards are accepted — `full`, `partial`, `none` or `unknown` —
with per-line overrides for the six JR companies, whose coverage is defined by
area rather than by company.

It was seeded from the `対象事業者一覧` table of the Japanese Wikipedia article on
the nationwide mutual-use service, which is the only openly licensed
machine-readable roll-up of the ~330 participating operators (JR East's own list
is a PDF behind an HTTP 403). Regenerate the seed with:

```bash
uv run seed_from_wikipedia.py
```

That writes `data/ic-coverage.generated.yaml` and prints a match report. It is a
review aid, never part of the build — the build must not depend on Wikipedia
being reachable or unchanged.

### Why absent means "not accepted"

`meta.unlisted_status` maps both modes to `none`. The participant list is
published as exhaustive, so an operator missing from it does not accept the
cards. The risk is not the logic but the _matching_: a name we fail to match
would be shown as "not accepted" when it is really a participant. Three things
bound that risk, and re-running them is how you re-do the review:

1. `coverage.normalize()` folds away corporate forms (`（株）`, `株式会社`) and
   Wikipedia's disambiguating suffixes (`関東自動車 (栃木県)`).
2. `coverage.split_joint()` splits the `A（株）・B（株）` spelling MLIT uses for a
   jointly operated route and resolves each operator separately — that alone
   accounts for about 70 of the busiest bus entries. A route counts as usable
   only when every operator on it accepts the cards, because the traveller does
   not choose which company's bus turns up.
3. A **near-miss scan**: for every unmatched source name, list the participants
   whose normalized name contains it or is contained by it. All 177 rail
   operators and all 91 bus near-misses were reviewed this way; the real renames
   went into `data/operator-aliases.yaml`, and the false ones are listed at the
   bottom of that file with the reason, so nobody re-adds them.

Anything still unmatched gets a synthetic operator with a stable
`x-<md5>` id, so it is still clickable and still highlightable on the map.

Operators we genuinely could not resolve either way — Utsunomiya's community
buses, for instance — carry an explicit `status: unknown` entry and render grey.
Grey means "we don't know", never "your card will be rejected".

## Files

| File                     | Role                                                         |
| ------------------------ | ------------------------------------------------------------ |
| `build_tiles.py`         | Orchestrator and entry point                                 |
| `ksj.py`                 | Downloads and unpacks the MLIT archives into `.cache/`       |
| `coverage.py`            | Name normalization, joint-route splitting, status resolution |
| `english.py`             | Japanese → English names, and where each one came from       |
| `n02_railway.py`         | N02 GeoJSON → tagged railway and station GeoJSONL            |
| `n07_bus.py`             | N07 GML → tagged, operator-dissolved bus GeoJSONL            |
| `p11_busstop.py`         | P11 GML → tagged bus stop GeoJSONL                           |
| `seed_from_wikipedia.py` | Seeding and review aid, not part of the build                |

## Tile attributes

Short keys, because they ride in every tile and the map style reads them by name.
`src/lib/map/status.ts` and `src/lib/map/operators.ts` are the other half of this
contract.

| Key  | Meaning                                                           |
| ---- | ----------------------------------------------------------------- |
| `st` | Acceptance: `0` none, `1` full, `2` partial, `3` unknown          |
| `op` | Operator ids, packed as `\|a\|b\|` — see `Coverage.operator_key`  |
| `nm` | Operator name as MLIT writes it (place name on station / busstop) |
| `ne` | English `nm` — station and busstop layers                         |
| `cp` | Operator name — station and busstop layers, where `nm` is taken   |
| `ln` | Line name (railway and station layers)                            |
| `le` | English `ln` — railway and station layers                         |
| `rt` | Route names through a bus stop, `、`-joined, first six only       |
| `rn` | How many further routes `rt` left out                             |
| `ar` | IC card area id: `suica`, `icoca`, …                              |
| `kd` | N02 railway class code                                            |
| `it` | N02 institution type code                                         |
