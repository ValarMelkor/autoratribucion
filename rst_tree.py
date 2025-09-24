```python
from __future__ import annotations
from typing import List, Optional, Tuple

class RSTNode:
    """Nodo RST minimalista.

    Atributos:
        label: nombre de la relación o etiqueta de hoja ("EDU:<id>")
        role: "N" | "S" | None
        children: lista de (role, child)
        edu_id: entero si es hoja; None si es interno
    """

    def __init__(self, label: str, role: Optional[str] = None, edu_id: Optional[int] = None):
        self.label = label
        self.role = role
        self.children: List[Tuple[Optional[str], RSTNode]] = []
        self.edu_id = edu_id

    def add(self, child: "RSTNode", role: Optional[str] = None):
        self.children.append((role, child))
        return self

    # --- Exportadores ---
    def to_brackets(self) -> str:
        if self.edu_id is not None:
            return f"({self.role or ''} {self.edu_id})".strip()
        inside = " ".join(
            f"({c.role or ''} {c.to_brackets()})" if c.edu_id is None else c.to_brackets()
            for (_, c) in self.children
        )
        return f"({self.label} {inside})"

    def to_newick(self) -> str:
        if self.edu_id is not None:
            return f"EDU{self.edu_id}"
        inside = ",".join(c.to_newick() for (_, c) in self.children)
        return f"({inside}){self.label}"

# --- Utilidades DOT ---

def brackets_to_dot(brackets: str) -> str:
    """Convierte una representación entre paréntesis a DOT (Graphviz).
    Estrategia: parseo recursivo simple con índices, generando nodos numerados.
    """
    counter = {"i": 0}
    lines = ["digraph RST {", "  node [shape=box];"]

    def new_id():
        counter["i"] += 1
        return f"n{counter['i']}"

    idx = 0

    def parse() -> Tuple[str, str]:
        nonlocal idx
        assert brackets[idx] == '('
        idx += 1
        # Leer etiqueta hasta espacio o '('
        label = []
        while idx < len(brackets) and brackets[idx] not in [' ', '(' ,')']:
            label.append(brackets[idx]); idx += 1
        label = "".join(label)
        node_id = new_id()
        lines.append(f"  {node_id} [label=\"{label}\"];\n")
        # hijos o hoja
        while idx < len(brackets) and brackets[idx] != ')':
            if brackets[idx] == ' ':
                idx += 1; continue
            if brackets[idx] == '(':
                child_id, _ = parse()
                lines.append(f"  {node_id} -> {child_id};\n")
            else:
                # token suelto (p.ej., '1' tras 'N')
                # consumimos hasta espacio o paréntesis
                token = []
                while idx < len(brackets) and brackets[idx] not in [' ', ')']:
                    token.append(brackets[idx]); idx += 1
                # Representar token como hijo hoja
                cid = new_id()
                tok = "".join(token)
                lines.append(f"  {cid} [label=\"{tok}\"];\n")
                lines.append(f"  {node_id} -> {cid};\n")
        idx += 1  # consume ')'
        return node_id, label

    while idx < len(brackets):
        if brackets[idx].isspace():
            idx += 1; continue
        if brackets[idx] == '(':
            parse()
        else:
            idx += 1
    lines.append("}")
    return "\n".join(lines)
