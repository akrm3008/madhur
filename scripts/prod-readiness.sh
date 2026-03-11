#!/usr/bin/env bash
set -euo pipefail

# ── Production Readiness Dashboard ──────────────────────────────────────────
# Compact table overview + details only for items needing attention.
# All git fetches and gh API calls run in parallel for speed.
# Usage: bash scripts/prod-readiness.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TMPDIR_BASE=$(mktemp -d)
trap 'rm -rf "$TMPDIR_BASE"' EXIT

# ── Color helpers ───────────────────────────────────────────────────────────
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
GREEN='\033[0;32m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

warn() { printf "${YELLOW}[!!]${RESET} %s\n" "$1"; }

# Filter out dependency/Renovate PRs (chore(deps), fix(deps), and Renovate config PRs)
filter_dep_prs() { jq '[.[] | select(.title | test("^(chore|fix)\\(deps\\)"; "i") or test("renovate"; "i") | not)]'; }

# ── Repo definitions ───────────────────────────────────────────────────────
REPOS=(
  "aisy-hasura|aisy-ai/hasura-config|dev/main"
  "serverless-functions|aisy-ai/serverless-functions|dev/main"
  "asm-prefect|aisy-ai/asm-prefect|dev/main"
  "app-frontend|aisy-ai/app-frontend|dev/main"
  "common-python-utils|aisy-ai/common-python-utils|dev/main"
  "infra-config|aisy-ai/infra-config|main-only"
)

ACTION_ITEMS=()
declare -A REPO_DETAILS  # keyed by repo name, values are newline-separated detail lines
DETAIL_ORDER=()          # tracks insertion order

add_repo_detail() {
  local repo="$1" line="$2"
  if [[ -z "${REPO_DETAILS[$repo]+x}" ]]; then
    REPO_DETAILS["$repo"]="$line"
    DETAIL_ORDER+=("$repo")
  else
    REPO_DETAILS["$repo"]+=$'\n'"$line"
  fi
}

# ── Phase 1: Fire off all git fetches + gh API calls in parallel ────────────
printf "${DIM}Fetching data...${RESET}"

for entry in "${REPOS[@]}"; do
  IFS='|' read -r local_dir gh_repo branch_model <<< "$entry"
  repo_path="$GIT_ROOT/$local_dir"
  d="$TMPDIR_BASE/$local_dir"
  mkdir -p "$d"

  # Git fetch
  if [[ -d "$repo_path/.git" ]]; then
    git -C "$repo_path" fetch --all --quiet 2>/dev/null &
  fi

  # gh API calls — all in parallel
  if [[ "$branch_model" == "dev/main" ]]; then
    (NO_COLOR=1 gh pr list --repo "$gh_repo" --base dev --state open --json number,title 2>/dev/null | filter_dep_prs > "$d/pr_dev.json") &
    (NO_COLOR=1 gh pr list --repo "$gh_repo" --base main --state open --json number,title 2>/dev/null | filter_dep_prs > "$d/pr_main.json") &
    (NO_COLOR=1 gh run list --repo "$gh_repo" --branch dev --limit 5 --json conclusion,status 2>/dev/null > "$d/ci_dev.json") &
    (NO_COLOR=1 gh run list --repo "$gh_repo" --branch main --limit 5 --json conclusion,status 2>/dev/null > "$d/ci_main.json") &
    (NO_COLOR=1 gh issue list --repo "$gh_repo" --label sync-dev-failed --state open --json number,title 2>/dev/null > "$d/sync.json") &
  else
    (NO_COLOR=1 gh pr list --repo "$gh_repo" --base main --state open --json number,title 2>/dev/null | filter_dep_prs > "$d/pr_main.json") &
    (NO_COLOR=1 gh run list --repo "$gh_repo" --branch main --limit 5 --json conclusion,status 2>/dev/null > "$d/ci_main.json") &
  fi
done

wait
printf " done.\n"

# ── Helpers for reading cached results ──────────────────────────────────────
read_json() {
  local file="$1"
  if [[ -s "$file" ]]; then
    cat "$file"
  else
    echo "[]"
  fi
}

parse_ci() {
  local file="$1"
  local runs
  runs=$(read_json "$file")
  local status conclusion
  status=$(echo "$runs" | jq -r '.[0].status // "unknown"')
  conclusion=$(echo "$runs" | jq -r '.[0].conclusion // "unknown"')
  if [[ "$status" == "completed" ]]; then
    echo "$conclusion"
  elif [[ "$status" == "in_progress" || "$status" == "queued" ]]; then
    echo "running"
  else
    echo "unknown"
  fi
}

