# Production Readiness Dashboard

Check the production readiness state of all repos and optionally create release PRs.

ARGUMENTS: $ARGUMENTS

## Instructions

1. Run the dashboard script:
   ```bash
   bash "$(git rev-parse --show-toplevel)/.claude/scripts/prod-readiness.sh"
   ```

2. **Interpret the results** for the user:
   - The script outputs a table showing each repo's state across: pending commits, branch divergence, open PRs, CI status, and sync-dev issues
   - Below the table is a grouped details section with commit lists and PR titles
   - At the bottom are cross-repo checks (DB migrations, Hasura metadata) and action items

3. **Summarize** the output concisely — only mention repos that need attention:
   - Do NOT list clean/green repos. Silence means healthy.
   - Only mention repos with issues, prioritized: CI failures > sync-dev issues > branch divergence > pending commits > open PRs
   - If everything across all repos is green, just say "All repos are production-ready."

4. **Present ready repos as a numbered pick-list:**
   - Show only repos that meet the readiness criteria (see below) as a compact numbered list
   - Format example:
     ```
     Ready to release:
       1. app-frontend (6 commits)
       2. common-python-utils (3 commits)
       3. aisy-hasura (2 commits)

     Which ones? (e.g. "1,3" or "all")
     ```
   - Keep it short — just the number, repo name, and commit count. Nothing else.
   - When the user replies with numbers (e.g. "1,3" or "1 and 3" or "all"), create release PRs for those repos:
     - For each selected repo, `cd` into the repo directory
     - Read `.claude/commands/pr.md` and follow its instructions for a `release` PR (source=`dev`, target=`main`)
   - After all PRs are created, list the PR URLs

5. **If the user provides arguments**, interpret them:
   - `/prod-readiness` — run the full dashboard and show the pick-list
   - `/prod-readiness <repo>` — only process the specified repo

## Column Reference

| Column | Meaning |
|--------|---------|
| Pending | Commits on dev not yet in main (pending for production) |
| Div | Commits on main not in dev (sync-dev failure / branch divergence) |
| PR:dev | Open PRs targeting dev (work in progress) |
| PR:main | Open PRs targeting main (production releases in review) |
| CI:dev | Latest CI run status on dev branch |
| CI:main | Latest CI run status on main branch |
| Sync | Open GitHub issues with `sync-dev-failed` label |

## Readiness Criteria for Release PRs

A repo is "ready for release" when ALL of these are true:
- Pending > 0 (there are commits to release)
- Div = 0 (no branch divergence)
- CI:dev = ok (dev CI is passing)
- Sync = 0 (no sync-dev failures)
- PR:main = 0 (no existing release PR already open)

## Notes

- Dependency update PRs (chore(deps), fix(deps), Renovate) are automatically filtered out
- The script runs all git fetches and GitHub API calls in parallel (~2s total)
- Green 0 = healthy, yellow = needs attention, red = urgent
