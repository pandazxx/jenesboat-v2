#!/usr/bin/env python3
"""Generate the GitHub Pages landing page listing every published build.

    python3 scripts/gen_build_index.py <site-dir> [--repo owner/name]

Scans ``<site-dir>/builds/*/build.json`` and writes ``<site-dir>/index.html`` plus a
machine-readable ``<site-dir>/builds.json`` (newest first) for agents.
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

KINDS = (("tag", "Tags and releases"), ("commit", "master commits"), ("pr", "Pull requests"))


def load_builds(site: Path) -> list[dict]:
    builds: list[dict] = []
    root = site / "builds"
    if not root.is_dir():
        return builds
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not (d / "index.html").is_file():
            continue
        meta: dict = {"name": d.name, "kind": "commit", "built_at": ""}
        meta_file = d / "build.json"
        if meta_file.is_file():
            try:
                meta.update(json.loads(meta_file.read_text()))
            except json.JSONDecodeError:
                pass
        meta["name"] = d.name
        meta["url"] = f"builds/{d.name}/"
        builds.append(meta)
    builds.sort(key=lambda b: b.get("built_at", ""), reverse=True)
    return builds


def _link(url: str | None, text: str) -> str:
    if not url:
        return html.escape(text)
    return f'<a href="{html.escape(url)}">{html.escape(text)}</a>'


def render_rows(builds: list[dict], repo: str | None) -> str:
    rows = []
    for b in builds:
        sha = b.get("sha") or ""
        commit_url = f"https://github.com/{repo}/commit/{sha}" if repo and sha else None
        pr = b.get("pr")
        pr_url = f"https://github.com/{repo}/pull/{pr}" if repo and pr else None
        ref = b.get("ref") or ""
        rows.append(
            "<tr>"
            f'<td><a class=play href="{html.escape(b["url"])}">{html.escape(b["name"])}</a></td>'
            f"<td>{html.escape(b.get('built_at', ''))}</td>"
            f"<td>{html.escape(ref)}{(' · ' + _link(pr_url, f'PR #{pr}')) if pr else ''}</td>"
            f"<td><code>{_link(commit_url, sha[:7])}</code></td>"
            f"<td>{html.escape(b.get('title', ''))}</td>"
            f"<td>{_link(b.get('run_url'), 'run') if b.get('run_url') else ''}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def render(builds: list[dict], repo: str | None) -> str:
    sections = []
    for kind, title in KINDS:
        subset = [b for b in builds if b.get("kind", "commit") == kind]
        if not subset:
            continue
        sections.append(
            f"<h2>{html.escape(title)} <small>({len(subset)})</small></h2>\n"
            "<table><thead><tr><th>build</th><th>built (UTC)</th><th>ref</th>"
            "<th>commit</th><th>title</th><th>CI</th></tr></thead>\n"
            f"<tbody>\n{render_rows(subset, repo)}\n</tbody></table>"
        )
    latest = builds[0] if builds else None
    latest_tag = next((b for b in builds if b.get("kind") == "tag"), None)
    quick = []
    if latest_tag:
        quick.append(f"latest release: {_link(latest_tag['url'], latest_tag['name'])}")
    if latest:
        quick.append(f"newest build: {_link(latest['url'], latest['name'])}")
    repo_link = _link(f"https://github.com/{repo}", repo) if repo else ""
    body = "\n".join(sections) if sections else "<p>No builds published yet.</p>"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>jenesboat-v2 builds</title>
<style>
 body{{font:15px/1.4 system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;
      background:#0c203c;color:#e6e6e6}}
 a{{color:#ffe678}} h1 small,h2 small{{color:#96a0aa;font-weight:normal}}
 table{{border-collapse:collapse;width:100%;margin-bottom:2rem}}
 th,td{{text-align:left;padding:.35rem .5rem;border-bottom:1px solid #1e3a60;vertical-align:top}}
 th{{color:#96a0aa;font-weight:normal}} code{{font-size:.9em}}
 a.play{{font-weight:bold}} .quick{{color:#96a0aa}}
</style></head><body>
<h1>jenesboat-v2 <small>builds</small></h1>
<p class=quick>{" · ".join(quick)}{(" · " + repo_link) if repo_link else ""}
 · <a href="builds.json">builds.json</a></p>
<p>Every CI build is playable here. Commit builds are named by short SHA, tag builds by tag.
Press <kbd>W</kbd>/<kbd>S</kbd> for throttle, <kbd>A</kbd>/<kbd>D</kbd> for rudder,
<kbd>Space</kbd> to dive or surface.</p>
{body}
</body></html>
"""


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("site", help="root of the gh-pages checkout")
    p.add_argument("--repo", default=None, help="owner/name for GitHub links")
    args = p.parse_args()
    site = Path(args.site)
    builds = load_builds(site)
    (site / "index.html").write_text(render(builds, args.repo))
    (site / "builds.json").write_text(json.dumps(builds, indent=2, sort_keys=True) + "\n")
    (site / ".nojekyll").touch()
    print(f"indexed {len(builds)} builds into {site / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
