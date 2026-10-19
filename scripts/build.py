#!/usr/bin/env python3
"""Generates every SVG under assets/ for the zShanCS profile README.

Stdlib only. Live numbers come from the GitHub API and are cached in
stats.json. Counts that include private org work (PRs, reviews, org repos) need
PROFILE_TOKEN (a read-only PAT); without it those keep their cached values.
Run: GITHUB_TOKEN=... [PROFILE_TOKEN=...] python3 scripts/build.py
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

USER = "zShanCS"
ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

THEMES = {
    "dark": dict(bg="#0d1117", card="#161b22", border="#30363d", fg="#e6edf3",
                 muted="#8b949e", faint="#21262d", term="#010409", a1="#a78bfa",
                 a2="#22d3ee", a3="#f472b6", ok="#3fb950"),
    "light": dict(bg="#ffffff", card="#f6f8fa", border="#d0d7de", fg="#1f2328",
                  muted="#59636e", faint="#eaeef2", term="#0d1117", a1="#7c3aed",
                  a2="#0891b2", a3="#db2777", ok="#1a7f37"),
}

STATS_FILE = ROOT / "stats.json"
# orgs to count repos across; kept in a secret so they never appear in this public repo
ORGS = [o for o in os.environ.get("PROFILE_ORGS", "").split(",") if o]

PROJECTS = [
    dict(slug="autoflow", name="Autoflow", tag="HACKATHON WINNER",
         line1="AI pair-programmer for VS Code, built",
         line2="before ChatGPT existed. 16 dev tools.",
         stack=["TypeScript", "Codex", "CodeT5", "FastAPI"]),
    dict(slug="patent-search", name="Patent Search", tag="DISTRIBUTED",
         line1="Semantic search over a huge patent",
         line2="corpus, fanned out broker → workers.",
         stack=["Python", "Embeddings", "FastAPI"]),
]


# ---------------------------------------------------------------- data

def gh(path, body=None, token=None):
    token = token or os.environ.get("GITHUB_TOKEN")
    url = "https://api.github.com" + path
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"bearer {token}",
                                          "User-Agent": USER})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def count(q, token):
    return gh("/search/issues?q=" + urllib.parse.quote(q), token=token)["total_count"]


def fetch_stats():
    stats = json.loads(STATS_FILE.read_text())
    try:
        if os.environ.get("GITHUB_TOKEN"):
            q = """{ user(login:"%s") { createdAt
              contributionsCollection { contributionCalendar { totalContributions } } } }""" % USER
            u = gh("/graphql", {"query": q})["data"]["user"]
            stats["contributions"] = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
            stats["since"] = int(u["createdAt"][:4])
        pat = os.environ.get("PROFILE_TOKEN")
        if pat:
            since = (datetime.now(timezone.utc) - timedelta(days=365)).date()
            stats["merged"] = count(f"author:{USER} type:pr is:merged created:>{since}", pat)
            stats["reviewed"] = count(f"reviewed-by:{USER} -author:{USER} type:pr created:>{since}", pat)
        if pat and ORGS:
            stats["org_repos"] = sum(gh(f"/orgs/{o}", token=pat)["total_private_repos"] +
                                     gh(f"/orgs/{o}", token=pat)["public_repos"] for o in ORGS)
    except Exception as exc:  # keep the build green; stale numbers beat a broken profile
        print("stats fetch failed, keeping cached values:", exc)
    STATS_FILE.write_text(json.dumps(stats, indent=2) + "\n")
    return stats


# ---------------------------------------------------------------- svgs

def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{escape(title)}">'
            f'<title>{escape(title)}</title>{body}</svg>\n')


def gradient(id_, t, animate=False):
    anim = ('<animateTransform attributeName="gradientTransform" type="translate" '
            'values="-1 0;1 0;-1 0" dur="8s" repeatCount="indefinite"/>') if animate else ""
    return (f'<linearGradient id="{id_}" x1="0" y1="0" x2="1" y2="0" spreadMethod="reflect">'
            f'<stop offset="0" stop-color="{t["a1"]}"/><stop offset=".5" stop-color="{t["a2"]}"/>'
            f'<stop offset="1" stop-color="{t["a3"]}"/>{anim}</linearGradient>')


def hero(t, s):
    W, H = 1200, 360
    # neural-net constellation in the background
    nodes = [(80, 300), (170, 250), (260, 320), (330, 60), (420, 110), (520, 40),
             (560, 300), (600, 200), (1150, 40), (1110, 320)]
    edges = [(0, 1), (1, 2), (1, 4), (3, 4), (4, 5), (5, 7), (6, 7), (4, 7), (2, 6)]
    net = "".join(
        f'<line x1="{nodes[a][0]}" y1="{nodes[a][1]}" x2="{nodes[b][0]}" y2="{nodes[b][1]}" '
        f'stroke="url(#g)" stroke-width="1" opacity=".18"/>' for a, b in edges)
    net += "".join(
        f'<circle cx="{x}" cy="{y}" r="3" fill="{t["a2"]}" opacity=".25">'
        f'<animate attributeName="opacity" values=".15;.8;.15" dur="{3 + i % 4}s" '
        f'begin="{i * .4:.1f}s" repeatCount="indefinite"/></circle>'
        for i, (x, y) in enumerate(nodes))

    # terminal that "types" a few commands
    tx, ty, tw, th = 640, 40, 520, 284
    session = [
        ("cmd", "whoami"),
        ("out", "builder + engineering manager, AI-first"),
        ("cmd", "cat focus.md"),
        ("out", "AI agents  ·  data platforms  ·  web + mobile"),
        ("cmd", "gh pr stats --last 12mo"),
        ("out", f"{s['merged']:,} merged  ·  {s['reviewed']:,} reviewed for the team"),
    ]
    cw, lh = 9.4, 30
    lines, defs, clock = [], [], 0.8
    for i, (kind, text) in enumerate(session):
        y = ty + 76 + i * lh
        x0 = tx + 24
        if kind == "cmd":
            n = len(text)
            steps = ";".join(str(round((k) * cw, 1)) for k in range(n + 1)) + ";600"
            dur = (n + 1) * 0.07
            defs.append(f'<clipPath id="c{i}"><rect x="{x0 + 22}" y="{y - 18}" height="26" width="0">'
                        f'<animate attributeName="width" values="{steps}" calcMode="discrete" '
                        f'begin="{clock:.2f}s" dur="{dur:.2f}s" fill="freeze"/></rect></clipPath>')
            lines.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{clock - .3:.2f}s" fill="freeze"/>'
                         f'<text x="{x0}" y="{y}" fill="{t["ok"]}">❯</text>'
                         f'<text x="{x0 + 22}" y="{y}" fill="#e6edf3" clip-path="url(#c{i})">{escape(text)}</text></g>')
            clock += dur + 0.25
        else:
            lines.append(f'<text x="{x0 + 22}" y="{y}" fill="#8b949e" opacity="0">{escape(text)}'
                         f'<set attributeName="opacity" to="1" begin="{clock:.2f}s" fill="freeze"/></text>')
            clock += 0.5
    cy = ty + 76 + len(session) * lh
    lines.append(f'<g opacity="0"><set attributeName="opacity" to="1" begin="{clock:.2f}s" fill="freeze"/>'
                 f'<text x="{tx + 24}" y="{cy}" fill="{t["ok"]}">❯</text>'
                 f'<rect x="{tx + 46}" y="{cy - 15}" width="9" height="18" fill="{t["a2"]}">'
                 f'<animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite"/></rect></g>')

    terminal = (
        f'<g filter="url(#sh)"><rect x="{tx}" y="{ty}" width="{tw}" height="{th}" rx="12" fill="{t["term"]}" '
        f'stroke="{t["border"]}"/></g>'
        f'<circle cx="{tx + 22}" cy="{ty + 22}" r="6" fill="#ff5f57"/>'
        f'<circle cx="{tx + 42}" cy="{ty + 22}" r="6" fill="#febc2e"/>'
        f'<circle cx="{tx + 62}" cy="{ty + 22}" r="6" fill="#28c840"/>'
        f'<text x="{tx + tw / 2}" y="{ty + 27}" text-anchor="middle" fill="#6e7681" font-size="13">~/zshan — zsh</text>'
        f'<line x1="{tx}" y1="{ty + 42}" x2="{tx + tw}" y2="{ty + 42}" stroke="#21262d"/>'
        f'<g font-family="{MONO}" font-size="15.5">{"".join(lines)}</g>'
    )

    left = (
        f'<text x="60" y="96" font-family="{MONO}" font-size="16" letter-spacing="4" fill="{t["muted"]}">HI, I\'M</text>'
        f'<text x="54" y="188" font-family="{SANS}" font-size="104" font-weight="800" letter-spacing="-4" fill="url(#ga)">zShan</text>'
        f'<text x="60" y="236" font-family="{SANS}" font-size="27" font-weight="600" fill="{t["fg"]}">I build products, and lead</text>'
        f'<text x="60" y="270" font-family="{SANS}" font-size="27" font-weight="600" fill="{t["fg"]}">the teams that ship them.</text>'
        f'<text x="60" y="310" font-family="{MONO}" font-size="15" fill="{t["muted"]}">builder  ·  eng manager  ·  AI-first</text>'
    )
    body = (
        f'<defs>{gradient("g", t)}{gradient("ga", t, True)}'
        f'<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse">'
        f'<circle cx="1" cy="1" r="1" fill="{t["border"]}"/></pattern>'
        f'<filter id="sh" x="-10%" y="-10%" width="120%" height="130%">'
        f'<feDropShadow dx="0" dy="12" stdDeviation="14" flood-color="{t["a1"]}" flood-opacity=".22"/></filter>'
        f'<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{t["bg"]}" stop-opacity="0"/>'
        f'<stop offset=".5" stop-color="{t["bg"]}" stop-opacity=".9"/></linearGradient>'
        f'{"".join(defs)}</defs>'
        f'<rect width="{W}" height="{H}" rx="18" fill="{t["bg"]}"/>'
        f'<rect width="{W}" height="{H}" rx="18" fill="url(#dots)" opacity=".7"/>'
        f'{net}{left}{terminal}'
        f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="17" fill="none" stroke="url(#g)" stroke-opacity=".5"/>'
    )
    return svg(W, H, body, "zShan — I build products, and lead the teams that ship them")


def project_card(p, t):
    W, H = 420, 196
    pills, x = [], 24
    for s in p["stack"]:
        w = len(s) * 7.4 + 20
        pills.append(f'<rect x="{x}" y="148" width="{w:.0f}" height="24" rx="12" fill="{t["faint"]}"/>'
                     f'<text x="{x + w / 2:.0f}" y="164.5" text-anchor="middle">{escape(s)}</text>')
        x += w + 8
    tagw = len(p["tag"]) * 7.6 + 18
    body = (
        f'<defs>{gradient("g", t)}</defs>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["card"]}" stroke="{t["border"]}"/>'
        f'<rect x="0" y="0" width="{W}" height="4" rx="2" fill="url(#g)"/>'
        f'<text x="24" y="52" font-family="{SANS}" font-size="24" font-weight="700" fill="{t["fg"]}">{escape(p["name"])}</text>'
        f'<rect x="{W - 24 - tagw:.0f}" y="31" width="{tagw:.0f}" height="24" rx="6" fill="none" stroke="url(#g)"/>'
        f'<text x="{W - 24 - tagw / 2:.0f}" y="47.5" text-anchor="middle" font-family="{MONO}" font-size="11.5" '
        f'font-weight="700" letter-spacing="1" fill="{t["a1"]}">{escape(p["tag"])}</text>'
        f'<g font-family="{SANS}" font-size="15" fill="{t["muted"]}">'
        f'<text x="24" y="92">{escape(p["line1"])}</text><text x="24" y="115">{escape(p["line2"])}</text></g>'
        f'<g font-family="{MONO}" font-size="12" fill="{t["fg"]}">{"".join(pills)}</g>'
    )
    return svg(W, H, body, f'{p["name"]} — {p["line1"]} {p["line2"]}')


def stats_card(s, t):
    W, H = 860, 132
    tiles = [(f'{s["merged"]:,}', "PRs merged, last 12 mo"),
             (f'{s["reviewed"]:,}', "teammates' PRs reviewed"),
             (f'{s["contributions"]:,}', "contributions, last 12 mo"),
             (str(s["org_repos"]), "repos I help run")]
    out = []
    for i, (big, small) in enumerate(tiles):
        x = 32 + i * 207
        out.append(f'<text x="{x}" y="70" font-family="{SANS}" font-size="38" font-weight="800" fill="url(#g)">{big}</text>'
                   f'<text x="{x}" y="96" font-family="{MONO}" font-size="12.5" fill="{t["muted"]}">{escape(small)}</text>')
    body = (
        f'<defs>{gradient("g", t)}</defs>'
        f'<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="14" fill="{t["card"]}" stroke="{t["border"]}"/>'
        f'{"".join(out)}'
        f'<text x="{W - 20}" y="{H - 12}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{t["muted"]}" opacity=".7">'
        f'auto-updated {datetime.now(timezone.utc):%Y-%m-%d}</text>'
    )
    return svg(W, H, body, "GitHub stats")


def stack_strip(t):
    groups = [("lang", ["TypeScript", "Python", "Dart", "C / C++"]),
              ("web", ["Next.js", "React", "Node", "FastAPI"]),
              ("ai", ["LLM agents", "RAG", "Embeddings", "Transformers"]),
              ("ship", ["Vercel", "Firebase", "AWS", "Claude Code"])]
    W, rows = 860, []
    for r, (label, items) in enumerate(groups):
        y = 4 + r * 44
        rows.append(f'<text x="2" y="{y + 18}" font-family="{MONO}" font-size="12" fill="{t["muted"]}">{label}</text>')
        x = 52
        for it in items:
            w = len(it) * 8.2 + 32
            rows.append(f'<rect x="{x:.0f}" y="{y}" width="{w:.0f}" height="28" rx="8" fill="{t["card"]}" stroke="{t["border"]}"/>'
                        f'<circle cx="{x + 14:.0f}" cy="{y + 14}" r="3.5" fill="url(#g)"/>'
                        f'<text x="{x + 24:.0f}" y="{y + 18.5}">{escape(it)}</text>')
            x += w + 10
    body = (f'<defs>{gradient("g", t)}</defs>'
            f'<g font-family="{SANS}" font-size="14" font-weight="600" fill="{t["fg"]}">{"".join(rows)}</g>')
    return svg(W, 8 + len(groups) * 44, body, "Tech stack")


def divider(t):
    W, H = 860, 24
    # repeat the wave across, drifting slowly
    wave = "".join(f'<use href="#w" x="{i * 107.5}"/>' for i in range(10))
    body = (f'<defs>{gradient("g", t, True)}<path id="w" d="M0 12 Q 26.875 2 53.75 12 T 107.5 12" fill="none" '
            f'stroke="url(#g)" stroke-width="2" stroke-linecap="round"/></defs>'
            f'<g opacity=".65">{wave}<animateTransform attributeName="transform" type="translate" '
            f'values="0 0;-107.5 0" dur="6s" repeatCount="indefinite"/></g>')
    return svg(W, H, body, "divider")


def main():
    stats = fetch_stats()
    ASSETS.mkdir(exist_ok=True)
    for old in ASSETS.glob("*.svg"):
        old.unlink()
    for name, t in THEMES.items():
        (ASSETS / f"hero-{name}.svg").write_text(hero(t, stats))
        (ASSETS / f"stats-{name}.svg").write_text(stats_card(stats, t))
        (ASSETS / f"stack-{name}.svg").write_text(stack_strip(t))
        (ASSETS / f"divider-{name}.svg").write_text(divider(t))
        for p in PROJECTS:
            (ASSETS / f"card-{p['slug']}-{name}.svg").write_text(project_card(p, t))
    print("built", len(list(ASSETS.glob("*.svg"))), "svgs with", stats)


if __name__ == "__main__":
    main()
