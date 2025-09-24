from __future__ import annotations
r["nucleus"]["edu_ids"] = [next_edu_id if i == old_id else i for i in r["nucleus"]["edu_ids"]]
r["satellite"]["edu_ids"] = [next_edu_id if i == old_id else i for i in r["satellite"]["edu_ids"]]
next_edu_id += 1


all_edus.extend(edus)
# clamp confidences
for r in relations:
r["confidence"] = max(0.0, min(1.0, float(r.get("confidence", 0.5))))
all_relations.extend(relations)
if tree and tree.get("value"):
bracket_forests.append(tree["value"]) # bosque por chunk


# Si hay múltiples árboles por chunk, unir en un pseudo-árbol secuencial
if len(bracket_forests) == 1:
full_brackets = bracket_forests[0]
elif len(bracket_forests) > 1:
# Construir un bracket wrapper que los conecte con Elaboration secuencial
inner = " ".join(f"(Elaboration {b})" for b in bracket_forests)
full_brackets = f"(Background {inner})"
else:
# fallback mínimo si el modelo no devolvió árbol
leaves = " ".join(f"(N {e['id']})" for e in all_edus[:min(4, len(all_edus))])
full_brackets = f"(Summary {leaves})"


result = {
"id": _short_hash(raw),
"lang": lang,
"edus": all_edus,
"relations": all_relations,
"tree": {"format": "brackets", "value": full_brackets},
"pragmatic_summary": data.get("pragmatic_summary", "") if chunks else "",
"metadata": {
"chars": len(raw),
"tokens_est": _estimate_tokens(raw),
"timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
"ruleset": ruleset,
"model": model or MODEL_NAME,
},
}


# Validación pydantic
try:
RSTResult.model_validate(result)
except ValidationError as e:
# Relajar si el árbol/relaciones faltan: garantizar estructura mínima
if not result.get("relations"):
result["relations"] = []
if not result.get("tree"):
result["tree"] = {"format": "brackets", "value": "(Summary (N 1))"}
RSTResult.model_validate(result) # reintento
return result
