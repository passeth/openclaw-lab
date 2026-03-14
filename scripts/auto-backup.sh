#!/bin/bash
cd ~/.openclaw/workspace || exit 1

if [ -n "$(git status --porcelain)" ]; then
  git add -A
  git commit -m "auto-backup $(TZ=Asia/Seoul date '+%Y-%m-%d %H:%M')" --quiet
  git push --quiet 2>/dev/null
  echo "✅ backup pushed $(date)"
else
  echo "no changes"
fi
