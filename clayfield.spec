# PyInstaller one-directory Linux bundle. Build with: python -m PyInstaller clayfield.spec
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ["main.py"],
    pathex=["src"],
    datas=collect_data_files("clayfield"),
    hiddenimports=["OpenGL.platform.glx", "OpenGL.platform.egl"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="clayfield", console=True)
coll = COLLECT(exe, a.binaries, a.datas, name="clayfield")
