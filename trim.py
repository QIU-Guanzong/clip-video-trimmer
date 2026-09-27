"""Reviewable stream-copy trimming core, not a Windows desktop application."""

import json
import math
from pathlib import Path
import subprocess


def probe(path):
    return json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            text=True,
        )
    )


def trim(source, target, start, end):
    source, target = Path(source).resolve(), Path(target).resolve()
    if source == target or target.exists():
        raise ValueError(
            "Choose a new output file; existing files are never overwritten"
        )
    if not all(math.isfinite(t) for t in (start, end)) or not 0 <= start < end:
        raise ValueError("Expected finite times with 0 <= start < end")
    metadata = probe(source)
    if end > float(metadata["format"]["duration"]):
        raise ValueError("End point exceeds source duration")
    if not any(s["codec_type"] == "video" for s in metadata["streams"]):
        raise ValueError("A video stream is required")
    # Stream copy retains compressed packets and seek preroll. A UI must explain
    # keyframe constraints instead of advertising arbitrary frame-exact cuts.
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-n",
            "-ss",
            str(start),
            "-i",
            str(source),
            "-t",
            str(end - start),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c",
            "copy",
            str(target),
        ],
        check=True,
    )
    return probe(target)
