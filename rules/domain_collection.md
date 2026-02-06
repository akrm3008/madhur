---
paths:
  - "asm-prefect/src/domain_collection/**"
  - "asm-prefect/src/content_discovery/**"
  - "common-python-utils/src/db/models/domain_collection/**"
  - "common-python-utils/src/db/models/content_discovery/**"
---

# Domain Collection & Content Discovery

## Pipeline Flow

```
TLD
 ├── DNS Enumeration (subfinder, amass)
 │     └── DNSEntry (key=hostname, record_type=A/AAAA/CNAME)
 │           └── IP (unique on ip, INET type)
 ├── Live Host Verification (httpx)
 │     └── LiveHost (domain includes scheme, e.g. https://example.com)
 │           └── Host (protocol context, owns endpoints)
 ├── Port Scanning
 │     └── IPPort ←→ LiveHost (many-to-many via port_live_host_association)
 └── Content Discovery (ffuf, waymore, nuclei, trufflehog)
       ├── Endpoint + EndpointValue (confirmed, with HTTP response data)
       ├── EndpointLead (unverified, from passive sources)
       └── NucleiScanResult / SecretsScanResult
```

## Key Relationships

- **DNSEntry → IP**: A/AAAA records link to `ips` table via `ip_id`. CNAME records do not.
- **DNSEntry → LiveHost**: Many DNS entries can point to the same LiveHost (`live_host_id`).
- **LiveHost → Host**: One-to-one. Host stores protocol; LiveHost stores full domain with scheme.
- **IP → IPPort**: One-to-many. Each port links back to its IP.
- **IPPort ↔ LiveHost**: Many-to-many. One live host can be on multiple ports; one port can serve multiple vhosts.

## Persistence Pattern

`persist_live_hosts_to_db()` in `domain_collection/flows/helpers.py` is the main upsert function. It:
1. Creates or finds the IP record
2. Creates or finds the DNSEntry
3. Creates or finds the Host (with protocol)
4. Creates or finds the LiveHost (with full domain URL)
5. Links DNSEntry → LiveHost and IPPort → LiveHost

## Scan Tracking

- **DomainCollectionScan** (`scans`) — one per TLD per scan run. Tracks orchestrator/pre-waymore/waymore/post-waymore flow run IDs.
- **ContentDiscoveryScan** (`content_discovery_scans`) — one per host per scan_type+http_method combo. Tracks ffuf/nuclei runs.
- **TaskRun** (`task_runs`) — individual task execution within a scan. Links to either scan type. Stores `task_metadata` as JSONB.

## EndpointLead Hierarchy

EndpointLeads have three levels of specificity (only one FK set):
1. `host_id` set — lead discovered on a live host (most specific)
2. `dns_entry_id` set, `host_id=None` — subdomain known but not live
3. `tld_id` set, both `None` — generic lead with no subdomain context
- `domain_hint` stores the domain string when we can't link to a DNSEntry
