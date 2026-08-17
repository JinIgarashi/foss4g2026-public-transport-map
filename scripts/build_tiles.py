"""Build the PMTiles the web map reads, plus the operator index it searches.

    uv run build_tiles.py            # reuse cached MLIT downloads
    uv run build_tiles.py --refresh  # re-download them first
    uv run build_tiles.py --skip-bus # railways only, for a quick loop

Outputs (all overwritten in place):
    static/tiles/railway.pmtiles
    static/tiles/station.pmtiles
    static/tiles/bus.pmtiles
    src/lib/data/operators.json
    src/lib/data/datasets.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import coverage as coverage_module
import ksj
import n02_railway
import n07_bus

SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPTS_DIR.parent
TILES_DIR = PROJECT_DIR / "static" / "tiles"
APP_DATA_DIR = PROJECT_DIR / "src" / "lib" / "data"

#: Shared tippecanoe flags. `-Z0` so the nationwide picture is there at the
#: opening zoom, `-z12` because neither dataset is drawn accurately enough to
#: reward more, and the drop/extend pair keeps dense city centres from blowing
#: the per-tile budget.
LINE_FLAGS = [
    "-Z0",
    "-z12",
    "--drop-densest-as-needed",
    "--extend-zooms-if-still-dropping",
    "--force",
]


def run_tippecanoe(source: Path, output: Path, layer: str, extra: list[str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    command = ["tippecanoe", "-o", str(output), "-l", layer, *extra, str(source)]
    print(f"    tippecanoe -l {layer} → {output.name}")
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise SystemExit(f"tippecanoe failed for {layer}")


def human(path: Path) -> str:
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f}{unit}"
        size /= 1024
    return ""


def write_operator_index(cov: coverage_module.Coverage) -> Path:
    """The table the operator filter searches and the popup reads names from.

    Only operators the tiles actually reference are included — the participant
    list names ferries and taxi companies that never appear in N02/N07.
    """
    entries = []
    for operator in cov.operators.values():
        if operator.rail_features == 0 and operator.bus_features == 0:
            continue
        entry: dict = {
            "id": operator.id,
            "ja": operator.name_ja,
            "status": operator.status,
            "modes": [
                mode
                for mode, count in (("rail", operator.rail_features), ("bus", operator.bus_features))
                if count
            ],
        }
        if operator.name_en:
            entry["en"] = operator.name_en
        if operator.area:
            entry["area"] = operator.area
        if operator.note_en or operator.note_ja:
            entry["note"] = {"en": operator.note_en, "ja": operator.note_ja}
        if operator.bbox:
            # 4 decimals is ~10 m, far finer than a `fitBounds` needs, and it
            # keeps this file from growing by a kilobyte per hundred operators.
            entry["bbox"] = [round(value, 4) for value in operator.bbox]
        entries.append(entry)

    entries.sort(key=lambda e: (e.get("en") or e["ja"]))

    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = APP_DATA_DIR / "operators.json"
    path.write_text(
        json.dumps(
            {"areas": cov.areas, "operators": entries}, ensure_ascii=False, separators=(",", ":")
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def write_dataset_metadata() -> Path:
    """Editions and licences, so the About dialog cannot drift from the tiles.

    Keyed off the tiles present on disk rather than off this run's flags: a
    `--skip-bus` pass must not drop the bus dataset from the credits while
    `bus.pmtiles` is still there and still being served.
    """
    include_bus = (TILES_DIR / "bus.pmtiles").exists()
    datasets = [
        {
            "id": dataset.key,
            "label": {"en": dataset.label_en, "ja": dataset.label_ja},
            "edition": {"en": dataset.edition_en, "ja": dataset.edition_ja},
            "url": dataset.url,
        }
        for dataset in (ksj.N02, *((ksj.N07,) if include_bus else ()))
    ]
    coverage_meta = coverage_module.load().meta
    path = APP_DATA_DIR / "datasets.json"
    path.write_text(
        json.dumps(
            {
                "datasets": datasets,
                "icSourceDate": coverage_meta.get("source_date"),
                "icReferences": coverage_meta.get("references", []),
            },
            ensure_ascii=False,
            indent="\t",
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def report(cov: coverage_module.Coverage, counts: dict[str, dict[int, int]]) -> None:
    print("\nAcceptance breakdown (features):")
    for layer, histogram in counts.items():
        total = sum(histogram.values()) or 1
        parts = " ".join(
            f"{coverage_module.STATUS_NAME[code]}={histogram.get(code, 0):,}"
            f" ({histogram.get(code, 0) / total:.0%})"
            for code in sorted(histogram)
        )
        print(f"  {layer:8} {total:>8,}  {parts}")

    if cov.unmatched:
        listed = sorted(cov.unmatched.items(), key=lambda item: -item[1])
        total = sum(cov.unmatched.values())
        print(
            f"\n{len(listed)} operator names fell back to `unlisted_status` "
            f"({total:,} features). Largest:"
        )
        for name, count in listed[:15]:
            print(f"    {count:7,}  {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-download the MLIT archives")
    parser.add_argument("--skip-bus", action="store_true", help="skip the slow bus dataset")
    args = parser.parse_args()

    if shutil.which("tippecanoe") is None:
        raise SystemExit("tippecanoe is not on PATH — see scripts/README.md")

    print("Loading the IC coverage table…")
    cov = coverage_module.load()
    print(f"  {len(cov.operators)} curated operators, {len(cov.areas)} card areas")

    counts: dict[str, dict[int, int]] = {}
    TILES_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)

        print("\nRailways (N02)…")
        n02_root = ksj.ensure(ksj.N02, refresh=args.refresh)

        sections = work / "railway.geojsonl"
        total = n02_railway.build_sections(n02_root, cov, sections)
        print(f"    {total:,} sections")
        counts["railway"] = _histogram(sections)
        run_tippecanoe(sections, TILES_DIR / "railway.pmtiles", "railway", LINE_FLAGS)

        stations = work / "station.geojsonl"
        total = n02_railway.build_stations(n02_root, cov, stations)
        print(f"    {total:,} stations (interchanges merged)")
        counts["station"] = _histogram(stations)
        run_tippecanoe(
            stations,
            TILES_DIR / "station.pmtiles",
            "station",
            # Stations only become readable once individual lines are, so there
            # is nothing to gain below z8. `-r1` keeps every station at the zooms
            # where they are shown rather than thinning them by density.
            ["-Z8", "-z13", "-r1", "--force"],
        )

        if not args.skip_bus:
            print("\nBus routes (N07)…")
            n07_root = ksj.ensure(ksj.N07, refresh=args.refresh)
            routes = work / "bus.geojsonl"
            total = n07_bus.build_routes(n07_root, cov, routes)
            print(f"    {total:,} features after dissolving by operator")
            counts["bus"] = _histogram(routes)
            run_tippecanoe(routes, TILES_DIR / "bus.pmtiles", "bus", LINE_FLAGS)

    index = write_operator_index(cov)
    metadata = write_dataset_metadata()

    report(cov, counts)

    print("\nOutputs:")
    for path in sorted(TILES_DIR.glob("*.pmtiles")) + [index, metadata]:
        print(f"  {human(path):>8}  {path.relative_to(PROJECT_DIR)}")


def _histogram(path: Path) -> dict[int, int]:
    histogram: dict[int, int] = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            status = json.loads(line)["properties"]["st"]
            histogram[status] = histogram.get(status, 0) + 1
    return histogram


if __name__ == "__main__":
    main()
