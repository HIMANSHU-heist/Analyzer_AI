import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.core.file_loader import load_dataframe, get_schema_summary, UnsupportedFileTypeError
from app.core.registry import register_file
import uuid

router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Simple in-memory registry mapping dataset_id -> file path.
# In Step 2+ we'll swap this for a real DB (SQLite/Postgres).
DATASET_REGISTRY: dict[str, str] = {}


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    Upload a dataset file (csv, xlsx, xls, json, parquet, tsv).
    Returns a dataset_id + schema summary so the frontend/chat
    can immediately show what's in the file.
    """
    ext = Path(file.filename).suffix.lower()

    dataset_id = str(uuid.uuid4())
    saved_path = UPLOAD_DIR / f"{dataset_id}{ext}"

    # Save file to disk
    with open(saved_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        df = load_dataframe(str(saved_path))
    except UnsupportedFileTypeError as e:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        saved_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")

    DATASET_REGISTRY[dataset_id] = str(saved_path)

    schema = get_schema_summary(df)
    register_file(dataset_id, filepath=str(saved_path), schema_summary=schema)   # <-- ADD THIS LINE
    return {
        "dataset_id": dataset_id,
        "filename": file.filename,
        "schema": schema,
    }
    


@router.get("/dataset/{dataset_id}/preview")
async def preview_dataset(dataset_id: str, rows: int = 10):
    """Return the first N rows of an uploaded dataset."""
    if dataset_id not in DATASET_REGISTRY:
        raise HTTPException(status_code=404, detail="Dataset not found")

    df = load_dataframe(DATASET_REGISTRY[dataset_id])
    preview = df.head(rows).fillna("null").to_dict(orient="records")
    return {"dataset_id": dataset_id, "rows_returned": len(preview), "data": preview}
