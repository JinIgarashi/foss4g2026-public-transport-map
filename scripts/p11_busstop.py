"""Turn the P11 bus stop GML into IC-tagged GeoJSON Lines.

P11 is one GML per prefecture, and each is shaped like N07: the stop references
its geometry by id (`<ksj:loc xlink:href="#n1"/>`) rather than inlining it, so
GDAL is no help and we stream the XML ourselves. The points are small enough to
hold in memory one prefecture at a time.

    <gml:Point gml:id="n1"><gml:pos>35.08289319 132.90474387</gml:pos></gml:Point>
    <ksj:BusStop gml:id="bs1">
      <ksj:loc xlink:href="#n1"/>   geometry reference
      <ksj:bsn>篠原口</ksj:bsn>      stop name          → nm
      <ksj:boc>奥出雲交通（株）</ksj:boc>  operator name  → cp, and the IC lookup
      <ksj:bri>                      one block per route through the stop
        <ksj:brn>阿井・高野線</ksj:brn>   route name       → rt
        <ksj:brt>1</ksj:brt>            1 private / 2 public / 3 community / 4 demand
      </ksj:bri>
    </ksj:BusStop>

One `BusStop` carries exactly one operator, so a stop served by two companies
appears twice — which is what we want, because the two records can differ in IC
acceptance and each gets its own colour.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator
import xml.etree.ElementTree as ET

from coverage import STATUS_CODE, Coverage
from english import NameBook

XLINK_HREF = "{http://www.w3.org/1999/xlink}href"

#: ~1 m at 6 decimals, the same trim `n07_bus.py` applies.
PRECISION = 6

#: How many route names ride along per stop. A Tokyo terminal lists dozens, and
#: past the first handful they stop being orientation and start being tile
#: weight — the popup says "and N more" instead.
MAX_ROUTES = 6


def _gml_paths(root: Path) -> list[Path]:
    paths = sorted(p for p in root.rglob("P11-*.xml") if not p.name.startswith("KS-META"))
    if not paths:
        raise FileNotFoundError(f"no P11 GML found under {root}")
    return paths


def _parse(path: Path) -> Iterator[tuple[str, str, list[str], list[float]]]:
    """Yield `(stop name, operator, route names, [lon, lat])` for one prefecture.

    Every `gml:Point` precedes every `ksj:BusStop` in the files MLIT ships, so a
    single forward pass resolves each reference. A stop whose point has not been
    seen is counted and reported rather than silently dropped — that would mean
    the layout changed and this parser needs a second pass.
    """
    points: dict[str, list[float]] = {}
    dangling = 0

    for _, element in ET.iterparse(path, events=("end",)):
        tag = element.tag.rsplit("}", 1)[-1]

        if tag == "Point":
            point_id = next(
                (v for k, v in element.attrib.items() if k.rsplit("}", 1)[-1] == "id"), None
            )
            pos = element.find("{*}pos")
            if point_id and pos is not None and pos.text:
                latitude, longitude = (float(v) for v in pos.text.split()[:2])
                points[point_id] = [round(longitude, PRECISION), round(latitude, PRECISION)]
            element.clear()

        elif tag == "BusStop":
            loc = element.find("{*}loc")
            href = (loc.get(XLINK_HREF) if loc is not None else "") or ""
            coordinates = points.get(href.lstrip("#"))
            if coordinates:
                name = element.findtext("{*}bsn") or ""
                operator = element.findtext("{*}boc") or ""
                routes = [
                    text.strip()
                    for text in (block.findtext("{*}brn") for block in element.findall("{*}bri"))
                    if text and text.strip()
                ]
                yield name.strip(), operator.strip(), routes, coordinates
            else:
                dangling += 1
            element.clear()

    if dangling:
        print(f"    {path.name}: {dangling:,} stops referenced a point we never saw")


def build_stops(root: Path, coverage: Coverage, names: NameBook, destination: Path) -> int:
    """Write bus stops with the same `st` acceptance code their operator gets."""
    count = 0
    with destination.open("w", encoding="utf-8") as out:
        for path in _gml_paths(root):
            for name, operator_name, routes, coordinates in _parse(path):
                status, operators = coverage.resolve(operator_name, mode="bus")
                # Deliberately no `bus_features` or `extend_bbox` here: N07 owns
                # both, and counting a stop as a route would inflate the operator
                # index while `--skip-bus` would leave it inconsistent.

                unique_routes: list[str] = []
                for route in routes:
                    if route not in unique_routes:
                        unique_routes.append(route)

                feature = {
                    "type": "Feature",
                    "properties": {
                        "st": STATUS_CODE[status],
                        "op": coverage.operator_key(operators),
                        "nm": name,
                        "ne": names.bus_stop(name, coordinates[0], coordinates[1])[0],
                        "cp": operator_name,
                        "rt": "、".join(unique_routes[:MAX_ROUTES]),
                        # How many were cut, so the popup can say so honestly.
                        "rn": max(0, len(unique_routes) - MAX_ROUTES),
                        "ar": next((o.area for o in operators if o.area), "") or "",
                    },
                    "geometry": {"type": "Point", "coordinates": coordinates},
                }
                out.write(json.dumps(feature, ensure_ascii=False, separators=(",", ":")))
                out.write("\n")
                count += 1
    return count
