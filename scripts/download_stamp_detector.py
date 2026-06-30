#!/usr/bin/env python3
"""Download the optional Apache-2.0 stamp detector model used by Philalens."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import ssl
from pathlib import Path
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[1]
MODEL_URL = "https://raw.githubusercontent.com/code2k13/philately-tool/main/model.pt"
SOURCE_REPOSITORY = "https://github.com/code2k13/philately-tool"
SOURCE_LICENSE = "https://github.com/code2k13/philately-tool/blob/main/LICENSE"
DEFAULT_DESTINATION = REPO_ROOT / "data" / "local" / "models" / "code2k13-philately-tool-model.pt"
EXPECTED_BYTES = 6_249_507


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    destination = args.dest
    if destination.exists() and not args.force:
        print(f"Model already exists: {destination}")
        print("Use --force to overwrite it.")
        return 0

    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_destination = destination.with_suffix(destination.suffix + ".tmp")
    sha256 = hashlib.sha256()
    total = 0

    with urlopen(MODEL_URL, context=_ssl_context()) as response, tmp_destination.open("wb") as output:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            sha256.update(chunk)
            output.write(chunk)

    if total != EXPECTED_BYTES:
        tmp_destination.unlink(missing_ok=True)
        raise RuntimeError(f"Downloaded {total} bytes; expected {EXPECTED_BYTES} bytes.")

    shutil.move(str(tmp_destination), destination)
    notice_path = destination.with_suffix(destination.suffix + ".source.json")
    notice_path.write_text(
        json.dumps(
            {
                "source_repository": SOURCE_REPOSITORY,
                "model_url": MODEL_URL,
                "license": "Apache-2.0",
                "license_url": SOURCE_LICENSE,
                "bytes": total,
                "sha256": sha256.hexdigest(),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )

    print(f"Downloaded model: {destination}")
    print(f"Source metadata: {notice_path}")
    print(f"SHA256: {sha256.hexdigest()}")
    return 0


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ModuleNotFoundError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


if __name__ == "__main__":
    raise SystemExit(main())
