# Cross-Domain Relationships

## FK Map: How Tables Connect

### Organisation → Everything
```
organisations ──→ tlds (organisation_id)
             ──→ org_asns (organisation_id)
             ──→ user_org_memberships (organisation_id)
             ──→ dns_entries (organisation_id)
             ──→ ips (organisation_id)
             ──→ live_hosts (organisation_id)
             ──→ hosts (organisation_id)
             ──→ ip_ports (organisation_id)
             ──→ vhosts (organisation_id)
             ──→ scans (organisation_id)
             ──→ threat_models (organisation_id)
             ──→ organization_security_config (organisation_id)
```

### TLD → Asset Chain
```
tlds ──→ dns_entries (tld_id)
     ──→ endpoint_leads (tld_id) — generic leads
     ──→ scans (tld_id)
     ──→ boundaries (tld_id)
     ──→ related_domain_leads (tld_id)
     ──→ imported_findings (tld_id)
     ──→ nuclei_scan_results (tld_id)
     ──→ secrets_scan_results (tld_id)
```

### DNS → IP → LiveHost → Host → Endpoints
```
dns_entries ──→ ips (ip_id) [A/AAAA records only]
            ──→ live_hosts (live_host_id) [many DNS entries → one LiveHost]

ips ──→ ip_ports (ip_id)
    ──→ ip_geolocations (ip_id) [1:1]

ip_ports ←→ live_hosts [M2M via port_live_host_association]

live_hosts ──→ hosts (host_id) [1:1]
           ──→ service_layers (live_host_id) [1:1]
           ──→ certificate_issues (live_host_id)
           ──→ boundary_memberships (live_host_id)
           ──→ imported_findings (live_host_id)

hosts ──→ endpoints (host_id)
      ──→ endpoint_leads (host_id)
      ──→ content_discovery_scans (host_id)
      ──→ vhosts (host_id) [1:1 via VHost]
      ──→ domain_analysis (host_id)

endpoints ──→ endpoint_values (endpoint_id)
          ──→ endpoint_leads (endpoint_id) — verified leads
```

### EndpointValue → Metadata (all M2M)
```
endpoint_values ←→ params [via endpoint_value_param_association]
                ←→ headers [via endpoint_value_header_association]
                ←→ titles [via endpoint_value_title_association]
                ←→ tech_tags [via endpoint_value_tech_tag_association]
```

### Findings → Groupings
```
imported_findings ←→ finding_duplicate_groups [via finding_duplicate_membership]
                  ←→ finding_correlation_groups [via finding_correlation_membership]
                  ──→ asset_references (finding_id)
                  ──→ vulnerability_identifiers (finding_id)
                  ──→ finding_cloud_metadata (finding_id) [1:1]
                  ──→ finding_bug_class_tags (finding_id)
                  ──→ finding_threat_model_memberships (finding_id)
                  ──→ findings_assignments (finding_id)
```

### Bug Class → Limitations
```
finding_bug_class_tags ──→ finding_limitations (finding_bug_class_tag_id)
                                  ──→ limitations (limitation_id)
```

### Scan Tracking
```
scans (DomainCollectionScan) ──→ task_runs (scan_id)
content_discovery_scans ──→ task_runs (content_discovery_scan_id)
```

## Common Join Paths

### "Get all endpoints for a TLD"
```
tlds → dns_entries (tld_id) → live_hosts (live_host_id) → hosts (host_id) → endpoints (host_id)
```

### "Get boundary for a finding"
```
imported_findings.live_host_id → boundary_memberships.live_host_id → boundaries
```

### "Get findings for a domain"
```
live_hosts.domain LIKE '%example.com%' → imported_findings.live_host_id
-- or via DNS:
dns_entries.key LIKE '%example.com%' → imported_findings.dns_entry_id
```

### "Get all assets in a boundary"
```
boundaries → boundary_memberships → ips / live_hosts / dns_entries / ip_ports / vhosts
```

### "Get endpoint leads with domain context"
```
-- Host-linked leads:
endpoint_leads (host_id IS NOT NULL) → hosts → live_hosts.domain
-- DNS-linked leads:
endpoint_leads (dns_entry_id IS NOT NULL) → dns_entries.key
-- Generic leads:
endpoint_leads (tld_id IS NOT NULL) → tlds.tld
```
