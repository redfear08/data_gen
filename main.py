from fastapi import FastAPI, Query, HTTPException, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from data_generator import generate_purchases

import csv
import io
import json
import uuid
import math
import time
from threading import Lock, BoundedSemaphore


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Purchase Data API",
    description="Sample REST API for Data Engineering pipelines",
    version="2.1.0"
)


# ============================================================
# IN-MEMORY DATASET STORAGE
# ============================================================
#
# Structure:
#
# DATASETS = {
#     "dataset-id": {
#         "metadata": {...},
#         "data": [...]
#     }
# }
#
# NOTE:
# This is temporary storage.
# Restarting the application will remove all datasets.
# Later this can be replaced with PostgreSQL.
# ============================================================

DATASETS = {}

# These limits apply to one process. Keep Uvicorn on a single worker.
MAX_RECORDS_PER_DATASET = 10_000
MAX_TOTAL_RECORDS = 50_000
MAX_DATASETS = 10
EXPORT_BATCH_SIZE = 100
STORAGE_LOCK = Lock()
PENDING_DATASETS = {}
DOWNLOAD_SLOTS = BoundedSemaphore(2)


def find_dataset(dataset_id):
    # Get a stable reference even if another request deletes the entry.
    with STORAGE_LOCK:
        dataset = DATASETS.get(dataset_id)
    if dataset is None:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


class LimitedDownloadResponse(StreamingResponse):
    async def __call__(self, scope, receive, send):
        # Release the slot on completion, disconnect, or streaming failure.
        try:
            await super().__call__(scope, receive, send)
        finally:
            DOWNLOAD_SLOTS.release()


def stream_json(purchases):
    yield "["
    for start in range(0, len(purchases), EXPORT_BATCH_SIZE):
        chunk = ",".join(
            json.dumps(record, ensure_ascii=False)
            for record in purchases[start:start + EXPORT_BATCH_SIZE]
        )
        yield ("," if start else "") + chunk
    yield "]"


def stream_csv(purchases):
    if not purchases:
        return
    with io.StringIO(newline="") as buffer:
        writer = csv.DictWriter(buffer, fieldnames=list(purchases[0]))
        writer.writeheader()
        for start in range(0, len(purchases), EXPORT_BATCH_SIZE):
            writer.writerows(purchases[start:start + EXPORT_BATCH_SIZE])
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)



# ============================================================
# REQUEST MODEL
# ============================================================

class DatasetRequest(BaseModel):

    start_date: str = Field(
        ...,
        examples=["2025-01-01"]
    )

    end_date: str = Field(
        ...,
        examples=["2025-12-31"]
    )

    num_records: int = Field(
        default=1000,
        ge=1,
        le=MAX_RECORDS_PER_DATASET
    )

    include_nulls: bool = False

    null_probability: float = Field(
        default=0.05,
        ge=0,
        le=1
    )


# ============================================================
# COMMON RESPONSE HEADERS
# ============================================================

def add_common_headers(response: Response):

    request_id = str(uuid.uuid4())

    response.headers["X-Request-ID"] = request_id

    # NOTE:
    # These headers are currently informational only.
    # Actual rate limiting will be implemented later.
    response.headers["X-RateLimit-Limit"] = "100"
    response.headers["X-RateLimit-Remaining"] = "99"
    response.headers["X-RateLimit-Reset"] = str(
        int(time.time()) + 60
    )

    return request_id


# ============================================================
# PLAYGROUND / HOME PAGE
# ============================================================

@app.get(
    "/",
    include_in_schema=False
)
def playground():

    return FileResponse(
        "index.html",
        media_type="text/html"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "version": "2.1.0",
        "datasets_loaded": len(DATASETS)
    }


# ============================================================
# CREATE DATASET
# ============================================================

@app.post(
    "/datasets",
    status_code=201
)
def create_dataset(
    request: DatasetRequest,
    response: Response
):

    request_id = add_common_headers(response)

    # --------------------------------------------------------
    # Generate unique dataset ID
    # --------------------------------------------------------

    dataset_id = str(uuid.uuid4())


    # Reserve capacity before generating, without holding the lock during work.
    with STORAGE_LOCK:
        used_records = sum(len(item["data"]) for item in DATASETS.values())
        reserved_records = sum(PENDING_DATASETS.values())
        if (len(DATASETS) + len(PENDING_DATASETS) >= MAX_DATASETS
                or used_records + reserved_records + request.num_records > MAX_TOTAL_RECORDS):
            raise HTTPException(
                status_code=503,
                detail="Dataset capacity reached. Delete an existing dataset and retry."
            )
        PENDING_DATASETS[dataset_id] = request.num_records

    try:
        purchases = generate_purchases(
            start_date=request.start_date,
            end_date=request.end_date,
            num_records=request.num_records,
            include_nulls=request.include_nulls,
            null_probability=request.null_probability
        )
        metadata = {
            "dataset_id": dataset_id,
            "start_date": request.start_date,
            "end_date": request.end_date,
            "num_records": request.num_records,
            "include_nulls": request.include_nulls,
            "null_probability": request.null_probability,
            "created_at": int(time.time())
        }
        with STORAGE_LOCK:
            DATASETS[dataset_id] = {"metadata": metadata, "data": purchases}
            del PENDING_DATASETS[dataset_id]
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    finally:
        # Failed generation must not permanently consume capacity.
        with STORAGE_LOCK:
            PENDING_DATASETS.pop(dataset_id, None)


    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {

        "request_id": request_id,

        "message":
            "Dataset created successfully",

        "dataset": metadata
    }


