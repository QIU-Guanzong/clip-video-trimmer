"""Bounded, generated large-file exercise; does not read customer media."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from desktop import ClipWindow


def wait(app, predicate, seconds=90):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(10)
    raise AssertionError("Timed out waiting for large-file operation")


def main():
    if shutil.disk_usage(tempfile.gettempdir()).free < 3_000_000_000:
        raise RuntimeError("Need 3 GB of free temporary space for this verification")
    app = QApplication.instance() or QApplication([])
    window = ClipWindow()
    window.show()
    result = {"synthetic": True, "not_real_customer_media": True}
    try:
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            small = folder / "seed.mp4"
            source = folder / "large.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc2=size=640x360:rate=25:duration=10",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=440:sample_rate=48000:duration=10",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "ultrafast",
                    "-crf",
                    "18",
                    "-g",
                    "50",
                    "-c:a",
                    "aac",
                    "-shortest",
                    str(small),
                ],
                check=True,
            )
            loops = max(1, 550_000_000 // small.stat().st_size + 1)
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-stream_loop",
                    str(loops),
                    "-i",
                    str(small),
                    "-c",
                    "copy",
                    str(source),
                ],
                check=True,
            )
            result["source_bytes"] = source.stat().st_size
            assert result["source_bytes"] >= 500_000_000
            window.load_source(source)
            wait(app, lambda: not window.busy)
            assert window.export_button.isEnabled(), window.status.text()
            result["duration_seconds"] = window.duration
            gaps = []
            last = [time.monotonic()]

            def tick():
                now = time.monotonic()
                gaps.append(now - last[0])
                last[0] = now

            timer = QTimer()
            timer.setInterval(10)
            timer.timeout.connect(tick)
            timer.start()
            cancelled = folder / "cancelled.mp4"
            window.export_to(cancelled)
            # Cancel as a queued user action while QProcess is active.
            QTimer.singleShot(10, window.cancel_button.click)
            wait(app, lambda: not window.busy)
            assert not cancelled.exists(), "Cancellation left a published destination"
            assert not list(folder.glob(".clip-*")), "Cancellation left temporary media"
            result["cancel_cleanup_passed"] = True
            output = folder / "output.mp4"
            started = time.monotonic()
            window.export_to(output)
            wait(app, lambda: not window.busy)
            result["export_seconds"] = round(time.monotonic() - started, 3)
            timer.stop()
            assert output.exists(), window.status.text()
            assert window.progress.value() == 100
            assert not list(folder.glob(".clip-*"))
            result["output_bytes"] = output.stat().st_size
            result["event_loop_max_gap_seconds"] = round(max(gaps), 4)
            result["event_loop_ticks"] = len(gaps)
            assert len(gaps) >= 2 and max(gaps) < 1.0, (
                "UI event loop stalled for at least a second"
            )
            window.player.stop()
            window.player.setSource(QUrl())
            app.processEvents()
    finally:
        window.close()
    Path("large-file-verification.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
