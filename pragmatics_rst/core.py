"""Implementación local y determinista de un analizador RST ligero."""

from __future__ import annotations

import hashlib
import os
import re
import time
from typing import Dict, List, Optional

from .schemas import EDU, Lang, Relation, RoleChunk, RSTResult, Span, ValidationError

MODEL_NAME = os.getenv("OPENAI_MODEL", "mock-gpt-rst")


def _short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _detect_language(text: str, hint: Optional[str]) -> Lang:
    if hint and hint != "auto":
        return hint  # type: ignore[return-value]
    lowered = text.lower()
    spanish_markers = {" el ", " la ", " de ", " que ", " los ", "ñ", "¿", "¡"}
    for marker in spanish_markers:
        if marker.strip() in {"ñ", "¿", "¡"}:
            if marker in lowered:
                return "es"
        elif marker in lowered:
            return "es"
    return "en"


def _split_edus(text: str) -> List[Dict]:
    pattern = re.compile(r"(?<=[.!?])\s+|\n{2,}")
    raw_segments = [segment.strip() for segment in pattern.split(text) if segment.strip()]
    if not raw_segments:
        raw_segments = [text.strip()]

    edus: List[Dict] = []
    cursor = 0
    for idx, segment in enumerate(raw_segments, start=1):
        search = re.search(re.escape(segment), text[cursor:])
        if search is None:
            start = cursor
            end = start + len(segment)
        else:
            start = cursor + search.start()
            end = start + len(segment)
        cursor = end
        edus.append(
            EDU(
                id=idx,
                text=segment,
                span=Span(start=start, end=end),
            ).model_dump()
        )
    return edus


def _build_relations(edus: List[Dict]) -> List[Dict]:
    relations: List[Dict] = []
    for first, second in zip(edus, edus[1:]):
        relation = Relation(
            type="Elaboration",
            nucleus=RoleChunk(edu_ids=[first["id"]]),
            satellite=RoleChunk(edu_ids=[second["id"]]),
            confidence=0.6,
        )
        relations.append(relation.model_dump())
    return relations


def _build_brackets(edus: List[Dict]) -> str:
    if not edus:
        return "(Summary)"
    nodes = [f"(N {edu['id']})" for edu in edus]
    while len(nodes) > 1:
        left = nodes.pop(0)
        right = nodes.pop(0)
        nodes.insert(0, f"(Elaboration {left} {right})")
    return f"(Background {nodes[0]})"


def _build_summary(edus: List[Dict], lang: Lang) -> str:
    if not edus:
        return ""
    sentences = [edu["text"] for edu in edus[:2]]
    summary = " ".join(sentences)
    if lang == "es":
        prefix = "Resumen: "
    else:
        prefix = "Summary: "
    return prefix + summary


def analyze_rst(
    text: str,
    *,
    lang_hint: Optional[str] = None,
    model: Optional[str] = None,
    ruleset: str = "extended",
) -> Dict:
    """Analiza un texto y devuelve un resultado con formato RST."""

    raw = text.strip()
    if not raw:
        raise ValueError("El texto a analizar está vacío")

    lang = _detect_language(raw, lang_hint)
    edus = _split_edus(raw)
    relations = _build_relations(edus)
    tree_value = _build_brackets(edus)
    summary = _build_summary(edus, lang)

    result = {
        "id": _short_hash(raw),
        "lang": lang,
        "edus": edus,
        "relations": relations,
        "tree": {"format": "brackets", "value": tree_value},
        "pragmatic_summary": summary,
        "metadata": {
            "chars": len(raw),
            "tokens_est": _estimate_tokens(raw),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ruleset": ruleset,
            "model": model or MODEL_NAME,
        },
    }

    try:
        RSTResult.model_validate(result)
    except ValidationError:
        if not result["relations"]:
            result["relations"] = []
        if not result["tree"]:
            result["tree"] = {"format": "brackets", "value": "(Summary (N 1))"}
        RSTResult.model_validate(result)

    return result