format_ci_cell() {
  local status="$1"
  case "$status" in
    success)   printf "${GREEN}%s${RESET}" "ok" ;;
    failure)   printf "${RED}%s${RESET}" "FAIL" ;;
    running)   printf "${DIM}%s${RESET}" "run" ;;
    cancelled) printf "${YELLOW}%s${RESET}" "canc" ;;
    *)         printf "${DIM}%s${RESET}" "-" ;;
  esac
}

# ── Phase 2: Assemble data from cache ───────────────────────────────────────
declare -a T_REPO T_PENDING T_DIVERGED T_PR_DEV T_PR_MAIN T_CI_DEV T_CI_MAIN T_SYNC

assemble_dev_main() {
  local local_dir="$1" gh_repo="$2"
  local repo_path="$GIT_ROOT/$local_dir"
  local d="$TMPDIR_BASE/$local_dir"

  T_REPO+=("$local_dir")

  if [[ ! -d "$repo_path/.git" ]]; then
    T_PENDING+=("ERR"); T_DIVERGED+=("ERR"); T_PR_DEV+=("-"); T_PR_MAIN+=("-")
    T_CI_DEV+=("unknown"); T_CI_MAIN+=("unknown"); T_SYNC+=("-")
    ACTION_ITEMS+=("$local_dir: clone or fix local repo")
    return
  fi

  # Pending commits
  local pending
  pending=$(git -C "$repo_path" -c color.ui=never rev-list --count --no-color origin/main..origin/dev 2>/dev/null) || pending="?"
  T_PENDING+=("$pending")
  if [[ "$pending" != "0" && "$pending" != "?" ]]; then
    ACTION_ITEMS+=("$local_dir: $pending commit(s) pending for production")
    local commits
    commits=$(git -C "$repo_path" -c color.ui=never log --no-color --oneline --no-merges origin/main..origin/dev 2>/dev/null | head -10)
    local detail_line
    detail_line=$(printf "${YELLOW}%s pending commit(s):${RESET}" "$pending")
    while IFS= read -r line; do
      detail_line+=$(printf "\n    ${DIM}%s${RESET}" "$line")
    done <<< "$commits"
    if [[ "$pending" -gt 10 ]] 2>/dev/null; then
      detail_line+=$(printf "\n    ${DIM}... and %d more${RESET}" "$((pending - 10))")
    fi
    add_repo_detail "$local_dir" "$detail_line"
  fi

  # Divergence
  local diverged
  diverged=$(git -C "$repo_path" -c color.ui=never rev-list --count --no-color origin/dev..origin/main 2>/dev/null) || diverged="?"
  T_DIVERGED+=("$diverged")
  if [[ "$diverged" != "0" && "$diverged" != "?" ]]; then
    ACTION_ITEMS+=("$local_dir: main diverged from dev by $diverged commit(s)")
  fi

  # PRs against dev
  local dev_prs dev_pr_count
  dev_prs=$(read_json "$d/pr_dev.json")
  dev_pr_count=$(echo "$dev_prs" | jq 'length')
  T_PR_DEV+=("$dev_pr_count")
  if [[ "$dev_pr_count" != "0" ]]; then
    local detail_line
    detail_line=$(printf "${BLUE}%s open PR(s) against dev:${RESET}" "$dev_pr_count")
    while IFS= read -r line; do
      detail_line+=$(printf "\n    %s" "$line")
    done < <(echo "$dev_prs" | jq -r '.[] | "#\(.number) \(.title)"' | head -5)
    add_repo_detail "$local_dir" "$detail_line"
  fi

  # PRs against main
  local main_prs main_pr_count
  main_prs=$(read_json "$d/pr_main.json")
  main_pr_count=$(echo "$main_prs" | jq 'length')
  T_PR_MAIN+=("$main_pr_count")
  if [[ "$main_pr_count" != "0" ]]; then
    ACTION_ITEMS+=("$local_dir: $main_pr_count PR(s) open against main")
    local detail_line
    detail_line=$(printf "${YELLOW}%s open PR(s) against main:${RESET}" "$main_pr_count")
    while IFS= read -r line; do
      detail_line+=$(printf "\n    %s" "$line")
    done < <(echo "$main_prs" | jq -r '.[] | "#\(.number) \(.title)"' | head -5)
    add_repo_detail "$local_dir" "$detail_line"
  fi

  # CI
  local dev_ci main_ci
  dev_ci=$(parse_ci "$d/ci_dev.json")
  main_ci=$(parse_ci "$d/ci_main.json")
  T_CI_DEV+=("$dev_ci")
  T_CI_MAIN+=("$main_ci")
  if [[ "$dev_ci" == "failure" ]]; then
    ACTION_ITEMS+=("$local_dir: dev branch CI is failing")
  fi
  if [[ "$main_ci" == "failure" ]]; then
    ACTION_ITEMS+=("$local_dir: main branch CI is failing")
  fi

  # Sync-dev issues
  local sync_issues sync_count
  sync_issues=$(read_json "$d/sync.json")
  sync_count=$(echo "$sync_issues" | jq 'length')
  T_SYNC+=("$sync_count")
  if [[ "$sync_count" != "0" ]]; then
    ACTION_ITEMS+=("$local_dir: $sync_count sync-dev-failed issue(s) open")
  fi
}

