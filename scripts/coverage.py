"""Resolve an MLIT operator (and line) name to an IC-card acceptance status.

The acceptance table itself lives in `data/ic-coverage.yaml`; this module only
knows how to match the messy operator strings in N02/N07 against it.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"
COVERAGE_PATH = DATA_DIR / "ic-coverage.yaml"
ALIASES_PATH = DATA_DIR / "operator-aliases.yaml"

#: Numeric codes written into the tiles. Short and stable — the style and the
#: legend both switch on them, so do not renumber without updating the app.
STATUS_CODE = {"none": 0, "full": 1, "partial": 2, "unknown": 3}
STATUS_NAME = {code: name for name, code in STATUS_CODE.items()}

#: Corporate-form noise that appears in N02/N07 but never in the source lists.
_LEGAL_FORMS = (
    "株式会社",
    "有限会社",
    "合同会社",
    "一般社団法人",
    "公益社団法人",
    "一般財団法人",
    "（株）",
    "（有）",
    "㈱",
    "㈲",
)

_PAREN_SUFFIX = re.compile(r"[（(][^（）()]*[）)]$")

#: N07 writes a jointly operated route as `A（株）・B（株）`, sometimes four deep.
#: Splitting on this and resolving each half is what stops ~90 of the busiest
#: bus operators from falling through as unrecognised.
_JOINT_SEPARATOR = "・"

#: Operator names that legitimately contain the joint separator, so splitting
#: them would produce two halves that match nothing.
_ATOMIC_NAMES = ("ジェイ・アール北海道バス", "アイ・ケーアライアンス")


def normalize(name: str | None) -> str:
    """Fold an operator name to a comparable key.

    NFKC first (so `（株）` and `(株)` converge), then strip the corporate form
    and every kind of space. Disambiguating suffixes that Wikipedia adds to
    article titles — `関東自動車 (栃木県)` — are dropped too, because MLIT never
    writes them.
    """
    if not name:
        return ""
    folded = unicodedata.normalize("NFKC", name)
    for form in _LEGAL_FORMS:
        folded = folded.replace(unicodedata.normalize("NFKC", form), "")
    folded = _PAREN_SUFFIX.sub("", folded)
    return re.sub(r"\s+", "", folded)


def split_joint(name: str) -> list[str]:
    """Split `A（株）・B（株）` into its constituent operators.

    Names that contain the separator as part of their own spelling are returned
    whole; anything else is split and each part resolved separately.
    """
    if not name or _JOINT_SEPARATOR not in name:
        return [name] if name else []

    parts: list[str] = []
    for chunk in name.split(_JOINT_SEPARATOR):
        # Re-join a piece that was severed from an atomic name: `ジェイ・アール北海道バス`
        # splits into `ジェイ` + `アール北海道バス`, neither of which resolves.
        if parts and any(
            normalize(atomic) == normalize(f"{parts[-1]}{_JOINT_SEPARATOR}{chunk}")
            for atomic in _ATOMIC_NAMES
        ):
            parts[-1] = f"{parts[-1]}{_JOINT_SEPARATOR}{chunk}"
        else:
            parts.append(chunk)
    return [part.strip() for part in parts if part.strip()]


@dataclass
class Operator:
    """One transit operator and how its IC acceptance was determined."""

    id: str
    name_ja: str
    name_en: str | None
    #: `full` / `partial` / `none` / `unknown` — the operator-wide default.
    status: str
    #: Card area id (`suica`, `icoca`, …) or `None` when not applicable.
    area: str | None
    modes: list[str]
    note_ja: str | None = None
    note_en: str | None = None
    #: Line name → status, overriding `status` for that line only.
    line_status: dict[str, str] = field(default_factory=dict)
    #: How many source features resolved to this operator, filled in by callers.
    rail_features: int = 0
    bus_features: int = 0
    #: `[west, south, east, north]` over every feature, filled in by callers.
    bbox: list[float] | None = None

    def status_for_line(self, line: str | None) -> str:
        if line and line in self.line_status:
            return self.line_status[line]
        return self.status

    def extend_bbox(self, coordinates) -> None:
        """Grow `bbox` to cover a GeoJSON coordinate array of any nesting depth.

        The web map fits the view to this when the visitor filters to an
        operator. Measuring it here is what makes that possible: the map only
        ever holds the tiles it has loaded, so it cannot find the extent of a
        Hokkaido operator while it is looking at Hiroshima.
        """
        if not coordinates:
            return
        first = coordinates[0]
        if isinstance(first, (list, tuple)):
            for part in coordinates:
                self.extend_bbox(part)
            return

        longitude, latitude = float(coordinates[0]), float(coordinates[1])
        if self.bbox is None:
            self.bbox = [longitude, latitude, longitude, latitude]
            return
        self.bbox[0] = min(self.bbox[0], longitude)
        self.bbox[1] = min(self.bbox[1], latitude)
        self.bbox[2] = max(self.bbox[2], longitude)
        self.bbox[3] = max(self.bbox[3], latitude)


#: Combining two operators on one route. A traveller does not choose which
#: company's bus turns up, so a route only counts as usable when every operator
#: on it accepts the cards.
def _combine(statuses: list[str]) -> str:
    if not statuses:
        return "unknown"
    if all(s == "full" for s in statuses):
        return "full"
    if any(s in ("full", "partial") for s in statuses):
        return "partial"
    if any(s == "unknown" for s in statuses):
        return "unknown"
    return "none"


class Coverage:
    """The curated acceptance table, indexed for lookup."""

    def __init__(self, coverage: dict, aliases: dict) -> None:
        self.meta: dict = coverage.get("meta") or {}
        self.areas: dict[str, dict] = coverage.get("areas") or {}
        self.operators: dict[str, Operator] = {}
        self._by_key: dict[str, Operator] = {}
        #: Operators minted on the fly for names the table does not cover.
        self._synthetic: dict[str, Operator] = {}
        #: Per-mode alias tables, keyed `any` / `rail` / `bus`.
        self._aliases: dict[str, dict[str, Operator]] = {"any": {}, "rail": {}, "bus": {}}
        #: What an operator absent from every table means. The participant list
        #: is published as exhaustive, so `none` is the honest reading — but it
        #: is spelled out in the data rather than hard-coded here.
        self.unlisted_status: dict[str, str] = {
            "rail": "unknown",
            "bus": "unknown",
            **(self.meta.get("unlisted_status") or {}),
        }
        #: Raw source names that resolved to nothing, with a feature count.
        self.unmatched: dict[str, int] = {}

        for entry in coverage.get("operators") or []:
            operator = Operator(
                id=entry["id"],
                name_ja=entry["name"]["ja"],
                name_en=entry["name"].get("en"),
                status=entry.get("status", "unknown"),
                area=entry.get("area"),
                modes=list(entry.get("modes") or []),
                note_ja=(entry.get("note") or {}).get("ja"),
                note_en=(entry.get("note") or {}).get("en"),
            )
            for status, lines in (entry.get("lines") or {}).items():
                for line in lines:
                    operator.line_status[line] = status

            if operator.id in self.operators:
                raise ValueError(f"duplicate operator id: {operator.id}")
            self.operators[operator.id] = operator

            for raw in [operator.name_ja, *(entry.get("match") or [])]:
                self._register(raw, operator)

        # Aliases map a raw MLIT string onto an operator that is already defined,
        # for the cases normalization cannot bridge (a city name standing in for
        # its transport bureau, a subsidiary folded into its parent, …). They are
        # per-mode because a city can run an IC-enabled tram and a cash-only
        # community bus under the same name — 熊本市 does exactly that.
        for mode, table in (aliases.get("aliases") or {}).items():
            if mode not in self._aliases:
                raise ValueError(f"operator-aliases.yaml has unknown mode section {mode!r}")
            for raw, operator_id in (table or {}).items():
                operator = self.operators.get(operator_id)
                if operator is None:
                    raise ValueError(
                        f"operator-aliases.yaml maps {raw!r} to unknown operator {operator_id!r}"
                    )
                self._aliases[mode][normalize(raw)] = operator

    def _register(self, raw: str, operator: Operator) -> None:
        key = normalize(raw)
        if not key:
            return
        existing = self._by_key.get(key)
        if existing is not None and existing.id != operator.id:
            raise ValueError(
                f"{raw!r} normalizes to {key!r}, claimed by both "
                f"{existing.id!r} and {operator.id!r}"
            )
        self._by_key[key] = operator

    def lookup(self, raw: str | None, mode: str = "rail") -> Operator | None:
        key = normalize(raw)
        if not key:
            return None
        return (
            self._by_key.get(key)
            or self._aliases.get(mode, {}).get(key)
            or self._aliases["any"].get(key)
        )

    def resolve(
        self, raw: str | None, line: str | None = None, mode: str = "rail"
    ) -> tuple[str, list[Operator]]:
        """Return `(status, operators)` for a source feature.

        `raw` may name several operators sharing a route, in which case every one
        of them is resolved and the strictest reading wins — see `_combine`.

        An operator that resolves to nothing falls back to `unlisted_status`,
        which the data sets per mode so the policy stays visible and reviewable
        rather than buried in this function.
        """
        names = split_joint(raw or "")
        if not names:
            return self.unlisted_status.get(mode, "unknown"), []

        statuses: list[str] = []
        operators: list[Operator] = []
        for name in names:
            operator = self.lookup(name, mode) or self._synthesize(name, mode)
            statuses.append(operator.status_for_line(line))
            operators.append(operator)

        return _combine(statuses), operators

    def _synthesize(self, raw: str, mode: str) -> Operator:
        """Mint an operator for a name the curated table does not cover.

        Without this, every unlisted operator would share the empty operator id
        and none of them could be picked out with the operator filter — which
        is most of the bus network. The id is an md5 of the normalized name
        rather than a counter so it survives a rebuild unchanged.
        """
        self.unmatched[raw] = self.unmatched.get(raw, 0) + 1
        key = normalize(raw)
        existing = self._synthetic.get(key)
        if existing is not None:
            return existing

        operator = Operator(
            id=f"x-{hashlib.md5(key.encode()).hexdigest()[:10]}",
            name_ja=raw,
            name_en=None,
            # A name reaching this point in both modes keeps the first mode's
            # fallback. That only matters if `unlisted_status` differs per mode,
            # which it does not today.
            status=self.unlisted_status.get(mode, "unknown"),
            area=None,
            modes=[mode],
        )
        # Kept out of `_by_key` so a mode-specific alias — 熊本市 is a tram
        # operator on rail and an unlisted community bus on bus — is not shadowed
        # by the synthetic entry minted for the other mode.
        self._synthetic[key] = operator
        self.operators[operator.id] = operator
        return operator

    @staticmethod
    def operator_key(operators: list[Operator]) -> str:
        """Pack operator ids for the tiles.

        MapLibre has no array membership test, but `["in", needle, haystack]`
        does substring matching on strings. Delimiting every id with pipes turns
        that into an exact membership test — without the delimiters `jr-east`
        would match a feature belonging only to `jr-east-bus`.
        """
        if not operators:
            return ""
        seen: list[str] = []
        for operator in operators:
            if operator.id not in seen:
                seen.append(operator.id)
        return "|" + "|".join(seen) + "|"

    def area_name(self, area_id: str | None, lang: str) -> str | None:
        if not area_id:
            return None
        area = self.areas.get(area_id)
        if not area:
            return None
        return (area.get("name") or {}).get(lang)


def load() -> Coverage:
    coverage = yaml.safe_load(COVERAGE_PATH.read_text(encoding="utf-8")) or {}
    aliases = (
        yaml.safe_load(ALIASES_PATH.read_text(encoding="utf-8")) or {}
        if ALIASES_PATH.exists()
        else {}
    )
    return Coverage(coverage, aliases)
