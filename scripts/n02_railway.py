"""Turn the N02 railway dataset into IC-tagged GeoJSON Lines.

N02 ships a UTF-8 GeoJSON next to the shapefile, already in EPSG:6668 with
lon/lat ordering, so there is nothing to reproject.

Attributes (see the MLIT product spec):
  N02_001  railway class code       N02_004  operating company
  N02_002  institution type code    N02_005  station name (Station.geojson only)
  N02_003  line name
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from coverage import STATUS_CODE, Coverage
from english import NameBook


def _geojson(root: Path, name: str) -> Path:
    path = root / "UTF-8" / f"{root.name.removesuffix('_GML')}_{name}.geojson"
    if not path.exists():
        raise FileNotFoundError(f"expected {path} in the N02 archive")
    return path


def _features(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)["features"]


def iter_section_properties(root: Path) -> Iterator[dict]:
    """Properties of every railway section — used by the seeding report."""
    for feature in _features(_geojson(root, "RailroadSection")):
        yield feature["properties"]


def _write(path: Path, features: Iterator[dict]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as out:
        for feature in features:
            out.write(json.dumps(feature, ensure_ascii=False, separators=(",", ":")))
            out.write("\n")
            count += 1
    return count


def build_sections(root: Path, coverage: Coverage, names: NameBook, destination: Path) -> int:
    """Write railway sections with an `st` acceptance code attached."""

    def features() -> Iterator[dict]:
        for feature in _features(_geojson(root, "RailroadSection")):
            props = feature["properties"]
            company, line = props.get("N02_004"), props.get("N02_003")
            status, operators = coverage.resolve(company, line, mode="rail")
            for operator in operators:
                operator.rail_features += 1
                operator.extend_bbox(feature["geometry"]["coordinates"])

            yield {
                "type": "Feature",
                # Short keys: these ride in every tile, and the style reads them
                # by name, so the saving is real and the mapping is documented
                # here and in `src/lib/map/layers.ts`.
                "properties": {
                    "st": STATUS_CODE[status],
                    "op": coverage.operator_key(operators),
                    "nm": company or "",
                    "ln": line or "",
                    "le": names.line(line or "")[0],
                    "ar": next((o.area for o in operators if o.area), "") or "",
                    "kd": props.get("N02_001") or "",
                    "it": props.get("N02_002") or "",
                },
                "geometry": feature["geometry"],
            }

    return _write(destination, features())


def build_stations(root: Path, coverage: Coverage, names: NameBook, destination: Path) -> int:
    """Write stations with the same acceptance code as their line."""

    def features() -> Iterator[dict]:
        for feature in _features(_geojson(root, "Station")):
            props = feature["properties"]
            company, line = props.get("N02_004"), props.get("N02_003")
            status, operators = coverage.resolve(company, line, mode="rail")

            geometry = feature["geometry"]
            # Stations are digitised as the platform centreline, not a point.
            # A label needs a point, so collapse to the middle vertex.
            if geometry["type"] == "LineString":
                coords = geometry["coordinates"]
                geometry = {"type": "Point", "coordinates": coords[len(coords) // 2]}

            name = props.get("N02_005") or ""
            longitude, latitude = geometry["coordinates"][0], geometry["coordinates"][1]

            yield {
                "type": "Feature",
                "properties": {
                    "st": STATUS_CODE[status],
                    "op": coverage.operator_key(operators),
                    "nm": name,
                    "ne": names.station(name, longitude, latitude)[0],
                    "cp": company or "",
                    "ln": line or "",
                    "le": names.line(line or "")[0],
                    "ar": next((o.area for o in operators if o.area), "") or "",
                    # Stations 300 m apart sharing a name are one interchange.
                    # `unique()` below keeps one per group and this key is
                    # dropped before tiling — the map never reads it.
                    "gc": props.get("N02_005g") or "",
                },
                "geometry": geometry,
            }

    # Deduplicate interchanges: keep the first station of each group.
    def unique() -> Iterator[dict]:
        seen: set[str] = set()
        for feature in features():
            group = feature["properties"].pop("gc")
            if group:
                if group in seen:
                    continue
                seen.add(group)
            yield feature

    return _write(destination, unique())