assemble_main_only() {
  local local_dir="$1" gh_repo="$2"
  local repo_path="$GIT_ROOT/$local_dir"
  local d="$TMPDIR_BASE/$local_dir"

  T_REPO+=("$local_dir")
  T_PENDING+=("-"); T_DIVERGED+=("-"); T_PR_DEV+=("-"); T_SYNC+=("-"); T_CI_DEV+=("-")

  if [[ ! -d "$repo_path/.git" ]]; then
    T_PR_MAIN+=("-"); T_CI_MAIN+=("unknown")
    ACTION_ITEMS+=("$local_dir: clone or fix local repo")
    return
  fi

  # PRs against main
  local main_prs main_pr_count
  main_prs=$(read_json "$d/pr_main.json")
  main_pr_count=$(echo "$main_prs" | jq 'length')
  T_PR_MAIN+=("$main_pr_count")
  if [[ "$main_pr_count" != "0" ]]; then
    ACTION_ITEMS+=("$local_dir: $main_pr_count PR(s) open against main")
    local detail_line
    detail_line=$(printf "${YELLOW}%s open PR(s) against main:${RESET}" "$main_pr_count")
    while IFS= read -r line; do
      detail_line+=$(printf "\n    %s" "$line")
    done < <(echo "$main_prs" | jq -r '.[] | "#\(.number) \(.title)"' | head -5)
    add_repo_detail "$local_dir" "$detail_line"
  fi

  # CI
  local main_ci
  main_ci=$(parse_ci "$d/ci_main.json")
  T_CI_MAIN+=("$main_ci")
  if [[ "$main_ci" == "failure" ]]; then
    ACTION_ITEMS+=("$local_dir: main branch CI is failing")
  fi
}

