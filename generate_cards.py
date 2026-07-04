#!/usr/bin/env python3
"""
generate_cards.py
------------------
Self-contained replacement for the live github-readme-stats "pin" cards and
the github-profile-trophy widget.

Why this exists:
  Both of the tools above render images on-demand from shared, free-tier
  servers. Under heavy shared traffic those servers rate-limit or time out,
  which is what was happening in the README. This script renders the exact
  same *kind* of information (repo pins + achievement stats) as plain SVG
  files that get committed straight into this repository. The README then
  points at those files with a relative path, so there is no third-party
  server involved when someone actually loads your profile page.

  A GitHub Actions workflow (.github/workflows/update-cards.yml) runs this
  script on a schedule so the numbers stay current without you doing
  anything.

Dependencies: none beyond the Python 3 standard library, on purpose --
fewer moving parts = fewer ways for the automation to break.

Usage:
  python3 scripts/generate_cards.py
  (reads GITHUB_TOKEN from the environment if present, for a higher API
  rate limit -- the GitHub Actions workflow sets this automatically)
"""

import json
import os
import sys
import textwrap
import urllib.request
import urllib.error
from html import escape

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GITHUB_USERNAME = "jeevan-1805"
REPOS_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "repos.json")
ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")

# Theme -- kept in sync with the colors used elsewhere in README.md
BG_COLOR = "#0B1020"
BORDER_COLOR = "#1E293B"
TITLE_COLOR = "#8B5CF6"
ICON_COLOR = "#38BDF8"
TEXT_COLOR = "#C9D1D9"
MUTED_COLOR = "#64748B"

# Official linguist colors (github-linguist/linguist languages.yml) for the
# languages that currently appear in this account's repos, plus a handful of
# common ones so new repos in other languages still get a real color instead
# of the fallback gray.
LANGUAGE_COLORS = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "Java": "#b07219",
    "C++": "#f34b7d",
    "C": "#555555",
    "Shell": "#89e051",
    "Jupyter Notebook": "#DA5B0B",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    None: "#8b949e",
}

# Simple 16x16 Octicon path data (MIT licensed, github/primer/octicons) --
# same icon set used internally by github-readme-stats.
ICON_REPO = "M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 1 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 0 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 0 1 1-1Z"
ICON_STAR = "M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"
ICON_FORK = "M5 3.25a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Zm5-1.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5ZM1.75 2.5a2.25 2.25 0 1 1 3 2.122v1.756a2.25 2.25 0 0 1 .75 1.372c0 .862-.63 1.5-1.5 1.5s-1.5-.638-1.5-1.5c0-.584.31-1.074.75-1.372V4.622A2.25 2.25 0 0 1 1.75 2.5ZM5 12.75a.75.75 0 1 0 0-1.5.75.75 0 0 0 0 1.5Z"


# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

def api_get(path):
    """GET a GitHub REST API path, using GITHUB_TOKEN if available."""
    url = f"https://api.github.com{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  [warn] GitHub API request failed for {path}: HTTP {e.code}", file=sys.stderr)
        return None
    except Exception as e:  # network hiccups shouldn't kill the whole run
        print(f"  [warn] GitHub API request failed for {path}: {e}", file=sys.stderr)
        return None


def load_repo_list():
    with open(REPOS_CONFIG_PATH) as f:
        return json.load(f)["repos"]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def wrap_text(text, max_chars=42, max_lines=2):
    if not text:
        return ["No description provided"]
    lines = textwrap.wrap(text, width=max_chars)
    if not lines:
        return ["No description provided"]
    if len(lines) > max_lines:
        kept = lines[:max_lines]
        kept[-1] = kept[-1].rstrip() + "…"
        return kept
    return lines


