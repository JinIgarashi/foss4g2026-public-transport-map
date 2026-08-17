"""Download and unpack National Land Numerical Information (国土数値情報) archives.

The archives are large and change roughly once a year, so everything lands in
`scripts/.cache/` and is reused until `--refresh` is passed.
"""

from __future__ import annotations

import shutil
import ssl
import urllib.request
import zipfile
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import certifi

SCRIPTS_DIR = Path(__file__).resolve().parent
CACHE_DIR = SCRIPTS_DIR / ".cache"

USER_AGENT = "foss4g2026-public-transport-map/0.1 (+https://github.com/JinIgarashi/foss4g2026-public-transport-map)"


@cache
def ssl_context() -> ssl.SSLContext:
    """Python installed from python.org ships no CA bundle, so verification fails
    against every HTTPS host until we point it at certifi's."""
    return ssl.create_default_context(cafile=certifi.where())


@dataclass(frozen=True)
class Dataset:
    """One KSJ product, pinned to a specific edition."""

    key: str
    url: str
    #: Directory the ZIP expands into, relative to the extraction root.
    root: str
    #: Dataset name and edition, surfaced verbatim in the app's About dialog.
    #: Kept here rather than in the UI messages so they cannot drift from the
    #: tiles that were actually built.
    label_en: str
    label_ja: str
    edition_en: str
    edition_ja: str


#: Railway sections and stations. Ships a UTF-8 GeoJSON alongside the shapefile,
#: which is what we read — no conversion needed.
N02 = Dataset(
    key="N02",
    url="https://nlftp.mlit.go.jp/ksj/gml/data/N02/N02-25/N02-25_GML.zip",
    root="N02-25_GML",
    label_en="Railway data (N02)",
    label_ja="鉄道データ（N02）",
    edition_en="FY2025 edition, as of 31 December 2025",
    edition_ja="2025年度（令和7年度）版・2025年12月31日時点",
)

#: Bus routes. GML only — no shapefile, no GeoJSON — and GDAL cannot read it
#: because the geometry is referenced by xlink rather than inlined, so
#: `n07_bus.py` parses the XML directly.
N07 = Dataset(
    key="N07",
    url="https://nlftp.mlit.go.jp/ksj/gml/data/N07/N07-22/N07-22_GML.zip",
    root="N07-22_GML",
    label_en="Bus route data (N07)",
    label_ja="バスルートデータ（N07）",
    edition_en="FY2022 edition — the most recent MLIT publishes",
    edition_ja="2022年度（令和4年度）版・国土交通省が公開している最新版",
)

DATASETS = {dataset.key: dataset for dataset in (N02, N07)}


def _download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    print(f"  downloading {url}")
    with (
        urllib.request.urlopen(request, timeout=120, context=ssl_context()) as response,
        partial.open("wb") as out,
    ):
        shutil.copyfileobj(response, out)
    partial.replace(destination)


def ensure(dataset: Dataset, *, refresh: bool = False) -> Path:
    """Return the extracted directory for `dataset`, downloading it if needed."""
    archive = CACHE_DIR / f"{dataset.key}.zip"
    extracted = CACHE_DIR / dataset.key

    if refresh:
        archive.unlink(missing_ok=True)
        shutil.rmtree(extracted, ignore_errors=True)

    if not archive.exists():
        _download(dataset.url, archive)
    else:
        print(f"  using cached {archive.relative_to(SCRIPTS_DIR)}")

    root = extracted / dataset.root
    if not root.is_dir():
        print(f"  extracting {archive.name}")
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(extracted)

    if not root.is_dir():
        raise FileNotFoundError(
            f"{archive} did not contain the expected directory {dataset.root!r}. "
            "The MLIT edition may have changed — update the Dataset definition."
        )
    return root
