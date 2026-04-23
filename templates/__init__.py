"""
Auto-discovers document generators from sibling modules.

Any module in this package that defines both DOC_TYPE (str) and generate() is
registered automatically — no manual wiring required.  To add a new document type,
create templates/<name>.py with:

    DOC_TYPE = "my_doc_type"

    def generate(fake, overlay_name=None) -> tuple[str, dict, list]:
        ...
        return text, pii_gt, non_pii_data
"""

import importlib
import pkgutil
from pathlib import Path

REGISTRY: dict[str, callable] = {}

for _importer, _modname, _ispkg in pkgutil.iter_modules([str(Path(__file__).parent)]):
    if _modname == "base":
        continue
    _mod = importlib.import_module(f".{_modname}", package=__name__)
    if hasattr(_mod, "DOC_TYPE") and hasattr(_mod, "generate"):
        REGISTRY[_mod.DOC_TYPE] = _mod.generate
