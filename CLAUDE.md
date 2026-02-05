# Global Claude Rules

This directory contains reusable rules and patterns for Claude across all projects.

## Structure

```
.claude/
├── CLAUDE.md           # This file
├── settings.json       # Plugin marketplace config
├── rules/
│   ├── formatting.md             # Output formatting rules (tables, diagrams)
│   ├── infrastructure_access.md  # DB, AWS, Docker access patterns
│   ├── asm_patterns.md           # ASM-specific code patterns
│   ├── python_rules.md           # Python tooling (uv, ruff)
│   ├── frontend_rules.md         # React/frontend patterns
│   ├── serverless_functions.md   # Serverless patterns
│   └── terraform/                # Terraform-specific rules
```

## Plugins

The `settings.json` configures the following plugin marketplaces:

- **cc-skills** (`terrylica/cc-skills`) — includes `ascii-diagram-validator` for validating box-drawing diagram alignment in markdown files

## Usage

These rules are loaded automatically when working in subdirectories of ~/git/.

For project-specific rules, create a `.claude/CLAUDE.md` in the project root.
