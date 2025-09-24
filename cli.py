#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys, os, json
from typing import List
from pragmatics_rst import analyze_rst
from pragmatics_rst.batch import analyze_many
from rst_tree import brackets_to_dot


def read_inputs(inp: str) -> List[str]:
    if not inp or inp == "-":
        return [sys.stdin.read()]
    if os.path.isdir(inp):
        texts = []
        for root, _, files in os.walk(inp):
            for fn in files:
                if fn.lower().endswith((".txt", ".md")):
                    with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
                        texts.append(f.read())
        return texts
    if os.path.isfile(inp):
        # ¿lista de rutas o un único archivo de texto?
        with open(inp, "r", encoding="utf-8") as f:
            data = f.read()
        # si contiene saltos de línea con rutas existentes, asume lista
        lines = [l.strip() for l in data.splitlines() if l.strip()]
        if len(lines) > 1 and all(os.path.exists(l) for l in lines):
            texts = []
            for p in lines:
                with open(p, "r", encoding="utf-8") as g:
                    texts.append(g.read())
            return texts
        return [data]
    raise SystemExit(f"--in no válido: {inp}")


def main():
    ap = argparse.ArgumentParser(description="Análisis pragmático retórico (RST)")
    ap.add_argument("--in", dest="inp", required=True, help="archivo.txt | carpeta | - (STDIN)")
    ap.add_argument("--out", dest="out", required=True, help="directorio de salida")
    ap.add_argument("--json", dest="emit_json", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--txt", dest="emit_txt", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--diagram", action="store_true", help="emitir .dot (Graphviz) además del árbol en brackets")
    ap.add_argument("--lang-hint", default=None, help="es|en|auto")
    ap.add_argument("--max-workers", type=int, default=4)
    ap.add_argument("--model", default=None, help="override del modelo; por defecto OPENAI_MODEL")
    ap.add_argument("--ruleset", choices=["minimal", "extended"], default="extended")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    texts = read_inputs(args.inp)

    results = analyze_many(texts, max_workers=args.max_workers, lang_hint=args.lang_hint, model=args.model, ruleset=args.ruleset)

    for i, res in enumerate(results, start=1):
        base = f"rst_{i:03d}_{res['id']}"
        if args.emit_json:
            with open(os.path.join(args.out, base + ".json"), "w", encoding="utf-8") as f:
                json.dump(res, f, ensure_ascii=False, indent=2)
        if args.emit_txt:
            with open(os.path.join(args.out, base + ".txt"), "w", encoding="utf-8") as f:
                # EDUs
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
