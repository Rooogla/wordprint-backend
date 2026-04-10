import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


class ProjectType(str, enum.Enum):
    MANUAL = "MANUAL"
    BLOG = "BLOG"


class SourceType(str, enum.Enum):
    PASTE = "PASTE"
    FILE = "FILE"
    URL = "URL"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    type: Mapped[ProjectType] = mapped_column(Enum(ProjectType), nullable=False, default=ProjectType.MANUAL)
    blog_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    analyses: Mapped[list["Analysis"]] = relationship("Analysis", back_populates="project", cascade="all, delete-orphan")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_label: Mapped[str] = mapped_column(String(1024), nullable=False, default="Manuell")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    statistics: Mapped[dict] = mapped_column(JSON, nullable=True)
    wordprint_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="analyses")
    words: Mapped[list["Word"]] = relationship("Word", back_populates="analysis", cascade="all, delete-orphan")


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_id: Mapped[int] = mapped_column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    surface_form: Mapped[str] = mapped_column(String(255), nullable=False)
    lemma: Mapped[str] = mapped_column(String(255), nullable=False)
    pos_tag: Mapped[str] = mapped_column(String(20), nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_foreign: Mapped[bool] = mapped_column(default=False)
    is_technical: Mapped[bool] = mapped_column(default=False)

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="words")
