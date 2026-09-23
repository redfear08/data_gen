"""Exercise a disposable local/CI API container using only the standard library."""
import argparse
import csv
import io
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def run(base_url):
    def request(path, body=None, method=None, expected=200):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            base_url.rstrip("/") + path, data=data, method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            response = urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            content = response.read()
            check(response.status == expected,
                  f"{path}: expected {expected}, got {response.status}: {content[:300]!r}")
            return response.headers, content

    deadline = time.monotonic() + 60
    while True:
        try:
            _, body = request("/health")
            health = json.loads(body)
            check(health["status"] == "healthy", "API is not healthy")
            break
        except (OSError, AssertionError, ValueError):
            if time.monotonic() >= deadline:
                raise
            time.sleep(1)

    version = (Path(__file__).resolve().parents[1] / "VERSION").read_text().strip()
    check(health["version"] == version, "Health version mismatch")
    check(isinstance(health["source_commit"], str), "Missing source identity")
    headers, html = request("/")
    check("text/html" in headers["Content-Type"], "Homepage must serve HTML")
    check(b"Purchase Data Generator" in html, "Missing playground")
    request("/docs")
    _, body = request("/openapi.json")
    check(json.loads(body)["info"]["version"] == version, "OpenAPI version mismatch")

    payload = dict(start_date="2025-01-01", end_date="2025-01-01",
                   num_records=205, include_nulls=True, null_probability=1)
    headers, body = request("/datasets", payload, expected=201)
    created = json.loads(body)
    dataset_id = created["dataset"]["dataset_id"]
    path = f"/datasets/{dataset_id}"
    try:
        check(headers["X-Request-ID"] == created["request_id"], "Request ID mismatch")
        request(path)
        _, body = request("/datasets")
        check(any(d["dataset_id"] == dataset_id for d in json.loads(body)["datasets"]),
              "Created dataset missing from list")
        rows = []
        for page, count in [(1, 100), (2, 100), (3, 5), (4, 0)]:
            _, body = request(f"/purchases?dataset_id={dataset_id}&page={page}&limit=100")
            result = json.loads(body)
            check(len(result["data"]) == count, "Incorrect page length")
            check(result["pagination"]["has_next"] == (page < 3), "Incorrect has_next")
            rows.extend(result["data"])
        check(len({row["purchase_id"] for row in rows}) == 205, "Duplicate purchases")
        _, body = request(f"/purchases?dataset_id={dataset_id}&page=1&limit=100")
        check(json.loads(body)["data"] == rows[:100], "Pagination is unstable")
        for row in rows:
            check(row["purchase_timestamp"].startswith("2025-01-01T"), "Date out of range")
            check(row["customer_name"] is None and row["quantity"] is not None,
                  "Null injection violated configured fields")
        for fmt in ["json", "csv"]:
            headers, body = request(path + f"/download?format={fmt}")
            check("attachment" in headers["Content-Disposition"], "Missing attachment header")
            exported = (json.loads(body) if fmt == "json" else
                        list(csv.DictReader(io.StringIO(body.decode("utf-8")))))
            check([r["purchase_id"] for r in exported] == [r["purchase_id"] for r in rows],
                  f"{fmt} export records differ")
            if fmt == "json":
                check(exported == rows, "JSON export values differ")
        request("/datasets", payload | {"num_records": 10001}, expected=422)
        request("/datasets", payload | {"start_date": "bad"}, expected=400)
        request(path + "/download?format=xml", expected=422)
        request(f"/purchases?dataset_id={dataset_id}&page=0", expected=422)
    finally:
        request(path, method="DELETE")
    request(path, expected=404)
    print("PASS: health/version, playground, Swagger, creation, stable pagination, exports, validation, deletion")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    run(parser.parse_args().base_url)
