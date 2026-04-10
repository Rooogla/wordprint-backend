import asyncio

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Analysis, Project, ProjectType, SourceType, Word
from ..nlp.scraper import discover_blog_urls, extract_text_from_url
from ..nlp.statistics import compute_statistics
from ..schemas import AnalysisDetail, AnalysisOut, TextInput, UrlInput

router = APIRouter(tags=["analyses"])


async def _get_project(project_id: int, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _create_analysis(
    db: AsyncSession,
    project_id: int,
    source_type: SourceType,
    source_label: str,
    text: str,
) -> Analysis:
    statistics, word_records, score = compute_statistics(text)

    analysis = Analysis(
        project_id=project_id,
        source_type=source_type,
        source_label=source_label,
        raw_text=text,
        statistics=statistics,
        wordprint_score=score,
    )
    db.add(analysis)
    await db.flush()

    for wr in word_records:
        word = Word(
            analysis_id=analysis.id,
            surface_form=wr["surface_form"],
            lemma=wr["lemma"],
            pos_tag=wr["pos_tag"],
            frequency=wr["frequency"],
            is_foreign=wr["is_foreign"],
            is_technical=wr["is_technical"],
        )
        db.add(word)

    await db.commit()
    await db.refresh(analysis)
    return analysis


@router.post("/projects/{project_id}/analyze/text", response_model=AnalysisOut, status_code=201)
async def analyze_text(project_id: int, data: TextInput, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    analysis = await _create_analysis(db, project_id, SourceType.PASTE, "Manuell", data.text)
    return analysis


@router.post("/projects/{project_id}/analyze/files", response_model=AnalysisOut, status_code=201)
async def analyze_files(
    project_id: int,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, db)

    texts = []
    filenames = []
    for f in files:
        content = await f.read()
        texts.append(content.decode("utf-8", errors="replace"))
        filenames.append(f.filename or "unknown")

    combined_text = "\n\n".join(texts)
    label = ", ".join(filenames)

    analysis = await _create_analysis(db, project_id, SourceType.FILE, label, combined_text)
    return analysis


@router.post("/projects/{project_id}/analyze/url", response_model=AnalysisOut, status_code=201)
async def analyze_url(project_id: int, data: UrlInput, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)

    text, title = await extract_text_from_url(data.url)
    if not text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from URL")

    label = data.url
    analysis = await _create_analysis(db, project_id, SourceType.URL, label, text)
    return analysis


@router.get("/projects/{project_id}/analyses", response_model=list[AnalysisOut])
async def list_analyses(project_id: int, db: AsyncSession = Depends(get_db)):
    await _get_project(project_id, db)
    result = await db.execute(
        select(Analysis)
        .where(Analysis.project_id == project_id)
        .order_by(Analysis.created_at.desc())
    )
    return result.scalars().all()


@router.get("/analyses/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Analysis)
        .where(Analysis.id == analysis_id)
        .options(selectinload(Analysis.words))
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.delete("/analyses/{analysis_id}", status_code=204)
async def delete_analysis(analysis_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Analysis).where(Analysis.id == analysis_id))
    analysis = result.scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    await db.delete(analysis)
    await db.commit()


@router.post("/projects/{project_id}/crawl", response_model=list[AnalysisOut], status_code=201)
async def crawl_blog(project_id: int, db: AsyncSession = Depends(get_db)):
    project = await _get_project(project_id, db)
    if project.type != ProjectType.BLOG or not project.blog_url:
        raise HTTPException(status_code=400, detail="Project is not a BLOG project or has no blog_url")

    urls = await discover_blog_urls(project.blog_url)
    if not urls:
        raise HTTPException(status_code=422, detail="No articles found")

    analyses = []
    for url in urls:
        try:
            text, title = await extract_text_from_url(url)
            if text.strip():
                analysis = await _create_analysis(db, project_id, SourceType.URL, url, text)
                analyses.append(analysis)
        except Exception:
            continue  # Skip failed URLs
        await asyncio.sleep(1)  # Rate limiting

    return analyses
