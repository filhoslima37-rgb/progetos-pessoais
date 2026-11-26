# PyInstaller spec for the standalone Windows demo.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH)
datas = [(str(ROOT / name), ".") for name in (
    "app.py", "auth.py", "database.py", "services.py",
    "relatorios.py", "metas.py",
)]
binaries = []
hiddenimports = []
package_datas, package_binaries, package_hiddenimports = collect_all("streamlit")
datas += package_datas
binaries += package_binaries
hiddenimports += package_hiddenimports

a = Analysis(
    [str(ROOT / "launcher_demo.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="FinanceiroDemo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
