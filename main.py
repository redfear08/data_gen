from fastapi import FastAPI, Query, HTTPException, Response
from pydantic import BaseModel, Field
from data_generator import generate_purchases

from typing import Optional
import uuid
import math
import time


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Purchase Data API",
    description="Sample REST API for Data Engineering pipelines",
    version="2.0.0"
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
        le=100000
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

    response.headers["X-RateLimit-Limit"] = "100"

    response.headers["X-RateLimit-Remaining"] = "99"

    response.headers["X-RateLimit-Reset"] = str(
        int(time.time()) + 60
    )

    return request_id


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():

    return {
        "message": "Purchase Data API is running",
        "version": "2.0.0",
        "docs": "/docs"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
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


    # --------------------------------------------------------
    # Generate purchase data
    # --------------------------------------------------------

    try:

        purchases = generate_purchases(
            start_date=request.start_date,
            end_date=request.end_date,
            num_records=request.num_records,
            include_nulls=request.include_nulls,
            null_probability=request.null_probability
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


    # --------------------------------------------------------
    # Dataset metadata
    # --------------------------------------------------------

    created_at = int(time.time())

    metadata = {

        "dataset_id": dataset_id,

        "start_date": request.start_date,
        "end_date": request.end_date,

        "num_records": request.num_records,

        "include_nulls": request.include_nulls,

        "null_probability":
            request.null_probability,

        "created_at": created_at
    }


    # --------------------------------------------------------
    # Store dataset
    # --------------------------------------------------------

    DATASETS[dataset_id] = {

        "metadata": metadata,

        "data": purchases
    }


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

    datasets = [

        dataset["metadata"]

        for dataset in DATASETS.values()

    ]

    return {

        "request_id": request_id,

        "total_datasets": len(datasets),

        "datasets": datasets
    }


# ============================================================
# GET DATASET INFORMATION
# ============================================================

@app.get("/datasets/{dataset_id}")
def get_dataset(
    dataset_id: str,
    response: Response
):

    request_id = add_common_headers(response)

    if dataset_id not in DATASETS:

        raise HTTPException(
            status_code=404,
            detail="Dataset not found"
        )

    return {

        "request_id": request_id,

        "dataset":
            DATASETS[dataset_id]["metadata"]
    }


# ============================================================
# GET PURCHASE DATA
# ============================================================

@app.get("/purchases")
def get_purchases(

    response: Response,

    dataset_id: str = Query(
        ...,
        description="Dataset ID returned from POST /datasets"
    ),

    page: int = Query(
        default=1,
        ge=1
    ),

    limit: int = Query(
        default=100,
        ge=1,
        le=1000
    )
):

    request_id = add_common_headers(response)


    # --------------------------------------------------------
    # Check dataset exists
    # --------------------------------------------------------

    if dataset_id not in DATASETS:

        raise HTTPException(
            status_code=404,
            detail="Dataset not found"
        )


    # --------------------------------------------------------
    # Get stored dataset
    # --------------------------------------------------------

    purchases = DATASETS[
        dataset_id
    ]["data"]


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
    # Extract page
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

        "data": paginated_data
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

    if dataset_id not in DATASETS:

        raise HTTPException(
            status_code=404,
            detail="Dataset not found"
        )

    del DATASETS[dataset_id]

    return {

        "request_id": request_id,

        "message":
            "Dataset deleted successfully",

        "dataset_id":
            dataset_id
    }