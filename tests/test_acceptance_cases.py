"""Every acceptance test case file must follow tests/acceptance/README.md."""

import re
from pathlib import Path

import pytest

CASES_DIR = Path(__file__).parent / "acceptance"
CASE_FILES = sorted(CASES_DIR.glob("TC-*.md"))
REQUIRED_KEYS = ("id", "title", "issue", "added_in")
REQUIRED_SECTIONS = ("## Preconditions", "## Steps", "## Expected")


def front_matter(text: str) -> dict[str, str]:
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    assert m, "missing front matter"
    out = {}
    for line in m.group(1).splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_there_are_cases():
    assert CASE_FILES


@pytest.mark.parametrize("path", CASE_FILES, ids=[p.stem for p in CASE_FILES])
def test_case_format(path: Path):
    text = path.read_text()
    meta = front_matter(text)
    for key in REQUIRED_KEYS:
        assert meta.get(key), f"{path.name}: missing {key}"
    assert re.fullmatch(r"TC-\d{3}", meta["id"])
    assert path.name.startswith(meta["id"] + "-"), f"{path.name}: filename must start with id"
    assert meta["issue"].isdigit() and meta["added_in"].isdigit()
    for section in REQUIRED_SECTIONS:
        assert section in text, f"{path.name}: missing {section}"


def test_ids_are_unique():
    ids = [front_matter(p.read_text())["id"] for p in CASE_FILES]
    assert len(ids) == len(set(ids))
