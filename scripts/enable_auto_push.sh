#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

chmod +x .githooks/post-commit
git config core.hooksPath .githooks
git config autopush.enabled true
if ! git config --get autopush.remote >/dev/null 2>&1; then
  git config autopush.remote origin
fi

echo "Auto-push enabled for this repo"
echo "hooksPath: $(git config --get core.hooksPath)"
echo "remote:    $(git config --get autopush.remote)"
