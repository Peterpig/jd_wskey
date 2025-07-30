# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['QT_jd.py'],
    pathex=[],
    binaries=[('.venv/lib/python3.8/site-packages/PySide6/Qt/lib/QtWebEngineCore.framework/Helpers/QtWebEngineProcess.app/Contents/MacOS/QtWebEngineProcess', '.')],
    datas=[('utils/jd_new_logo.png', 'utils'), ('utils/jd.png', 'utils')],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtNetwork',
        'asyncio',
        'concurrent.futures',
        'logging',
        'json',
        're',
        'datetime',
        'platform',
        'os',
        'sys',
        'traceback'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'numpy.testing',
        'IPython',
        'jupyter',
        'notebook',
        'sphinx',
        'pydoc',
        'doctest',
        'unittest',
        'test',
        'tests'
    ],
    noarchive=False,
    optimize=2,  # 启用优化
)
pyz = PYZ(a.pure, cipher=None)  # 禁用加密以提高启动速度

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='QT_jd',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,  # 启用strip以减少文件大小
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe,
    name='QT_jd.app',
    icon='icon.icns',
    bundle_identifier='com.jd.app',
    info_plist={
        'CFBundleDisplayName': 'JD应用',
        'CFBundleName': 'QT_jd',
        'CFBundleIdentifier': 'com.jd.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
        'LSMinimumSystemVersion': '10.15.0',
        'NSRequiresAquaSystemAppearance': False,
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True
        },
        'LSEnvironment': {
            'QTWEBENGINE_CHROMIUM_FLAGS': '--disable-logging --disable-gpu-sandbox --disable-dev-shm-usage',
            'QT_LOGGING_RULES': 'qt.webenginecontext.debug=false',
            'QT_AUTO_SCREEN_SCALE_FACTOR': '1',
            'QT_SCALE_FACTOR': '1'
        }
    }
)
