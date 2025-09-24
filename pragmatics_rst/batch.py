"""Ejecutores en lote para el análisis RST."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from .core import analyze_rst


def analyze_many(
    texts: List[str],
    *,
    max_workers: int = 4,
    lang_hint: Optional[str] = None,
    model: Optional[str] = None,
    ruleset: str = "extended",
) -> List[Dict]:
    """Ejecuta ``analyze_rst`` sobre una lista de textos en paralelo."""

    if not texts:
        return []

    results: List[Dict] = [None] * len(texts)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                analyze_rst, text, lang_hint=lang_hint, model=model, ruleset=ruleset
            ): idx
            for idx, text in enumerate(texts)
        }
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()
    return results

