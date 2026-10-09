#!/bin/sh
set -eu

if [ "$#" != 2 ]; then
  echo "Usage: $0 <extracted-package> <installation-prefix>" >&2
  exit 1
fi
package_dir=$1
prefix=$2
"$package_dir/install.sh" "$prefix"
"$prefix/bin/codex-suggest" --version
"$prefix/bin/codex-suggest" --help
"$prefix/bin/codex-suggest" features list
installed="$prefix/share/codex-prompt-suggestions"
"$installed/bin/codex-code-mode-host" --help
"$installed/codex-resources/bwrap" --version
"$installed/codex-path/rg" --version
"$installed/codex-resources/zsh/bin/zsh" -fc 'print -r -- codex-suggest-zsh-ok'
