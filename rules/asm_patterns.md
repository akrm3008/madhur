# ASM Codebase Patterns

## LiveHost.domain Format

`LiveHost.domain` stores the **full URL with scheme** (e.g., `https://example.com`).

- Always include scheme when creating LiveHost records
- Use `urlparse` from `urllib.parse` for URL parsing, never string splitting
- Domain uniqueness is based on full URL (http vs https are different records)

```python
from urllib.parse import urlparse

# Creating LiveHost - include scheme
domain_with_scheme = f"{protocol}://{domain}"
live_host = LiveHost(domain=domain_with_scheme, ...)

# Looking up LiveHost - use full URL with scheme
live_host = session.scalar(
    select(LiveHost).where(LiveHost.domain == f"https://{hostname}")
)

# Extracting hostname from LiveHost.domain
parsed = urlparse(live_host.domain)
hostname = parsed.netloc  # e.g., "example.com"
scheme = parsed.scheme    # e.g., "https"
```

## URL Parsing

**Never use string splitting for URLs.** Always use `urlparse`:

```python
# BAD - don't do this
if "://" in url:
    domain = url.split("://", 1)[1]

# GOOD - use urlparse
from urllib.parse import urlparse
parsed = urlparse(url)
hostname = parsed.netloc or parsed.hostname
scheme = parsed.scheme
```

## Host vs LiveHost vs DNSEntry

- **Host**: Stores protocol (http/https), links to endpoints
- **LiveHost**: Identity of a live web host, stores full URL with scheme in `domain` field
- **DNSEntry**: DNS resolution record, `key` field stores hostname WITHOUT scheme

```
Host.protocol = "https"
LiveHost.domain = "https://api.example.com"  # WITH scheme
DNSEntry.key = "api.example.com"             # WITHOUT scheme
```

## SQLAlchemy Patterns

### Union queries (SQLAlchemy 2.0)
```python
# union() already returns distinct results - don't call .distinct() on CompoundSelect
query = query1.union(query2)  # Correct
query = query1.union(query2).distinct()  # WRONG - AttributeError
```

### Upserts
```python
from sqlalchemy.dialects.postgresql import insert

stmt = (
    insert(Model)
    .values(field=value)
    .on_conflict_do_nothing(index_elements=["unique_field"])
)
session.execute(stmt)
```

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
