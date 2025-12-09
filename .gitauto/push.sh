#!/bin/bash
set -o pipefail

REPO="/home/ransomeye/rebuild"
LOGDIR="$REPO/.gitauto"
LOGFILE="$LOGDIR/push.log"
BRANCH="main"
TIMESTAMP() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

mkdir -p "$LOGDIR"
cd "$REPO" || { echo "$(TIMESTAMP) - ERROR: cannot cd to $REPO" >>"$LOGFILE"; exit 1; }

# ensure we are on the expected branch
git symbolic-ref --short HEAD 2>/dev/null | grep -q "^${BRANCH}$" || git checkout -q "$BRANCH" 2>/dev/null || true

# fetch latest remote metadata
git fetch origin "$BRANCH" >>"$LOGFILE" 2>&1 || true

# if there are no changes, exit
if [ -z "$(git status --porcelain)" ]; then
  echo "$(TIMESTAMP) - No changes to commit" >>"$LOGFILE"
  exit 0
fi

# stage everything
git add -A >>"$LOGFILE" 2>&1

# commit with timestamp
COMMIT_MSG="Auto-sync: $(TIMESTAMP)"
git commit -m "$COMMIT_MSG" >>"$LOGFILE" 2>&1 || { echo "$(TIMESTAMP) - Commit failed" >>"$LOGFILE"; exit 1; }

# rebase onto remote to avoid merge commits
if ! git pull --rebase origin "$BRANCH" >>"$LOGFILE" 2>&1; then
  echo "$(TIMESTAMP) - git pull --rebase failed; aborting and reverting local commit" >>"$LOGFILE"
  # try to abort rebase and reset to remote to avoid leaving repo in bad state
  git rebase --abort >>"$LOGFILE" 2>&1 || true
  git reset --hard "origin/$BRANCH" >>"$LOGFILE" 2>&1 || true
  exit 1
fi

# push
if git push origin "$BRANCH" >>"$LOGFILE" 2>&1; then
  echo "$(TIMESTAMP) - Push successful: $COMMIT_MSG" >>"$LOGFILE"
  exit 0
else
  echo "$(TIMESTAMP) - Push failed" >>"$LOGFILE"
  exit 1
fi
