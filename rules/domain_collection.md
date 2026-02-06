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

## Downstream Consumers

vuln-mgmt-prefect reads this data for ML analysis. The key consumption point is `format_domain_data_impl()` in `vuln-mgmt-prefect core/analysis/boundaries/utils.py`, which converts ASM records into labelled text for LLM reasoning:

- **dns_entries** → SHARED_IP groupings, CNAME service detection, REVERSE_IP_DNS, SIBLING_DNS
- **live_hosts** → DOMAIN, STATUS, CREATED date
- **endpoints + endpoint_leads** → CONFIRMED_ENDPOINTS, LEAD_ENDPOINTS (merged + deduped)
- **ips** → IP infrastructure summary (which domains share IPs)
- **attribute_tags** → TECHNOLOGY, TAGS
- **titles, headers** → TITLE, HEADERS

Changes to ASM data shapes (new columns, renamed fields, different data formats) directly affect ML pipeline quality. See `ML_GUIDE.md` in vuln-mgmt-prefect for the full context formatting spec.
