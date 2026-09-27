"""A small desktop front end for reviewing and exporting one clip at a time."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import sys
import tempfile

from PySide6.QtCore import QProcess, Qt, QUrl
from PySide6.QtGui import QAction
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


def tool(name):
    suffix = ".exe" if sys.platform == "win32" else ""
    folder = (
        Path(sys.executable).parent
        if getattr(sys, "frozen", False)
        else Path(__file__).parent
    )
    local = folder / "tools" / (name + suffix)
    return str(local) if local.is_file() else shutil.which(name)


def publish_clip(temporary, destination):
    """Create the destination without replacing a file created during export."""
    os.link(temporary, destination)
    Path(temporary).unlink()


class ClipWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clip — Trim without re-encoding")
        self.resize(960, 760)
        self.setMinimumSize(680, 590)
        self.source = None
        self.destination = None
        self.scratch = None
        self.duration = 0.0
        self.busy = False
        self.cancelled = False
        self.phase = None
        self.raw = bytearray()
        self.errors = bytearray()
        self.progress_buffer = ""
        self.metadata = None
        self.process = QProcess(self)
        self.process.readyReadStandardOutput.connect(self.read_output)
        self.process.readyReadStandardError.connect(self.read_errors)
        self.process.finished.connect(self.finished)
        self.process.errorOccurred.connect(self.process_error)
        self.player = QMediaPlayer(self)
        self.audio = QAudioOutput(self)
        self.player.setAudioOutput(self.audio)
        self.audio.setVolume(0.5)
        self.video = QVideoWidget()
        self.video.setMinimumHeight(240)
        self.player.setVideoOutput(self.video)
        self.player.positionChanged.connect(self.position_changed)
        self.player.playbackStateChanged.connect(self.playback_changed)
        self.player.errorOccurred.connect(lambda *_: self.preview_error())

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)
        header = QHBoxLayout()
        title = QLabel("Trim a clip")
        font = title.font()
        font.setPointSize(22)
        font.setBold(True)
        title.setFont(font)
        header.addWidget(title)
        header.addStretch()
        self.open_button = QPushButton("Open video…")
        self.open_button.clicked.connect(self.choose_source)
        header.addWidget(self.open_button)
        layout.addLayout(header)
        self.filename = QLabel("Choose a video to begin. Your source stays unchanged.")
        self.filename.setWordWrap(True)
        layout.addWidget(self.filename)
        layout.addWidget(self.video, 1)
        self.seek = QSlider(Qt.Orientation.Horizontal)
        self.seek.setAccessibleName("Playback position")
        self.seek.sliderMoved.connect(self.player.setPosition)
        self.seek.valueChanged.connect(self.seek_changed)
        layout.addWidget(self.seek)
        transport = QHBoxLayout()
        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_play)
        transport.addWidget(self.play_button)
        self.clock = QLabel("00:00.000 / 00:00.000")
        transport.addWidget(self.clock)
        transport.addStretch()
        self.mark_in = QPushButton("Set in point")
        self.mark_out = QPushButton("Set out point")
        self.mark_in.clicked.connect(
            lambda: self.start.setValue(self.player.position() / 1000)
        )
        self.mark_out.clicked.connect(
            lambda: self.end.setValue(self.player.position() / 1000)
        )
        transport.addWidget(self.mark_in)
        transport.addWidget(self.mark_out)
        layout.addLayout(transport)
        times = QHBoxLayout()
        self.start = QDoubleSpinBox()
        self.end = QDoubleSpinBox()
        for label, spin in [("In (seconds)", self.start), ("Out (seconds)", self.end)]:
            spin.setDecimals(3)
            spin.setSingleStep(0.04)
            spin.setRange(0, 86400)
            spin.setAccessibleName(label)
            times.addWidget(QLabel(label))
            times.addWidget(spin, 1)
            spin.valueChanged.connect(self.update_controls)
        layout.addLayout(times)
        self.note = QLabel(
            "Lossless stream copy keeps encoded quality. Cut boundaries can shift to nearby frames; exact-frame export is not included."
        )
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setAccessibleName("Export progress")
        layout.addWidget(self.progress)
        actions = QHBoxLayout()
        self.status = QLabel("Ready")
        self.status.setWordWrap(True)
        actions.addWidget(self.status, 1)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel)
        actions.addWidget(self.cancel_button)
        self.export_button = QPushButton("Export clip…")
        self.export_button.clicked.connect(self.choose_export)
        actions.addWidget(self.export_button)
        layout.addLayout(actions)
        self.setCentralWidget(root)
        open_action = QAction("Open video", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.choose_source)
        self.addAction(open_action)
        self.update_controls()

    @staticmethod
    def timestamp(ms):
        seconds, millis = divmod(max(0, ms), 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        prefix = f"{hours:02}:" if hours else ""
        return f"{prefix}{minutes:02}:{seconds:02}.{millis:03}"

    def update_controls(self, *_):
        loaded = self.source is not None and self.duration > 0
        self.open_button.setEnabled(not self.busy)
        for widget in (
            self.start,
            self.end,
            self.mark_in,
            self.mark_out,
            self.play_button,
            self.seek,
        ):
            widget.setEnabled(loaded and not self.busy)
        self.export_button.setEnabled(
            loaded and not self.busy and self.start.value() < self.end.value()
        )
        self.cancel_button.setEnabled(self.busy)

    def choose_source(self):
        if self.busy:
            return
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open video",
            "",
            "Videos (*.mp4 *.mov *.mkv *.avi *.webm);;All files (*)",
        )
        if filename:
            self.load_source(Path(filename))

    def load_source(self, path):
        executable = tool("ffprobe")
        if not executable or not tool("ffmpeg"):
            self.status.setText(
                "FFmpeg is missing. Put ffmpeg and ffprobe in the tools folder beside Clip, then try again. See USER_GUIDE.md."
            )
            return
        self.player.stop()
        self.player.setSource(QUrl())
        self.source = Path(path).resolve()
        self.duration = 0
        self.metadata = None
        self.filename.setText(self.source.name)
        self.begin(
            "probe",
            executable,
            [
                "-v",
                "error",
                "-show_format",
                "-show_streams",
                "-of",
                "json",
                str(self.source),
            ],
        )
        self.status.setText("Reading video information…")

    def begin(self, phase, executable, args):
        self.phase = phase
        self.cancelled = False
        self.raw.clear()
        self.errors.clear()
        self.progress_buffer = ""
        self.busy = True
        self.progress.setRange(0, 0 if phase == "probe" else 100)
        self.progress.setValue(0)
        self.update_controls()
        self.process.start(executable, args)

    def read_errors(self):
        self.errors.extend(bytes(self.process.readAllStandardError()))
        self.errors = self.errors[-16384:]

    def read_output(self):
        data = bytes(self.process.readAllStandardOutput())
        if self.phase != "export":
            self.raw.extend(data)
            return
        self.progress_buffer += data.decode("utf8", errors="replace")
        lines = self.progress_buffer.split("\n")
        self.progress_buffer = lines.pop()
        for line in lines:
            if line.startswith("out_time_us="):
                try:
                    elapsed = int(line.split("=", 1)[1]) / 1_000_000
                    self.progress.setValue(
                        min(99, max(0, int(100 * elapsed / self.export_duration)))
                    )
                except ValueError:
                    pass

    def process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.finished(-1, QProcess.ExitStatus.CrashExit)

    def finished(self, code, _):
        self.read_output()
        self.read_errors()
        phase = self.phase
        self.phase = None
        self.busy = False
        self.progress.setRange(0, 100)
        try:
            if self.cancelled:
                self.status.setText("Cancelled. No exported file was saved.")
                self.progress.setValue(0)
            elif code != 0:
                detail = self.errors.decode("utf8", errors="replace").strip()[-600:]
                self.status.setText(
                    "Could not process this file. "
                    + (detail or self.process.errorString())
                )
            elif phase == "probe":
                self.metadata = json.loads(self.raw)
                self.duration = float(self.metadata["format"]["duration"])
                video = next(
                    s for s in self.metadata["streams"] if s["codec_type"] == "video"
                )
                if not 0 < self.duration < 604800:
                    raise ValueError("Unsupported video duration")
                self.start.setMaximum(self.duration)
                self.end.setMaximum(self.duration)
                self.start.setValue(0)
                self.end.setValue(self.duration)
                self.seek.setRange(0, round(self.duration * 1000))
                self.player.setSource(QUrl.fromLocalFile(str(self.source)))
                self.position_changed(0)
                self.status.setText(
                    f"{video['width']} × {video['height']} · {video['codec_name']} · Set your in and out points."
                )
                self.progress.setValue(0)
            elif phase == "export":
                # Probe the finished output asynchronously before publishing it.
                self.begin(
                    "verify",
                    tool("ffprobe"),
                    [
                        "-v",
                        "error",
                        "-show_format",
                        "-show_streams",
                        "-of",
                        "json",
                        str(self.partial),
                    ],
                )
                self.status.setText("Checking exported video…")
                return
            elif phase == "verify":
                output = json.loads(self.raw)
                video = next(s for s in output["streams"] if s["codec_type"] == "video")
                original = next(
                    s for s in self.metadata["streams"] if s["codec_type"] == "video"
                )
                if (video["width"], video["height"]) != (
                    original["width"],
                    original["height"],
                ):
                    raise ValueError("Output dimensions differ from the source")
                duration = float(output["format"]["duration"])
                if duration <= 0:
                    raise ValueError("Export is empty")
                publish_clip(self.partial, self.destination)
                self.progress.setValue(100)
                self.status.setText(
                    f"Saved {self.destination.name} · {duration:.3f}s actual duration (requested {self.export_duration:.3f}s)."
                )
        except (ValueError, KeyError, StopIteration, OSError) as error:
            if phase == "probe":
                self.duration = 0
            self.status.setText(
                f"Could not complete: {error}. Choose another file or try again."
            )
        finally:
            if not self.busy and self.scratch:
                self.scratch.cleanup()
                self.scratch = None
            self.update_controls()

    def choose_export(self):
        if self.busy or not self.source:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export clip",
            str(self.source.with_name(self.source.stem + "-clip" + self.source.suffix)),
            "Video (*" + self.source.suffix + ")",
        )
        if filename:
            self.export_to(Path(filename))

    def export_to(self, destination):
        if (
            self.busy
            or not self.source
            or not 0 <= self.start.value() < self.end.value() <= self.duration
        ):
            return
        destination = destination.resolve()
        if destination.exists() or destination == self.source:
            self.status.setText(
                "Choose a new filename. Existing files are never overwritten."
            )
            return
        if destination.suffix.lower() != self.source.suffix.lower():
            self.status.setText(
                "Keep the source file extension for stream-copy export."
            )
            return
        try:
            self.scratch = tempfile.TemporaryDirectory(
                prefix=".clip-", dir=destination.parent
            )
        except OSError as error:
            self.status.setText(f"Cannot write to that folder: {error}")
            return
        self.destination = destination
        self.partial = Path(self.scratch.name) / ("clip" + destination.suffix)
        self.export_duration = self.end.value() - self.start.value()
        self.player.pause()
        self.begin(
            "export",
            tool("ffmpeg"),
            [
                "-hide_banner",
                "-loglevel",
                "error",
                "-nostdin",
                "-n",
                "-ss",
                str(self.start.value()),
                "-i",
                str(self.source),
                "-t",
                str(self.export_duration),
                "-map",
                "0:v:0",
                "-map",
                "0:a?",
                "-c",
                "copy",
                "-progress",
                "pipe:1",
                "-nostats",
                str(self.partial),
            ],
        )
        self.status.setText("Exporting without re-encoding…")

    def cancel(self):
        if self.busy:
            self.cancelled = True
            self.process.kill()

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def playback_changed(self, state):
        self.play_button.setText(
            "Pause" if state == QMediaPlayer.PlaybackState.PlayingState else "Play"
        )

    def position_changed(self, position):
        if not self.seek.isSliderDown():
            self.seek.blockSignals(True)
            self.seek.setValue(position)
            self.seek.blockSignals(False)
        self.clock.setText(
            self.timestamp(position)
            + " / "
            + self.timestamp(round(self.duration * 1000))
        )

    def seek_changed(self, value):
        if not self.seek.isSliderDown():
            self.player.setPosition(value)

    def preview_error(self):
        if not self.busy:
            self.status.setText(
                "Preview unavailable for this codec. You can still enter times and try stream-copy export."
            )

    def closeEvent(self, event):
        if self.busy:
            answer = QMessageBox.question(
                self, "Export in progress", "Cancel processing and close Clip?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.cancel()
            self.process.waitForFinished(3000)
        self.player.stop()
        if self.scratch:
            self.scratch.cleanup()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Clip")
    window = ClipWindow()
    window.show()
    if len(sys.argv) > 1:
        window.load_source(Path(sys.argv[1]))
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
