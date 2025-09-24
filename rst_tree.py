"""Herramientas para manipular representaciones de árboles RST."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class RSTNode:
    """Nodo ligero para árboles RST."""

    label: str
    role: Optional[str] = None
    edu_id: Optional[int] = None
    children: List[Tuple[Optional[str], "RSTNode"]] = field(default_factory=list)

    def add(self, child: "RSTNode", role: Optional[str] = None) -> "RSTNode":
        self.children.append((role, child))
        return self

    def to_brackets(self) -> str:
        if self.edu_id is not None:
            token = f"{self.role or 'N'} {self.edu_id}".strip()
            return f"({token})"
        inside = []
        for role, child in self.children:
            if child.edu_id is None:
                inside.append(f"({role or ''} {child.to_brackets()})".strip())
            else:
                inside.append(child.to_brackets())
        joined = " ".join(inside)
        return f"({self.label} {joined})"

    def to_newick(self) -> str:
        if self.edu_id is not None:
            return f"EDU{self.edu_id}"
        joined = ",".join(child.to_newick() for _, child in self.children)
        return f"({joined}){self.label}"


def brackets_to_dot(brackets: str) -> str:
    """Convierte un árbol en formato brackets a un grafo DOT."""

    counter = {"i": 0}
    lines: List[str] = ["digraph RST {", "  node [shape=box];"]
    idx = 0

    def new_id() -> str:
        counter["i"] += 1
        return f"n{counter['i']}"

    def parse() -> Tuple[str, str]:
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
                child_id, _ = parse()
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
        return node_id, label

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

