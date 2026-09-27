"""Native Qt interactions and actual FFmpeg exports on generated media."""

import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from PySide6.QtCore import QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from desktop import ClipWindow

app = QApplication.instance() or QApplication([])


def until(predicate, timeout=10):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return
        QTest.qWait(15)
    raise AssertionError("Timed out waiting for native event loop")


class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        cls.source = cls.root / "synthetic fixture.mp4"
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
                "-bf",
                "2",
                "-c:a",
                "aac",
                "-shortest",
                str(cls.source),
            ],
            check=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.window = ClipWindow()
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()
        QTest.qWaitForWindowActive(self.window, 3000)
        app.processEvents()

    def tearDown(self):
        if self.window.busy:
            self.window.cancel()
            until(lambda: not self.window.busy)
        self.window.close()
        self.window.deleteLater()
        app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        app.processEvents()

    def load(self):
        self.window.load_source(self.source)
        until(lambda: not self.window.busy)
        self.assertEqual(self.window.duration, 8)
        self.assertTrue(self.window.export_button.isEnabled())

    def test_export_from_native_controls(self):
        self.load()
        QTest.mouseClick(self.window.play_button, Qt.MouseButton.LeftButton)
        until(lambda: self.window.player.position() > 400)
        QTest.mouseClick(self.window.play_button, Qt.MouseButton.LeftButton)
        self.assertTrue(self.window.video.videoSink().videoFrame().isValid())
        self.window.start.setValue(2)
        self.window.end.setValue(4)
        destination = self.root / "finished.mp4"
        with patch(
            "desktop.QFileDialog.getSaveFileName", return_value=(str(destination), "")
        ):
            QTest.mouseClick(self.window.export_button, Qt.MouseButton.LeftButton)
        self.assertTrue(self.window.cancel_button.isEnabled())
        self.assertFalse(self.window.open_button.isEnabled())
        until(lambda: not self.window.busy)
        self.assertTrue(destination.is_file(), self.window.status.text())
        self.assertIn("actual duration", self.window.status.text())
        self.assertEqual(self.window.progress.value(), 100)
        self.assertFalse(any(self.root.glob(".clip-*")))
        shots = Path(os.environ.get("CLIP_SCREENSHOTS", "screenshots"))
        shots.mkdir(exist_ok=True)
        self.window.grab().save(str(shots / "desktop-export.png"))
        self.window.resize(680, 620)
        app.processEvents()
        self.window.grab().save(str(shots / "compact-export.png"))

    def test_aligns_to_real_keyframes(self):
        self.load()
        self.window.start.setValue(2.36)
        self.window.end.setValue(4.36)
        QTest.mouseClick(self.window.align_button, Qt.MouseButton.LeftButton)
        until(lambda: not self.window.busy)
        self.assertEqual(self.window.start.value(), 2)
        self.assertEqual(self.window.end.value(), 6)
        self.assertIn("Review this range", self.window.status.text())

    def test_cancel_leaves_no_output(self):
        self.load()
        destination = self.root / "cancelled.mp4"
        self.window.export_to(destination)
        QTest.mouseClick(self.window.cancel_button, Qt.MouseButton.LeftButton)
        until(lambda: not self.window.busy)
        self.assertFalse(destination.exists())
        self.assertFalse(any(self.root.glob(".clip-*")))
        self.assertIn("Cancelled", self.window.status.text())

    def test_destination_created_during_export_is_preserved(self):
        self.load()
        destination = self.root / "collision.mp4"
        self.window.export_to(destination)
        destination.write_bytes(b"created by someone else")
        until(lambda: not self.window.busy)
        self.assertEqual(destination.read_bytes(), b"created by someone else")
        self.assertIn("Could not complete", self.window.status.text())
        self.assertFalse(any(self.root.glob(".clip-*")))

    def test_invalid_selection_disables_export(self):
        self.load()
        self.window.start.setValue(6)
        self.window.end.setValue(3)
        self.assertFalse(self.window.export_button.isEnabled())
        self.window.end.setValue(7)
        self.assertTrue(self.window.export_button.isEnabled())
        self.window.activateWindow()
        self.window.start.setFocus()
        until(lambda: self.window.start.hasFocus())
        QTest.keyClick(self.window.start, Qt.Key.Key_Tab)
        self.assertIsNotNone(app.focusWidget())

    def test_bad_input_can_recover(self):
        bad = self.root / "bad.mp4"
        bad.write_bytes(b"not a video")
        self.window.load_source(bad)
        until(lambda: not self.window.busy)
        self.assertFalse(self.window.export_button.isEnabled())
        self.assertIn("Could not process", self.window.status.text())
        self.load()

    def test_missing_tool_has_actionable_message(self):
        with patch("desktop.tool", return_value=None):
            self.window.load_source(self.source)
        self.assertIn("FFmpeg is missing", self.window.status.text())
        self.assertFalse(self.window.busy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
