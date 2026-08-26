#!/usr/bin/env bash
# Install local-skills-catalog into personal skill directories (symlink for live edit).
set -euo pipefail

SKILL_SRC="$(cd "$(dirname "$0")/.." && pwd)"
NAME="local-skills-catalog"

install_one() {
  local root="$1"
  mkdir -p "$root"
  local dest="$root/$NAME"
  if [[ -e "$dest" && ! -L "$dest" ]]; then
    echo "SKIP (already a real directory): $dest"
    return
  fi
  ln -sfn "$SKILL_SRC" "$dest"
  echo "OK  $dest -> $SKILL_SRC"
}

echo "Skill source: $SKILL_SRC"
install_one "$HOME/.agents/skills"
install_one "$HOME/.claude/skills"
install_one "$HOME/.cursor/skills"

echo
echo "Verify:"
for p in \
  "$HOME/.agents/skills/$NAME/SKILL.md" \
  "$HOME/.claude/skills/$NAME/SKILL.md" \
  "$HOME/.cursor/skills/$NAME/SKILL.md"
do
  if [[ -f "$p" ]]; then
    echo "  ✓ $p"
  else
    echo "  ✗ missing $p"
  fi
done

echo
echo "Smoke scan:"
python3 "$SKILL_SRC/scripts/catalog.py" --format json \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"  unique={d['total_unique']} raw={d['total_raw']}\"); [print(f\"  - {s['label']}: {s['count']} (exists={s['exists']})\") for s in d['sources']]"
