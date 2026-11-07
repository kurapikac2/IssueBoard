"""Environment configuration without a separate settings dependency."""
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    database: Path
    cookie_secure: bool = False
    session_hours: int = 24

    @classmethod
    def from_env(cls) -> "Settings":
        path = Path(os.getenv("ISSUEBOARD_DB", "data/issueboard.sqlite3"))
        hours = int(os.getenv("ISSUEBOARD_SESSION_HOURS", "24"))
        if not 1 <= hours <= 168:
            raise ValueError("ISSUEBOARD_SESSION_HOURS must be between 1 and 168")
        return cls(
            database=path if path.is_absolute() else ROOT / path,
            cookie_secure=os.getenv("ISSUEBOARD_COOKIE_SECURE", "false").lower() == "true",
            session_hours=hours,
        )