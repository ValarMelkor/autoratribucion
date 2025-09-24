"""Definiciones de esquemas Pydantic para el análisis RST."""

from __future__ import annotations

from typing import Dict, List, Literal

from pydantic import BaseModel, ConfigDict, Field


Lang = Literal["es", "en", "auto"]


class Span(BaseModel):
    """Rango de caracteres asociado a una unidad discursiva."""

    start: int = Field(ge=0)
    end: int = Field(ge=0)


class EDU(BaseModel):
    """Elementary Discourse Unit."""

    id: int
    text: str
    span: Span


class RoleChunk(BaseModel):
    """Colección de IDs de EDUs que actúan como núcleo o satélite."""

    edu_ids: List[int] = Field(default_factory=list)


RelationType = Literal[
    "Elaboration",
    "Evidence",
    "Justify",
    "Contrast",
    "Concession",
    "Cause",
    "Result",
    "Condition",
    "Purpose",
    "Background",
    "Summary",
    "Antithesis",
    "Enablement",
    "Circumstance",
]


class Relation(BaseModel):
    """Relación retórica entre uno o varios EDUs."""

    type: RelationType
    nucleus: RoleChunk
    satellite: RoleChunk
    confidence: float = Field(ge=0.0, le=1.0)


class Tree(BaseModel):
    """Representación estructurada del análisis."""

    format: Literal["brackets", "newick"]
    value: str


class RSTResult(BaseModel):
    """Resultado completo para un texto analizado."""

    model_config = ConfigDict(extra="ignore")

    id: str
    lang: Lang
    edus: List[EDU]
    relations: List[Relation]
    tree: Tree
    pragmatic_summary: str
    metadata: Dict[str, object]


class ADKPayload(BaseModel):
    """Payload de entrada esperado por el adaptador ADK."""

    texts: List[str]
    lang_hint: Lang = "auto"
    ruleset: Literal["minimal", "extended"] = "extended"


class Artifact(BaseModel):
    """Artefacto generado por el adaptador ADK."""

    path: str


class ADKResponse(BaseModel):
    """Respuesta serializable para ADK."""

    results: List[RSTResult]
    artifacts: List[Artifact] = Field(default_factory=list)

