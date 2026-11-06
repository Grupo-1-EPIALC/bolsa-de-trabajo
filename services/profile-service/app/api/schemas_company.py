"""Schemas de entrada del perfil de empresa. `PATCH` reemplaza cada sección enviada completa.

Razón social, CUIT y actividad no se editan acá (son de auth-service).
"""

from typing import Annotated, Any

from pydantic import Field

from app.api.schemas import Email, LocationIn, StrictModel, Text, Url
from app.domain.company import CompanyLinkType, CompanySize, CompanyVisibility
from app.domain.enums import WorkModality

ShortText = Annotated[str, Field(min_length=1, max_length=80)]


class CompanyLinkIn(StrictModel):
    type: CompanyLinkType
    url: Url


class CompanyContactIn(StrictModel):
    email: Email | None = None
    phone: Annotated[str, Field(pattern=r"^[0-9+()\-\s]{6,30}$")] | None = None
    name: Text | None = None
    public: bool = False


class HiringIn(StrictModel):
    areas: list[ShortText] = Field(default_factory=list, max_length=15)
    hires_students: bool = True
    internship_program: bool = False
    internship_agreements: list[Text] = Field(default_factory=list, max_length=20)


class InclusiveHiringIn(StrictModel):
    accepts_disability_certificate: bool = False
    accessible_workplace: bool = False


class CompanyProfilePatch(StrictModel):
    display_name: Annotated[str, Field(min_length=2, max_length=120)] | None = None
    tagline: Annotated[str, Field(max_length=140)] | None = None
    description: Annotated[str, Field(max_length=3000)] | None = None
    industry: ShortText | None = None
    size: CompanySize | None = None
    founded_year: Annotated[int, Field(ge=1800, le=2100)] | None = None
    location: LocationIn | None = None
    offices: list[LocationIn] | None = Field(default=None, max_length=20)
    website: Url | None = None
    links: list[CompanyLinkIn] | None = Field(default=None, max_length=10)
    contact: CompanyContactIn | None = None
    work_modalities: list[WorkModality] | None = Field(default=None, max_length=3)
    benefits: list[ShortText] | None = Field(default=None, max_length=20)
    values: list[ShortText] | None = Field(default=None, max_length=10)
    hiring: HiringIn | None = None
    inclusive_hiring: InclusiveHiringIn | None = None
    visibility: CompanyVisibility | None = None

    def changes(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_unset=True)
