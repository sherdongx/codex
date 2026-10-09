#!/usr/bin/env python3
"""Wrap a verified codex-suggest Linux payload in an Ubuntu Debian package."""

import argparse
import hashlib
import json
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
TEMPLATES = Path(__file__).with_name("debian")
PROFILE = "usr.lib.codex-suggest.codex-resources.bwrap"
VERSION = "0.161.0+suggest.1"
EXECUTABLES = (
    "bin/codex",
    "bin/codex-code-mode-host",
    "codex-resources/bwrap",
    "codex-path/rg",
    "codex-resources/zsh/bin/zsh",
)


def sha256(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def git(*arguments):
    return subprocess.check_output(
        ["git", "-C", str(REPO), *arguments], text=True
    ).strip()


def build(archive, output):
    checksum = archive.with_name(archive.name + ".sha256").read_text().split()
    if checksum != [sha256(archive), archive.name]:
        raise ValueError("Payload checksum does not match its SHA-256 file")
    destination = output / f"codex-suggest_{VERSION}_amd64.deb"
    if destination.exists():
        raise FileExistsError(destination)
    packaging_commit = git("rev-parse", "HEAD")

    with tempfile.TemporaryDirectory(prefix="codex deb ") as temporary:
        temporary = Path(temporary)
        unpacked = temporary / "payload"
        prefix = archive.name.removesuffix(".tar.gz")
        with tarfile.open(archive) as package:
            for member in package.getmembers():
                path = PurePosixPath(member.name)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or not path.parts
                    or path.parts[0] != prefix
                    or not (member.isfile() or member.isdir())
                    or member.mode & 0o6000
                ):
                    raise ValueError(f"Unsafe payload member: {member.name}")
            package.extractall(unpacked, filter="data")
        payload = unpacked / prefix
        metadata = json.loads((payload / "codex-package.json").read_text())
        if (
            metadata.get("target") != "x86_64-unknown-linux-musl"
            or metadata.get("version") != "0.161.0"
            or metadata.get("entrypoint") != "bin/codex"
            or metadata.get("variant") != "codex"
            or metadata.get("layoutVersion") != 1
            or metadata.get("resourcesDir") != "codex-resources"
            or metadata.get("pathDir") != "codex-path"
            or (payload / "ARCHITECTURE").read_text().strip() != "x86_64"
        ):
            raise ValueError("Expected the Codex 0.161.0 x86_64 Linux payload")
        build_info = dict(
            line.split(": ", 1)
            for line in (payload / "BUILD.txt").read_text().splitlines()
        )
        source_commit = build_info["Commit"]
        if re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
            raise ValueError("Expected a full payload source commit SHA")
        if prefix != f"codex-suggest-ubuntu-x86_64-{source_commit[:12]}":
            raise ValueError("Payload filename and source commit disagree")
        # Reuse an already-built payload only when its application inputs match.
        for tree in ("codex-rs", "third_party/v8", "scripts/codex_package"):
            if git("rev-parse", f"{source_commit}:{tree}") != git(
                "rev-parse", f"{packaging_commit}:{tree}"
            ):
                raise ValueError(
                    f"Payload source differs from packaging source: {tree}"
                )
        if sha256(payload / "codex-resources/bwrap") != build_info["Bwrap SHA-256"]:
            raise ValueError("Payload sandbox helper digest mismatch")
        for name in EXECUTABLES:
            executable = payload / name
            with executable.open("rb") as source:
                header = source.read(20)
            if (
                header[:6] != b"\x7fELF\x02\x01"
                or struct.unpack_from("<H", header, 18)[0] != 62
                or not executable.stat().st_mode & 0o111
            ):
                raise ValueError(f"Expected executable x86-64 ELF: {name}")

        stage = temporary / "deb"
        bundle = stage / "usr/lib/codex-suggest"
        bundle.mkdir(parents=True)
        for name in ("bin", "codex-path", "codex-resources"):
            shutil.copytree(payload / name, bundle / name)
        for name in ("codex-package.json", "ARCHITECTURE", "BUILD.txt"):
            shutil.copyfile(payload / name, bundle / name)
        (bundle / "PACKAGING.txt").write_text(
            f"Debian version: {VERSION}\nPackaging commit: {packaging_commit}\n"
            f"Payload archive SHA-256: {checksum[0]}\n"
        )
        command = stage / "usr/bin/codex-suggest"
        command.parent.mkdir(parents=True)
        shutil.copyfile(TEMPLATES / "codex-suggest", command)
        command.chmod(0o755)
        policy = stage / "etc/apparmor.d" / PROFILE
        policy.parent.mkdir(parents=True)
        shutil.copyfile(TEMPLATES / PROFILE, policy)
        documentation = stage / "usr/share/doc/codex-suggest"
        documentation.mkdir(parents=True)
        shutil.copyfile(
            REPO / "docs/prompt-suggestions-ubuntu-deb.md", documentation / "README.md"
        )
        shutil.copyfile(payload / "LICENSE", documentation / "copyright")
        shutil.copyfile(payload / "NOTICE", documentation / "NOTICE")
        control = stage / "DEBIAN"
        control.mkdir()
        size = sum(
            int(line.split()[0])
            for line in subprocess.check_output(
                [
                    "du",
                    "--apparent-size",
                    "-sk",
                    str(stage / "usr"),
                    str(stage / "etc"),
                ],
                text=True,
            ).splitlines()
        )
        text = (TEMPLATES / "control").read_text()
        (control / "control").write_text(
            text.replace("@VERSION@", VERSION).replace("@SIZE@", str(size))
        )
        (control / "conffiles").write_text(f"/etc/apparmor.d/{PROFILE}\n")
        for name in ("postinst", "postrm"):
            shutil.copyfile(TEMPLATES / name, control / name)
            (control / name).chmod(0o755)
        for path in stage.rglob("*"):
            path.chmod(0o755 if path.is_dir() or path.stat().st_mode & 0o111 else 0o644)
        sums = []
        for path in sorted((stage / "usr").rglob("*")):
            if path.is_file():
                digest = hashlib.md5(
                    path.read_bytes(), usedforsecurity=False
                ).hexdigest()
                sums.append(f"{digest}  {path.relative_to(stage)}\n")
        (control / "md5sums").write_text("".join(sums))
        (control / "md5sums").chmod(0o644)
        stage.chmod(0o755)
        output.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "dpkg-deb",
                "--root-owner-group",
                "-Zxz",
                "--threads-max=2",
                "--build",
                str(stage),
                str(destination),
            ],
            check=True,
        )
    destination.with_name(destination.name + ".sha256").write_text(
        f"{sha256(destination)}  {destination.name}\n"
    )
    print(f"Built Debian package: {destination}")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("payload", type=Path, help="Verified portable .tar.gz payload")
    parser.add_argument("output", type=Path, help="Debian package output directory")
    args = parser.parse_args()
    build(args.payload.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
