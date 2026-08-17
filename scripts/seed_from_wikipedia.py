"""Bootstrap `data/ic-coverage.yaml` from the Japanese Wikipedia article.

The article's `対象事業者一覧` table is the only openly licensed, machine-readable
roll-up of every operator in the nationwide mutual-use service; JR East's own
list is a PDF behind a 403.

This is a *seeding* tool, not part of the build. Run it, review the generated
YAML, and merge what you trust into `ic-coverage.yaml` by hand — the build must
not depend on Wikipedia being up or unchanged.

    uv run seed_from_wikipedia.py
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

import ksj
import n02_railway
import n07_bus
from coverage import normalize

ARTICLE = "交通系ICカード全国相互利用サービス"
API = "https://ja.wikipedia.org/w/api.php"

DATA_DIR = Path(__file__).resolve().parent / "data"
OUTPUT = DATA_DIR / "ic-coverage.generated.yaml"

#: Table heading → the area id used in `ic-coverage.yaml`.
AREA_IDS = {
    "kitaca": "kitaca",
    "suica": "suica",
    "pasmo": "pasmo",
    "toica": "toica",
    "manaca": "manaca",
    "icoca": "icoca",
    "pitapa": "pitapa",
    "sugoca": "sugoca",
    "nimoca": "nimoca",
    "はやかけん": "hayakaken",
}


def fetch_wikitext() -> str:
    params = {
        "action": "parse",
        "page": ARTICLE,
        "prop": "wikitext",
        "format": "json",
        "formatversion": "2",
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": ksj.USER_AGENT})
    with urllib.request.urlopen(request, timeout=60, context=ksj.ssl_context()) as response:
        return json.load(response)["parse"]["wikitext"]


def area_id_for(heading: str) -> str | None:
    lowered = heading.lower()
    for needle, area_id in AREA_IDS.items():
        if needle in lowered:
            return area_id
    return None


_REF = re.compile(r"<ref[^>]*?(?:/>|>.*?</ref>)", re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
# `{{font color||yellow|[[X]]}}` marks an operator that runs both trains and
# buses. Matching on "no braces inside" rather than on a fixed parameter count is
# what keeps the named-parameter spelling — `{{Font color|2=yellow|3=[[X]]}}` —
# from swallowing the rest of the cell up to the next template.
_TEMPLATE = re.compile(r"\{\{[Ff]ont ?[Cc]olor\|([^{}]*)\}\}")
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


def extract_operators(cell: str) -> list[str]:
    """Pull operator names out of one table cell.

    Footnotes name the companies contracted to *run* a community bus, which are
    not themselves participants, so they are stripped before parsing.
    """
    cell = _REF.sub("", cell)
    cell = _COMMENT.sub("", cell)
    cell = _TEMPLATE.sub(lambda m: m.group(1).rsplit("|", 1)[-1], cell)

    names: list[str] = []
    for target, display in _LINK.findall(cell):
        # `[[泉観光バス (新潟県)|アイ・ケーアライアンス、泉観光バス]]` is two operators
        # sharing one article.
        for part in (display or target).split("、"):
            part = part.strip()
            if part:
                names.append(part)
    return names


def parse_table(wikitext: str) -> list[tuple[str, str, list[str]]]:
    """Return `(area_id, mode, [operator names])` rows from the coverage table."""
    start = wikitext.index("== 対象事業者一覧")
    end = wikitext.index("== 利用方法")
    section = wikitext[start:end]

    rows: list[tuple[str, str, list[str]]] = []
    current_area: str | None = None

    for block in section.split("\n|-"):
        # A wikitext cell may run over several physical lines — a multi-line
        # `<ref>` inside the operator list does exactly that. Only a line
        # starting with `|` opens a new cell; everything else continues the
        # previous one, and dropping those lines silently loses operators.
        cells: list[str] = []
        for line in block.splitlines():
            if line.startswith("|}"):
                continue
            if line.startswith("|"):
                # `rowspan=2|PASMOエリア` → `PASMOエリア`
                cells.append(re.sub(r"^\s*(?:rowspan|colspan)\s*=\s*\d+\s*\|", "", line[1:]))
            elif cells:
                cells[-1] += "\n" + line
        cells = [cell.strip() for cell in cells]
        if not cells:
            continue

        # A row is either [area, mode, operators] or, under a rowspan, [mode, operators].
        if len(cells) >= 3:
            area = area_id_for(cells[0])
            if area is None:
                continue
            current_area, mode, body = area, cells[1], cells[2]
        elif len(cells) == 2 and current_area:
            mode, body = cells
        else:
            continue

        kind = "rail" if "鉄道" in mode else "bus" if "バス" in mode else None
        if kind is None:
            continue
        rows.append((current_area, kind, extract_operators(body)))

    return rows


def slugify(name: str, taken: set[str]) -> str:
    """A stable, readable id. Japanese names have no useful ASCII form, so fall
    back to a numbered slug rather than inventing a romanization."""
    ascii_ish = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    base = ascii_ish or f"op-{len(taken) + 1:04d}"
    candidate = base
    suffix = 2
    while candidate in taken:
        candidate = f"{base}-{suffix}"
        suffix += 1
    taken.add(candidate)
    return candidate


def source_operator_counts() -> tuple[dict[str, int], dict[str, int]]:
    """Feature counts per raw operator name, so the report can be ranked."""
    rail_dir = ksj.ensure(ksj.N02)
    bus_dir = ksj.ensure(ksj.N07)

    rail: dict[str, int] = {}
    for props in n02_railway.iter_section_properties(rail_dir):
        name = props.get("N02_004")
        if name:
            rail[name] = rail.get(name, 0) + 1

    bus: dict[str, int] = {}
    for name, count in n07_bus.operator_counts(bus_dir).items():
        bus[name] = count

    return rail, bus


def main() -> None:
    print("Fetching Wikipedia article…")
    rows = parse_table(fetch_wikitext())

    merged: dict[str, dict] = {}
    for area, mode, names in rows:
        for name in names:
            key = normalize(name)
            entry = merged.setdefault(
                key, {"name": name, "areas": set(), "modes": set(), "variants": set()}
            )
            entry["areas"].add(area)
            entry["modes"].add(mode)
            entry["variants"].add(name)

    print(f"  {len(merged)} distinct operators across {len(rows)} table rows")

    print("Loading source data for the match report…")
    rail_counts, bus_counts = source_operator_counts()
    source_keys = {normalize(n): n for n in (*rail_counts, *bus_counts)}

    taken: set[str] = set()
    operators = []
    for key, entry in sorted(merged.items(), key=lambda kv: kv[1]["name"]):
        name = entry["name"]
        operators.append(
            {
                "id": slugify(name, taken),
                "name": {"ja": name},
                # A single area is the common case; multiple means the operator is
                # listed under more than one card, which is fine — pick one by hand.
                "area": sorted(entry["areas"])[0],
                "modes": sorted(entry["modes"]),
                "status": "full",
                "match": sorted(entry["variants"]),
                "_matches_source": key in source_keys,
            }
        )

    OUTPUT.write_text(
        "# GENERATED by seed_from_wikipedia.py — review before merging into ic-coverage.yaml.\n"
        + yaml.safe_dump(
            {"operators": operators}, allow_unicode=True, sort_keys=False, width=200
        ),
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT.relative_to(Path.cwd()) if OUTPUT.is_relative_to(Path.cwd()) else OUTPUT}")

    matched = {k for k in merged if k in source_keys}
    print(f"\n{len(matched)}/{len(merged)} Wikipedia operators found in the MLIT data.")

    wiki_keys = set(merged)
    for label, counts in (("RAIL", rail_counts), ("BUS", bus_counts)):
        missing = sorted(
            ((n, c) for n, c in counts.items() if normalize(n) not in wiki_keys),
            key=lambda item: -item[1],
        )
        total = sum(counts.values())
        unlisted = sum(c for _, c in missing)
        print(
            f"\n{label}: {len(missing)}/{len(counts)} operators are not in the "
            f"Wikipedia table ({unlisted}/{total} features, {unlisted / total:.1%})."
        )
        print(f"  Largest unlisted {label.lower()} operators:")
        for name, count in missing[:40]:
            print(f"    {count:7,}  {name}")


if __name__ == "__main__":
    main()
