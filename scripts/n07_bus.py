"""Turn the N07 bus route GML into IC-tagged GeoJSON Lines.

N07 is distributed as GML only, and GDAL reads zero layers from it: the route
features carry their geometry by reference (`<ksj:loc xlink:href="#cv1"/>`)
rather than inline, and the `GML_SKIP_RESOLVE_ELEMS` resolvers do not handle
this shape. So we stream the XML ourselves.

The file is ~280 MB expanded with ~353k routes, hence `iterparse` plus
`element.clear()` — building a DOM would need several GB.

Attributes: `ksj:boc` is the operator name (a municipality for community buses);
there is no line name, so bus acceptance is necessarily per-operator.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Iterator

from coverage import STATUS_CODE, Coverage

XLINK_HREF = "{http://www.w3.org/1999/xlink}href"

#: Coordinates are ~1 m apart at 6 decimals, well under the precision that
#: survives tiling, and trimming them shaves a third off the intermediate file.
PRECISION = 6

#: Cap on line parts per emitted feature. Dissolving to one MultiLineString per
#: operator would give Kanachu a single 5,500-part feature that tippecanoe has to
#: carry into every tile it touches; chunking keeps features tile-sized while
#: still collapsing 353k routes down to a few thousand features.
CHUNK = 500


def _gml_path(root: Path) -> Path:
    candidates = sorted(p for p in root.glob("N07-*.xml") if not p.name.startswith("KS-META"))
    if not candidates:
        raise FileNotFoundError(f"no N07 GML found under {root}")
    return candidates[0]


def _parse(path: Path) -> tuple[dict[str, list[list[float]]], list[tuple[str, str]]]:
    """Return `(curve id → coordinates, [(curve id, operator)])`."""
    curves: dict[str, list[list[float]]] = {}
    routes: list[tuple[str, str]] = []

    for _, element in ET.iterparse(path, events=("end",)):
        tag = element.tag.rsplit("}", 1)[-1]

        if tag == "Curve":
            curve_id = next(
                (v for k, v in element.attrib.items() if k.rsplit("}", 1)[-1] == "id"), None
            )
            pos_list = element.find(".//{*}posList")
            if curve_id and pos_list is not None and pos_list.text:
                numbers = pos_list.text.split()
                # GML posList here is latitude longitude; GeoJSON wants the reverse.
                curves[curve_id] = [
                    [round(float(numbers[i + 1]), PRECISION), round(float(numbers[i]), PRECISION)]
                    for i in range(0, len(numbers) - 1, 2)
                ]
            element.clear()

        elif tag == "BusRoute":
            loc = element.find("{*}loc")
            boc = element.find("{*}boc")
            href = (loc.get(XLINK_HREF) if loc is not None else None) or ""
            if href:
                routes.append((href.lstrip("#"), (boc.text or "").strip() if boc is not None else ""))
            element.clear()

    return curves, routes


def operator_counts(root: Path) -> dict[str, int]:
    """Route counts per raw operator name — used by the seeding report."""
    counts: dict[str, int] = defaultdict(int)
    for _, element in ET.iterparse(_gml_path(root), events=("end",)):
        if element.tag.rsplit("}", 1)[-1] == "BusRoute":
            boc = element.find("{*}boc")
            if boc is not None and boc.text:
                counts[boc.text.strip()] += 1
            element.clear()
    return dict(counts)


def build_routes(root: Path, coverage: Coverage, destination: Path) -> int:
    """Write bus routes dissolved per operator, with an `st` acceptance code."""
    curves, routes = _parse(_gml_path(root))
    print(f"    parsed {len(curves):,} curves / {len(routes):,} routes")

    by_operator: dict[str, list[list[list[float]]]] = defaultdict(list)
    for curve_id, name in routes:
        coordinates = curves.get(curve_id)
        if coordinates and len(coordinates) >= 2:
            by_operator[name].append(coordinates)

    def features() -> Iterator[dict]:
        for name, parts in by_operator.items():
            status, operators = coverage.resolve(name, mode="bus")
            for operator in operators:
                operator.bus_features += len(parts)
                operator.extend_bbox(parts)

            properties = {
                "st": STATUS_CODE[status],
                "op": coverage.operator_key(operators),
                "nm": name,
                "ar": next((o.area for o in operators if o.area), "") or "",
            }
            for start in range(0, len(parts), CHUNK):
                yield {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": {
                        "type": "MultiLineString",
                        "coordinates": parts[start : start + CHUNK],
                    },
                }

    count = 0
    with destination.open("w", encoding="utf-8") as out:
        for feature in features():
            out.write(json.dumps(feature, ensure_ascii=False, separators=(",", ":")))
            out.write("\n")
            count += 1
    return count
