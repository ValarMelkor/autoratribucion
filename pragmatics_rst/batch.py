from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from .core import analyze_rst




def analyze_many(texts: List[str], *, max_workers: int = 4, lang_hint: Optional[str] = None,
model: Optional[str] = None, ruleset: str = "extended") -> List[Dict]:
"""Ejecuta análisis RST sobre 1..N textos en paralelo (hilos)."""
results: List[Dict] = []
with ThreadPoolExecutor(max_workers=max_workers) as ex:
futures = [ex.submit(analyze_rst, t, lang_hint=lang_hint, model=model, ruleset=ruleset) for t in texts]
for fut in as_completed(futures):
results.append(fut.result())
# conservar orden de entrada aprox. por id hash
return results
