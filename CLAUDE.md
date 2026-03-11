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
│   ├── icons.md                           # Icon library standards (Phosphor only)
│   ├── serverless_functions.md            # Serverless patterns
│   ├── formatting.md                      # Output formatting rules (tables, diagrams)
│   ├── stacked_prs.md                     # Stacked PRs with av (Aviator CLI)
│   └── terraform/                         # Terraform-specific rules
├── skills/
│   ├── db-schema/                         # DB schema reference (points to ORM models + ML_GUIDE.md)
│   │   └── SKILL.md                       # Skill entry point
│   └── codex-review/                      # Run OpenAI Codex code review on current branch
│       └── SKILL.md
```

## Skills

- **db-schema** — Database schema reference. Points to the ORM models, ML_GUIDE.md, and docs/database-schema-guide.md for column-level detail beyond what the always-loaded `data_architecture.md` provides.
- **codex-review** — Run an OpenAI Codex code review on the current branch. Requires `codex` CLI installed and authenticated.

## Plugins

The `settings.json` configures the following plugin marketplaces:

- **cc-skills** (`terrylica/cc-skills`) — the `doc-tools` plugin, which bundles the `ascii-diagram-validator` skill for validating box-drawing diagram alignment in markdown files

## Usage

These rules are loaded automatically when working in subdirectories of ~/git/.

For project-specific rules, create a `.claude/CLAUDE.md` in the project root.

## Git: Preventing ANSI Color Codes

zsh syntax highlighting injects ANSI escape sequences into `$(...)` command substitutions, corrupting commit messages and PR descriptions. Follow these rules for ALL git commits, not just PRs:

1. **NEVER use HEREDOC or `$(...)` for commit messages.** Use direct single-quoted strings or write to a temp file with the Write tool then `git commit -F /tmp/msg.txt`.
2. **Always use `git -c color.ui=never`** for any git command that produces output.
3. **Always use `--no-color`** flag on git commands that support it.
4. **Always prefix `gh` CLI commands with `NO_COLOR=1`.**

```bash
# CORRECT
git -c color.ui=never commit -m 'Add delete user feature'

# CORRECT - for multi-line messages, write file with Write tool first
git commit -F /tmp/clean-commit-msg.txt

# WRONG - HEREDOC gets ANSI-injected by zsh
git commit -m "$(cat <<'EOF'
Add delete user feature
EOF
)"
```
