#!/usr/bin/env python3
"""Generate self-hosted SVG cards for the GitHub profile README.

The script uses only the Python standard library and GitHub's public REST API.
It is designed to run in GitHub Actions with the repository GITHUB_TOKEN.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

USERNAME = os.getenv("PROFILE_USERNAME", "matheusflorindo32")
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN", "")
API_ROOT = "https://api.github.com"
ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"

LANGUAGE_COLORS = {
    "JavaScript": "#f7df1e",
    "TypeScript": "#3178c6",
    "Python": "#3776ab",
    "HTML": "#e34f26",
    "CSS": "#1572b6",
    "Java": "#b07219",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "PHP": "#4f5d95",
    "Shell": "#89e051",
    "Jupyter Notebook": "#da5b0b",
    "Vue": "#41b883",
    "Dart": "#00b4ab",
    "Kotlin": "#a97bff",
}


def api_get(path: str) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USERNAME}-profile-stats",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"

    request = urllib.request.Request(f"{API_ROOT}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_repositories() -> list[dict[str, Any]]:
    repositories: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = api_get(
            f"/users/{USERNAME}/repos?type=owner&sort=updated&direction=desc&per_page=100&page={page}"
        )
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected response while reading repositories")
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repositories


def collect_languages(repositories: list[dict[str, Any]]) -> Counter[str]:
    totals: Counter[str] = Counter()
    for repository in repositories:
        if repository.get("fork") or repository.get("archived"):
            continue
        full_name = repository.get("full_name")
        if not full_name:
            continue
        try:
            languages = api_get(f"/repos/{full_name}/languages")
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            continue
        if isinstance(languages, dict):
            for language, amount in languages.items():
                if isinstance(amount, int) and amount > 0:
                    totals[language] += amount
    return totals


def overview_svg(profile: dict[str, Any], repositories: list[dict[str, Any]]) -> str:
    public_repos = int(profile.get("public_repos", len(repositories)))
    followers = int(profile.get("followers", 0))
    original_projects = sum(1 for repo in repositories if not repo.get("fork"))
    total_stars = sum(int(repo.get("stargazers_count", 0)) for repo in repositories)
    active_projects = sum(
        1 for repo in repositories if not repo.get("fork") and not repo.get("archived")
    )
    updated = datetime.now(timezone.utc).strftime("%d/%m/%Y")

    metrics = [
        (str(public_repos), "repositórios públicos"),
        (str(original_projects), "projetos originais"),
        (str(total_stars), "stars recebidas"),
        (str(followers), "seguidores"),
    ]

    boxes = []
    for index, (value, label) in enumerate(metrics):
        x = 24 + index * 134
        boxes.append(
            f'''<rect x="{x}" y="94" width="122" height="92" rx="14" fill="#ffffff" opacity="0.035" stroke="#334155"/>
    <text x="{x + 61}" y="137" text-anchor="middle" fill="#e5c56f" font-size="31" font-weight="800">{escape(value)}</text>
    <text x="{x + 61}" y="162" text-anchor="middle" fill="#cbd5e1" font-size="11.5">{escape(label)}</text>'''
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="580" height="230" viewBox="0 0 580 230" role="img" aria-labelledby="title desc">
  <title id="title">Estatísticas públicas do GitHub</title>
  <desc id="desc">Repositórios, projetos originais, estrelas e seguidores de {escape(USERNAME)}.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0b1525"/>
      <stop offset="1" stop-color="#172235"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="578" height="228" rx="20" fill="url(#bg)" stroke="#334155"/>
  <rect x="24" y="24" width="5" height="34" rx="2.5" fill="#d4af37"/>
  <text x="42" y="48" fill="#f8fafc" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="22" font-weight="700">GitHub em números</text>
  <text x="42" y="70" fill="#94a3b8" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="13">Dados públicos calculados pela API oficial do GitHub</text>
  <g font-family="Inter,Segoe UI,Arial,sans-serif">
    {''.join(boxes)}
  </g>
  <circle cx="28" cy="207" r="4" fill="#22c55e"/>
  <text x="40" y="212" fill="#64748b" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12">{active_projects} projetos ativos • atualizado em {updated}</text>
</svg>'''


def languages_svg(language_totals: Counter[str]) -> str:
    updated = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    total = sum(language_totals.values())
    top_languages = language_totals.most_common(5)

    if total <= 0 or not top_languages:
        top_languages = [("Dados indisponíveis", 1)]
        total = 1

    rows = []
    for index, (language, amount) in enumerate(top_languages):
        percentage = amount / total * 100
        y = 97 + index * 27
        color = LANGUAGE_COLORS.get(language, "#d4af37")
        bar_width = max(4.0, min(310.0, percentage * 3.1))
        rows.append(
            f'''<circle cx="30" cy="{y}" r="5" fill="{color}"/>
    <text x="44" y="{y + 5}" fill="#e2e8f0" font-size="13" font-weight="600">{escape(language)}</text>
    <rect x="178" y="{y - 7}" width="310" height="10" rx="5" fill="#ffffff" opacity="0.055"/>
    <rect x="178" y="{y - 7}" width="{bar_width:.1f}" height="10" rx="5" fill="{color}" opacity="0.82"/>
    <text x="548" y="{y + 5}" text-anchor="end" fill="#94a3b8" font-size="12">{percentage:.1f}%</text>'''
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="580" height="230" viewBox="0 0 580 230" role="img" aria-labelledby="title desc">
  <title id="title">Linguagens do portfólio público</title>
  <desc id="desc">Distribuição das cinco principais linguagens por volume de código em repositórios públicos não arquivados.</desc>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0b1525"/>
      <stop offset="1" stop-color="#172235"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="578" height="228" rx="20" fill="url(#bg)" stroke="#334155"/>
  <rect x="24" y="24" width="5" height="34" rx="2.5" fill="#d4af37"/>
  <text x="42" y="48" fill="#f8fafc" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="22" font-weight="700">Linguagens do portfólio</text>
  <text x="42" y="70" fill="#94a3b8" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="13">Distribuição por bytes de código nos projetos públicos ativos</text>
  <g font-family="Inter,Segoe UI,Arial,sans-serif">
    {''.join(rows)}
  </g>
  <text x="24" y="216" fill="#64748b" font-family="Inter,Segoe UI,Arial,sans-serif" font-size="12">Atualizado automaticamente em {updated} • não representa nível de domínio</text>
</svg>'''


def main() -> int:
    try:
        profile = api_get(f"/users/{USERNAME}")
        repositories = fetch_repositories()
        languages = collect_languages(repositories)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError) as error:
        print(f"Profile statistics were not updated: {error}", file=sys.stderr)
        return 1

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    (ASSETS_DIR / "github-overview.svg").write_text(
        overview_svg(profile, repositories), encoding="utf-8"
    )
    (ASSETS_DIR / "top-languages.svg").write_text(
        languages_svg(languages), encoding="utf-8"
    )
    print("Profile statistics generated successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
