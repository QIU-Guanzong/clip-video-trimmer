# Clip — a small Python video trimmer

A small Python core prepared for the Windows video-trimmer brief, Freelancer project 40734232. The trimming proof is now accompanied by a native PySide6 interface. The source has been exercised on macOS; Windows delivery is still in progress. No tested Windows installer is available yet.

## Run

Use Python 3.10+ with `ffmpeg` and `ffprobe` on PATH. The verification needs an FFmpeg build with libx264 and AAC support. No Python packages are needed.

```sh
python verify.py
```

The script generates an eight-second H.264/AAC test clip with B-frames, then cuts at both keyframe-aligned and intermediate positions. No client media, credentials or network calls are used. Temporary media is removed after the run; results are written to `verification.json`.

Five tests passed on macOS with FFmpeg 9.0.2:
- Both cuts retain the 320x180 frame dimensions.
- Every decoded output video frame matches a contiguous sequence from the source (frame hashes).
- Compressed audio packets match a contiguous source sequence (SHA-256 hashes).
- The synthetic fixture has matching audio/video start timestamps and under 70 ms of end-duration difference.
- Invalid ranges, replacing the source and overwriting an existing output are rejected.

These checks establish data preservation for this generated fixture, not universal audio-sync accuracy. The sine track does not test perceptual lip sync. The two requested two-second cuts each produce 2.08 seconds of video; stream copying does **not** guarantee exact cut positions. See [FFmpeg's seeking documentation](https://ffmpeg.org/ffmpeg.html#Main-options): seeking with stream copy preserves data around seek points.

## Desktop interface and Windows delivery

Run `python desktop.py` after installing `requirements.txt`. The interface supports preview/play/pause, in/out markers, typed time entry, seek controls, asynchronous export, cancellation, invalid-file recovery and a non-overwriting output flow. It checks output dimensions and displays the exported duration. The source is never modified; cancelled and failed export temporary files are removed.

Six native Qt interaction tests passed on macOS via `python test_desktop.py`, including an actual FFmpeg export, active cancellation, a destination created during export, invalid-range controls, missing-tool messaging and invalid-file recovery. Playback was also exercised in the real native window and the rendered video checked visually. Normal and compact layouts were inspected; the UI adds no decorative animation. Qt widget-only screenshots omit the GPU-backed video surface; the independent native-window capture includes it.

`packaging/build-windows.ps1` and `packaging/clip.iss` describe a Windows PyInstaller + Inno Setup build. The installer, bundled dependencies, large-file behavior and Windows keyboard/media behavior remain unverified. The script requires a supplied FFmpeg build and notices and stops if prerequisites/tests fail. See [USER_GUIDE.md](USER_GUIDE.md) and [THIRD_PARTY.md](THIRD_PARTY.md).

Not yet implemented: showing snapped keyframe boundaries before export, frame-exact re-encoding, multi-cut joining, additional video tracks or subtitle copying. Stream-copy cuts can differ from entered times; the output duration is displayed. This is development evidence for the brief, not a claim that its full Windows acceptance criteria have passed.

Developed with AI assistance and checked against real FFmpeg output. No prior Windows client delivery is claimed.

## License

The Python sample is offered under the MIT License. Copyright (c) 2026 QIU-Guanzong. Permission is granted, free of charge, to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies, subject to including this notice. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. FFmpeg and any future GUI or packaging components retain their own licenses.
