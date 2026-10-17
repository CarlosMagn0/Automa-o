from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
DATABASE_PATH = Path(os.getenv("BONUS_DATABASE_PATH", str(ROOT / "data" / "bonus_automation.sqlite3")))
