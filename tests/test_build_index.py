import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gen_build_index.py"
spec = importlib.util.spec_from_file_location("gen_build_index", SCRIPT)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def make_build(site: Path, name: str, start_page: bool = True, **meta):
    d = site / "builds" / name
    d.mkdir(parents=True)
    (d / "index.html").write_text("<html></html>")
    if start_page:
        (d / "start.html").write_text("<html></html>")
    (d / "build.json").write_text(json.dumps({"name": name, **meta}))


def test_index_lists_builds_newest_first(tmp_path):
    make_build(tmp_path, "abc1234", kind="commit", built_at="2026-10-01T00:00Z", sha="abc1234def")
    make_build(tmp_path, "v0.1.0", kind="tag", built_at="2026-10-02T00:00Z", ref="v0.1.0")
    make_build(tmp_path, "9876543", kind="pr", built_at="2026-10-03T00:00Z", pr=7)
    make_build(tmp_path, "old1234", start_page=False, built_at="2026-09-01T00:00Z")
    (tmp_path / "builds" / "stray").mkdir()  # no index.html -> ignored

    builds = gen.load_builds(tmp_path)
    assert [b["name"] for b in builds] == ["9876543", "v0.1.0", "abc1234", "old1234"]
    assert builds[0]["url"] == "builds/9876543/"  # the game page, for agents
    assert builds[0]["start_url"] == "builds/9876543/start.html"  # the difficulty chooser
    assert builds[-1]["start_url"] == "builds/old1234/"  # a build from before start pages

    html = gen.render(builds, repo="owner/repo")
    assert 'href="builds/v0.1.0/start.html"' in html  # the link opens the chooser
    assert 'href="builds/old1234/"' in html
    assert 'newest build: <a href="builds/9876543/start.html">' in html
    assert "latest release" in html
    assert "https://github.com/owner/repo/pull/7" in html
    assert "https://github.com/owner/repo/commit/abc1234def" in html


def test_empty_site(tmp_path):
    assert gen.load_builds(tmp_path) == []
    assert "No builds published yet" in gen.render([], None)


def test_start_page_offers_every_difficulty(tmp_path):
    build_web_spec = importlib.util.spec_from_file_location(
        "build_web", SCRIPT.parent / "build_web.py"
    )
    build_web = importlib.util.module_from_spec(build_web_spec)
    build_web_spec.loader.exec_module(build_web)
    from jenesboat_v2.sim.params import DEFAULT_DIFFICULTY, DIFFICULTIES

    page = build_web.render_start_page("abc1234")
    assert "build abc1234" in page
    for d in DIFFICULTIES.values():
        assert f'href="index.html?difficulty={d.name}"' in page
        assert f"<b>{d.title}</b>" in page and d.description in page
    assert page.count('<a class="level') == len(DIFFICULTIES)
    assert f'class="level default" href="index.html?difficulty={DEFAULT_DIFFICULTY}"' in page
    assert 'href="../../"' in page  # back to the build index
