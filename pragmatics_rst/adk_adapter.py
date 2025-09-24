"""Adaptador sencillo para integrar el analizador con ADK."""

from __future__ import annotations

import os
import tempfile
from typing import Dict

from .batch import analyze_many
from .schemas import ADKPayload, ADKResponse, Artifact
from rst_tree import brackets_to_dot


def run(payload: Dict) -> Dict:
    """Ejecuta el análisis y construye artefactos compatibles con ADK."""

    request = ADKPayload.model_validate(payload)
    results = analyze_many(
        request.texts, lang_hint=request.lang_hint, ruleset=request.ruleset
    )

    artifacts = []
    try:
        if results:
            graphs = [brackets_to_dot(r["tree"]["value"]) for r in results]
            dot_content = "\n\n".join(graphs)
            tmpdir = tempfile.mkdtemp(prefix="rst_forest_")
            outpath = os.path.join(tmpdir, "forest.dot")
            with open(outpath, "w", encoding="utf-8") as handle:
                handle.write(dot_content)
            artifacts = [Artifact(path=outpath)]
    except Exception:
        artifacts = []

    response = ADKResponse(results=results, artifacts=artifacts)
    return response.model_dump()

