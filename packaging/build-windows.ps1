# Run from an existing Windows Python 3.12 environment with Inno Setup 6.
# Supply reviewed FFmpeg executables and their complete notices in tools/.
$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectRoot
if ($env:OS -ne 'Windows_NT') { throw 'Build on Windows; cross-compiling is not supported.' }
foreach ($RequiredFile in @('tools/ffmpeg.exe', 'tools/ffprobe.exe', 'tools/LICENSE.txt')) {
    if (!(Test-Path $RequiredFile)) { throw "Missing $RequiredFile. Read USER_GUIDE.md before packaging." }
}
$IsccPath = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6/ISCC.exe'
if (!(Test-Path $IsccPath)) { throw 'Inno Setup 6 compiler was not found.' }
$env:PATH = (Join-Path $ProjectRoot 'tools') + ';' + $env:PATH
python -m pip install -r requirements-build.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
python verify.py
if ($LASTEXITCODE -ne 0) { throw 'FFmpeg verification failed.' }
python test_keyframes.py
if ($LASTEXITCODE -ne 0) { throw 'Keyframe verification failed.' }
python test_desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Desktop verification failed.' }
python verify_large_file.py
if ($LASTEXITCODE -ne 0) { throw 'Large-file verification failed.' }
python -m PyInstaller --clean --noconfirm --windowed --onedir --name Clip desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Application build failed.' }
Copy-Item -Recurse tools dist/Clip/tools
Copy-Item USER_GUIDE.md,THIRD_PARTY.md dist/Clip/
# Keep the installed distribution's license texts alongside the dynamic Qt DLLs.
python -c "import importlib.metadata,pathlib,shutil; target=pathlib.Path('dist/Clip/licenses'); target.mkdir(exist_ok=True); names=('PySide6','PySide6_Addons','PySide6_Essentials','shiboken6'); [(target/n).mkdir(exist_ok=True) for n in names]; [(shutil.copyfile(d.locate_file(p),target/n/pathlib.Path(str(p)).name)) for n in names for d in [importlib.metadata.distribution(n)] for p in (d.files or []) if 'licenses/' in str(p) and d.locate_file(p).is_file()]"
if ($LASTEXITCODE -ne 0) { throw 'License collection failed.' }
& $IsccPath packaging/clip.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
Get-FileHash dist/installer/Clip-Setup-0.1.0.exe -Algorithm SHA256
