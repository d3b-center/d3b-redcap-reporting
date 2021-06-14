# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(['since_last_visit.py'],
             pathex=[],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='REDCap_Subject_Last_Seen',
          debug=False,
          bootloader_ignore_signals=False,
          strip=True,
          upx=False,
          console=False)
app = BUNDLE(exe,
             a.binaries,
             a.zipfiles,
             a.datas,
             name='REDCap_Subject_Last_Seen.app',
             icon=None,
             bundle_identifier=None)
