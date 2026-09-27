# Clip user guide

An unsigned internal Windows preview has passed automated install, launch and uninstall checks on Windows Server 2022. It is not a final client release. Refer to the matching build report for the tested source revision and remaining acceptance scope.

## Trim a video

1. Choose **Open video** (Ctrl+O) and select a local MP4, MOV, MKV, AVI or WebM file. Available codecs depend on the installed media tools.
2. Use **Play** and the position slider to preview the clip. **Set in point** and **Set out point** copy the current playback time; the seconds fields also accept typed values and arrow keys.
3. Choose **Align to keyframes** to review enclosing in/out times. The scan can be cancelled. A 2.36–4.36 second selection may expand to 2–6 seconds when keyframes are two seconds apart. Then choose **Export clip**, select a new filename with the same extension, and wait for the completed message. It reports the actual exported duration so differences are visible.
4. **Cancel** stops processing and removes the temporary export. Existing files and the original video are never overwritten. Choose a different filename to retry.

Export copies the compressed video and audio rather than encoding again. This preserves encoded quality but can include frames around the requested boundaries. It is not an exact-frame cut mode. The first video stream and all audio streams are selected; subtitles and additional video streams are not included. Review the exported clip before using it.

On Windows, saving the completed export uses a same-volume rename that refuses an existing filename. It does not require hard links, which FAT32 and exFAT do not support. FAT32's file-size limit still applies; use a suitable destination for larger exports. Removable-drive and representative-media acceptance remain separate from the automated checks.

## Setup from source

Install Python 3.10 or later, then install the pinned dependency in `requirements.txt` and run `python desktop.py`. Install FFmpeg and ffprobe from a trusted build linked by https://ffmpeg.org/download.html. Both commands must be on PATH, or in a `tools` folder beside `desktop.py`. On Windows their names are `ffmpeg.exe` and `ffprobe.exe`.

If preview is unavailable, the codec may not be supported by Qt on that machine. Entered times can still be exported by FFmpeg. Errors are displayed in the bottom status area, without changing the source file.

## Windows packaging checklist

A maintainer should build on Windows with Python 3.12 and Inno Setup 6. Supply a compatible FFmpeg build in `tools`, including both executables, complete license notices as `tools/LICENSE.txt`, and any required source/source-offer materials for that exact distribution. The script does not download or silently accept an FFmpeg distribution on your behalf.

Run `packaging/build-windows.ps1`. It runs verification, builds a directory-based application, includes local FFmpeg files and Qt license files, and invokes the per-user installer compiler. It stops when a prerequisite or test fails. It does not request admin access, purchase a signing certificate or claim the installer is signed.

Before releasing: install/uninstall on a clean Windows machine, test the actual bundled executables and codecs, use representative large files, verify playback and audio/video timing, try cancelling a slow export and a read-only destination, and verify the redistributable dependency notices. Automated runner tests now cover installation, launch, uninstall, source-level export/cancellation and a 553 MB generated MP4. Clean consumer Windows desktop and representative-media acceptance remain pending.
