# Purchase Data Generator REST API

A containerized REST API built with **Python and FastAPI** for generating synthetic purchase data that can be consumed by data engineering pipelines.

The project is designed as a learning and testing source system for building pipelines with tools such as **Databricks, PySpark, Delta Lake, AWS, and other data platforms**.

The API can generate configurable purchase datasets containing customer, product, and transaction information, including optional null values for testing data-quality scenarios.

---

## Architecture

```text
                         POST /datasets
                               │
                               ▼
                    ┌─────────────────────┐
                    │   FastAPI Service   │
                    │                     │
                    │  Data Generator     │
                    └──────────┬──────────┘
                               │
                               ▼
                    Generate Dataset Once
                               │
                               ▼
                    ┌─────────────────────┐
                    │  In-Memory Storage  │
                    │                     │
                    │    dataset_id       │
                    └──────────┬──────────┘
                               │
                    GET /purchases
                               │
                  dataset_id + pagination
                               │
                               ▼
                       REST API Client
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
             Databricks                 Other Clients
                 │
                 ▼
              Bronze
                 │
                 ▼
              Silver
                 │
                 ▼
       ┌─────────┴─────────┐
       ▼                   ▼
   Dimensions             Fact
```

---

## Features

* Synthetic purchase-data generation
* Configurable start and end dates
* Configurable number of records
* Customer master data
* Product master data
* Transaction-level purchase information
* Optional random null-value generation
* Configurable null probability
* Stable generated datasets using `dataset_id`
* REST API pagination
* Request IDs for tracing
* Sample rate-limit response headers
* Health-check endpoint
* Automatic Swagger/OpenAPI documentation
* Docker support

---

## Project Structure

```text
data_gen/
│
├── main.py
├── data_generator.py
├── requirements.txt
├── Dockerfile
└── README.md
```

### `main.py`

Contains the FastAPI application and REST endpoints.

### `data_generator.py`

Generates synthetic purchase records containing:

* transaction information
* customer information
* product information
* payment information
* timestamps
* optional null values

### `Dockerfile`

Packages the FastAPI application into a Docker container.

---

# Generated Data Model

The API intentionally produces a **denormalized purchase dataset**.

Example record:

```json
{
  "purchase_id": "cb42f58e-985d-42d4-8731-9fdb21f5bd53",
  "purchase_timestamp": "2025-05-18T10:25:41+00:00",
  "created_at": "2025-05-18T10:25:41+00:00",
  "updated_at": "2025-05-18T15:40:41+00:00",

  "customer_id": 1002,
  "customer_name": "Priya Das",
  "customer_email": "priya.das@example.com",
  "customer_city": "Kolkata",
  "customer_state": "West Bengal",
  "customer_segment": "Regular",

  "product_id": "P104",
  "product_name": "Riding Jacket",
  "category": "Riding Gear",

  "quantity": 2,
  "unit_price": 4500,
  "gross_amount": 9000,
  "discount": 500,
  "total_amount": 8500,

  "payment_method": "UPI",
  "order_status": "COMPLETED"
}
```

The denormalized structure is intentional so downstream pipelines can transform the raw data into dimensional models.

For example:

```text
Raw Purchase Data
        │
        ▼
     Bronze
        │
        ▼
     Silver
        │
        ├──────────────► dim_customer
        │
        ├──────────────► dim_product
        │
        ├──────────────► dim_date
        │
        └──────────────► fact_purchase
```

---

# API Endpoints

## Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "healthy",
  "datasets_loaded": 1
}
```

---

## Create Dataset

```http
POST /datasets
```

Creates a new synthetic purchase dataset.

### Request Body

```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "num_records": 1000,
  "include_nulls": true,
  "null_probability": 0.05
}
```

### Parameters

| Parameter          | Description                                  | Example      |
| ------------------ | -------------------------------------------- | ------------ |
| `start_date`       | Beginning of purchase date range             | `2025-01-01` |
| `end_date`         | End of purchase date range                   | `2025-12-31` |
| `num_records`      | Number of purchases to generate              | `1000`       |
| `include_nulls`    | Introduce random null values                 | `true`       |
| `null_probability` | Probability of nullable fields becoming null | `0.05`       |

### Example Response

```json
{
  "request_id": "78ea15f6-95ae-45c5-aac8-ff3784226302",
  "message": "Dataset created successfully",
  "dataset": {
    "dataset_id": "d570155e-a4ca-407d-b91e-8a50814b7de5",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "num_records": 1000,
    "include_nulls": true,
    "null_probability": 0.05,
    "created_at": 1790000000
  }
}
```

Save the returned `dataset_id`. It is required when retrieving purchase records.

---

## List Datasets

```http
GET /datasets
```

Returns metadata for datasets currently stored by the API.

---

## Get Dataset Metadata

```http
GET /datasets/{dataset_id}
```

Example:

```http
GET /datasets/d570155e-a4ca-407d-b91e-8a50814b7de5
```

---

## Retrieve Purchases

```http
GET /purchases
```

### Query Parameters

| Parameter    | Required | Description                                     |
| ------------ | -------- | ----------------------------------------------- |
| `dataset_id` | Yes      | Dataset to retrieve                             |
| `page`       | No       | Page number; default `1`                        |
| `limit`      | No       | Records per page; default `100`, maximum `1000` |

Example:

```http
GET /purchases?dataset_id=d570155e-a4ca-407d-b91e-8a50814b7de5&page=1&limit=100
```

Example response:

```json
{
  "request_id": "6625df29-f6aa-43d5-bbf0-272ce6259a64",

  "dataset_id": "d570155e-a4ca-407d-b91e-8a50814b7de5",

  "pagination": {
    "page": 1,
    "limit": 100,
    "total_records": 1000,
    "total_pages": 10,
    "records_returned": 100,
    "has_next": true,
    "has_previous": false
  },

  "data": []
}
```

---

## Delete Dataset

```http
DELETE /datasets/{dataset_id}
```

Deletes the specified dataset from the API's in-memory storage.

---

# Pagination

Pagination prevents large datasets from being returned in a single HTTP response.

For a dataset containing `1000` records with:

```text
limit = 100
```

the API exposes:

```text
Page 1  → records 1-100
Page 2  → records 101-200
Page 3  → records 201-300
...
Page 10 → records 901-1000
```

Clients should continue requesting pages while:

```json
"has_next": true
```

---

# Random Null Generation

The generator can intentionally introduce null values for data-quality testing.

Example:

```json
{
  "start_date": "2025-01-01",
  "end_date": "2025-12-31",
  "num_records": 10000,
  "include_nulls": true,
  "null_probability": 0.05
}
```

`null_probability = 0.05` means each configured nullable field has approximately a **5% probability** of being replaced with `null`.

Core transaction identifiers and required measures are intentionally protected from normal null generation.

This allows downstream pipelines to practice:

* null detection
* mandatory-column validation
* data-quality rules
* rejected-record handling
* quarantine tables
* cleansing
* default-value handling

---

# Response Headers

The API includes response headers useful for pipeline and API-client testing.

Example:

```text
X-Request-ID
X-RateLimit-Limit
X-RateLimit-Remaining
X-RateLimit-Reset
Content-Type
```

`X-Request-ID` can be used for request tracing and troubleshooting.

The current rate-limit headers are simulated metadata and do not yet enforce actual request throttling.

---

# Running Locally

Install the dependencies:

```bash
pip install -r requirements.txt
```

Start the application:

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

---

# Swagger Documentation

FastAPI automatically provides interactive API documentation.

Open:

```text
http://localhost:8000/docs
```

From Swagger UI you can create datasets, inspect dataset metadata, retrieve paginated purchase data, and delete datasets.

---

# Running with Docker

Build the Docker image:

```bash
docker build -t purchase-api .
```

Run the container:

```bash
docker run -d \
  --name purchase-api-container \
  -p 8000:8000 \
  purchase-api
