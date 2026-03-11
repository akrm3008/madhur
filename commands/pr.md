# Create Pull Request

Push the current branch and open a pull request.

ARGUMENTS: $ARGUMENTS

## Routing

Parse `$ARGUMENTS` to determine the PR type:

| Command | Source | Target | Use case |
|---------|--------|--------|----------|
| `/pr` | current feature branch | `dev` | Day-to-day: merge feature into dev for testing |
| `/pr release` | `dev` | `main` | Promote dev to production |
| `/pr from <branch>` | `<branch>` | `dev` | PR a specific branch into dev |
| `/pr from <branch> into <base>` | `<branch>` | `<base>` | Custom source and target |
| `/pr hotfix` | current branch | `main` | Urgent fix directly to prod |

**Defaults:** If no arguments are provided, source = current branch, target = `dev`.
If the current branch IS `dev`, source = `dev`, target = `main` (assumes a release PR).

## Branch Naming Conventions

Feature branches should follow these prefixes:
- `feat/` — new features
- `fix/` — bug fixes
- `refactor/` — code restructuring
- `docs/` — documentation changes
- `chore/` — maintenance tasks
- `perf/` — performance improvements
- `test/` — test additions or changes

Examples: `feat/waymore-cache-support`, `fix/tlsx-timeout-handling`

## Instructions

1. **Determine source and target branches** from arguments (see Routing table above).

2. **Ensure you are on the source branch:**
   ```bash
   git checkout <source-branch>
   ```

3. **Check for uncommitted changes:**
   - Run `git status --porcelain` to see modified tracked files
   - If there are uncommitted changes, stage and commit them:
     - `git add -u`
     - Generate a meaningful commit message based on the changes
     - `git -c color.ui=never commit -m 'message'` (direct single-quoted string, NEVER HEREDOC)
   - If the working tree is clean, proceed without committing

4. **Inspect the diff:**
   - Run `git diff --stat --no-color <target>..<source>` to understand the scope of changes
   - Run `git -c color.ui=never log --oneline --no-color <target>..<source>` to see commits
   - Analyze the changes to determine what they accomplish
   - Read modified files or diff content if needed for context

5. **Push the source branch:**
   ```bash
   git push -u origin <source-branch>
   ```

6. **Create the pull request** using `gh pr create` with `NO_COLOR=1`:
   - **CRITICAL**: Always prefix with `NO_COLOR=1` to prevent ANSI injection
   - Generate a concise PR title summarizing the changes
   - Generate a PR body with:
     - `## Summary` section with bullet points describing the changes
     - `## Files Changed` section listing the modified files
   - **CRITICAL**: Pass body as a direct single-quoted string, NOT via HEREDOC or command substitution
   - **Merge strategy reminder in body** — include the appropriate reminder based on PR type:
     - Feature → dev: `Merge via **squash and merge**.`
     - Release (dev → main): `Merge via **create a merge commit**.`
     - Hotfix → main: `Merge via **squash and merge**.`
   - Example:
     ```bash
     NO_COLOR=1 gh pr create --base dev --head feat/my-feature --title "title" --body '## Summary
     - Change 1

     ## Files Changed
     - file1.py

     Merge via **squash and merge**.'
     ```

7. **Post-merge instructions** — tell the user what to do after the PR is merged:

   **If this was a feature → dev PR:**
   - The merge to `dev` auto-deploys to the dev environment for testing
   - When ready to promote to production, run `/pr release`

   **If this was a dev → main (release) PR or hotfix → main PR:**
   - After the PR is merged on GitHub, sync `dev` with `main`:
     ```bash
     git checkout main && git pull
     git checkout dev && git merge main && git push origin dev
     ```
   - This creates a merge commit on `dev` — that is expected and correct.
   - **NEVER use `git reset --hard` or `git push --force-with-lease`** to sync branches.
   - Optionally tag the release:
     ```bash
     gh release create v<version> --target main --generate-notes
     ```

8. **Report back with:**
   - The source and target branches
   - The PR URL (from `gh pr create` output)
   - Files included
   - Post-merge instructions (from step 7, based on PR type)

## Merge Strategy

- **Feature → dev PRs**: Use **Squash and merge** on GitHub.
- **Release (dev → main) PRs**: Use **Create a merge commit** on GitHub. This preserves shared commit history between dev and main, making subsequent syncs clean and trivial.
- **Hotfix → main PRs**: Use **Squash and merge** on GitHub.
- **NEVER use "Rebase and merge"** for any PR type.

## Hotfix Flow

For urgent production fixes:
1. Create a branch from `main`: `git checkout -b fix/critical-bug main`
2. Make the fix, then `/pr hotfix` to PR directly into `main`
3. After merge, sync dev: `git checkout dev && git merge main && git push origin dev`

## Critical: Preventing ANSI Color Codes

ANSI escape sequences (like `[38;2;...m`) corrupt commit messages and PR descriptions. zsh syntax highlighting injects ANSI codes into `$(...)` command substitutions, so **all text passed to git/gh must be direct string literals**.

1. **Always use `git -c color.ui=never`** for any git command that produces output:
   ```bash
   git -c color.ui=never diff --stat
   git -c color.ui=never log --oneline -5
   ```

2. **NEVER use HEREDOC or `$(...)` for commit messages or PR bodies.** Pass them as direct single-quoted strings:
   ```bash
   # CORRECT - direct single-quoted string
   git -c color.ui=never commit -m 'Migrate tier filtering to Tier enum'

   # WRONG - HEREDOC inside command substitution gets ANSI-injected by zsh
   git commit -m "$(cat <<'EOF'
   Migrate tier filtering to Tier enum
   EOF
   )"
   ```

3. **Use `--no-color` flag** as additional safety on commands that support it:
   ```bash
   git diff --stat --no-color
   git log --oneline --no-color
   ```

4. **For gh CLI**, prefix with `NO_COLOR=1` and pass title/body as direct single-quoted string literals, not interpolated from command output

## Important Notes

- Only include tracked files that have modifications (use `git add -u`, not `git add .`)
- Do NOT include untracked files unless the user explicitly asks
- If there are no changes between the source and target branches, inform the user and stop
- The main branch is called `main`
- The default development branch is `dev`
- **NEVER delete `dev`** — it is the persistent working branch for development
- **NEVER force push** to `dev` or `main` — use `git merge` to sync branches