from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    type: str = "MANUAL"
    blog_url: str | None = None


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str | None
    type: str
    blog_url: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectOut):
    analyses: list["AnalysisOut"]


class AnalysisOut(BaseModel):
    id: int
    project_id: int
    source_type: str
    source_label: str
    wordprint_score: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisDetail(AnalysisOut):
    raw_text: str
    statistics: dict | None
    words: list["WordOut"]


class WordOut(BaseModel):
    id: int
    surface_form: str
    lemma: str
    pos_tag: str
    frequency: int
    is_foreign: bool
    is_technical: bool

    model_config = {"from_attributes": True}


class TextInput(BaseModel):
    text: str


class UrlInput(BaseModel):
    url: str
