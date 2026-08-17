"""Resolve a Japanese station, bus stop, line or operator name to an English one.

MLIT publishes no English at all — not in N02, not in N07, not in P11 — so every
English string on the map is either curated here, borrowed from a project that
does publish one, or transliterated. Four sources, tried in this order:

  manual   `data/name-en.yaml`, plus `name.en` from `data/ic-coverage.yaml`
  osm      `name:en` on OpenStreetMap stations, bus stops and route relations
  wikidata English labels of Japanese railway lines
  romaji   Hepburn transliteration by pykakasi, as the floor

The first three need the network. The build must not depend on that, so every
response is cached under `.cache/names/` and re-used until `--refresh`; when a
source is unreachable and uncached we say so and fall through to `romaji`. That
is the same rule `seed_from_wikipedia.py` follows.

Every resolver returns `(english, source)` so `build_tiles.py` can report the
mix, and so the review file `data/name-en.generated.yaml` can show which names
are still only a machine's guess.
"""

from __future__ import annotations

import json
import re
import ssl
import unicodedata
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

import certifi
import yaml

import coverage

SCRIPTS_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPTS_DIR / "data"
CACHE_DIR = SCRIPTS_DIR / ".cache" / "names"
MANUAL_PATH = DATA_DIR / "name-en.yaml"
GENERATED_PATH = DATA_DIR / "name-en.generated.yaml"

USER_AGENT = "foss4g2026-public-transport-map/0.1 (+https://github.com/JinIgarashi/foss4g2026-public-transport-map)"

#: Overpass mirrors, tried in order. The main instance is frequently at
#: capacity, and a build that dies because a volunteer server is busy would be
#: a bad trade for a name suffix.
OVERPASS_ENDPOINTS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"

#: Japan in eight boxes. One nationwide Overpass query for bus stops times out;
#: split like this each chunk answers in tens of seconds, and each is cached
#: separately so a failure halfway through does not throw away what came before.
JAPAN_BBOXES: tuple[tuple[float, float, float, float], ...] = (
    (41.2, 139.0, 46.0, 146.5),  # Hokkaido
    (37.5, 138.5, 41.3, 142.5),  # Tohoku
    (35.4, 138.0, 37.6, 141.2),  # Kanto + Niigata
    (34.5, 135.6, 37.6, 138.1),  # Chubu
    (33.4, 134.0, 35.5, 136.2),  # Kansai + Shikoku east
    (32.5, 130.8, 35.6, 134.1),  # Chugoku + Shikoku west
    (30.5, 128.0, 34.0, 131.5),  # Kyushu
    (23.5, 122.0, 30.6, 131.5),  # Okinawa and the islands
)


def _ssl_context() -> ssl.SSLContext:
    return ssl.create_default_context(cafile=certifi.where())


def _http(url: str, *, data: bytes | None = None, headers: dict | None = None) -> bytes:
    request = urllib.request.Request(
        url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})}
    )
    with urllib.request.urlopen(request, timeout=300, context=_ssl_context()) as response:
        return response.read()


def _cached_json(name: str, fetch, *, refresh: bool) -> dict | None:
    """Fetch `name` once and keep it. `None` means "unavailable, carry on"."""
    path = CACHE_DIR / f"{name}.json"
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))

    try:
        payload = fetch()
    except Exception as error:  # noqa: BLE001 — any failure means "no source"
        print(f"    {name}: unavailable ({error.__class__.__name__}: {error})")
        if path.exists():
            print(f"    {name}: falling back to the cached copy")
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def _overpass(query: str) -> dict:
    last: Exception | None = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            raw = _http(endpoint, data=query.encode("utf-8"))
            return json.loads(raw)
        except Exception as error:  # noqa: BLE001 — try the next mirror
            last = error
    raise RuntimeError(f"every Overpass mirror failed: {last}")


def _wikidata(query: str) -> dict:
    url = f"{WIKIDATA_ENDPOINT}?{urllib.parse.urlencode({'query': query})}"
    raw = _http(url, headers={"Accept": "application/sparql-results+json"})
    return json.loads(raw)


# --------------------------------------------------------------------------- #
# Name normalization
# --------------------------------------------------------------------------- #

_PARENTHETICAL = re.compile(r"[（(][^（）()]*[）)]")
#: OSM route relations spell out the direction — `都営新宿線 : 本八幡→新宿`,
#: `東急田園都市線 (中央林間 -> 渋谷)` — and none of that is part of the name.
_DIRECTION = re.compile(r"\s*[:：].*$|\s*[-=]+>.*$|\s*[→⇒].*$")

