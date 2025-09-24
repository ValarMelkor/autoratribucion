from __future__ import annotations
import os, tempfile
from typing import Dict
from .schemas import ADKPayload, ADKResponse, Artifact
from .batch import analyze_many
from rst_tree import brackets_to_dot




def run(payload: Dict) -> Dict:
"""Adaptador ADK genérico.


Espera: {"texts": [...], "lang_hint": "auto", "ruleset": "extended"}
Devuelve: {"results": [...], "artifacts": [{"path": ".../forest.dot"}]}
"""
req = ADKPayload.model_validate(payload)
results = analyze_many(req.texts, lang_hint=req.lang_hint, ruleset=req.ruleset)


# Artefacto DOT opcional (bosque combinado)
try:
dot = "digraph Forest {\n node [shape=box];\n}"
if results:
graphs = [brackets_to_dot(r["tree"]["value"]) for r in results]
dot = "\n\n".join(graphs)
tmpdir = tempfile.mkdtemp(prefix="rst_forest_")
outpath = os.path.join(tmpdir, "forest.dot")
with open(outpath, "w", encoding="utf-8") as f:
f.write(dot)
artifacts = [Artifact(path=outpath)]
except Exception:
artifacts = []


return ADKResponse(results=results, artifacts=artifacts).model_dump()
