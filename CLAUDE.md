# Global Claude Rules

This directory contains reusable rules and patterns for Claude across all projects.

## Structure

```
.claude/
├── CLAUDE.md                              # This file
├── settings.json                          # Plugin marketplace config
├── rules/
│   ├── project_overview.md                # What Aisy is, mono-repo map, data flow
│   ├── data_architecture.md               # Domain-level table map, cross-domain patterns
│   ├── asm_patterns.md                    # ASM gotchas (LiveHost.domain, DNS, endpoints)
│   ├── domain_collection.md               # DC/CD pipeline flow, persistence patterns
│   ├── vulnerability_management.md        # Vuln mgmt pipeline, dedup/correlation/boundaries
│   ├── infrastructure_access.md           # DB, AWS, Docker access patterns
│   ├── python_rules.md                    # Python tooling (uv, ruff)
│   ├── frontend_rules.md                  # React/frontend patterns
│   ├── serverless_functions.md            # Serverless patterns
│   ├── formatting.md                      # Output formatting rules (tables, diagrams)
│   └── terraform/                         # Terraform-specific rules
├── skills/
│   └── db-schema/                         # Full DB schema reference (invoke for column-level detail)
│       ├── SKILL.md                       # Skill entry point
│       └── reference/                     # Per-domain schema docs
│           ├── business.md
│           ├── domain_collection.md
│           ├── content_discovery.md
│           ├── vulnerability_management.md
│           ├── infrastructure.md
│           └── relationships.md           # Cross-domain FK map + join paths
```

## Skills

- **db-schema** — Full database schema reference. Use when you need column-level detail (types, constraints, FKs, indexes) beyond what the always-loaded `data_architecture.md` provides.

## Plugins

The `settings.json` configures the following plugin marketplaces:

- **cc-skills** (`terrylica/cc-skills`) — includes `ascii-diagram-validator` for validating box-drawing diagram alignment in markdown files

## Usage

These rules are loaded automatically when working in subdirectories of ~/git/.

For project-specific rules, create a `.claude/CLAUDE.md` in the project root.
