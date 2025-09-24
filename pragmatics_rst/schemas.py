"""Definiciones ligeras de esquemas para el análisis RST."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Sequence


JsonDict = Dict[str, Any]
Lang = Literal["es", "en", "auto"]


class ValidationError(ValueError):
    """Error de validación con una interfaz parecida a ``pydantic``."""

    def __init__(self, message: str, *, field: str | None = None) -> None:
        super().__init__(message)
        self.field = field

    def errors(self) -> List[JsonDict]:
        """Devuelve una lista de errores similar a ``ValidationError`` de pydantic."""

        location: List[str] = [self.field] if self.field else []
        return [
            {
                "loc": location,
                "msg": str(self),
                "type": "value_error",
            }
        ]


@dataclass
class _BaseSchema:
    """Proporciona utilidades compatibles con la API usada anteriormente."""

    def model_dump(self) -> JsonDict:
        return asdict(self)

    def model_copy(self) -> "_BaseSchema":
        return type(self).model_validate(self.model_dump())

    @classmethod
    def _ensure_dict(cls, value: "_BaseSchema | JsonDict") -> JsonDict:
        if isinstance(value, _BaseSchema):
            return value.model_dump()
        if isinstance(value, dict):
            return value
        raise ValidationError(f"{cls.__name__} requiere un diccionario válido")

    @staticmethod
    def _ensure_int(value: Any, *, field: str) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field} debe ser un entero", field=field) from exc


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
    def model_validate(cls, value: JsonDict | "Span") -> "Span":
        data = cls._ensure_dict(value)
        try:
            start = cls._ensure_int(data["start"], field="start")
            end = cls._ensure_int(data["end"], field="end")
            return cls(start=start, end=end)
        except KeyError as exc:
            raise ValidationError(f"Falta el campo requerido {exc.args[0]} en Span", field=exc.args[0]) from exc


@dataclass
class EDU(_BaseSchema):
    """Elementary Discourse Unit."""

    id: int
    text: str
    span: Span

    @classmethod
    def model_validate(cls, value: JsonDict | "EDU") -> "EDU":
        data = cls._ensure_dict(value)
        try:
            span = Span.model_validate(data["span"])
            edu_id = cls._ensure_int(data["id"], field="id")
            text = str(data["text"])
            if not text:
                raise ValidationError("El texto del EDU no puede estar vacío", field="text")
            return cls(id=edu_id, text=text, span=span)
        except KeyError as exc:
            raise ValidationError(f"Falta el campo requerido {exc.args[0]} en EDU", field=exc.args[0]) from exc


@dataclass
class RoleChunk(_BaseSchema):
    """Colección de IDs de EDUs que actúan como núcleo o satélite."""

    edu_ids: List[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        cleaned: List[int] = []
        for value in self.edu_ids:
            cleaned.append(self._ensure_int(value, field="edu_ids"))
        self.edu_ids = sorted(dict.fromkeys(cleaned))
        if not self.edu_ids:
            raise ValidationError("edu_ids no puede estar vacío", field="edu_ids")

    @classmethod
    def model_validate(cls, value: JsonDict | "RoleChunk") -> "RoleChunk":
        data = cls._ensure_dict(value)
        edu_ids = data.get("edu_ids", [])
        if not isinstance(edu_ids, Sequence):
            raise ValidationError("edu_ids debe ser una secuencia", field="edu_ids")
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

ALLOWED_RELATIONS: Sequence[str] = (
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


@dataclass
class Relation(_BaseSchema):
    """Relación retórica entre uno o varios EDUs."""

    type: RelationType
    nucleus: RoleChunk
    satellite: RoleChunk
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.type not in ALLOWED_RELATIONS:
            raise ValidationError(f"Tipo de relación no soportado: {self.type}", field="type")
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValidationError("La confianza debe estar entre 0 y 1", field="confidence")
        self.confidence = float(self.confidence)

    @classmethod
    def model_validate(cls, value: JsonDict | "Relation") -> "Relation":
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
                f"Falta el campo requerido {exc.args[0]} en Relation",
                field=exc.args[0],
            ) from exc


@dataclass
class Tree(_BaseSchema):
    """Representación estructurada del análisis."""

    format: Literal["brackets", "newick"]
    value: str

    def __post_init__(self) -> None:
        if self.format not in {"brackets", "newick"}:
            raise ValidationError("Formato de árbol no soportado", field="format")
        text = str(self.value)
        if not text:
            raise ValidationError("El valor del árbol no puede estar vacío", field="value")
        self.value = text

    @classmethod
    def model_validate(cls, value: JsonDict | "Tree") -> "Tree":
        data = cls._ensure_dict(value)
        try:
            fmt = str(data["format"])
            val = str(data["value"])
            return cls(format=fmt, value=val)
        except KeyError as exc:
            raise ValidationError(f"Falta el campo requerido {exc.args[0]} en Tree", field=exc.args[0]) from exc


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
            raise ValidationError(f"Idioma no soportado: {self.lang}", field="lang")
        if not isinstance(self.metadata, dict):
            raise ValidationError("metadata debe ser un diccionario", field="metadata")
        if not self.edus:
            raise ValidationError("Debe existir al menos un EDU", field="edus")
        if not isinstance(self.relations, list):
            raise ValidationError("relations debe ser una lista", field="relations")

    @classmethod
    def model_validate(cls, value: JsonDict | "RSTResult") -> "RSTResult":
        data = cls._ensure_dict(value)
        try:
            edus_raw = data.get("edus", [])
            edus = [EDU.model_validate(item) for item in edus_raw]
            relations_raw = data.get("relations", [])
            relations = [Relation.model_validate(item) for item in relations_raw]
            tree = Tree.model_validate(data["tree"])
            summary = str(data.get("pragmatic_summary", ""))
            metadata = dict(data.get("metadata", {}))
            return cls(
                id=str(data["id"]),
                lang=str(data["lang"]),
                edus=edus,
                relations=relations,
                tree=tree,
                pragmatic_summary=summary,
                metadata=metadata,
            )
        except KeyError as exc:
            raise ValidationError(
                f"Falta el campo requerido {exc.args[0]} en RSTResult",
                field=exc.args[0],
            ) from exc


@dataclass
class ADKPayload(_BaseSchema):
    """Payload de entrada esperado por el adaptador ADK."""

    texts: List[str]
    lang_hint: Lang = "auto"
    ruleset: Literal["minimal", "extended"] = "extended"

    def __post_init__(self) -> None:
        if not isinstance(self.texts, list) or not all(
            isinstance(item, str) and item.strip() for item in self.texts
        ):
            raise ValidationError("texts debe ser una lista de strings no vacíos", field="texts")
        if self.lang_hint not in ("es", "en", "auto"):
            raise ValidationError("lang_hint debe ser es, en o auto", field="lang_hint")
        if self.ruleset not in ("minimal", "extended"):
            raise ValidationError("ruleset debe ser minimal o extended", field="ruleset")

    @classmethod
    def model_validate(cls, value: JsonDict | "ADKPayload") -> "ADKPayload":
        data = cls._ensure_dict(value)
        texts = data.get("texts")
        if texts is None:
            raise ValidationError("texts es un campo obligatorio en ADKPayload", field="texts")
        if isinstance(texts, str):
            texts = [texts]
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
    def model_validate(cls, value: JsonDict | "Artifact") -> "Artifact":
        data = cls._ensure_dict(value)
        try:
            return cls(path=str(data["path"]))
        except KeyError as exc:
            raise ValidationError(f"Falta el campo requerido {exc.args[0]} en Artifact", field=exc.args[0]) from exc


@dataclass
class ADKResponse(_BaseSchema):
    """Respuesta serializable para ADK."""

    results: List[Dict[str, Any]]
    artifacts: List[Artifact] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.results, list):
            raise ValidationError("results debe ser una lista", field="results")
        self.artifacts = [Artifact.model_validate(a) for a in self.artifacts]

    @classmethod
    def model_validate(cls, value: JsonDict | "ADKResponse") -> "ADKResponse":
        data = cls._ensure_dict(value)
        results = data.get("results", [])
        artifacts = [Artifact.model_validate(a) for a in data.get("artifacts", [])]
        if not isinstance(results, list):
            raise ValidationError("results debe ser una lista", field="results")
        return cls(results=list(results), artifacts=artifacts)


