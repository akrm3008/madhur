# codex-review — Run OpenAI Codex Code Review

Run an AI code review using OpenAI Codex on the current branch's changes.

## Prerequisites

- Codex CLI installed: `npm install -g @openai/codex`
- Authenticated: `codex login`

## Usage

Find and run the `codex-review.sh` script from the current repo's `scripts/` directory:

```bash
# Review changes against dev (default)
./scripts/codex-review.sh

# Review against a different base branch
./scripts/codex-review.sh --base main

# Save review to a file
./scripts/codex-review.sh --output review.md
```

The script must be run from within a git repo that contains `scripts/codex-review.sh`.

## Options

- `--base BRANCH` — Base branch to diff against (default: `dev`)
- `--model MODEL` — Codex model to use (default: `gpt-5.2-codex`)
- `--output FILE` — Save review to file instead of stdout
- `--json` — Output raw JSON instead of extracted message

## What It Does

1. Fetches the base branch and computes the diff
2. Excludes lock files and generated files (`*.lock`, `requirements.txt`, `*.min.js`, `*.min.css`)
3. Builds a prompt with changed files list, project standards references, and the diff
4. Runs `codex exec` and extracts the review text
5. Codex reads the repo's `docs/reference/standards.md`, `docs/reference/engineering-philosophy.md`, and `AGENTS.md` for project-specific review criteria

## CI Integration

The GitHub Actions workflow at `.github/workflows/codex-review.yaml` can also trigger reviews:
- Manually via workflow dispatch
- On `@codex` mentions in PR comments

## When to Use

- Before opening a PR, to catch issues early
- When you want a second opinion on code changes
- To verify compliance with project coding standards
