"""Definiciones ligeras de esquemas para el análisis RST."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Sequence


Lang = Literal["es", "en", "auto"]


class ValidationError(ValueError):
    """Error de validación con semántica similar a ``pydantic``."""


@dataclass
class _BaseSchema:
    """Proporciona utilidades compatibles con la API de Pydantic usada."""

    def model_dump(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def _ensure_dict(cls, value: "_BaseSchema | Dict[str, Any]") -> Dict[str, Any]:
        if isinstance(value, _BaseSchema):
            return value.model_dump()
        if isinstance(value, dict):
            return value
        raise ValidationError(f"{cls.__name__} requiere un diccionario válido")


@dataclass
class Span(_BaseSchema):
    """Rango de caracteres asociado a una unidad discursiva."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < 0:
            raise ValidationError("Los índices del span deben ser no negativos")
        if self.end < self.start:
            raise ValidationError("El final del span no puede ser menor que el inicio")

    @classmethod
    def model_validate(cls, value: Dict[str, Any] | "Span") -> "Span":
        data = cls._ensure_dict(value)
        try:
            return cls(start=int(data["start"]), end=int(data["end"]))
        except KeyError as exc:
            raise ValidationError(f"Falta el campo requerido {exc.args[0]} en Span") from exc


@dataclass
class EDU(_BaseSchema):
    """Elementary Discourse Unit."""

    id: int
    text: str
    span: Span

    @classmethod
    def model_validate(cls, value: Dict[str, Any] | "EDU") -> "EDU":
        data = cls._ensure_dict(value)
        try:
            span = Span.model_validate(data["span"])
            return cls(id=int(data["id"]), text=str(data["text"]), span=span)
        except KeyError as exc:
            raise ValidationError(f"Falta el campo requerido {exc.args[0]} en EDU") from exc


@dataclass
class RoleChunk(_BaseSchema):
    """Colección de IDs de EDUs que actúan como núcleo o satélite."""

    edu_ids: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.edu_ids = [int(value) for value in self.edu_ids]

    @classmethod
    def model_validate(cls, value: Dict[str, Any] | "RoleChunk") -> "RoleChunk":
        data = cls._ensure_dict(value)
        edu_ids = data.get("edu_ids", [])
        if not isinstance(edu_ids, Sequence):
            raise ValidationError("edu_ids debe ser una secuencia")
        return cls(edu_ids=list(edu_ids))


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


@dataclass
class Relation(_BaseSchema):
    """Relación retórica entre uno o varios EDUs."""

    type: RelationType
    nucleus: RoleChunk
    satellite: RoleChunk
    confidence: float = 0.0

    def __post_init__(self) -> None:
        allowed: Sequence[str] = (
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
        )
        if self.type not in allowed:
            raise ValidationError(f"Tipo de relación no soportado: {self.type}")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValidationError("La confianza debe estar entre 0 y 1")
        self.confidence = float(self.confidence)

    @classmethod
    def model_validate(cls, value: Dict[str, Any] | "Relation") -> "Relation":
        data = cls._ensure_dict(value)
        try:
            nucleus = RoleChunk.model_validate(data["nucleus"])
            satellite = RoleChunk.model_validate(data["satellite"])
            confidence = float(data.get("confidence", 0.0))
            return cls(
                type=data["type"],
                nucleus=nucleus,
                satellite=satellite,
                confidence=confidence,
            )
        except KeyError as exc:
            raise ValidationError(
                f"Falta el campo requerido {exc.args[0]} en Relation"
            ) from exc


@dataclass
class Tree(_BaseSchema):
    """Representación estructurada del análisis."""

    format: Literal["brackets", "newick"]
    value: str

    def __post_init__(self) -> None:
        if self.format not in {"brackets", "newick"}:
            raise ValidationError("Formato de árbol no soportado")
        self.value = str(self.value)

    @classmethod
    def model_validate(cls, value: Dict[str, Any] | "Tree") -> "Tree":
        data = cls._ensure_dict(value)
        try:
            return cls(format=data["format"], value=str(data["value"]))
        except KeyError as exc:
            raise ValidationError(f"Falta el campo requerido {exc.args[0]} en Tree") from exc


@dataclass
class RSTResult(_BaseSchema):
    """Resultado completo para un texto analizado."""

    id: str
    lang: Lang
    edus: List[EDU]
    relations: List[Relation]
    tree: Tree
    pragmatic_summary: str
    metadata: Dict[str, Any]

    def __post_init__(self) -> None:
        if self.lang not in ("es", "en", "auto"):
            raise ValidationError(f"Idioma no soportado: {self.lang}")
        if not isinstance(self.metadata, dict):
            raise ValidationError("metadata debe ser un diccionario")

    @classmethod
    def model_validate(cls, value: Dict[str, Any] | "RSTResult") -> "RSTResult":
        data = cls._ensure_dict(value)
        try:
            edus = [EDU.model_validate(item) for item in data.get("edus", [])]
            relations = [
                Relation.model_validate(item) for item in data.get("relations", [])
            ]
            tree = Tree.model_validate(data["tree"])
            return cls(
                id=str(data["id"]),
                lang=data["lang"],
                edus=edus,
                relations=relations,
                tree=tree,
                pragmatic_summary=str(data.get("pragmatic_summary", "")),
                metadata=dict(data.get("metadata", {})),
            )
        except KeyError as exc:
            raise ValidationError(
                f"Falta el campo requerido {exc.args[0]} en RSTResult"
            ) from exc


@dataclass
class ADKPayload(_BaseSchema):
    """Payload de entrada esperado por el adaptador ADK."""

    texts: List[str]
    lang_hint: Lang = "auto"
    ruleset: Literal["minimal", "extended"] = "extended"

    def __post_init__(self) -> None:
        if not isinstance(self.texts, list) or not all(
            isinstance(item, str) for item in self.texts
        ):
            raise ValidationError("texts debe ser una lista de strings")
        if self.lang_hint not in ("es", "en", "auto"):
            raise ValidationError("lang_hint debe ser es, en o auto")
        if self.ruleset not in ("minimal", "extended"):
            raise ValidationError("ruleset debe ser minimal o extended")

    @classmethod
    def model_validate(cls, value: Dict[str, Any] | "ADKPayload") -> "ADKPayload":
        data = cls._ensure_dict(value)
        texts = data.get("texts")
        if texts is None:
            raise ValidationError("texts es un campo obligatorio en ADKPayload")
        return cls(
            texts=list(texts),
            lang_hint=data.get("lang_hint", "auto"),
            ruleset=data.get("ruleset", "extended"),
        )


@dataclass
class Artifact(_BaseSchema):
    """Artefacto generado por el adaptador ADK."""

    path: str

    @classmethod
    def model_validate(cls, value: Dict[str, Any] | "Artifact") -> "Artifact":
        data = cls._ensure_dict(value)
        try:
            return cls(path=str(data["path"]))
        except KeyError as exc:
            raise ValidationError(f"Falta el campo requerido {exc.args[0]} en Artifact") from exc


@dataclass
class ADKResponse(_BaseSchema):
    """Respuesta serializable para ADK."""

    results: List[Dict[str, Any]]
    artifacts: List[Artifact] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.results, list):
            raise ValidationError("results debe ser una lista")
        self.artifacts = [Artifact.model_validate(a) for a in self.artifacts]


