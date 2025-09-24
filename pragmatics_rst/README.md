# pragmatics_rst — Análisis pragmático retórico (RST) con OpenAI

**Objetivo**: dado 1..N textos, producir por cada uno segmentación en **EDUs**, relaciones **RST** con **Nucleus/Satellite**, árbol en formato **brackets** y **resumen pragmático**. Salidas en **JSON** (ADK‑ready) y **.txt** legible; opción de **.dot** (Graphviz).

> Teoría: Mann & Thompson (1987), *Rhetorical Structure Theory*.

## Instalación

```bash
pip install openai pydantic
# exporta tu API key
export OPENAI_API_KEY=sk-...
# (opcional) el modelo por defecto
export OPENAI_MODEL=gpt-4o
