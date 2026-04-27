#!/usr/bin/env bash
set -eu

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PATTERN='(answer_text|response_text|user_text|raw_answer|raw_response|message_body|chat_message)'
TARGETS=("$ROOT_DIR/migrations" "$ROOT_DIR/backend/migrations" "$ROOT_DIR/backend/app/db")

EXISTING=()
for t in "${TARGETS[@]}"; do
  if [ -e "$t" ]; then
    EXISTING+=("$t")
  fi
done

if [ ${#EXISTING[@]} -eq 0 ]; then
  echo "[no-text-storage] target paths not yet exist (${TARGETS[*]}) — skipping"
  exit 0
fi

MATCHES=$(grep -rEn "$PATTERN" "${EXISTING[@]}" 2>/dev/null || true)

if [ -n "$MATCHES" ]; then
  echo "[no-text-storage] FORBIDDEN field names found:"
  echo "$MATCHES"
  echo ""
  echo "Запрещённые паттерны: $PATTERN"
  echo "См. CLAUDE.md > Coding Rules > No text storage."
  exit 1
fi

echo "[no-text-storage] OK — no forbidden field names in: ${EXISTING[*]}"
exit 0
