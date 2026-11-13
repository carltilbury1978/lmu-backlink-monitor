"""Submit LMU to Best Rated Company's explicitly documented FREE application API.

Single-use. No paid service, no CAPTCHA evasion. Public runner:
do not log the private application identifier or personal email address.
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
MARKER = ROOT / "best-rated-status.json"
BASE = "https://www.bestratedcompany.co.uk/api/v1/"
WEBSITE = "https://www.lovemyuniform.com/"
BUSINESS = "Love My Uniform Ltd"
SUBMISSION_KEY = str(uuid.uuid5(uuid.NAMESPACE_URL, "https://www.lovemyuniform.com|bestratedcompany|application|2026-11"))
DESCRIPTION = (
    "Love My Uniform Ltd supplies uniforms, workwear and branded clothing to UK businesses. "
    "We offer polo shirts, T-shirts, scrubs, tunics, fleeces, sweatshirts, jackets and "
    "teamwear. Suitable garments can be embroidered or printed for coordinated staff uniforms."
)


def post(path: str, payload: dict, timeout: int, headers=None):
    req = Request(
        BASE + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read(100_000).decode("utf-8"))
    except HTTPError as error:
        raw = error.read(100_000)
        try:
            obj = json.loads(raw.decode("utf-8"))
        except Exception:
            obj = {}
        return error.code, obj


def safe_record(value: str):
    MARKER.write_text(
        json.dumps({
            "directory": "Best Rated Company",
            "website": WEBSITE,
            "status": value,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "note": "No link is counted until the directory publishes a live page. Approval email goes to the business.",
        }, indent=2) + "\n",
        encoding="utf-8",
    )


def main():
    # All directory contact information below is public on LMU's own website.
    # The owner explicitly requested a no-cost listing campaign and expects email approval.
    if MARKER.exists():
        print("SKIP: prior application state recorded, avoiding duplicate submission.")
        print("STATUS=" + json.loads(MARKER.read_text())["status"])
        return 0

    try:
        lookup_status, lookup = post("lookups", {"url": WEBSITE}, timeout=90)
    except (TimeoutError, URLError, OSError) as err:
        lookup_status, lookup = 0, {}
    print("LOOKUP_HTTP=" + str(lookup_status))
    payload = {
        "country": "GB",
        "name": "Love My Uniform team",
        "business": BUSINESS,
        "email": "hello@lovemyuniform.com",
        "phone": "0117 287 0521",
        "trade": "Workwear and Uniform Suppliers",
        "town": "Yate",
        "online_only": True,
        "website": WEBSITE,
        "message": DESCRIPTION,
        "consent": True,
        "submitter": "agency",
        "agency_name": "ChatGPT, AI assistant acting for Love My Uniform Ltd",
        "agency_told": True,
        "timezone": "Europe/London",
    }
    ref = lookup.get("lookup_ref")
    if lookup_status == 200 and ref:
        payload["lookup_ref"] = ref
    elif lookup_status in (429,):
        payload["lookup_failed"] = "limit"
    elif lookup_status in (503,):
        payload["lookup_failed"] = "busy"
    elif lookup_status == 422 and lookup.get("code") == "website_unreadable":
        payload["lookup_failed"] = "unreadable"
    else:
        payload["lookup_failed"] = "error"

    try:
        status, result = post("applications", payload, timeout=30, headers={"Idempotency-Key": SUBMISSION_KEY})
    except (TimeoutError, URLError, OSError):
        print("APPLICATION_HTTP=network_error")
        return 1

    print("APPLICATION_HTTP=" + str(status))
    if status == 201:
        # Docs explicitly describe the application ID as secret. Never print/store it publicly.
        safe_record("RECEIVED_PENDING_REVIEW")
        print("STATUS=RECEIVED_PENDING_REVIEW")
        print("NEXT=Directory review, then business email verification. Not yet published.")
        return 0
    code = str(result.get("code", "unknown"))
    print("APPLICATION_CODE=" + code)
    if status == 409 and code in ("listed", "waiting"):
        value = "ALREADY_LISTED_VERIFY_URL" if code == "listed" else "ALREADY_PENDING"
        safe_record(value)
        print("STATUS=" + value)
        return 0
    if status in (403, 422) and code in ("not_accepted", "not_listed"):
        safe_record("DECLINED_DO_NOT_RETRY")
        print("STATUS=DECLINED_DO_NOT_RETRY")
        return 0
    if status == 422:
        print("VALIDATION_FIELDS=" + ",".join(e.get("field", "?") for e in result.get("errors", [])))
    # Do not mark as submitted on validation, rate, or server errors.
    print("STATUS=NOT_SUBMITTED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
