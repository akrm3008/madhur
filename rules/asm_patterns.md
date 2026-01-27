# ASM Codebase Patterns

## LiveHost.domain Format

`LiveHost.domain` stores the **full URL with scheme** (e.g., `https://example.com`).

- Always include scheme when creating LiveHost records
- Use `urlparse` from `urllib.parse` for URL parsing, never string splitting
- Domain uniqueness is based on full URL (http vs https are different records)


## Key Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `live_hosts` | Live web hosts | `domain` (full URL with scheme) |
| `hosts` | Host identity | `protocol` |
| `dns_entries` | DNS records | `key` (hostname), `record_type` |
| `endpoints` | URL paths | `endpoint_path`, `host_id` |
| `endpoint_values` | HTTP response data | `status_code`, `content_length` |
| `tlds` | Root domains | `tld`, `tier`, `in_scope` |

## Code Locations

- **Domain collection flows:** `asm-prefect/src/domain_collection/flows/`
- **Content discovery tools:** `asm-prefect/src/content_discovery/tools/`
- **Database models:** `common-python-utils/src/db/models/`
- **Main persistence function:** `domain_collection/flows/helpers.py` → `persist_live_hosts_to_db()`
