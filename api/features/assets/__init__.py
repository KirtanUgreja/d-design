"""Assets: the only file-handling surface in v1
(docs/v1/plan/10-brand-and-uploads.md).
"""

from features.assets.assets_data import (
    find_by_storage_key,
    get_asset,
    list_assets,
    save_asset,
)
from features.assets.sanitize_svg import sanitize_svg
from features.assets.upload import (
    SVG_MIME,
    Upload,
    read_object,
    store,
    verify_and_reencode,
)

__all__ = [
    "SVG_MIME",
    "Upload",
    "find_by_storage_key",
    "get_asset",
    "list_assets",
    "read_object",
    "sanitize_svg",
    "save_asset",
    "store",
    "verify_and_reencode",
]
