from __future__ import annotations


class Span(BaseModel):
start: int = Field(ge=0)
end: int = Field(ge=0)


class EDU(BaseModel):
id: int
text: str
span: Span


class RoleChunk(BaseModel):
edu_ids: List[int] = Field(default_factory=list)


RelationType = Literal[
"Elaboration", "Evidence", "Justify", "Contrast", "Concession",
"Cause", "Result", "Condition", "Purpose", "Background",
"Summary", "Antithesis", "Enablement", "Circumstance"
]


class Relation(BaseModel):
type: RelationType
nucleus: RoleChunk
satellite: RoleChunk
confidence: float = Field(ge=0.0, le=1.0)


class Tree(BaseModel):
format: Literal["brackets", "newick"]
value: str


class RSTResult(BaseModel):
model_config = ConfigDict(extra="ignore")


id: str
lang: Lang
edus: List[EDU]
relations: List[Relation]
tree: Tree
pragmatic_summary: str
metadata: dict


# ADK payloads
class ADKPayload(BaseModel):
texts: List[str]
lang_hint: Lang = "auto"
ruleset: Literal["minimal", "extended"] = "extended"


class Artifact(BaseModel):
path: str


class ADKResponse(BaseModel):
results: List[RSTResult]
artifacts: List[Artifact] = Field(default_factory=list)