# ============================================================
# LIST DATASETS
# ============================================================

@app.get("/datasets")
def list_datasets(
    response: Response
):

    request_id = add_common_headers(response)

    with STORAGE_LOCK:
        datasets = [dataset["metadata"] for dataset in DATASETS.values()]

    return {

        "request_id": request_id,

        "total_datasets": len(datasets),

        "datasets": datasets
    }


# ============================================================
# DOWNLOAD DATASET
# ============================================================
#
# Examples:
#
# CSV:
# /datasets/{dataset_id}/download?format=csv
#
# JSON:
# /datasets/{dataset_id}/download?format=json
#
# IMPORTANT:
# Keep this route BEFORE /datasets/{dataset_id}.
# ============================================================

@app.get("/datasets/{dataset_id}/download")
def download_dataset(

    dataset_id: str,

    format: str = Query(
        default="json",
        pattern="^(json|csv)$",
        description="Download format: json or csv"
    )
):

    # Bound the number of downloads retaining dataset references after deletion.
    if not DOWNLOAD_SLOTS.acquire(blocking=False):
        raise HTTPException(
            status_code=503,
            detail="Download capacity reached. Retry shortly.",
            headers={"Retry-After": "5"}
        )
    try:
        purchases = find_dataset(dataset_id)["data"]
        content = stream_json(purchases) if format == "json" else stream_csv(purchases)
        return LimitedDownloadResponse(
            content,
            media_type="application/json" if format == "json" else "text/csv",
            headers={"Content-Disposition":
                     f'attachment; filename="purchase_data_{dataset_id}.{format}"'}
        )
    except BaseException:
        DOWNLOAD_SLOTS.release()
        raise


# ============================================================
# GET DATASET INFORMATION
# ============================================================

@app.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: str,
    response: Response
):

    request_id = add_common_headers(response)

    dataset = find_dataset(dataset_id)
    return {"request_id": request_id, "dataset": dataset["metadata"]}


# ============================================================
# GET PURCHASE DATA
# ============================================================

@app.get("/purchases")
def get_purchases(

    response: Response,

    dataset_id: str = Query(
        ...,
        description=(
            "Dataset ID returned "
            "from POST /datasets"
        )
    ),

    page: int = Query(
        default=1,
        ge=1,
        description="Page number"
    ),

    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Records per page"
    )
):

    request_id = add_common_headers(response)


    purchases = find_dataset(dataset_id)["data"]

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    total_records = len(purchases)

    total_pages = math.ceil(
        total_records / limit
    )


    start_index = (
        page - 1
    ) * limit


    end_index = (
        start_index + limit
    )


    # --------------------------------------------------------
    # Extract requested page
    # --------------------------------------------------------

    paginated_data = purchases[
        start_index:end_index
    ]


    # --------------------------------------------------------
    # Pagination metadata
    # --------------------------------------------------------

    has_next = (
        page < total_pages
    )

    has_previous = (
        page > 1
    )


    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {

        "request_id": request_id,

        "dataset_id": dataset_id,

        "pagination": {

            "page": page,

            "limit": limit,

            "total_records":
                total_records,

            "total_pages":
                total_pages,

            "records_returned":
                len(paginated_data),

            "has_next":
                has_next,

            "has_previous":
                has_previous
        },

        "data":
            paginated_data
    }


# ============================================================
# DELETE DATASET
# ============================================================

@app.delete("/datasets/{dataset_id}")
def delete_dataset(
    dataset_id: str,
    response: Response
):

    request_id = add_common_headers(response)


    with STORAGE_LOCK:
        if DATASETS.pop(dataset_id, None) is None:
            raise HTTPException(status_code=404, detail="Dataset not found")


    return {

        "request_id":
            request_id,

        "message":
            "Dataset deleted successfully",

        "dataset_id":
            dataset_id
    }