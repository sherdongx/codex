# codex-suggest for macOS

This is a community build of the Codex terminal CLI with optional next-prompt
suggestions. Suggestions use low reasoning effort. It requires **macOS 15 or
newer**, and each user signs in with their own account.

## Download and share

Open the fork's [macOS build workflow](https://github.com/sherdongx/codex/actions/workflows/codex-suggest-macos.yml),
select a successful run, and download the artifact for your Mac:

| Mac | Artifact |
| --- | --- |
| Apple Silicon (M-series) | `codex-suggest-macos-arm64` |
| Intel | `codex-suggest-macos-x86_64` |

GitHub requires sign-in to download Actions artifacts. Unzip the downloaded
artifact to get a `.tar.gz` package and matching `.sha256` checksum. You can send
those two files directly to friends; they do not need GitHub to install them.
Actions artifacts expire after 30 days, so keep a downloaded copy for sharing.

Each archive includes the CLI, code-mode helper, ripgrep, patched zsh, installer,
instructions, license notices, and `BUILD.txt` identifying its source commit.

## Install

In Terminal, change to the folder containing the downloaded package. Verify the
checksum, replacing the filename below with the downloaded checksum filename:

```sh
shasum -a 256 -c codex-suggest-macos-arm64-COMMIT.tar.gz.sha256
```

Extract the `.tar.gz`, open Terminal in the extracted folder, and run:

```sh
./install.sh
"$HOME/.local/bin/codex-suggest" --version
"$HOME/.local/bin/codex-suggest" login
"$HOME/.local/bin/codex-suggest"
```

The installer uses `~/.local/bin/codex-suggest` and
`~/.local/share/codex-prompt-suggestions`. It keeps the ordinary `codex` command and
your existing global configuration. An optional directory argument changes the
installation prefix: `./install.sh /path/to/prefix`.

To use the short command in the current terminal:

```sh
export PATH="$HOME/.local/bin:$PATH"
codex-suggest
```

Add that PATH line to `~/.zshrc` if you want it in future terminals. After a
successful response, press Tab or Right Arrow to edit the dim suggestion, Enter
to submit, or Escape to dismiss it. Each suggestion uses an additional model
request. Disable suggestions for a run with
`codex-suggest -c tui.prompt_suggestions=false`.

## macOS approval

These builds are **ad-hoc signed, not Apple-notarized**. If macOS blocks a binary
you trust, follow [Apple's instructions for opening an unnotarized app](https://support.apple.com/102445)
in System Settings > Privacy & Security. The installer does not disable Gatekeeper
or remove quarantine attributes. A managed Mac may require administrator approval.

## Rebuild

The workflow builds pushes to `feature/prompt-suggestions` and
`feature/macos-packages` when build inputs change. A registered workflow can also
be rerun from its existing Actions run. `workflow_dispatch` is included for manual
runs once the workflow is present on the repository's default branch.

Both native macOS jobs verify packaged architecture, signatures, system-library
dependencies, archive extraction, installation, and executable startup before
uploading. These checks do not sign into a real account or exercise a paid model
request. To update an installation, close `codex-suggest`, extract a newer package,
and run its installer again.
