"""Implementación local y determinista de un analizador RST ligero."""

from __future__ import annotations

import hashlib
import os
import re
import time
from itertools import cycle
from typing import Dict, Iterable, List, Optional, Sequence

from .schemas import (
    EDU,
    Lang,
    Relation,
    RoleChunk,
    RSTResult,
    Span,
    Tree,
    ValidationError,
    ALLOWED_RELATIONS,
)

MODEL_NAME = os.getenv("OPENAI_MODEL", "mock-gpt-rst")

LANGUAGE_MARKERS: Dict[Lang, Sequence[str]] = {
    "es": (" el ", " la ", " de ", " que ", " los ", "las ", "ñ", "¿", "¡"),
    "en": (" the ", " and ", " of ", " to ", "ing ", "tion"),
    "auto": (),
}

EXTENDED_RELATION_ROTATION: Sequence[str] = tuple(ALLOWED_RELATIONS)


def _short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _detect_language(text: str, hint: Optional[str]) -> Lang:
    if hint in ("es", "en"):
        return hint  # type: ignore[return-value]
    lowered = f" {text.lower()} "
    for marker in LANGUAGE_MARKERS["es"]:
        if marker.strip() in {"ñ", "¿", "¡"}:
            if marker.strip() in lowered:
                return "es"
        elif marker in lowered:
            return "es"
    return "en"


def _tokenize_sentences(text: str) -> List[str]:
    splitter = re.compile(r"(?<=[.!?¡¿])\s+|\n{2,}")
    pieces = [segment.strip() for segment in splitter.split(text) if segment.strip()]
    if not pieces:
        pieces = [text.strip()]
    return pieces


def _build_span(text: str, fragment: str, start_hint: int) -> Span:
    window = text[start_hint:]
    match = window.find(fragment)
    if match == -1:
        start = start_hint
    else:
        start = start_hint + match
    end = start + len(fragment)
    return Span(start=start, end=end)


def _generate_edus(text: str) -> List[EDU]:
    edus: List[EDU] = []
    cursor = 0
    for idx, sentence in enumerate(_tokenize_sentences(text), start=1):
        span = _build_span(text, sentence, cursor)
        cursor = span.end
        edus.append(EDU(id=idx, text=sentence, span=span))
    return edus


def _relation_type_sequence(ruleset: str) -> Iterable[str]:
    if ruleset == "minimal":
        return cycle(["Elaboration"])
    return cycle(EXTENDED_RELATION_ROTATION or ["Elaboration"])


def _generate_relations(edus: List[EDU], *, ruleset: str) -> List[Relation]:
    if len(edus) < 2:
        return []
    selector = _relation_type_sequence(ruleset)
    relations: List[Relation] = []
    for edu_a, edu_b, relation_type in zip(edus, edus[1:], selector):
        relations.append(
            Relation(
                type=relation_type,
                nucleus=RoleChunk(edu_ids=[edu_a.id]),
                satellite=RoleChunk(edu_ids=[edu_b.id]),
                confidence=0.6,
            )
        )
    return relations


def _build_brackets(edus: List[EDU], relations: List[Relation]) -> str:
    if not edus:
        return "(Summary)"
    nodes = [f"(N {edu.id})" for edu in edus]
    relation_cycle = cycle(relations) if relations else cycle([None])
    while len(nodes) > 1:
        left = nodes.pop(0)
        right = nodes.pop(0)
        relation = next(relation_cycle)
        rel_type = relation.type if relation else "Elaboration"
        nodes.insert(0, f"({rel_type} {left} {right})")
    return f"(Background {nodes[0]})"


def _build_summary(edus: List[EDU], lang: Lang) -> str:
    if not edus:
        return ""
    sentences = [edu.text for edu in edus[:2]]
    summary = " ".join(sentences)
    prefix = "Resumen: " if lang == "es" else "Summary: "
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

    if ruleset not in {"minimal", "extended"}:
        raise ValueError("ruleset debe ser 'minimal' o 'extended'")

    lang = _detect_language(raw, lang_hint)
    edus = _generate_edus(raw)
    relations = _generate_relations(edus, ruleset=ruleset)
    tree_value = _build_brackets(edus, relations)
    summary = _build_summary(edus, lang)

    result = RSTResult(
        id=_short_hash(raw),
        lang=lang,
        edus=edus,
        relations=relations,
        tree=Tree(format="brackets", value=tree_value),
        pragmatic_summary=summary,
        metadata={
            "chars": len(raw),
            "tokens_est": _estimate_tokens(raw),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ruleset": ruleset,
            "model": model or MODEL_NAME,
        },
    )

    try:
        validated = RSTResult.model_validate(result.model_dump())
    except ValidationError as exc:
        raise ValueError(f"Resultado RST inválido: {exc}") from exc

    return validated.model_dump()

