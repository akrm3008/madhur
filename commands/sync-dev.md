# Sync Dev with Main

Sync the `dev` branch with `main` after a release or hotfix PR has been merged.

## Instructions

1. **Fetch latest and update main:**
   ```bash
   git fetch origin
   git checkout main
   git pull origin main
   ```

2. **Merge main into dev:**
   ```bash
   git checkout dev
   git merge main
   ```

3. **Push dev:**
   ```bash
   git push origin dev
   ```

4. **Return to previous branch (optional):**
   ```bash
   git checkout -
   ```

5. **Report back** with confirmation that dev is synced.

## Important Notes

- This creates a merge commit on `dev` — that is expected and correct
- **NEVER use `git reset --hard` or `git push --force-with-lease`** to sync branches
- If there are merge conflicts, stop and inform the user
- **NEVER force push** to `dev` or `main`
