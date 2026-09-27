"""Fetch the checksum-pinned upstream Windows archive for an internal build."""

import hashlib
from pathlib import Path
import shutil
import tempfile
import urllib.request
import zipfile

URL = "https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-9.0.2-essentials_build.zip"
SHA256 = "60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba"


def main():
    target = Path("tools")
    if target.exists():
        raise SystemExit("tools already exists; use a clean checkout")
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "ffmpeg.zip"
        with (
            urllib.request.urlopen(URL, timeout=120) as source,
            archive.open("wb") as output,
        ):
            shutil.copyfileobj(source, output)
        with archive.open("rb") as downloaded:
            actual_digest = hashlib.file_digest(downloaded, "sha256").hexdigest()
        if actual_digest != SHA256:
            raise SystemExit("FFmpeg archive checksum does not match")
        target.mkdir()
        with zipfile.ZipFile(archive) as bundle:
            for filename in ["ffmpeg.exe", "ffprobe.exe"]:
                candidates = [
                    n for n in bundle.namelist() if n.endswith("/bin/" + filename)
                ]
                if len(candidates) != 1:
                    raise RuntimeError(f"Expected exactly one {filename}")
                (target / filename).write_bytes(bundle.read(candidates[0]))
            # Keep the original notices and build readme rather than paraphrasing.
            notices = [
                n
                for n in bundle.namelist()
                if Path(n).name.lower() in ["license", "license.txt", "readme.txt"]
            ]
            if not notices:
                raise RuntimeError("No upstream notices found")
            for name in notices:
                (target / Path(name).name).write_bytes(bundle.read(name))
        if not (target / "LICENSE.txt").exists():
            license_file = next(
                p for p in target.iterdir() if p.name.lower().startswith("license")
            )
            shutil.copyfile(license_file, target / "LICENSE.txt")
    (target / "SOURCE.txt").write_text(
        "Unmodified FFmpeg binaries from "
        + URL
        + "\nArchive SHA256: "
        + SHA256
        + "\nBuild/source reference: https://github.com/GyanD/codexffmpeg/releases/tag/9.0.2\n"
        "FFmpeg source: https://github.com/FFmpeg/FFmpeg/commit/946fcce07b\n"
        "Distribution is an internal draft pending review of all corresponding dependency sources.\n"
    )
    print("Verified FFmpeg archive", SHA256)


if __name__ == "__main__":
    main()
