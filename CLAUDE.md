# Global Claude Rules

This directory contains reusable rules and patterns for Claude across all projects.

## Structure

```
.claude/
├── CLAUDE.md           # This file
├── rules/
│   ├── infrastructure_access.md  # DB, AWS, Docker access patterns
│   ├── asm_patterns.md           # ASM-specific code patterns
│   ├── python_rules.md           # Python tooling (uv, ruff)
│   ├── frontend_rules.md         # React/frontend patterns
│   ├── icons.md                  # Icon library standards (Phosphor only)
│   ├── serverless_functions.md   # Serverless patterns
│   └── terraform/                # Terraform-specific rules
```

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
