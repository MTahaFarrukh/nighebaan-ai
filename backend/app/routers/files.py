"""Multipart media analysis; filenames and extracted content are never logged."""

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool

from app.routers.analyze import save_history
from app.schemas import FileAnalyzeResponse
from app.services import media, media_text, text_analysis
from app.services.extractors import ExtractionError
from app.services.media_config import MAX_BYTES

router = APIRouter(prefix="/analyze", tags=["analyze"])


def process(data: bytes, content_type: str | None) -> FileAnalyzeResponse:
    """Use exactly the shared classifier/rules pipeline and record metadata once."""
    try:
        kind, extracted = media.extract(data, content_type)
        ml_input, notes = media_text.model_text(extracted.text)
        result = text_analysis.analyze(extracted.text, ml_text=ml_input)
        result = save_history(result, kind)
        return FileAnalyzeResponse(
            **result.model_dump(),
            modality=kind,
            extracted_text=media_text.preview(extracted.text),
            extraction_confidence=extracted.confidence,
            warnings=extracted.warnings
            + notes
            + (
                [
                    "Preview shortened to 5,000 characters; analysis used the complete extraction."
                ]
                if len(extracted.text) > 5000
                else []
            ),
        )
    except ExtractionError as error:
        raise HTTPException(status_code=error.status, detail=error.message) from None
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 - privacy boundary: library exceptions can include source content
        raise HTTPException(
            status_code=422,
            detail="Media processing failed. Try a clearer supported file.",
        ) from None


@router.post("/file", response_model=FileAnalyzeResponse)
async def analyze_file(file: Annotated[UploadFile, File()]) -> FileAnalyzeResponse:
    """Close framework spool files on every success/failure path."""
    try:
        data = await file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise HTTPException(
                status_code=413, detail="File exceeds the configured upload size limit."
            )
        return await run_in_threadpool(process, data, file.content_type)
    finally:
        await file.close()