def render_pin_card(repo):
    """repo: dict with name, description, language, stars, forks, url"""
    name = escape(repo["name"])
    desc_lines = [escape(l) for l in wrap_text(repo.get("description"))]
    lang = repo.get("language") or "N/A"
    lang_color = LANGUAGE_COLORS.get(repo.get("language"), LANGUAGE_COLORS[None])
    stars = repo.get("stars", 0)
    forks = repo.get("forks", 0)

    desc_svg = "\n".join(
        f'<text x="18" y="{58 + i * 19}" class="desc">{line}</text>'
        for i, line in enumerate(desc_lines)
    )

    return f'''<svg width="400" height="150" viewBox="0 0 400 150" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{name} repository card">
  <style>
    .title {{ font: 600 18px "Segoe UI", Ubuntu, Helvetica, Arial, sans-serif; fill: {TITLE_COLOR}; }}
    .desc  {{ font: 400 13px "Segoe UI", Ubuntu, Helvetica, Arial, sans-serif; fill: {TEXT_COLOR}; }}
    .meta  {{ font: 400 12px "Segoe UI", Ubuntu, Helvetica, Arial, sans-serif; fill: {TEXT_COLOR}; }}
  </style>
  <rect x="0.5" y="0.5" rx="10" width="399" height="149" fill="{BG_COLOR}" stroke="{BORDER_COLOR}"/>
  <g transform="translate(18,16)">
    <path d="{ICON_REPO}" fill="{ICON_COLOR}"/>
  </g>
  <text x="42" y="30" class="title">{name}</text>
  {desc_svg}
  <circle cx="24" cy="121" r="6" fill="{lang_color}"/>
  <text x="36" y="126" class="meta">{escape(lang)}</text>
  <g transform="translate(150,114)"><path d="{ICON_STAR}" fill="{ICON_COLOR}"/></g>
  <text x="172" y="126" class="meta">{stars}</text>
  <g transform="translate(210,114)"><path d="{ICON_FORK}" fill="{ICON_COLOR}"/></g>
  <text x="232" y="126" class="meta">{forks}</text>
</svg>'''


def render_achievements(stats):
    """stats: list of (label, value) tuples, 4 items expected"""
    width = 800
    height = 130
    block_w = width / len(stats)
    blocks = []
    for i, (label, value) in enumerate(stats):
        cx = block_w * i + block_w / 2
        blocks.append(f'''
  <text x="{cx}" y="58" text-anchor="middle" class="value">{escape(str(value))}</text>
  <text x="{cx}" y="86" text-anchor="middle" class="label">{escape(label)}</text>''')
        if i > 0:
            x = block_w * i
            blocks.append(f'<line x1="{x}" y1="24" x2="{x}" y2="{height - 24}" stroke="{BORDER_COLOR}" stroke-width="1"/>')

    return f'''<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="GitHub achievement stats">
  <style>
    .value {{ font: 700 30px "Segoe UI", Ubuntu, Helvetica, Arial, sans-serif; fill: {TITLE_COLOR}; }}
    .label {{ font: 400 13px "Segoe UI", Ubuntu, Helvetica, Arial, sans-serif; fill: {TEXT_COLOR}; letter-spacing: 0.5px; }}
  </style>
  <rect x="0.5" y="0.5" rx="12" width="{width - 1}" height="{height - 1}" fill="{BG_COLOR}" stroke="{BORDER_COLOR}"/>
  {"".join(blocks)}
</svg>'''


# ---------------------------------------------------------------------------
# Data assembly
# ---------------------------------------------------------------------------

def build_repo_data(repo_name):
    data = api_get(f"/repos/{GITHUB_USERNAME}/{repo_name}")
    if data is None:
        return None
    return {
        "name": data.get("name", repo_name),
        "description": data.get("description"),
        "language": data.get("language"),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "url": data.get("html_url", f"https://github.com/{GITHUB_USERNAME}/{repo_name}"),
    }


def build_achievement_stats():
    user = api_get(f"/users/{GITHUB_USERNAME}")
    repos = api_get(f"/users/{GITHUB_USERNAME}/repos?per_page=100")

    public_repos = user.get("public_repos") if user else (len(repos) if repos else "N/A")
    followers = user.get("followers") if user else "N/A"

    total_stars = "N/A"
    top_language = "N/A"
    if repos:
        total_stars = sum(r.get("stargazers_count", 0) for r in repos)
        lang_counts = {}
        for r in repos:
            lang = r.get("language")
            if lang:
                lang_counts[lang] = lang_counts.get(lang, 0) + 1
        if lang_counts:
            top_language = max(lang_counts.items(), key=lambda kv: kv[1])[0]

    return [
        ("Public Repos", public_repos),
        ("Total Stars", total_stars),
        ("Followers", followers),
        ("Top Language", top_language),
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    os.makedirs(ASSETS_DIR, exist_ok=True)
    repo_names = load_repo_list()

    print(f"Generating pin cards for: {', '.join(repo_names)}")
    for repo_name in repo_names:
        repo = build_repo_data(repo_name)
        if repo is None:
            print(f"  [skip] Could not fetch {repo_name}, leaving existing card (if any) untouched.")
            continue
        svg = render_pin_card(repo)
        out_path = os.path.join(ASSETS_DIR, f"pin-{repo_name.lower()}.svg")
        with open(out_path, "w") as f:
            f.write(svg)
        print(f"  [ok] {out_path}")

    print("Generating achievements strip")
    stats = build_achievement_stats()
    svg = render_achievements(stats)
    out_path = os.path.join(ASSETS_DIR, "achievements.svg")
    with open(out_path, "w") as f:
        f.write(svg)
    print(f"  [ok] {out_path} -> {stats}")


if __name__ == "__main__":
    main()
