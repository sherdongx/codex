# Local prompt suggestions for Codex CLI

This branch restores the composer UI removed by upstream PR #48621, on top of
Codex CLI 0.161.0. It uses the current isolated structured-request mechanism for
generation rather than the removed implementation's conversation fork.

## Behavior

After a successful live response, a suggested next message can appear as dim text
in the empty input box. Press **Tab** or **Right Arrow** to put it into the editable
draft, then **Enter** to send it. Press **Escape** to dismiss it. Typing hides it.
Existing drafts, popups, attachments, paste handling and custom bindings for Tab
or Right Arrow take priority.
Suggestions are never submitted automatically. Failed, interrupted and replayed
turns do not trigger them; new turns and thread changes cancel pending results.

Generation uses the current model with low reasoning effort and recent visible
conversation text (the same bounded history selection used by recaps: up to eight
exchanges). Each eligible response adds a model request and therefore consumes
usage. Suggestions may be absent when the model returns no suitable continuation,
the response is invalid, or the request times out after 30 seconds.

Suggestion threads are ephemeral, hidden from the conversation UI, and detached
after completion or cancellation. They use Codex's existing structured-request
isolation: no tools, plugins, hooks, external connectors or environment access.
They do not inherit the main thread's goal or run the suggested task.

## Running locally

The local installation provides a separate `codex-suggest` command. It enables
`tui.prompt_suggestions` for that invocation and uses an embedded server with
`--no-daemon`. The normal `codex` launcher and global configuration remain unchanged.

```sh
codex-suggest
codex-suggest resume
codex-suggest -c tui.prompt_suggestions=false
```

Use the regular `codex` command to return to the official build. Updating the
official npm installation does not rebuild this branch; future updates require
rebasing and retesting the local changes. This is a local custom build, not a
feature enabled in the official 0.161.0 binary.

## Building and checking

For downloadable Apple Silicon and Intel packages, see
[codex-suggest for macOS](prompt-suggestions-macos.md).
For the portable Ubuntu x86_64 package, see
[codex-suggest for Ubuntu](prompt-suggestions-ubuntu.md).

Use the Rust version in `codex-rs/rust-toolchain.toml` and the build prerequisites
in [install.md](install.md). On this machine Rust is installed separately under
`~/.local/share/codex-suggestions-build`, without changing shell startup files.
The existing Homebrew OpenSSL installation supplies build headers and static
libraries.

```sh
cd codex-rs
export CARGO_HOME="$HOME/.local/share/codex-suggestions-build/cargo"
export RUSTUP_HOME="$HOME/.local/share/codex-suggestions-build/rustup"
export PATH="$CARGO_HOME/bin:$PATH"
export OPENSSL_DIR=/home/linuxbrew/.linuxbrew/opt/openssl@3
export OPENSSL_STATIC=1
export CARGO_BUILD_JOBS=4
export CARGO_PROFILE_DEV_DEBUG=0
export CARGO_PROFILE_TEST_DEBUG=0
export RUST_MIN_STACK=8388608
cargo test --locked -p codex-tui --lib prompt_suggestion
cargo build --locked -p codex-cli --bin codex
```

The release tag's manifest says 0.161.0 while its lockfile still uses 0.0.0 for
workspace packages. This branch reconciles those local package versions in the
lockfile; third-party dependency versions and checksums are unchanged.
