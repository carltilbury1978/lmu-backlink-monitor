"""Read-only backlink verification for Love My Uniform. No paid APIs or logins."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
TARGETS = ROOT / "targets.csv"
REPORT = ROOT / "report.csv"
SUMMARY = ROOT / "summary.md"
DOMAIN = "lovemyuniform.com"


class LinkParser(HTMLParser):
    def __init__(self, base: str):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.found = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        data = dict(attrs)
        href = data.get("href") or ""
        full = urljoin(self.base, href)
        parsed = urlsplit(full)
        if parsed.scheme in ("http", "https") and (parsed.hostname or "").lower().removeprefix("www.") == DOMAIN:
            self.found.append((full, data.get("rel", "")))


def check(name: str, url: str):
    try:
        req = Request(url, headers={"User-Agent": "LMU-Link-Verification/1.0 (+https://www.lovemyuniform.com)", "Accept": "text/html"})
        with urlopen(req, timeout=12) as response:
            status = response.status
            ctype = response.headers.get("Content-Type", "").lower()
            final_url = response.geturl()
            body = response.read(1_500_000).decode("utf-8", "replace")
        if "html" not in ctype:
            return "UNKNOWN", "", "Not HTML; manual review needed"
        parser = LinkParser(final_url)
        parser.feed(body)
        if parser.found:
            href, rel = parser.found[0]
            return "LINK_FOUND", href, ("rel=" + str(rel)) if rel else "Direct HTML link"
        return "NOT_FOUND", "", "No direct HTML link found on fetched page"
    except HTTPError as exc:
        return "UNKNOWN", "", "HTTP " + str(exc.code) + "; do not treat as a missing backlink"
    except (URLError, TimeoutError, ValueError, OSError) as exc:
        return "UNKNOWN", "", type(exc).__name__ + "; manual review needed"


def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with TARGETS.open(newline="", encoding="utf-8") as f:
        targets = list(csv.DictReader(f))
    rows = []
    for row in targets[:25]:
        status, found, reason = check(row["site"], row["source_url"])
        rows.append({
            "site": row["site"], "source_url": row["source_url"],
            "status": status, "linked_url": found,
            "detail": reason, "checked_at": now,
        })
    with REPORT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["site", "source_url", "status", "linked_url", "detail", "checked_at"])
        writer.writeheader()
        writer.writerows(rows)
    counts = {key: sum(r["status"] == key for r in rows) for key in ("LINK_FOUND", "NOT_FOUND", "UNKNOWN")}
    lines = [
        "# Love My Uniform backlink verification",
        "",
        "Checked: " + now,
        "",
        "Verified direct HTML links: " + str(counts["LINK_FOUND"]),
        "Not found on the fetched page: " + str(counts["NOT_FOUND"]),
        "Unknown / blocked / manual checks needed: " + str(counts["UNKNOWN"]),
        "",
        "This verifies links on the listed pages only. It does not create links,",
        "rank their SEO value, bypass verification, or submit directory listings.",
        "A NOT_FOUND result on a directory search page does not prove that a separate",
        "business profile is absent. Check report.csv for details.",
        "",
    ]
    SUMMARY.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