_STATION_SUFFIXES = ("停留場", "停留所", "駅前", "駅")
_STOP_SUFFIXES = ("バス停留所", "バス停", "停留所", "停留場")

#: MLIT writes `宇品三丁目`, OSM writes `宇品3丁目`, and they are the same stop.
#: Folding the kanji numeral to a digit is what lets the two meet.
_KANJI_DIGITS = {"〇": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_KANJI_NUMBER = re.compile(r"[〇一二三四五六七八九十]+(?=丁目)")


def _to_arabic(match: re.Match) -> str:
    """Read a kanji numeral below 100 — the only sizes a 丁目 ever reaches."""
    text = match.group()
    if "十" not in text:
        return str(sum(_KANJI_DIGITS.get(ch, 0) for ch in text)) if text else text
    tens, _, ones = text.partition("十")
    return str((_KANJI_DIGITS.get(tens, 1) if tens else 1) * 10 + (_KANJI_DIGITS.get(ones, 0)))


def normalize(name: str | None, *, suffixes: tuple[str, ...] = ()) -> str:
    """Fold a Japanese name to a comparable key.

    NFKC, drop any parenthetical and any direction annotation, drop the trailing
    `駅` / `停留所` that one source writes and the other does not, then remove
    every space and interpunct. `coverage.normalize()` does the same job for
    operator names; this one cannot simply call it because the suffixes and the
    direction annotations are specific to place names.
    """
    if not name:
        return ""
    # Parentheses first: `東急田園都市線 (中央林間 -> 渋谷)` has its direction
    # inside them, and cutting at the arrow first would leave a dangling `(`.
    folded = unicodedata.normalize("NFKC", name)
    folded = _PARENTHETICAL.sub("", folded)
    folded = _DIRECTION.sub("", folded).strip()
    for suffix in suffixes:
        if folded.endswith(suffix) and len(folded) > len(suffix):
            folded = folded[: -len(suffix)]
            break
    folded = _KANJI_NUMBER.sub(_to_arabic, folded)
    return re.sub(r"[\s・]+", "", folded)


def clean_english(name: str) -> str:
    """Tidy an English name borrowed from OSM or Wikidata.

    Direction annotations go the same way as on the Japanese side, and macrons
    are flattened: station signage in Japan is inconsistent about them, and one
    house style reads better than a mix of `Yūrakuchō` and `Yurakucho`.
    """
    cleaned = _PARENTHETICAL.sub("", name)
    cleaned = _DIRECTION.sub("", cleaned).strip()
    decomposed = unicodedata.normalize("NFD", cleaned)
    stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s{2,}", " ", unicodedata.normalize("NFC", stripped)).strip()


# --------------------------------------------------------------------------- #
# Romanization
# --------------------------------------------------------------------------- #

#: Suffixes worth translating rather than transliterating, longest first so
#: `本線` wins over `線`. Without this, `山陽本線` romanizes to `Sanyouhonsen`.
LINE_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("新幹線", " Shinkansen"),
    ("本線", " Main Line"),
    ("支線", " Branch Line"),
    ("線", " Line"),
)

STATION_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("駅", " Station"),
    ("停留場", " Stop"),
)

#: Trailing morphemes that hang off the word before them with a hyphen rather
#: than standing alone: `中電前` is Chuden-mae, never `Chuden Mae`. Their reading
#: still comes from kakasi, because `町` is machi in one name and cho in the next
#: and neither this table nor any other can tell which.
_HYPHENATED = {"前", "口", "入口", "丁目", "町", "通", "橋", "下"}

#: Words that are translated rather than transliterated, because the English
#: they came from is what the sign says: `広島バスセンター` is the Hiroshima Bus
#: Center, not the `Hiroshima Basusentaa`. Longest first — the pattern is an
#: alternation, and `バスセンター` has to win over `バス`.
_TRANSLATED = {
    "バスセンター": "Bus Center",
    "バスターミナル": "Bus Terminal",
    "ジェイアールバス": "JR Bus",
    "ケーブルカー": "Cable Car",
    "ジェイアール": "JR",
    # JR Hokkaido's bus arm spells itself with an interpunct.
    "ジェイ・アール": "JR",
    "モノレール": "Monorail",
    "ターミナル": "Terminal",
    "センター": "Center",
    "タクシー": "Taxi",
    "電鉄": "Electric Railway",
    "鉄道": "Railway",
    "空港": "Airport",
    "バス": "Bus",
}