# ── Render the table ────────────────────────────────────────────────────────
render_table() {
  local n=${#T_REPO[@]}
  local repo_w=4
  for ((i=0; i<n; i++)); do
    local len=${#T_REPO[$i]}
    (( len > repo_w )) && repo_w=$len
  done

  printf "\n${BOLD}%-${repo_w}s  %7s  %4s  %6s  %7s  %6s  %7s  %4s${RESET}\n" \
    "Repo" "Pending" "Div" "PR:dev" "PR:main" "CI:dev" "CI:main" "Sync"
  printf "${DIM}"
  printf '%0.s─' $(seq 1 $((repo_w + 55)))
  printf "${RESET}\n"

  for ((i=0; i<n; i++)); do
    printf "%-${repo_w}s  " "${T_REPO[$i]}"

    # Pending
    local v="${T_PENDING[$i]}"
    if [[ "$v" == "-" ]]; then printf "${DIM}%7s${RESET}  " "-"
    elif [[ "$v" == "0" ]]; then printf "${GREEN}%7s${RESET}  " "0"
    else printf "${YELLOW}%7s${RESET}  " "$v"; fi

    # Diverged
    v="${T_DIVERGED[$i]}"
    if [[ "$v" == "-" ]]; then printf "${DIM}%4s${RESET}  " "-"
    elif [[ "$v" == "0" ]]; then printf "${GREEN}%4s${RESET}  " "0"
    else printf "${RED}%4s${RESET}  " "$v"; fi

    # PR:dev
    v="${T_PR_DEV[$i]}"
    if [[ "$v" == "-" ]]; then printf "${DIM}%6s${RESET}  " "-"
    elif [[ "$v" == "0" ]]; then printf "${GREEN}%6s${RESET}  " "0"
    else printf "${BLUE}%6s${RESET}  " "$v"; fi

    # PR:main
    v="${T_PR_MAIN[$i]}"
    if [[ "$v" == "-" ]]; then printf "${DIM}%7s${RESET}  " "-"
    elif [[ "$v" == "0" ]]; then printf "${GREEN}%7s${RESET}  " "0"
    else printf "${YELLOW}%7s${RESET}  " "$v"; fi

    # CI:dev
    printf " "
    if [[ "${T_CI_DEV[$i]}" == "-" ]]; then printf "${DIM}%-6s${RESET}" "-"
    else printf " "; format_ci_cell "${T_CI_DEV[$i]}"; printf "   "; fi

    # CI:main
    if [[ "${T_CI_MAIN[$i]}" == "-" ]]; then printf "${DIM}%-7s${RESET}" "-"
    else printf " "; format_ci_cell "${T_CI_MAIN[$i]}"; printf "   "; fi

    # Sync
    v="${T_SYNC[$i]}"
    if [[ "$v" == "-" ]]; then printf "${DIM}%4s${RESET}" "-"
    elif [[ "$v" == "0" ]]; then printf "${GREEN}%4s${RESET}" "0"
    else printf "${RED}%4s${RESET}" "$v"; fi

    printf "\n"
  done
}

# ── Cross-repo checks ──────────────────────────────────────────────────────
cross_repo_checks() {
  local has_cross=false

  # DB Migrations
  local cpu_path="$GIT_ROOT/common-python-utils"
  if [[ -d "$cpu_path/.git" ]]; then
    local migration_files
    migration_files=$(git -C "$cpu_path" -c color.ui=never diff --no-color --name-only \
      origin/main..origin/dev -- src/db/alembic/versions/ 2>/dev/null) || migration_files=""
    if [[ -n "$migration_files" ]]; then
      has_cross=true
      local migration_count
      migration_count=$(echo "$migration_files" | wc -l | tr -d ' ')
      warn "$migration_count pending DB migration file(s)"
      echo "$migration_files" | while read -r f; do
        printf "  ${DIM}%s${RESET}\n" "$(basename "$f")"
      done
      ACTION_ITEMS+=("common-python-utils: $migration_count DB migration(s) pending")
    fi
  fi

  # Hasura Metadata
  local hasura_path="$GIT_ROOT/aisy-hasura"
  if [[ -d "$hasura_path/.git" ]]; then
    local metadata_files
    metadata_files=$(git -C "$hasura_path" -c color.ui=never diff --no-color --name-only \
      origin/main..origin/dev -- metadata/ 2>/dev/null) || metadata_files=""
    if [[ -n "$metadata_files" ]]; then
      has_cross=true
      local meta_count
      meta_count=$(echo "$metadata_files" | wc -l | tr -d ' ')
      warn "$meta_count Hasura metadata file(s) changed between dev and main"
      echo "$metadata_files" | head -10 | while read -r f; do
        printf "  ${DIM}%s${RESET}\n" "$f"
      done
      if [[ "$meta_count" -gt 10 ]] 2>/dev/null; then
        printf "  ${DIM}... and %d more${RESET}\n" "$((meta_count - 10))"
      fi
      ACTION_ITEMS+=("aisy-hasura: $meta_count metadata file(s) pending")
    fi
  fi

  if [[ "$has_cross" == true ]]; then printf "\n"; fi
}

# ── Summary ─────────────────────────────────────────────────────────────────
print_summary() {
  if [[ ${#ACTION_ITEMS[@]} -eq 0 ]]; then
    printf "${GREEN}All repos are production-ready. Nothing to do.${RESET}\n\n"
  else
    printf "${BOLD}Action Items (${#ACTION_ITEMS[@]})${RESET}\n"
    local i=1
    for item in "${ACTION_ITEMS[@]}"; do
      printf "  ${YELLOW}%d.${RESET} %s\n" "$i" "$item"
      ((i++))
    done
    printf "\n"
  fi
}

# ── Main ────────────────────────────────────────────────────────────────────
main() {
  printf "\n${BOLD}Production Readiness Dashboard${RESET}\n"
  printf "${DIM}%s${RESET}\n" "$(date '+%Y-%m-%d %H:%M:%S')"

  # Assemble (reads from cache, git ops are local/fast)
  for entry in "${REPOS[@]}"; do
    IFS='|' read -r local_dir gh_repo branch_model <<< "$entry"
    if [[ "$branch_model" == "dev/main" ]]; then
      assemble_dev_main "$local_dir" "$gh_repo"
    else
      assemble_main_only "$local_dir" "$gh_repo"
    fi
  done

  render_table

  if [[ ${#DETAIL_ORDER[@]} -gt 0 ]]; then
    printf "\n${BOLD}Details${RESET}\n"
    for repo in "${DETAIL_ORDER[@]}"; do
      printf "\n${BOLD}%s${RESET}\n" "$repo"
      printf "%b\n" "${REPO_DETAILS[$repo]}"
    done
  fi

  printf "\n${BOLD}Cross-Repo${RESET}\n"
  cross_repo_checks
  print_summary
}

main
