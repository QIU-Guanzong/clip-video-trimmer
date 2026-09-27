# Clip — a small Python video trimmer

A small Python core prepared for the Windows video-trimmer brief, Freelancer project 40734232. The trimming proof is now accompanied by a native PySide6 interface. The source has been exercised on macOS and a Windows Server 2022 runner. An unsigned internal installer preview was built and passed automated installation, launch and uninstall checks; client acceptance and final redistribution review are still pending.

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

Seven native Qt interaction tests passed on macOS and Windows via `python test_desktop.py`, including an actual FFmpeg export, active cancellation, a destination created during export, invalid-range controls, missing-tool messaging and invalid-file recovery. Playback was also exercised in the real native window and the rendered video checked visually. Normal and compact layouts were inspected; the UI adds no decorative animation. Qt widget-only screenshots omit the GPU-backed video surface; the independent native-window capture includes it.

`packaging/build-windows.ps1` and `packaging/clip.iss` build a Windows PyInstaller + Inno Setup package. [Windows run 36294393850](https://github.com/QIU-Guanzong/clip-video-trimmer/actions/runs/36294393850) verified source `7869852a66a8c2fcdf42b171585ca81a001d0d48`: five core tests, four keyframe tests, seven native interaction tests, a 552,891,936-byte synthetic-file export/cancel exercise, and installer install/launch/uninstall. This is runner evidence, not human acceptance across Windows desktops. No signing certificate was purchased; the binary remains an internal draft. The script requires a supplied FFmpeg build and notices and stops if prerequisites/tests fail. See [USER_GUIDE.md](USER_GUIDE.md) and [THIRD_PARTY.md](THIRD_PARTY.md).

Use **Align to keyframes** to review enclosing cut boundaries before export. The scan is bounded around each marker and can be cancelled; a range with no nearby keyframe is rejected rather than guessed. Not implemented: frame-exact re-encoding, multi-cut joining, additional video tracks or subtitle copying. Stream-copy cuts can differ from entered times; the output duration is displayed. This is development evidence for the brief, not a claim that its full Windows acceptance criteria have passed.

Developed with AI assistance and checked against real FFmpeg output. No prior Windows client delivery is claimed.

## License

The Python sample is offered under the MIT License. Copyright (c) 2026 QIU-Guanzong. Permission is granted, free of charge, to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies, subject to including this notice. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND. FFmpeg and any future GUI or packaging components retain their own licenses.

## Verification scope

The Windows large-file exercise exported the generated 553 MB clip in 0.906 seconds with a largest event-loop gap of 0.016 seconds on that runner. These numbers are observations for that synthetic fixture, not performance guarantees. Tests assert compressed audio/video preservation on the small fixture; perceptual lip sync and diverse real-media compatibility still need acceptance checks. Original per-step reports retain their own scope, and the core report's legacy `windows_installer_verified: false` / `large_files_verified: false` fields do not incorporate the separate successful installer and large-file stages.