_TRANSLATED_SPLIT = re.compile(
    f"({'|'.join(sorted(_TRANSLATED, key=len, reverse=True))})"
)

#: Long vowels are written out by kakasi (`toukyou`) but dropped in the
#: romanization Japan actually signposts (`Tokyo`).
_LONG_VOWELS = ("ou", "oo", "uu", "aa")


@cache
def _kakasi():
    import pykakasi  # imported lazily so `--help` works without the dependency

    return pykakasi.kakasi()


def _shorten(word: str) -> str:
    """Collapse written-out long vowels: `toukyou` → `tokyo`, `chuuou` → `chuo`.

    A handful of names lose by this — `井上` is i-no-u-e, where the `ou` spans
    two morae, and comes out `Inoe`. Nothing at the kana level separates that
    from `公園` (kouen → Koen), which is far commoner in stop names, so the
    collapse is unconditional and the rare loser goes in `name-en.yaml`.
    """
    out: list[str] = []
    index = 0
    while index < len(word):
        pair = word[index : index + 2]
        if pair in _LONG_VOWELS:
            out.append(pair[0])
            index += 2
        else:
            out.append(word[index])
            index += 1
    return "".join(out)


def _titlecase(word: str) -> str:
    return word[:1].upper() + word[1:] if word else word


def _tokenize(text: str) -> list[str]:
    """Romanized words for `text`, translating the vocabulary in `_TRANSLATED`.

    Splitting on those words before kakasi sees them is what makes the
    translation possible at all: kakasi merges a katakana run into one token, so
    `広島バスセンター` arrives as `広島` + `バスセンター` and a token-by-token
    lookup would never find the `バス` inside it.
    """
    words: list[str] = []
    for chunk in _TRANSLATED_SPLIT.split(text):
        if not chunk:
            continue
        if chunk in _TRANSLATED:
            words.append(_TRANSLATED[chunk])
            continue
        for token in _kakasi().convert(chunk.replace("・", " ")):
            _append_token(words, token)
    return words


def romanize(name: str, *, suffixes: tuple[tuple[str, str], ...] = ()) -> str:
    """Hepburn transliteration, with a translated suffix where one applies."""
    text = unicodedata.normalize("NFKC", name).strip()
    if not text:
        return ""

    tail = ""
    for japanese, english in suffixes:
        if text.endswith(japanese):
            # A name that is *only* the suffix — Hiroden's `本線` — becomes the
            # translated suffix alone, or `本線` would come out `Hon Line`.
            text, tail = text[: -len(japanese)], english
            if not text:
                return tail.strip()
            break

    return " ".join(w for w in _tokenize(text) if w).strip() + tail


def _append_token(words: list[str], token: dict) -> None:
    """Add one kakasi token to the words built so far."""
    original = token["orig"].strip()
    if not original:
        return
    if original.isascii() and not original.isalpha():
        # Digits and punctuation ride through untouched: `宇品3丁目` has to stay
        # `Ujina 3-chome`, not become `Ujina san-chome`.
        words.append(original)
        return

    reading = _shorten(token["hepburn"].strip())
    if original in _HYPHENATED and words:
        words[-1] = f"{words[-1]}-{reading}"
        return
    words.append(_titlecase(reading))


# --------------------------------------------------------------------------- #
# The name book
# --------------------------------------------------------------------------- #


@dataclass
class _Candidate:
    lon: float
    lat: float
    english: str


