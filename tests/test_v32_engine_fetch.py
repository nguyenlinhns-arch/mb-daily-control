from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fetch_v32_engine as engine_fetch


def make_bundle(root: Path, *, malicious: str | None = None) -> tuple[Path, dict]:
    engine = root / "fixture" / "engine_v32"
    engine.mkdir(parents=True)
    runtime = engine / "runtime_plan.py"
    runtime.write_text("print('fixture')\n", encoding="utf-8")
    tree_line = f"{sha256(runtime.read_bytes()).hexdigest()}  runtime_plan.py\n"
    tree_hash = sha256(tree_line.encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": "MB_V32_ENGINE_MANIFEST_V1",
        "file_count": 1,
        "tree_sha256": tree_hash,
    }
    (engine / "manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    archive = root / "engine.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(engine, arcname="engine_v32")
        if malicious:
            payload = b"bad"
            info = tarfile.TarInfo(malicious)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))
    metadata = {
        "schema_version": "MB_V32_PRIVATE_DRIVE_ENGINE_V1",
        "drive_file_id": "fixture_file_id_12345",
        "archive_file_name": "engine.tar.gz",
        "archive_size_bytes": archive.stat().st_size,
        "archive_sha256": sha256(archive.read_bytes()).hexdigest(),
        "engine_file_count": 1,
        "engine_tree_sha256": tree_hash,
    }
    return archive, engine_fetch.validate_metadata(metadata)


class PrivateEngineTests(unittest.TestCase):
    def test_install_verified_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, metadata = make_bundle(root)
            destination = root / "installed" / "engine_v32"
            engine_fetch.install_archive(archive, metadata, destination)
            self.assertEqual(
                (destination / "runtime_plan.py").read_text(encoding="utf-8"),
                "print('fixture')\n",
            )

    def test_hash_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, metadata = make_bundle(root)
            metadata["archive_sha256"] = "0" * 64
            with self.assertRaises(engine_fetch.EngineFetchError):
                engine_fetch.install_archive(
                    archive, metadata, root / "engine_v32"
                )

    def test_path_traversal_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, metadata = make_bundle(root, malicious="../escape.py")
            with self.assertRaises(engine_fetch.EngineFetchError):
                engine_fetch.install_archive(
                    archive, metadata, root / "engine_v32"
                )

    def test_existing_destination_blocks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive, metadata = make_bundle(root)
            destination = root / "engine_v32"
            destination.mkdir()
            with self.assertRaises(engine_fetch.EngineFetchError):
                engine_fetch.install_archive(archive, metadata, destination)


if __name__ == "__main__":
    unittest.main()
