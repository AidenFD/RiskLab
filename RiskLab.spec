# Build on the target OS; PyInstaller cannot verify Windows from a Linux host.
from pathlib import Path
root = Path(SPECPATH)
a = Analysis([str(root/'scripts'/'launch.py')],pathex=[str(root)],
             binaries=[],datas=[(str(root/'risklab'/'resources'),'risklab/resources')],
             hiddenimports=[],hookspath=[],hooksconfig={},runtime_hooks=[],
             excludes=['matplotlib','pandas','scipy','IPython','tkinter',
                       'PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineQuick',
                       'PySide6.QtPdf','PySide6.QtPdfWidgets','PySide6.QtQml','PySide6.QtQuick'],noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,[],exclude_binaries=True,name='RiskLab',debug=False,
          bootloader_ignore_signals=False,strip=False,upx=False,console=False)
coll = COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='RiskLab')
