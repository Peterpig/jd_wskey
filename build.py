import os
import platform
import sys

from PyInstaller.__main__ import run

# 获取当前操作系统
system = platform.system().lower()

# 基础配置
app_name = "JD账户管理器"
main_script = "QT_jd.py"
icon_file = os.path.join("icons", "icon.ico" if system == "windows" else "icon.icns")

# 公共参数
common_options = [
    main_script,
    "--noconfirm",
    "--clean",
    "--name",
    app_name,
    "--hidden-import",
    "PyQt6.QtWebEngineCore",
    "--hidden-import",
    "PyQt6.QtWebEngineWidgets",
    "--collect-data",
    "PyQt6.QtWebEngineCore",
    "--add-data",
    f"qinglong.py{os.pathsep}.",
]

# 如果图标文件存在，添加图标选项
if os.path.exists(icon_file):
    common_options.extend(["--icon", icon_file])

# macOS特定配置
if system == "darwin":
    # 获取PyQt6安装路径
    import PyQt6
    qt_path = os.path.dirname(PyQt6.__file__)

    # 添加必要的框架和资源
    common_options.extend([
        '--hidden-import', 'PyQt6.QtWebEngineCore',
        '--hidden-import', 'PyQt6.QtWebEngineWidgets',
        '--hidden-import', 'PyQt6.QtNetwork',
        '--collect-data', 'PyQt6.QtWebEngineCore',
        '--collect-all', 'PyQt6.QtWebEngineCore',
    ])

    # 添加WebEngine进程
    webengine_process = os.path.join(qt_path, 'Qt6', 'lib', 'QtWebEngineCore')
    if os.path.exists(webengine_process):
        common_options.extend(['--add-binary', f'{webengine_process}:PyQt6/Qt6/lib/QtWebEngineCore'])

# 根据操作系统添加特定选项
if system == "windows":
    options = [
        *common_options,
        "--windowed",  # Windows下不显示控制台
        "--add-binary",
        f'{os.path.join(sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__)), "venv/Lib/site-packages/PyQt6/Qt6/bin/QtWebEngineProcess.exe")};PyQt6/Qt6/bin',
    ]
elif system == "darwin":  # macOS
    options = [
        *common_options,
        "--windowed",
        "--codesign-identity",
        "-",  # 使用临时签名
        "--osx-bundle-identifier",
        "com.jd.account.manager",
    ]
else:  # Linux
    options = [
        *common_options,
        "--onefile",
    ]

# 运行打包命令
run(options)
