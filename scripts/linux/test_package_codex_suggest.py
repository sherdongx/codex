"""Exercise Linux package assembly before compiling the full CLI."""

import hashlib
import os
import platform
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(
    platform.system() == "Linux" and platform.machine() == "x86_64",
    "requires Linux x86_64 build tools",
)
class NativePackageTest(unittest.TestCase):
    def test_rejects_source_without_the_prompt_suggestion_changes(self):
        with tempfile.TemporaryDirectory(prefix="codex wrong source ") as temporary:
            root = Path(temporary)
            binaries = root / "binaries"
            binaries.mkdir()
            source = root / "fixture.c"
            source.write_text("int main(void) { return 0; }\n")
            for name in ("codex", "codex-code-mode-host", "bwrap"):
                subprocess.run(
                    ["cc", "-static", str(source), "-o", str(binaries / name)],
                    check=True,
                    capture_output=True,
                )
            digest = hashlib.sha256((binaries / "bwrap").read_bytes()).hexdigest()
            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts/linux/package-codex-suggest.sh"),
                    str(binaries),
                    str(root / "dist"),
                ],
                cwd=REPO_ROOT,
                check=False,
                env={
                    **os.environ,
                    "CODEX_BWRAP_SHA256": digest,
                    "CODEX_SOURCE_COMMIT": "092d3acd6bec3e3a14bdc7e7a2810ab628ab759d",
                },
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0, "Mismatched source was accepted")
            self.assertIn("Source commit build inputs differ", result.stderr)
            self.assertFalse(list((root / "dist").glob("*.tar.gz")))

    def test_package_extract_and_install_static_executables(self):
        with tempfile.TemporaryDirectory(prefix="codex package test ") as temporary:
            root = Path(temporary)
            binaries = root / "binaries"
            binaries.mkdir()
            source = root / "fixture.c"
            source.write_text("int main(void) { return 0; }\n")
            for name in ("codex", "codex-code-mode-host", "bwrap"):
                subprocess.run(
                    ["cc", "-static", str(source), "-o", str(binaries / name)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            digest = hashlib.sha256((binaries / "bwrap").read_bytes()).hexdigest()
            result = subprocess.run(
                [
                    "bash",
                    str(REPO_ROOT / "scripts/linux/package-codex-suggest.sh"),
                    str(binaries),
                    str(root / "dist"),
                ],
                cwd=REPO_ROOT,
                env={**os.environ, "CODEX_BWRAP_SHA256": digest},
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("Verified archive:", result.stdout)
            self.assertEqual(len(list((root / "dist").glob("*.tar.gz"))), 1)
            self.assertEqual(len(list((root / "dist").glob("*.sha256"))), 1)
            archive = next((root / "dist").glob("*.tar.gz"))
            with tarfile.open(archive) as package:
                metadata = (
                    package.extractfile(
                        archive.name.removesuffix(".tar.gz") + "/BUILD.txt"
                    )
                    .read()
                    .decode()
                )
            packaging_commit = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
            ).strip()
            source_commit = os.environ.get("CODEX_SOURCE_COMMIT", packaging_commit)
            self.assertIn(f"Commit: {source_commit}\n", metadata)
            self.assertIn(f"Packaging commit: {packaging_commit}\n", metadata)


if __name__ == "__main__":
    unittest.main()
