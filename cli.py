#!/usr/bin/env python3
"""Herramienta de línea de comandos para un análisis RST ligero.

El objetivo es contar con un único módulo ejecutable que pueda procesar
textos desde la terminal sin dependencias adicionales. El análisis es
heurístico y determinista; no intenta ser exhaustivo, pero entrega una
estructura consistente para inspeccionar textos rápidamente.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

Lang = str

LANGUAGE_MARKERS: Dict[Lang, Sequence[str]] = {
    "es": (" el ", " la ", " de ", " que ", " los ", "las ", "ñ", "¿", "¡"),
    "en": (" the ", " and ", " of ", " to ", "ing ", "tion"),
    "auto": (),
}

ALLOWED_RELATIONS: Sequence[str] = (
    "Elaboration",
    "Background",
    "Explanation",
    "Sequence",
    "Contrast",
    "Evaluation",
    "Summary",
)


@dataclass
class Span:
    start: int
    end: int


@dataclass
class EDU:
    id: int
    text: str
    span: Span


@dataclass
class RelationRole:
    edu_ids: List[int]


@dataclass
class Relation:
    type: str
    nucleus: RelationRole
    satellite: RelationRole
    confidence: float


def _short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]


def _estimate_tokens(text: str) -> int:
    return max(1, len(text.split()))


def _detect_language(text: str, hint: Optional[str]) -> Lang:
    if hint in ("es", "en"):
        return hint  # type: ignore[return-value]
    lowered = f" {text.lower()} "
    for marker in LANGUAGE_MARKERS["es"]:
        if marker.strip() in {"ñ", "¿", "¡"} and marker.strip() in lowered:
            return "es"
        if marker in lowered:
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


def _relation_types(ruleset: str) -> Iterable[str]:
    if ruleset == "minimal":
        while True:
            yield "Elaboration"
    while True:
        for relation in ALLOWED_RELATIONS:
            yield relation


def _generate_relations(edus: List[EDU], *, ruleset: str) -> List[Relation]:
    if len(edus) < 2:
        return []
    selector = _relation_types(ruleset)
    relations: List[Relation] = []
    for edu_a, edu_b in zip(edus, edus[1:]):
        relations.append(
            Relation(
                type=next(selector),
                nucleus=RelationRole(edu_ids=[edu_a.id]),
                satellite=RelationRole(edu_ids=[edu_b.id]),
                confidence=0.6,
            )
        )
    return relations


def _build_brackets(edus: List[EDU], relations: List[Relation]) -> str:
    if not edus:
        return "(Summary)"
    nodes = [f"(N {edu.id})" for edu in edus]
    relation_iter = iter(relations) if relations else iter([])
    while len(nodes) > 1:
        left = nodes.pop(0)
        right = nodes.pop(0)
        try:
            relation = next(relation_iter)
        except StopIteration:
            relation_iter = iter(relations)
            relation = next(relation_iter) if relations else None
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


def analyze_text(
    text: str,
    *,
    lang_hint: Optional[str] = None,
    ruleset: str = "extended",
) -> Dict:
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

    return {
        "id": _short_hash(raw),
        "lang": lang,
        "edus": [
            {
                "id": edu.id,
                "text": edu.text,
                "span": {"start": edu.span.start, "end": edu.span.end},
            }
            for edu in edus
        ],
        "relations": [
            {
                "type": rel.type,
                "nucleus": {"edu_ids": rel.nucleus.edu_ids},
                "satellite": {"edu_ids": rel.satellite.edu_ids},
                "confidence": rel.confidence,
            }
            for rel in relations
        ],
        "tree": {"format": "brackets", "value": tree_value},
        "pragmatic_summary": summary,
        "metadata": {
            "chars": len(raw),
            "tokens_est": _estimate_tokens(raw),
            "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "ruleset": ruleset,
        },
    }


def analyze_many(
    texts: List[str],
    *,
    max_workers: int = 4,
    lang_hint: Optional[str] = None,
    ruleset: str = "extended",
) -> List[Dict]:
    if not texts:
        return []

    results: List[Optional[Dict]] = [None] * len(texts)

    def _task(idx_text: int, value: str) -> None:
        results[idx_text] = analyze_text(value, lang_hint=lang_hint, ruleset=ruleset)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(_task, idx, text): idx for idx, text in enumerate(texts)
        }
        for future in as_completed(futures):
            future.result()

    return [res for res in results if res is not None]


def brackets_to_dot(brackets: str) -> str:
    counter = {"i": 0}
    lines: List[str] = ["digraph RST {", "  node [shape=box];"]
    idx = 0

    def new_id() -> str:
        counter["i"] += 1
        return f"n{counter['i']}"

    def parse() -> str:
        nonlocal idx
        assert brackets[idx] == "("
        idx += 1
        label_chars: List[str] = []
        while idx < len(brackets) and brackets[idx] not in " ()":
            label_chars.append(brackets[idx])
            idx += 1
        label = "".join(label_chars)
        node_id = new_id()
        lines.append(f"  {node_id} [label=\"{label}\"];")
        while idx < len(brackets) and brackets[idx] != ")":
            if brackets[idx].isspace():
                idx += 1
                continue
            if brackets[idx] == "(":
                child_id = parse()
                lines.append(f"  {node_id} -> {child_id};")
            else:
                token_chars: List[str] = []
                while idx < len(brackets) and brackets[idx] not in " )":
                    token_chars.append(brackets[idx])
                    idx += 1
                token = "".join(token_chars)
                child_id = new_id()
                lines.append(f"  {child_id} [label=\"{token}\"];")
                lines.append(f"  {node_id} -> {child_id};")
        idx += 1
        return node_id

    while idx < len(brackets):
        if brackets[idx].isspace():
            idx += 1
            continue
        if brackets[idx] == "(":
            parse()
        else:
            idx += 1

    lines.append("}")
    return "\n".join(lines)


def read_inputs(inp: str) -> List[str]:
    if not inp or inp == "-":
        return [sys.stdin.read()]
    if os.path.isdir(inp):
        texts: List[str] = []
        for root, _, files in os.walk(inp):
            for fn in files:
                if fn.lower().endswith((".txt", ".md")):
                    with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
                        texts.append(f.read())
        return texts
    if os.path.isfile(inp):
        with open(inp, "r", encoding="utf-8") as f:
            data = f.read()
        lines = [l.strip() for l in data.splitlines() if l.strip()]
        if len(lines) > 1 and all(os.path.exists(l) for l in lines):
            texts: List[str] = []
            for path in lines:
                with open(path, "r", encoding="utf-8") as g:
                    texts.append(g.read())
            return texts
        return [data]
    raise SystemExit(f"--in no válido: {inp}")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Analizador pragmático retórico (RST) simplificado"
    )
    ap.add_argument("--in", dest="inp", required=True, help="archivo.txt | carpeta | - (STDIN)")
    ap.add_argument("--out", dest="out", required=True, help="directorio de salida")
    ap.add_argument("--json", dest="emit_json", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--txt", dest="emit_txt", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--diagram", action="store_true", help="emitir .dot (Graphviz) además del árbol en brackets")
    ap.add_argument("--lang-hint", default=None, help="es|en|auto")
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--ruleset", choices=["minimal", "extended"], default="extended")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    texts = read_inputs(args.inp)

    results = analyze_many(
        texts,
        max_workers=args.max_workers,
        lang_hint=args.lang_hint,
        ruleset=args.ruleset,
    )

    for i, res in enumerate(results, start=1):
        base = f"rst_{i:03d}_{res['id']}"
        if args.emit_json:
            with open(os.path.join(args.out, base + ".json"), "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False, indent=2)
        if args.emit_txt:
            with open(os.path.join(args.out, base + ".txt"), "w", encoding="utf-8") as f:
                f.write("EDUs\n")
                for edu in res["edus"]:
                    f.write(f"[{edu['id']}] {edu['text']}\n")
                f.write("\nRelaciones (tipo | Nucleus | Satellite | conf)\n")
                for rel in res["relations"]:
                    f.write(
                        f"{rel['type']} | {','.join(map(str, rel['nucleus']['edu_ids']))} | "
                        f"{','.join(map(str, rel['satellite']['edu_ids']))} | {rel['confidence']:.2f}\n"
                    )
                f.write("\nÁrbol (brackets)\n")
                f.write(res["tree"]["value"] + "\n")
                f.write("\nResumen pragmático\n")
                f.write(res.get("pragmatic_summary", "") + "\n")
        if args.diagram:
            dot = brackets_to_dot(res["tree"]["value"])
            with open(os.path.join(args.out, base + ".dot"), "w", encoding="utf-8") as f:
                f.write(dot)

    print(f"OK · {len(results)} textos procesados · salida en {args.out}")


if __name__ == "__main__":
    main()
