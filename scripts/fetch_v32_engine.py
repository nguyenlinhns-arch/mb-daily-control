#!/usr/bin/env python3
"""Fetch and safely unpack the frozen V32 runtime from private Google Drive."""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import tarfile
import tempfile
from typing import Any


DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
MAX_ARCHIVE_BYTES = 10 * 1024 * 1024
MAX_UNPACKED_BYTES = 25 * 1024 * 1024


class EngineFetchError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise EngineFetchError(f"Khong doc duoc metadata engine: {path}") from exc
    if not isinstance(value, dict):
        raise EngineFetchError("Metadata engine phai la JSON object")
    return value


def validate_metadata(value: dict[str, Any]) -> dict[str, Any]:
    if value.get("schema_version") != "MB_V32_PRIVATE_DRIVE_ENGINE_V1":
        raise EngineFetchError("Sai schema metadata engine")
    file_id = str(value.get("drive_file_id") or "")
    archive_name = str(value.get("archive_file_name") or "")
    archive_hash = str(value.get("archive_sha256") or "").lower()
    tree_hash = str(value.get("engine_tree_sha256") or "").lower()
    if not re.fullmatch(r"[A-Za-z0-9_-]{10,200}", file_id):
        raise EngineFetchError("Drive file ID khong hop le")
    if not re.fullmatch(r"[A-Za-z0-9._-]+\.tar\.gz", archive_name):
        raise EngineFetchError("Ten goi engine khong hop le")
    if not re.fullmatch(r"[0-9a-f]{64}", archive_hash):
        raise EngineFetchError("SHA-256 goi engine khong hop le")
    if not re.fullmatch(r"[0-9a-f]{64}", tree_hash):
        raise EngineFetchError("Tree SHA-256 engine khong hop le")
    try:
        archive_size = int(value["archive_size_bytes"])
        engine_file_count = int(value["engine_file_count"])
    except (KeyError, TypeError, ValueError) as exc:
        raise EngineFetchError("Metadata engine thieu size/file_count") from exc
    if not 1 <= archive_size <= MAX_ARCHIVE_BYTES:
        raise EngineFetchError("Kich thuoc goi engine vuot gioi han")
    if not 1 <= engine_file_count <= 500:
        raise EngineFetchError("So file engine vuot gioi han")
    return {
        **value,
        "drive_file_id": file_id,
        "archive_file_name": archive_name,
        "archive_sha256": archive_hash,
        "engine_tree_sha256": tree_hash,
        "archive_size_bytes": archive_size,
        "engine_file_count": engine_file_count,
    }


def service_account_info() -> dict[str, Any]:
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not raw:
        raise EngineFetchError("Thieu secret GOOGLE_SERVICE_ACCOUNT_JSON")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EngineFetchError("GOOGLE_SERVICE_ACCOUNT_JSON khong hop le") from exc
    required = {"client_email", "private_key", "token_uri"}
    if not isinstance(value, dict) or not required.issubset(value):
        raise EngineFetchError("Service account JSON thieu truong bat buoc")
    return value


def download_from_drive(metadata: dict[str, Any], output: Path) -> None:
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError as exc:
        raise EngineFetchError("Thieu Google API runtime") from exc

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info(), scopes=[DRIVE_READONLY_SCOPE]
    )
    service = build("drive", "v3", credentials=credentials, cache_discovery=False)
    remote = service.files().get(
        fileId=metadata["drive_file_id"],
        fields="id,name,size,mimeType,trashed",
        supportsAllDrives=True,
    ).execute()
    if remote.get("trashed") is True:
        raise EngineFetchError("Goi engine tren Drive da vao thung rac")
    if remote.get("name") != metadata["archive_file_name"]:
        raise EngineFetchError("Ten goi engine tren Drive khong khop metadata")
    try:
        remote_size = int(remote.get("size"))
    except (TypeError, ValueError) as exc:
        raise EngineFetchError("Drive khong tra kich thuoc goi engine") from exc
    if remote_size != metadata["archive_size_bytes"]:
        raise EngineFetchError("Kich thuoc goi engine tren Drive khong khop")

    request = service.files().get_media(
        fileId=metadata["drive_file_id"], supportsAllDrives=True
    )
    with output.open("wb") as handle:
        downloader = MediaIoBaseDownload(handle, request, chunksize=1024 * 1024)
        done = False
        while not done:
            _status, done = downloader.next_chunk()
            if handle.tell() > MAX_ARCHIVE_BYTES:
                raise EngineFetchError("Download engine vuot gioi han")


