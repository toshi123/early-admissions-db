"""Create a deterministic, metadata-free archive of the public MCP client."""

import gzip
import hashlib
import json
import tarfile
from pathlib import Path


SITE = Path(__file__).resolve().parents[1]
SOURCE = SITE / "dist-mcp" / "client"
ARCHIVE = SITE / "mcp" / "frozen-client-v0.1.tar.gz"
RECEIPT = SITE / "mcp" / "frozen-client-v0.1.json"


def excluded(relative: Path) -> bool:
    return any(part == "_redirects" or part == ".DS_Store" or part.startswith("._") for part in relative.parts) or relative.suffix == ".map"


def main() -> None:
    manifest = json.loads((SOURCE / "site-data" / "build_manifest.json").read_text())
    expected = json.loads(RECEIPT.read_text())
    if (
        manifest["build_id"] != expected["site_data_build_id"]
        or manifest["counts"]["search_rows"] != expected["confirmed_rows"]
        or manifest["validation"]["status"] != "passed"
        or manifest["publication"]["production_ready"] is not True
    ):
        raise ValueError("Frozen MCP client source is not the expected validated build")

    source_paths = list(SOURCE.rglob("*"))
    paths = sorted(path for path in source_paths if path.is_file() and not excluded(path.relative_to(SOURCE)))
    if not paths or any(path.is_symlink() for path in source_paths):
        raise ValueError("Frozen MCP client source is empty or contains symlinks")

    with ARCHIVE.open("wb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0, compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                for path in paths:
                    relative = path.relative_to(SOURCE).as_posix()
                    info = tarfile.TarInfo(relative)
                    info.size = path.stat().st_size
                    info.mode = 0o644
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ""
                    with path.open("rb") as source:
                        archive.addfile(info, source)

    with tarfile.open(ARCHIVE, mode="r:gz") as packaged:
        members = packaged.getmembers()
        if len(members) != len(paths) or any(
            not member.isfile() or member.pax_headers or excluded(Path(member.name)) for member in members
        ):
            raise ValueError("Frozen MCP client archive contains unexpected entries or metadata")

    expected["sha256"] = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    expected["asset_count"] = len(paths)
    RECEIPT.write_text(json.dumps(expected, indent=2) + "\n")
    print(json.dumps({"archive": str(ARCHIVE), "sha256": expected["sha256"], "assets": len(paths)}))


if __name__ == "__main__":
    main()