@dataclass
class NameBook:
    """Every English name we can find, indexed by normalized Japanese name."""

    manual: dict[str, dict[str, str]] = field(default_factory=dict)
    osm_stations: dict[str, list[_Candidate]] = field(default_factory=dict)
    osm_stops: dict[str, list[_Candidate]] = field(default_factory=dict)
    osm_lines: dict[str, str] = field(default_factory=dict)
    wikidata_lines: dict[str, str] = field(default_factory=dict)
    #: `(kind, source)` → count, reported at the end of a build.
    stats: Counter = field(default_factory=Counter)
    #: Every line resolved this run, for the review file.
    seen_lines: dict[str, tuple[str, str]] = field(default_factory=dict)

    #: How far a same-named OSM feature may sit from the MLIT one, in degrees.
    #: Stations are digitised as long platforms and interchanges sprawl, so they
    #: get ~1 km; bus stops are dense enough that a loose match would steal a
    #: neighbour's name, so they get ~300 m.
    station_tolerance: float = 0.01
    stop_tolerance: float = 0.003

    # -- resolvers ---------------------------------------------------------- #

    def station(self, name_ja: str, lon: float, lat: float) -> tuple[str, str]:
        return self._place(
            name_ja, lon, lat, "station", self.osm_stations, _STATION_SUFFIXES, STATION_SUFFIXES,
            self.station_tolerance,
        )

    def bus_stop(self, name_ja: str, lon: float, lat: float) -> tuple[str, str]:
        return self._place(
            name_ja, lon, lat, "bus_stop", self.osm_stops, _STOP_SUFFIXES, (), self.stop_tolerance
        )

    def operator(self, name_ja: str) -> tuple[str, str]:
        if not name_ja:
            return "", "none"
        manual = self.manual.get("operators", {}).get(name_ja)
        if manual:
            return self._record("operator", "manual", manual)
        # `coverage.normalize` first, or `中国ジェイアールバス（株）` transliterates
        # its corporate form along with its name: `… ( Kabu )`.
        return self._record("operator", "romaji", romanize(coverage.normalize(name_ja)))

    def line(self, name_ja: str) -> tuple[str, str]:
        """English name of a railway line. Cached per name — 553 of them cover
        every one of the 21,933 sections, so this runs 553 times, not 21,933."""
        if not name_ja:
            return "", "none"
        if name_ja in self.seen_lines:
            english, source = self.seen_lines[name_ja]
            self.stats[("line", source)] += 1
            return english, source

        key = normalize(name_ja)
        manual = self.manual.get("lines", {}).get(name_ja)
        if manual:
            english, source = manual, "manual"
        elif key in self.wikidata_lines:
            english, source = self.wikidata_lines[key], "wikidata"
        elif key in self.osm_lines:
            english, source = self.osm_lines[key], "osm"
        else:
            english, source = romanize(name_ja, suffixes=LINE_SUFFIXES), "romaji"

        self.seen_lines[name_ja] = (english, source)
        return self._record("line", source, english)

    # -- internals ---------------------------------------------------------- #

    def _place(
        self,
        name_ja: str,
        lon: float,
        lat: float,
        kind: str,
        index: dict[str, list[_Candidate]],
        strip: tuple[str, ...],
        suffixes: tuple[tuple[str, str], ...],
        tolerance: float,
    ) -> tuple[str, str]:
        if not name_ja:
            return "", "none"

        manual = self.manual.get(f"{kind}s", {}).get(name_ja)
        if manual:
            return self._record(kind, "manual", manual)

        nearest = self._nearest(index.get(normalize(name_ja, suffixes=strip), ()), lon, lat, tolerance)
        if nearest:
            return self._record(kind, "osm", nearest)

        return self._record(kind, "romaji", romanize(name_ja, suffixes=suffixes))

    @staticmethod
    def _nearest(candidates, lon: float, lat: float, tolerance: float) -> str | None:
        """Closest same-named candidate within `tolerance`, or nothing.

        Degrees rather than metres: at Japan's latitudes the error is under 20%
        and the comparison is only ever "is this the same place", which no
        pairing gets wrong by that margin.
        """
        best: tuple[float, str] | None = None
        for candidate in candidates:
            distance = max(abs(candidate.lon - lon) * 0.82, abs(candidate.lat - lat))
            if distance <= tolerance and (best is None or distance < best[0]):
                best = (distance, candidate.english)
        return best[1] if best else None

    def _record(self, kind: str, source: str, english: str) -> tuple[str, str]:
        self.stats[(kind, source)] += 1
        return english, source

    def report(self) -> None:
        print("\nEnglish names by source:")
        kinds = sorted({kind for kind, _ in self.stats})
        for kind in kinds:
            counts = {source: n for (k, source), n in self.stats.items() if k == kind}
            total = sum(counts.values()) or 1
            parts = " ".join(
                f"{source}={count:,} ({count / total:.0%})"
                for source, count in sorted(counts.items(), key=lambda item: -item[1])
            )
            print(f"  {kind:9} {total:>8,}  {parts}")

    def write_line_review(self) -> Path:
        """Dump every line name and where its English came from.

        A review aid like `ic-coverage.generated.yaml`, never a build input: the
        553 line names are few enough to read through, and the ones still marked
        `romaji` are exactly the list worth curating into `name-en.yaml`.
        """
        lines = {
            japanese: {"en": english, "source": source}
            for japanese, (english, source) in sorted(self.seen_lines.items())
        }
        GENERATED_PATH.write_text(
            "# Generated by build_tiles.py — a review aid, never a build input.\n"
            "# Move corrected entries into name-en.yaml under `lines:`.\n"
            + yaml.safe_dump({"lines": lines}, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        return GENERATED_PATH


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

_STATION_QUERY = """[out:json][timeout:240];
nwr["railway"~"^(station|halt|tram_stop)$"]["name:en"]({bbox});
out center tags;
"""

_STOP_QUERY = """[out:json][timeout:240];
nwr["highway"="bus_stop"]["name:en"]({bbox});
out center tags;
"""

_LINE_QUERY = """[out:json][timeout:240];
(
  rel["type"="route_master"]["name:en"]({bbox});
  rel["type"="route"]["route"~"^(train|subway|tram|light_rail|monorail|funicular)$"]["name:en"]({bbox});
);
out tags;
"""

_WIKIDATA_LINE_QUERY = """SELECT ?ja ?en WHERE {
  ?line wdt:P31/wdt:P279* wd:Q728937 ; wdt:P17 wd:Q17 ;
        rdfs:label ?ja , ?en .
  FILTER(lang(?ja)="ja") FILTER(lang(?en)="en")
}
"""


def _elements(kind: str, query: str, *, refresh: bool) -> list[dict]:
    collected: list[dict] = []
    for index, bbox in enumerate(JAPAN_BBOXES):
        payload = _cached_json(
            f"osm-{kind}-{index}",
            lambda bbox=bbox: _overpass(query.format(bbox=",".join(str(v) for v in bbox))),
            refresh=refresh,
        )
        if payload:
            collected.extend(payload.get("elements", []))
    return collected


def _index_places(elements: list[dict], strip: tuple[str, ...]) -> dict[str, list[_Candidate]]:
    index: dict[str, list[_Candidate]] = {}
    for element in elements:
        tags = element.get("tags") or {}
        japanese, english = tags.get("name"), tags.get("name:en")
        if not japanese or not english:
            continue
        centre = element.get("center") or element
        lon, lat = centre.get("lon"), centre.get("lat")
        if lon is None or lat is None:
            continue
        key = normalize(japanese, suffixes=strip)
        if key:
            index.setdefault(key, []).append(
                _Candidate(float(lon), float(lat), clean_english(english))
            )
    return index


def _index_lines(elements: list[dict]) -> dict[str, str]:
    """One English name per line, by majority vote.

    A single line has one relation per direction and often several per operator
    variant, so the same key arrives many times with slightly different English.
    The most frequent spelling is the one the mappers agreed on.
    """
    votes: dict[str, Counter] = {}
    for element in elements:
        tags = element.get("tags") or {}
        japanese, english = tags.get("name"), tags.get("name:en")
        if not japanese or not english:
            continue
        key = normalize(japanese)
        cleaned = clean_english(english)
        if key and cleaned:
            votes.setdefault(key, Counter())[cleaned] += 1
    return {key: counter.most_common(1)[0][0] for key, counter in votes.items()}


def load(*, refresh: bool = False, offline: bool = False) -> NameBook:
    """Assemble the name book, downloading what is missing from the cache."""
    manual = yaml.safe_load(MANUAL_PATH.read_text(encoding="utf-8")) or {} if MANUAL_PATH.exists() else {}
    book = NameBook(manual={key: value or {} for key, value in manual.items() if key != "meta"})

    if offline:
        print("  --offline: transliterating everything OSM and Wikidata would have named")
        return book

    print("  OSM stations…")
    book.osm_stations = _index_places(
        _elements("station", _STATION_QUERY, refresh=refresh), _STATION_SUFFIXES
    )
    print("  OSM bus stops…")
    book.osm_stops = _index_places(_elements("stop", _STOP_QUERY, refresh=refresh), _STOP_SUFFIXES)
    print("  OSM route relations…")
    book.osm_lines = _index_lines(_elements("line", _LINE_QUERY, refresh=refresh))

    print("  Wikidata railway lines…")
    payload = _cached_json(
        "wikidata-lines", lambda: _wikidata(_WIKIDATA_LINE_QUERY), refresh=refresh
    )
    if payload:
        for row in payload.get("results", {}).get("bindings", []):
            key = normalize(row["ja"]["value"])
            english = clean_english(row["en"]["value"])
            if key and english:
                book.wikidata_lines.setdefault(key, english)

    print(
        f"    {len(book.osm_stations):,} station names, {len(book.osm_stops):,} bus stop names, "
        f"{len(book.osm_lines):,} OSM lines, {len(book.wikidata_lines):,} Wikidata lines"
    )
    return book
