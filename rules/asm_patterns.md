# ASM Codebase Patterns

## LiveHost.domain Format

`LiveHost.domain` stores the **full URL with scheme** (e.g., `https://example.com`).

- Always include scheme when creating LiveHost records
- Use `urlparse` from `urllib.parse` for URL parsing, never string splitting
- Domain uniqueness is based on full URL (http vs https are different records)

## DNSEntry.key vs DNSEntry.value

- `key` = the hostname being resolved (e.g., `web.example.com`)
- `value` = the resolution result (e.g., `1.1.1.1` for A records, `other.example.com` for CNAME)
- `record_type` = A, AAAA, CNAME, etc.
- A/AAAA records also populate `ip_id`; CNAME records do not

## Endpoint vs EndpointLead

- **Endpoint** = confirmed path on a live host (verified by ffuf/httpx). Has response data via EndpointValue.
- **EndpointLead** = unverified path from passive sources (waymore, jsluice, linkfinder). May not be live.
- EndpointLeads use a specificity hierarchy: `host_id` (live host known) > `dns_entry_id` (subdomain known) > `tld_id` (generic, no subdomain context)

## Key Tables

- **`live_hosts`** — live web hosts. Key: `domain` (full URL with scheme)
- **`hosts`** — host identity. Key: `protocol`
- **`dns_entries`** — DNS records. Key: `key` (hostname), `record_type`
- **`ips`** — IP addresses (INET). Key: `ip` (unique)
- **`ip_ports`** — open ports. Key: `port`, `ip_id`
- **`endpoints`** — URL paths. Key: `endpoint_path`, `host_id`
- **`endpoint_values`** — HTTP response data. Key: `status_code`, `content_length`
- **`endpoint_leads`** — unverified paths. Key: `endpoint_path`, `source`
- **`tlds`** — root domains. Key: `tld`, `tier`, `in_scope`

## Code Locations

- **Domain collection flows:** `asm-prefect/src/domain_collection/flows/`
- **Content discovery tools:** `asm-prefect/src/content_discovery/tools/`
- **Database models:** `common-python-utils/src/db/models/`
- **Main persistence function:** `domain_collection/flows/helpers.py` → `persist_live_hosts_to_db()`
