#!/bin/bash
# =============================================================================
# industrace-merge-upstream.sh
# Safe merge of upstream (github.com/industrace/industrace) into our fork branch.
#
# POLICY: KEEP our modifications + take upstream's new changes.
#   - If upstream has nothing new  -> report "nothing to merge", exit 0
#   - If merge is clean            -> merge, push to github + gitea, report
#   - If merge has CONFLICTS       -> STOP, do NOT auto-resolve, list conflicts
#                                    for deliberate review. Never overwrite our
#                                    component/model work blindly.
#
# Usage: bash industrace-merge-upstream.sh [--dry-run]
#   --dry-run: fetch + report divergence, do NOT merge or push.
# =============================================================================
set -uo pipefail

REPO="${INDUSTRACE_REPO:-/home/hmcadmin/industrace-v2.3.1}"
BRANCH="feature/lifecycle-statuses"
UPSTREAM_REF="origin/main"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

cd "$REPO" || { echo "FATAL: repo not found at $REPO"; exit 1; }

echo "=== Industrace upstream merge ==="
echo "repo:   $REPO"
echo "branch: $BRANCH"
echo "mode:   $([ $DRY_RUN -eq 1 ] && echo 'DRY-RUN (no changes)' || echo 'LIVE (will merge+push)')"
echo

# 0. Guard: working tree must be clean before any merge
if [ $DRY_RUN -eq 0 ]; then
  if [ -n "$(git status --porcelain)" ]; then
    echo "FATAL: working tree is NOT clean. Commit or stash before merging."
    git status --short
    exit 1
  fi
  if [ -f .git/MERGE_HEAD ]; then
    echo "FATAL: a merge is already in progress. Resolve or abort it first."
    exit 1
  fi
fi

# 1. Fetch upstream main branch explicitly (the origin refspec only pulls the
#    v2.3.1 tag, not refs/heads/main — so we must fetch main by name).
echo "--- fetching upstream main ---"
git fetch origin refs/heads/main:refs/remotes/origin/main 2>&1 | tail -3 \
  || { echo "FATAL: fetch failed"; exit 1; }

UPSTREAM_SHA=$(git rev-parse "$UPSTREAM_REF" 2>/dev/null)
[ -z "$UPSTREAM_SHA" ] && { echo "FATAL: cannot resolve $UPSTREAM_REF"; exit 1; }
echo "upstream $UPSTREAM_REF = $UPSTREAM_SHA"

# 2. Check divergence
AHEAD=$(git rev-list --count "$UPSTREAM_SHA..HEAD" 2>/dev/null)
BEHIND=$(git rev-list --count "HEAD..$UPSTREAM_SHA" 2>/dev/null)
echo "we are: $AHEAD ahead, $BEHIND behind upstream"

if [ "$BEHIND" -eq 0 ]; then
  echo
  echo "RESULT: nothing to merge — upstream has no commits we lack."
  echo "Our branch already contains all of upstream. No action needed."
  exit 0
fi

echo
echo "Upstream has $BEHIND new commit(s) we do not have. Merge required."

if [ $DRY_RUN -eq 1 ]; then
  echo
  echo "DRY-RUN: would merge $UPSTREAM_SHA into $BRANCH."
  echo "New upstream commits:"
  git log --oneline HEAD.."$UPSTREAM_SHA"
  echo
  echo "Files upstream changed that we also touched (potential conflict):"
  git diff --name-only HEAD "$UPSTREAM_SHA" | while read -r f; do
    if git log --oneline HEAD -- "$f" | grep -q .; then
      echo "  [BOTH TOUCHED] $f"
    fi
  done
  exit 0
fi

# 3. Perform the merge
echo "--- merging $UPSTREAM_SHA into $BRANCH ---"
if git merge --no-edit "$UPSTREAM_SHA" 2>&1; then
  echo
  echo "MERGE CLEAN. Commits now:"
  git log --oneline -5
  echo
  echo "--- pushing to github + gitea ---"
  git push github "$BRANCH" 2>&1 | tail -3
  git push gitea "$BRANCH" 2>&1 | tail -3
  echo
  echo "RESULT: merge complete, pushed. Our modifications preserved + upstream changes integrated."
  exit 0
else
  echo
  echo "!!! MERGE CONFLICTS !!!"
  echo "Do NOT auto-resolve. Review each conflicted file deliberately."
  echo "Conflicted files:"
  git diff --name-only --diff-filter=U
  echo
  echo "To see a conflict:  git diff <file>"
  echo "To abort the merge: git merge --abort"
  echo "To resolve: edit files, git add <file>, then git commit"
  echo
  echo "RESULT: merge paused with conflicts — needs human/agent review. Nothing pushed."
  exit 2
fi
