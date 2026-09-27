# Dependencies and design references

- PySide6 / Qt 6.11.2: https://doc.qt.io/qtforpython-6/licenses.html . Keep the dependency license texts and required notices with distributed builds. The directory-based package keeps Qt libraries separate; an installer recipe is not a completed distribution audit.
- FFmpeg: https://ffmpeg.org/legal.html . Licensing depends on the supplied build and enabled components. The source sample does not bundle FFmpeg binaries. Supply the notices and source availability required by the particular Windows build before distribution.
- PyInstaller 6.22.3: https://pyinstaller.org/en/stable/license.html . Used only by the build recipe.
- Inno Setup: https://jrsoftware.org/isinfo.php . External Windows installer compiler, not included.

The interface uses standard native controls, a large preview area and one primary export action. It uses visible labels and keyboard focus instead of decorative motion. Reference: Microsoft's button guidance, https://learn.microsoft.com/en-us/windows/apps/develop/ui/controls/buttons . Qt's QMediaPlayer and QProcess documentation informed preview and asynchronous process handling: https://doc.qt.io/qtforpython-6/PySide6/QtMultimedia/QMediaPlayer.html and https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html . No visual assets or layouts were copied.
