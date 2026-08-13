#!/usr/bin/env bash
# SessionStart: link this plugin's tools onto a stable path, then bring up the bus.
#
# Role definitions and reference docs refer to ~/.claude/bin/<tool>. Plugin
# bodies do not get ${CLAUDE_PLUGIN_ROOT} expanded, so the plugin symlinks its
# scripts to that stable location instead of hard-coding its install path.
# Idempotent, silent, and never fails the session.
set -u
ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BIN="$HOME/.claude/bin"
PORT="${AGENT_BUS_PORT:-8477}"

mkdir -p "$BIN" 2>/dev/null || exit 0

for tool in run-role agent-bus agent-board orchestrator-harnesses; do
  src="$ROOT/scripts/$tool"
  dst="$BIN/$tool"
  [ -x "$src" ] || continue
  # Leave a real file alone — the user may have their own copy on purpose.
  if [ -e "$dst" ] && [ ! -L "$dst" ]; then continue; fi
  [ "$(readlink "$dst" 2>/dev/null)" = "$src" ] || ln -sf "$src" "$dst" 2>/dev/null
done

# Bus: reuse if something already holds the port.
if ! curl -fsS -m 1 -o /dev/null "http://127.0.0.1:$PORT/health" 2>/dev/null; then
  nohup "$ROOT/scripts/agent-bus" serve --port "$PORT" >/dev/null 2>&1 &
fi

exit 0