def _safe_archive_files(
    archive: tarfile.TarFile, expected_count: int
) -> list[tarfile.TarInfo]:
    files: list[tarfile.TarInfo] = []
    unpacked = 0
    for member in archive.getmembers():
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts:
            raise EngineFetchError("Goi engine co duong dan nguy hiem")
        if member.isdir():
            if path.parts != ("engine_v32",):
                raise EngineFetchError("Goi engine co thu muc ngoai engine_v32")
            continue
        if not member.isfile():
            raise EngineFetchError("Goi engine chua symlink/device khong duoc phep")
        if len(path.parts) != 2 or path.parts[0] != "engine_v32":
            raise EngineFetchError("File engine nam ngoai thu muc khoa")
        name = path.name
        if name != "manifest.json" and Path(name).suffix not in {".py", ".pkl"}:
            raise EngineFetchError("Goi engine co loai file khong duoc phep")
        if member.size < 0:
            raise EngineFetchError("Goi engine co kich thuoc file am")
        unpacked += member.size
        if unpacked > MAX_UNPACKED_BYTES:
            raise EngineFetchError("Goi engine bung nen vuot gioi han")
        files.append(member)
    if len(files) != expected_count + 1:
        raise EngineFetchError("So file trong goi engine khong khop metadata")
    if len({member.name for member in files}) != len(files):
        raise EngineFetchError("Goi engine co ten file trung")
    return files


def verify_engine_tree(engine: Path, metadata: dict[str, Any]) -> None:
    manifest_path = engine / "manifest.json"
    manifest = read_json(manifest_path)
    try:
        manifest_count = int(manifest["file_count"])
        manifest_tree = str(manifest["tree_sha256"]).lower()
    except (KeyError, TypeError, ValueError) as exc:
        raise EngineFetchError("Manifest engine thieu file_count/tree hash") from exc
    if manifest_count != metadata["engine_file_count"]:
        raise EngineFetchError("File count trong manifest khong khop metadata")
    if manifest_tree != metadata["engine_tree_sha256"]:
        raise EngineFetchError("Tree hash trong manifest khong khop metadata")
    files = sorted(
        path for path in engine.iterdir()
        if path.is_file() and path.suffix in {".py", ".pkl"}
    )
    lines = [
        f"{sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
        for path in files
    ]
    actual_tree = sha256("".join(lines).encode("utf-8")).hexdigest()
    if len(files) != manifest_count or actual_tree != manifest_tree:
        raise EngineFetchError("Noi dung engine khong khop manifest da khoa")


def install_archive(
    archive_path: Path, metadata: dict[str, Any], destination: Path
) -> None:
    if destination.exists():
        raise EngineFetchError(f"Thu muc dich da ton tai: {destination}")
    actual_size = archive_path.stat().st_size
    if actual_size != metadata["archive_size_bytes"]:
        raise EngineFetchError("Kich thuoc file download khong khop metadata")
    actual_hash = sha256(archive_path.read_bytes()).hexdigest()
    if actual_hash != metadata["archive_sha256"]:
        raise EngineFetchError("SHA-256 goi engine khong khop")

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="v32-engine-", dir=destination.parent
    ) as temp_dir:
        staging_root = Path(temp_dir)
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = _safe_archive_files(
                archive, metadata["engine_file_count"]
            )
            for member in members:
                source = archive.extractfile(member)
                if source is None:
                    raise EngineFetchError("Khong doc duoc file trong goi engine")
                target = staging_root / member.name
                target.parent.mkdir(parents=True, exist_ok=True)
                with source, target.open("wb") as handle:
                    shutil.copyfileobj(source, handle, length=1024 * 1024)
        staged_engine = staging_root / "engine_v32"
        verify_engine_tree(staged_engine, metadata)
        os.replace(staged_engine, destination)


def fetch(metadata_path: Path, destination: Path) -> None:
    metadata = validate_metadata(read_json(metadata_path))
    if destination.name != "engine_v32":
        raise EngineFetchError("Thu muc dich bat buoc ten engine_v32")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        prefix="v32-engine-", suffix=".tar.gz", dir=destination.parent,
        delete=False,
    ) as handle:
        archive_path = Path(handle.name)
    try:
        download_from_drive(metadata, archive_path)
        install_archive(archive_path, metadata, destination)
    finally:
        archive_path.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument(
        "--local-archive", type=Path,
        help="Chi dung cho kiem thu/offline; van kiem tra day du SHA/manifest",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        metadata = validate_metadata(read_json(args.metadata))
        if args.destination.name != "engine_v32":
            raise EngineFetchError("Thu muc dich bat buoc ten engine_v32")
        if args.local_archive:
            install_archive(args.local_archive, metadata, args.destination)
        else:
            fetch(args.metadata, args.destination)
        print(
            "V32_PRIVATE_ENGINE_VERIFIED "
            f"tree={metadata['engine_tree_sha256']}"
        )
        return 0
    except (EngineFetchError, OSError, tarfile.TarError) as exc:
        print(f"V32_PRIVATE_ENGINE_BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
