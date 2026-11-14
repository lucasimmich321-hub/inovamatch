"""Contrato estrito da Responses API; não confunde existência do trecho e interpretação."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator
from .matching import FIELDS, OPS

ComparableField = Literal[tuple(FIELDS)]
Operator = Literal[tuple(OPS)]
Value = str | float | int | list[str] | None


class StrictObject(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True, str_max_length=6000)


class Evidence(StrictObject):
    page: int | None
    quote: str


class Requirement(StrictObject):
    description: str
    kind: Literal['startup', 'project', 'documentation', 'finance', 'restriction', 'selection', 'submission', 'additional']
    mandatory: bool | None
    field: ComparableField
    operator: Operator
    value: Value
    evidence: Evidence
    basis: Literal['fact', 'interpretation']
    needs_review: bool
    review_reason: str


class MetadataFact(StrictObject):
    name: Literal['institution', 'title', 'objective', 'target_audience', 'registration_status', 'opening_date',
                  'closing_date', 'funding_total', 'funding_limit', 'themes', 'region']
    value: Value
    evidence: Evidence
    basis: Literal['fact', 'interpretation']
    needs_review: bool


class Section(StrictObject):
    title: str
    page: int
    kind: Literal['section', 'table', 'annex']


class Extraction(StrictObject):
    facts: list[MetadataFact]
    requirements: list[Requirement]
    sections: list[Section]
    warnings: list[str]
    possible_amendments: bool

    @model_validator(mode='after')
    def bounded(self):
        if len(self.requirements) > 100 or len(self.facts) > 50 or len(self.sections) > 80 or len(self.warnings) > 30:
            raise ValueError('Resposta excede os limites locais da análise.')
        return self