```

For Windows PowerShell:

```powershell
docker run -d --name purchase-api-container -p 8000:8000 purchase-api
```

Check the running container:

```bash
docker ps
```

View logs:

```bash
docker logs purchase-api-container
```

Stop the container:

```bash
docker stop purchase-api-container
```

Remove it:

```bash
docker rm purchase-api-container
```

---

# Example Python Client

```python
import requests

BASE_URL = "http://localhost:8000"


# Create dataset

dataset_request = {
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "num_records": 1000,
    "include_nulls": True,
    "null_probability": 0.05
}

response = requests.post(
    f"{BASE_URL}/datasets",
    json=dataset_request,
    timeout=30
)

response.raise_for_status()

dataset_id = response.json()["dataset"]["dataset_id"]

print("Dataset:", dataset_id)


# Retrieve all pages

page = 1
limit = 100

all_records = []

while True:

    response = requests.get(
        f"{BASE_URL}/purchases",
        params={
            "dataset_id": dataset_id,
            "page": page,
            "limit": limit
        },
        timeout=30
    )

    response.raise_for_status()

    result = response.json()

    all_records.extend(result["data"])

    print(
        f"Page {page}: "
        f"{len(result['data'])} records"
    )

    if not result["pagination"]["has_next"]:
        break

    page += 1


print(
    f"Total records downloaded: {len(all_records)}"
)
```

---

# Databricks Pipeline Use Case

The API is intended to act as a synthetic source system for practicing REST-based data ingestion.

Example architecture:

```text
Purchase Generator
        │
        ▼
Purchase REST API
        │
        │ HTTPS / JSON
        ▼
Databricks Ingestion
        │
        ▼
Bronze Delta
        │
        ▼
Data Quality
        │
        ├── Null checks
        ├── Duplicate checks
        ├── Schema validation
        ├── Type validation
        └── Invalid-record quarantine
        │
        ▼
Silver Delta
        │
        ▼
Dimensional Model
        │
        ├── dim_customer
        ├── dim_product
        ├── dim_date
        └── fact_purchase
```

The project can therefore be used to practice concepts including:

* REST API ingestion
* pagination
* retries
* rate limits
* JSON processing
* PySpark transformations
* Bronze/Silver/Gold architecture
* data-quality validation
* dimensional modeling
* incremental ingestion
* idempotency
* SCD processing

---

# Current Storage Limitation

Datasets are currently stored **in memory**.

```python
DATASETS = {}
```

Therefore datasets are lost when the API process or Docker container restarts.

The current implementation is suitable for development and pipeline testing but is not intended to provide durable production storage.

A future version will replace the in-memory store with a persistent database such as PostgreSQL.

---

# Planned Improvements

Future development may include:

* PostgreSQL persistence
* API-key or token authentication
* actual API rate limiting
* HTTP `429 Too Many Requests`
* `Retry-After` support
* standardized error responses
* structured logging
* persistent request tracing
* incremental/watermark-based extraction
* dataset expiration/cleanup
* schema versioning
* automated tests
* cloud deployment
* Databricks Bronze/Silver/Gold pipeline

---

# Technology Stack

* Python
* FastAPI
* Uvicorn
* Docker
* REST / JSON

Planned downstream stack:

* Databricks
* PySpark
* Delta Lake

---

## Purpose

This project is primarily designed as a hands-on **Data Engineering learning and testing project**.

It provides a controllable REST API source so data pipelines can be developed and tested against realistic scenarios such as pagination, dirty data, data-quality failures, dimensional modeling, and eventually incremental ingestion and rate limiting.

