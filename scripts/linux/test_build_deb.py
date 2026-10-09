"""Validate Debian package metadata, ownership and input integrity."""

import hashlib
import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

import build_deb


class DebianPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix="codex deb test ")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        source = cls.root / "fixture.c"
        source.write_text(
            "#include <stdio.h>\nint main(int n, char **v) { "
            "for (int i=1;i<n;i++) puts(v[i]); return 0; }\n"
        )
        binary = cls.root / "fixture"
        subprocess.run(["cc", "-static", str(source), "-o", str(binary)], check=True)
        commit = build_deb.git("rev-parse", "HEAD")
        cls.payload = cls.root / f"codex-suggest-ubuntu-x86_64-{commit[:12]}"
        cls.payload.mkdir()
        for name in build_deb.EXECUTABLES:
            destination = cls.payload / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(binary, destination)
        (cls.payload / "codex-package.json").write_text(
            json.dumps(
                {
                    "target": "x86_64-unknown-linux-musl",
                    "version": "0.161.0",
                    "entrypoint": "bin/codex",
                    "variant": "codex",
                    "layoutVersion": 1,
                    "resourcesDir": "codex-resources",
                    "pathDir": "codex-path",
                }
            )
        )
        (cls.payload / "ARCHITECTURE").write_text("x86_64\n")
        (cls.payload / "BUILD.txt").write_text(
            f"Commit: {commit}\nBwrap SHA-256: {build_deb.sha256(binary)}\n"
        )
        for name in ("LICENSE", "NOTICE", "README.md", "install.sh"):
            (cls.payload / name).write_text("fixture\n")
        cls.archive = cls.root / (cls.payload.name + ".tar.gz")
        with tarfile.open(cls.archive, "w:gz") as package:
            package.add(cls.payload, arcname=cls.payload.name)
        cls.archive.with_name(cls.archive.name + ".sha256").write_text(
            f"{build_deb.sha256(cls.archive)}  {cls.archive.name}\n"
        )
        previous = os.umask(0o077)
        try:
            cls.deb = build_deb.build(cls.archive, cls.root / "output")
        finally:
            os.umask(previous)

    def test_metadata_and_dependencies(self):
        fields = subprocess.check_output(
            [
                "dpkg-deb",
                "--show",
                "--showformat=${Package}\n${Version}\n${Architecture}\n${Depends}\n",
                str(self.deb),
            ],
            text=True,
        ).splitlines()
        self.assertEqual(fields[:3], ["codex-suggest", "0.161.0+suggest.1", "amd64"])
        for dependency in (
            "libc6 (>= 2.38)",
            "libtinfo6",
            "apparmor (>= 4.0)",
            "ca-certificates",
        ):
            self.assertIn(dependency, fields[3])
        self.assertEqual(
            self.deb.with_name(self.deb.name + ".sha256").read_text().split(),
            [build_deb.sha256(self.deb), self.deb.name],
        )

    def test_root_ownership_and_permissions_ignore_build_umask(self):
        data = subprocess.check_output(["dpkg-deb", "--fsys-tarfile", str(self.deb)])
        with tarfile.open(fileobj=io.BytesIO(data)) as package:
            for member in package.getmembers():
                self.assertEqual((member.uid, member.gid), (0, 0), member.name)
                if member.isdir():
                    self.assertEqual(member.mode, 0o755, member.name)
            for name in build_deb.EXECUTABLES:
                member = package.getmember(f"./usr/lib/codex-suggest/{name}")
                self.assertEqual(member.mode, 0o755)
                self.assertEqual(
                    package.extractfile(member).read(),
                    (self.payload / name).read_bytes(),
                )
            self.assertNotIn("./usr/lib/codex-suggest/install.sh", package.getnames())
            self.assertEqual(package.getmember("./usr/bin/codex-suggest").mode, 0o755)
        data = subprocess.check_output(["dpkg-deb", "--ctrl-tarfile", str(self.deb)])
        with tarfile.open(fileobj=io.BytesIO(data)) as control:
            self.assertEqual(control.getmember("./md5sums").mode, 0o644)
            self.assertEqual(control.getmember("./postinst").mode, 0o755)
            self.assertEqual(control.getmember("./postrm").mode, 0o755)
            self.assertEqual(
                control.extractfile("./conffiles").read().decode(),
                f"/etc/apparmor.d/{build_deb.PROFILE}\n",
            )

    def test_installed_size_covers_unpacked_file_bytes(self):
        size_kib = int(
            subprocess.check_output(
                ["dpkg-deb", "--field", str(self.deb), "Installed-Size"], text=True
            )
        )
        data = subprocess.check_output(["dpkg-deb", "--fsys-tarfile", str(self.deb)])
        with tarfile.open(fileobj=io.BytesIO(data)) as package:
            total = sum(
                member.size for member in package.getmembers() if member.isfile()
            )
        self.assertGreaterEqual(size_kib * 1024, total)

    def test_bad_payload_checksum_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / self.archive.name
            shutil.copyfile(self.archive, archive)
            archive.with_name(archive.name + ".sha256").write_text(
                f"{'0' * 64}  {archive.name}\n"
            )
            with self.assertRaisesRegex(ValueError, "checksum"):
                build_deb.build(archive, Path(directory) / "output")
            self.assertFalse((Path(directory) / "output").exists())

    def test_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "unsafe.tar.gz"
            with tarfile.open(archive, "w:gz") as package:
                member = tarfile.TarInfo("../escape")
                member.size = 1
                package.addfile(member, io.BytesIO(b"x"))
            archive.with_name(archive.name + ".sha256").write_text(
                f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n"
            )
            with self.assertRaisesRegex(ValueError, "Unsafe payload"):
                build_deb.build(archive, Path(directory) / "output")
            self.assertFalse((Path(directory) / "output").exists())

    def test_unprivileged_startup_failure_is_not_masked(self):
        with tempfile.TemporaryDirectory(prefix="codex failing deb ") as directory:
            root = Path(directory)
            payload = root / self.payload.name
            shutil.copytree(self.payload, payload)
            source = root / "failure.c"
            source.write_text("int main(void) { return 17; }\n")
            subprocess.run(
                ["cc", "-static", str(source), "-o", str(payload / "bin/codex")],
                check=True,
            )
            archive = root / self.archive.name
            with tarfile.open(archive, "w:gz") as package:
                package.add(payload, arcname=payload.name)
            archive.with_name(archive.name + ".sha256").write_text(
                f"{build_deb.sha256(archive)}  {archive.name}\n"
            )
            deb = build_deb.build(archive, root / "output")
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "--rm",
                    "-e",
                    "CODEX_DEB_CONTAINER_TEST=1",
                    "--mount",
                    f"type=bind,src={deb},dst=/package.deb,readonly",
                    "--mount",
                    f"type=bind,src={build_deb.REPO / 'scripts/linux'},dst=/checks,readonly",
                    "ubuntu:24.04",
                    "sh",
                    "/checks/check-deb-container.sh",
                    "/package.deb",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode, 17, (result.stdout + result.stderr)[-4000:]
            )


if __name__ == "__main__":
    unittest.main()
