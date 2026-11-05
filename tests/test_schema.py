import re
from pathlib import Path

SCHEMA = (Path(__file__).resolve().parent.parent / "db" / "schema.sql").read_text()


def test_findings_has_tone_column_limited_to_1_5():
    assert re.search(
        r"ALTER TABLE findings ADD COLUMN IF NOT EXISTS tone INTEGER\s+CHECK \(tone BETWEEN 1 AND 5\);",
        SCHEMA,
    )
