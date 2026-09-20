from fastapi import FastAPI, Query, Response, HTTPException
from data_generator import generate_purchases

import math
import time
import uuid


# ============================================================
# FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="Purchase Data API",
    description="REST API for generating sample purchase data",
    version="1.0.0"
)


# ============================================================
# ROOT ENDPOINT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Purchase Data API is running",
        "docs": "/docs",
        "health": "/health",
        "purchases": "/purchases"
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# ============================================================
# PURCHASE ENDPOINT
# ============================================================

@app.get("/purchases")
def get_purchases(

    response: Response,

    # --------------------------------------------------------
    # DATA GENERATION PARAMETERS
    # --------------------------------------------------------

    start_date: str = Query(
        "2025-01-01",
        description="Start date in YYYY-MM-DD format"
    ),

    end_date: str = Query(
        "2025-12-31",
        description="End date in YYYY-MM-DD format"
    ),

    num_records: int = Query(
        100,
        ge=1,
        le=100000,
        description="Total number of records to generate"
    ),

    include_nulls: bool = Query(
        False,
        description="Whether random null values should be generated"
    ),

    null_probability: float = Query(
        0.05,
        ge=0,
        le=1,
        description="Probability of nullable fields becoming null"
    ),


    # --------------------------------------------------------
    # PAGINATION PARAMETERS
    # --------------------------------------------------------

    page: int = Query(
        1,
        ge=1,
        description="Page number"
    ),

    limit: int = Query(
        100,
        ge=1,
        le=1000,
        description="Number of records per page"
    )
):

    # --------------------------------------------------------
    # REQUEST ID
    # --------------------------------------------------------

    request_id = str(uuid.uuid4())

    response.headers["X-Request-ID"] = request_id


    # --------------------------------------------------------
    # SAMPLE RATE LIMIT HEADERS
    # --------------------------------------------------------

    response.headers["X-RateLimit-Limit"] = "100"

    response.headers["X-RateLimit-Remaining"] = "99"

    response.headers["X-RateLimit-Reset"] = str(
        int(time.time()) + 60
    )


    # --------------------------------------------------------
    # GENERATE DATA
    # --------------------------------------------------------

    try:

        purchases = generate_purchases(
            start_date=start_date,
            end_date=end_date,
            num_records=num_records,
            include_nulls=include_nulls,
            null_probability=null_probability
        )

    except ValueError as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


    # --------------------------------------------------------
    # PAGINATION CALCULATION
    # --------------------------------------------------------

    total_records = len(purchases)

    total_pages = math.ceil(
        total_records / limit
    )

    start_index = (page - 1) * limit

    end_index = start_index + limit


    # --------------------------------------------------------
    # INVALID PAGE CHECK
    # --------------------------------------------------------

    if start_index >= total_records:

        return {
            "request_id": request_id,

            "page": page,
            "limit": limit,

            "total_records": total_records,
            "total_pages": total_pages,

            "has_next": False,
            "has_previous": page > 1,

            "records_returned": 0,

            "data": []
        }


    # --------------------------------------------------------
    # GET CURRENT PAGE
    # --------------------------------------------------------

    paginated_data = purchases[
        start_index:end_index
    ]


    # --------------------------------------------------------
    # PAGINATION FLAGS
    # --------------------------------------------------------

    has_next = page < total_pages

    has_previous = page > 1


    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {

        "request_id": request_id,

        "generation_parameters": {
            "start_date": start_date,
            "end_date": end_date,
            "num_records": num_records,
            "include_nulls": include_nulls,
            "null_probability": null_probability
        },

        "pagination": {
            "page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages,
            "records_returned": len(paginated_data),
            "has_next": has_next,
            "has_previous": has_previous
        },

        "data": paginated_data
    }