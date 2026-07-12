#!/usr/bin/env python3
"""Valida consistência documental e referências essenciais do perfil GitHub."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
METRICS = ROOT / "data" / "profile-metrics.json"
PUBLICATIONS = ROOT / "data" / "publications.json"

REQUIRED_ASSETS = [
    ROOT / "assets" / "authority-hero-3d.svg",
    ROOT / "assets" / "profile-impact.svg",
    ROOT / "assets" / "digital-ecosystem-3d.svg",
    ROOT / "assets" / "visual-engineering-stack.svg",
    ROOT / "assets" / "github-overview.svg",
    ROOT / "assets" / "top-languages.svg",
    ROOT / "assets" / "authority-quote.svg",
]

REQUIRED_DOMAINS = [
    "https://www.nucleotatico.com",
    "https://www.tropacientifica.com",
    "https://viapneusbr.com",
    "https://longevida50studio.com.br/",
    "https://conacips2025.com",
]

FORBIDDEN_PATTERNS = [
    r"REPLACE_WITH",
    r"TODO",
    r"TBD",
    r"wa\.me/",
    r"\(27\)\s*9?\d{4}[-\s]?\d{4}",
]


def fail(message: str) -> None:
    print(f"ERRO: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"arquivo ausente: {path.relative_to(ROOT)}")
    except json.JSONDecodeError as exc:
        fail(f"JSON inválido em {path.relative_to(ROOT)}: {exc}")


def main() -> None:
    if not README.exists():
        fail("README.md ausente")

    readme = README.read_text(encoding="utf-8")
    metrics = load_json(METRICS)
    publications = load_json(PUBLICATIONS)

    published = [item for item in publications if item.get("status") == "published"]
    if metrics.get("published_articles") != len(published):
        fail(
            "a métrica published_articles não corresponde ao total de publicações "
            f"com status published ({len(published)})"
        )

    dois = set()
    for item in published:
        doi = str(item.get("doi", "")).strip()
        if not doi or not re.fullmatch(r"10\.\d{4,9}/\S+", doi):
            fail(f"DOI ausente ou inválido: {item.get('title', 'sem título')}")
        if doi in dois:
            fail(f"DOI duplicado: {doi}")
        dois.add(doi)
        if doi not in readme:
            fail(f"DOI não referenciado no README: {doi}")

    for asset in REQUIRED_ASSETS:
        if not asset.exists():
            fail(f"ativo visual ausente: {asset.relative_to(ROOT)}")

    for domain in REQUIRED_DOMAINS:
        if domain not in readme:
            fail(f"produto publicado ausente do README: {domain}")

    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, readme, flags=re.IGNORECASE):
            fail(f"padrão proibido encontrado no README: {pattern}")

    expected = {
        "digital_products": 5,
        "published_articles": 4,
        "books_with_isbn": 3,
        "conference_works": 6,
        "public_safety_since": 2010,
    }
    for key, value in expected.items():
        if metrics.get(key) != value:
            fail(f"métrica inesperada em {key}: {metrics.get(key)!r}; esperado {value!r}")

    print("Perfil validado com sucesso.")
    print(f"Publicações verificadas: {len(published)}")
    print(f"Ativos visuais verificados: {len(REQUIRED_ASSETS)}")
    print(f"Produtos publicados verificados: {len(REQUIRED_DOMAINS)}")


if __name__ == "__main__":
    main()
