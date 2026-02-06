# Stacked PRs with av

Aisy can use [av](https://github.com/aviator-co/av) (Aviator CLI) for stacked PRs — breaking large features into smaller, dependent pull requests.

## Key Commands

- `av branch <name>` — create a new branch stacked on the current one
- `av tree` — show the stack visualization
- `av pr --all` — create PRs for the entire stack
- `av sync` — fetch, rebase the stack, and push
- `av pr --queue` — queue the current PR for merge

## Workflow

```bash
# Start from main
git checkout main && git pull

# Create first branch in the stack
av branch feature-part1
# ... make changes, commit ...

# Stack another branch on top
av branch feature-part2
# ... make changes, commit ...

# Create PRs for the whole stack
av pr --all

# After review feedback, sync the stack
av sync
```

## Merging

Merge PRs bottom-up: merge PR #1 via GitHub UI, run `av sync` to rebase the rest, repeat.

## Notes

- Reviewers don't need av — stacked PRs appear as normal GitHub PRs
- Works with git worktrees — av metadata is shared across worktrees
- Run `av sync` frequently after changes or merges
