"""
repo_parser.py
--------------
Safely unpacks an uploaded .zip project archive and merges its valid source
files into a single delimited text payload for downstream analysis.
"""

import io
import os
import shutil
import zipfile
import tempfile
from pathlib import Path

ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".json", ".go"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "venv", ".venv"}


def _is_within_directory(directory: Path, target: Path) -> bool:
    """Zip-slip guard: ensures extracted paths never escape the workspace."""
    try:
        target.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def extract_and_merge_repo(uploaded_zip) -> tuple[str, list[str]]:
    """
    Safely unpacks an uploaded .zip into a temp workspace, walks it, and
    merges every valid source file into one delimited text payload.

    Args:
        uploaded_zip: a file-like object (e.g. Streamlit's UploadedFile).

    Returns:
        (merged_payload, list_of_included_filenames)
    """
    workspace = Path(tempfile.mkdtemp(prefix="graphrag_guard_"))
    included_files: list[str] = []
    payload_parts: list[str] = []

    try:
        zip_bytes = io.BytesIO(uploaded_zip.read())
        with zipfile.ZipFile(zip_bytes) as zf:
            for member in zf.infolist():
                dest_path = workspace / member.filename
                if not _is_within_directory(workspace, dest_path):
                    continue  # skip anything attempting path traversal
            zf.extractall(workspace)

        for root, _dirs, files in os.walk(workspace):
            if any(part in SKIP_DIRS for part in Path(root).parts):
                continue

            for filename in files:
                file_path = Path(root) / filename
                if file_path.suffix.lower() not in ALLOWED_EXTENSIONS:
                    continue

                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                if not content.strip():
                    continue

                rel_name = str(file_path.relative_to(workspace))
                included_files.append(rel_name)
                payload_parts.append(f"--- File: {rel_name} ---\n{content}\n")

        merged_payload = "\n".join(payload_parts)
        return merged_payload, included_files

    finally:
        shutil.rmtree(workspace, ignore_errors=True)
