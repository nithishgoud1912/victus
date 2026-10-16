# Folder bundle only. Build from the isolated pinned packaging environment.
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

root = Path(SPECPATH).resolve().parents[1]
staging = root / 'build' / 'windows-staging'
if not (staging / 'dashboard' / 'index.html').is_file():
    raise RuntimeError('Build and stage dashboard before freezing')

datas = [(str(staging / 'dashboard'), 'dashboard'),
         (str(root / 'backend/victus/storage/sql'), 'victus/storage/sql'),
         # MCP's reviewed source pin remains independently inspectable when frozen.
         (str(root / 'backend/victus/adapters/mcp/reference_server.py'), 'victus/adapters/mcp')]
for distribution in ('victus-assistant', 'langgraph', 'langgraph-checkpoint',
                     'langgraph-checkpoint-sqlite', 'openwakeword', 'numpy',
                     'onnxruntime', 'scipy', 'scikit-learn'):
    datas += copy_metadata(distribution)
for package in ('faster_whisper', 'sounddevice'):
    datas += collect_data_files(package)
hidden = collect_submodules('victus') + collect_submodules('langgraph')
hidden += ['win32api', 'win32job', 'win32cred', 'win32com.client', 'uvicorn.logging',
           'uvicorn.loops.auto', 'uvicorn.protocols.http.auto', 'uvicorn.lifespan.on',
           'faster_whisper', 'sounddevice', 'openwakeword.model']
a = Analysis([str(root / 'packaging/windows/entry.py')], pathex=[str(root / 'backend')],
             binaries=[], datas=datas, hiddenimports=hidden,
             excludes=['pytest', 'ruff', 'torch', 'tensorflow', 'tkinter', 'matplotlib',
                       'notebook', 'IPython'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Victus', debug=False,
          bootloader_ignore_signals=False, strip=False, upx=False, console=True,
          icon=str(root / 'packaging/windows/victus.ico'),
          version=str(root / 'packaging/windows/version-info.txt'),
          manifest=str(root / 'packaging/windows/app.manifest'), uac_admin=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Victus')
