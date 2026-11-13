# Love My Uniform backlink monitor

This public repository contains a **free, read-only** checker for external links to [Love My Uniform](https://www.lovemyuniform.com/), a UK workwear and staff-uniform supplier.

The script checks specifically nominated public pages, looks for an actual HTML link to the Love My Uniform domain, and writes a CSV and summary. An inaccessible page is marked **UNKNOWN**, not falsely reported as a missing link.

## Running it

```sh
python backlinks/verify.py
```

The `LMU free backlink verification` GitHub Action runs every day at 06:17 UTC and whenever `backlinks/targets.csv` or `backlinks/verify.py` changes. You can run it manually from GitHub Actions too.

The reports are in `backlinks/report.csv` and `backlinks/summary.md` after a successful run. The initial list is deliberately short. Add only direct, verified profile or article URLs.

## Scope and restrictions

- £0 additional spend: public-repository standard GitHub-hosted runners only, no paid APIs.
- No website logins, directory form submissions, CAPTCHAs, spam postings, or paid links.
- No Shopify theme or site changes. No outreach email.
- The tool verifies links; it **does not** itself create or guarantee third-party editorial backlinks.
- GitHub's own public README link above is an example of a legitimate reference to the business; it should not be confused with a high-value editorial SEO backlink.

The directory outreach and organic channel development are separate workstreams.
