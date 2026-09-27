"""Exercise real FFmpeg with generated video and audio; no customer data."""

import json
from pathlib import Path
import platform
import subprocess
import tempfile
import unittest
from trim import trim


def run(*args):
    return subprocess.check_output(args, text=True)


def frames(path):
    output = run(
        "ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-f", "framemd5", "-"
    )
    return [
        line.split(",")[-1].strip()
        for line in output.splitlines()
        if line and not line.startswith("#")
    ]


def audio_packets(path):
    output = run(
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_packets",
        "-show_data_hash",
        "sha256",
        "-show_entries",
        "packet=data_hash",
        "-of",
        "json",
        str(path),
    )
    return [p["data_hash"] for p in json.loads(output)["packets"]]


def contained(part, whole):
    return bool(part) and any(
        whole[i : i + len(part)] == part for i in range(len(whole) - len(part) + 1)
    )


class TrimmingProof(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        cls.source = cls.root / "synthetic source.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc2=size=320x180:rate=25:duration=8",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000:duration=8",
                "-c:v",
                "libx264",
                "-g",
                "50",
                "-keyint_min",
                "50",
                "-sc_threshold",
                "0",
                "-bf",
                "2",
                "-c:a",
                "aac",
                "-shortest",
                str(cls.source),
            ],
            check=True,
        )
        cls.source_frames = frames(cls.source)
        cls.source_audio = audio_packets(cls.source)
        cls.results = []

    @classmethod
    def tearDownClass(cls):
        Path("verification.json").write_text(
            json.dumps(
                {
                    "platform": platform.platform(),
                    "ffmpeg": run("ffmpeg", "-version").splitlines()[0],
                    "cases": cls.results,
                    "scope": "Small synthetic FFmpeg fixture only; separate reports cover installer and large files",
                },
                indent=2,
            )
            + "\n"
        )
        cls.tmp.cleanup()

    def check_cut(self, start, end):
        output = self.root / f"cut-{start}.mp4"
        metadata = trim(self.source, output, start, end)
        video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
        audio = next(s for s in metadata["streams"] if s["codec_type"] == "audio")
        self.assertEqual((video["width"], video["height"]), (320, 180))
        decoded = frames(output)
        self.assertTrue(contained(decoded, self.source_frames), "decoded video changed")
        self.assertTrue(
            contained(audio_packets(output), self.source_audio), "audio payload changed"
        )
        delta = abs(float(video["start_time"]) - float(audio["start_time"]))
        end_delta = abs(
            float(video["start_time"])
            + float(video["duration"])
            - float(audio["start_time"])
            - float(audio["duration"])
        )
        self.assertLessEqual(delta, 0.1)
        self.assertLessEqual(end_delta, 0.15)
        self.results.append(
            {
                "start": start,
                "end": end,
                "video_frames": len(decoded),
                "output_duration": metadata["format"]["duration"],
                "video_frames_unchanged": True,
                "audio_packets_unchanged": True,
                "start_delta_seconds": delta,
                "end_delta_seconds": end_delta,
            }
        )

    def test_keyframe_aligned(self):
        self.check_cut(2, 4)

    def test_between_keyframes(self):
        self.check_cut(2.36, 4.36)

    def test_rejects_invalid_ranges(self):
        for start, end in [(-1, 2), (2, 1), (0, 9), (0, float("inf"))]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                trim(self.source, self.root / "invalid.mp4", start, end)

    def test_preserves_existing_output(self):
        target = self.root / "existing.mp4"
        target.write_bytes(b"keep me")
        with self.assertRaises(ValueError):
            trim(self.source, target, 0, 1)
        self.assertEqual(target.read_bytes(), b"keep me")

    def test_preserves_input(self):
        with self.assertRaises(ValueError):
            trim(self.source, self.source, 0, 1)
        self.assertEqual(len(frames(self.source)), 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
