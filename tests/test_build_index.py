import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gen_build_index.py"
spec = importlib.util.spec_from_file_location("gen_build_index", SCRIPT)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def make_build(site: Path, name: str, **meta):
    d = site / "builds" / name
    d.mkdir(parents=True)
    (d / "index.html").write_text("<html></html>")
    (d / "build.json").write_text(json.dumps({"name": name, **meta}))


def test_index_lists_builds_newest_first(tmp_path):
    make_build(tmp_path, "abc1234", kind="commit", built_at="2026-10-01T00:00Z", sha="abc1234def")
    make_build(tmp_path, "v0.1.0", kind="tag", built_at="2026-10-02T00:00Z", ref="v0.1.0")
    make_build(tmp_path, "9876543", kind="pr", built_at="2026-10-03T00:00Z", pr=7)
    (tmp_path / "builds" / "stray").mkdir()  # no index.html -> ignored

    builds = gen.load_builds(tmp_path)
    assert [b["name"] for b in builds] == ["9876543", "v0.1.0", "abc1234"]

    html = gen.render(builds, repo="owner/repo")
    assert 'href="builds/v0.1.0/"' in html
    assert "latest release" in html
    assert "https://github.com/owner/repo/pull/7" in html
    assert "https://github.com/owner/repo/commit/abc1234def" in html


def test_empty_site(tmp_path):
    assert gen.load_builds(tmp_path) == []
    assert "No builds published yet" in gen.render([], None)
