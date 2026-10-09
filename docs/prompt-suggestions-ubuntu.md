# Portable Ubuntu build payload

This portable archive is the build input for the
[Ubuntu Debian package](prompt-suggestions-ubuntu-deb.md). The delivered Ubuntu
release uses that `.deb` format. This community build of Codex CLI 0.161.0 adds optional next-prompt suggestions
using low reasoning effort. It requires **Ubuntu 24.04 or newer on Intel/AMD 64-bit (x86_64)**.
The CLI and its code-mode, sandbox, and search helpers are statically linked.
The bundled patched zsh requires glibc 2.38 or newer and Ubuntu's `libtinfo6`
terminal library. Ubuntu 22.04 is not supported.
Rust and Node.js are not required to install the package.

## Download and install

Download the Ubuntu `.tar.gz` and its matching `.sha256` file. In their download
folder, verify the checksum, replacing `COMMIT` with the downloaded filename:

```sh
sha256sum -c codex-suggest-ubuntu-x86_64-COMMIT.tar.gz.sha256
```

Extract the archive, open a terminal in the extracted folder, and run:

```sh
./install.sh
"$HOME/.local/bin/codex-suggest" login
"$HOME/.local/bin/codex-suggest"
```

Sign in with your own account. Installation uses `~/.local/bin/codex-suggest` and
`~/.local/share/codex-prompt-suggestions`, preserving the ordinary `codex` command
and existing global configuration. No `sudo` is needed. An optional argument
sets another installation prefix: `./install.sh /path/to/prefix`.

To use the short command in the current terminal:

```sh
export PATH="$HOME/.local/bin:$PATH"
codex-suggest
```

Add that PATH line to `~/.bashrc` if needed for future terminals. Close the app
before installing an updated package.

After a response, press Tab or Right Arrow to edit the dim suggestion, Enter to
send it, or Escape to dismiss it. Each suggestion consumes an additional model
request. Disable suggestions with `codex-suggest -c tui.prompt_suggestions=false`.

## Package and compatibility checks

The archive includes the CLI, code-mode helper, bubblewrap sandbox helper,
ripgrep, patched zsh, installer, source metadata, and license notices.
`BUILD.txt` records the source commit and the exact sandbox helper digest embedded
in the CLI.

The Ubuntu workflow checks x86-64 architecture, static helpers, zsh dependencies,
checksums, extraction,
installation into paths with spaces, and startup on Ubuntu 24.04.
The final Debian package is additionally tested through apt installation,
removal, and restricted shell execution using its package-owned AppArmor profile.
These checks do not sign into an account or send model requests.

Restricted execution requires a host that permits the necessary user namespaces.
AppArmor or administrator policy can restrict them, particularly on Ubuntu 24.04.
The installer does not change security policy. If sandbox startup is blocked,
ask your administrator to provide an application-specific `userns` AppArmor
profile for the installed helper, following
[Ubuntu's namespace-policy documentation](https://documentation.ubuntu.com/release-notes/24.04/#unprivileged-user-namespace-restrictions).
The CI result proves the package in that provisioned environment; it does not
prove sandbox execution on an untouched Ubuntu installation. Keep the sandbox
and the system-wide namespace restriction enabled.

## Rebuild

The `Build codex-suggest for Ubuntu` workflow runs for build-input changes on
`feature/ubuntu-package`. It uses the upstream musl toolchain and V8 resources,
builds and hashes bubblewrap before compiling the CLI, and wraps this payload in a Debian package. It uploads the `.deb`
and its checksum. Actions artifacts expire after 30 days, so keep a downloaded copy.
