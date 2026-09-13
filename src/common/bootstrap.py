# -*- coding: utf-8 -*-
"""把 src/ 加入 sys.path，便于 `python src/03_xxx/02_neo4j_cypher.py` 直接 import common。"""

from __future__ import annotations

import sys
from pathlib import Path


def ensure_src_on_path() -> Path:
    src = Path(__file__).resolve().parent
    s = str(src)
    if s not in sys.path:
        sys.path.insert(0, s)
    return src
