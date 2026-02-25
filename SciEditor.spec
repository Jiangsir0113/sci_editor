# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['sci_editor.rules.abbreviations', 'sci_editor.rules.affiliations', 'sci_editor.rules.authors', 'sci_editor.rules.body', 'sci_editor.rules.ci_format', 'sci_editor.rules.corresponding', 'sci_editor.rules.funding', 'sci_editor.rules.headings', 'sci_editor.rules.keywords', 'sci_editor.rules.references', 'sci_editor.rules.statistics', 'sci_editor.rules.title', 'sci_editor.rules.units']
hiddenimports += collect_submodules('sci_editor.rules')


a = Analysis(
    ['sci_editor\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('sci_editor/rules', 'sci_editor/rules'), ('templates', 'templates')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SciEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
