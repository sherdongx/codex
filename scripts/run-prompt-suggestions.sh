#!/usr/bin/env sh
# Launch the separately installed local Codex build with prompt suggestions.
export RUST_LOG="${RUST_LOG:-off}"
exec "$HOME/.local/share/codex-prompt-suggestions/bin/codex" \
  --no-daemon -c tui.prompt_suggestions=true "$@"
