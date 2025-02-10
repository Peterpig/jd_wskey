import os
import platform
import sys

from PyInstaller.__main__ import run

# 获取当前操作系统
system = platform.system().lower()

# 基础配置
app_name = "JD账户管理器"
main_script = "QT_jd.py"

# 公共参数
common_options = [
    main_script,
    "--noconfirm",
    "--clean",
    "--name",
    app_name,
    # 必要的导入
    "--hidden-import",
    "PyQt6.QtWebEngineCore",
    "--hidden-import",
    "PyQt6.QtWebEngineWidgets",
    "--hidden-import",
    "PyQt6.QtNetwork",
    "--hidden-import",
    "PyQt6.QtPrintSupport",
    "--hidden-import",
    "PyQt6.QtQml",
    "--hidden-import",
    "PyQt6.QtQuick",
    "--hidden-import",
    "PyQt6.QtQuickWidgets",
    "--hidden-import",
    "PyQt6.QtPositioning",
    # 收集所有Qt相关数据
    "--collect-all",
    "PyQt6",
    # 数据文件
    "--add-data",
    f"qinglong.py{os.pathsep}.",
    # 添加图标文件
    "--add-data",
    f"utils{os.pathsep}.",  # 确保图标文件被打包
]

# macOS特定配置
if system == "darwin":
    import PyQt6

    qt_path = os.path.dirname(PyQt6.__file__)
    qt_framework_path = os.path.join(qt_path, "Qt6")

    # WebEngine进程
    webengine_process = os.path.join(
        qt_framework_path,
        "QtWebEngineCore.framework",
        "Helpers",
        "QtWebEngineProcess.app",
        "Contents",
        "MacOS",
        "QtWebEngineProcess",
    )

    if os.path.exists(webengine_process):
        target_path = os.path.join(
            "PyQt6",
            "Qt6",
            "lib",
            "QtWebEngineCore.framework",
            "Helpers",
            "QtWebEngineProcess.app",
            "Contents",
            "MacOS",
        )
        common_options.extend(["--add-binary", f"{webengine_process}:{target_path}"])

    # Resources
    resources_path = os.path.join(
        qt_framework_path, "QtWebEngineCore.framework", "Resources"
    )
    if os.path.exists(resources_path):
        target_resources = os.path.join(
            "PyQt6", "Qt6", "lib", "QtWebEngineCore.framework", "Resources"
        )
        common_options.extend(["--add-data", f"{resources_path}:{target_resources}"])

# 系统特定选项
if system == "windows":
    options = [
        *common_options,
        "--windowed",
        "--add-binary",
        f'{os.path.join(sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__)), "venv/Lib/site-packages/PyQt6/Qt6/bin/QtWebEngineProcess.exe")};PyQt6/Qt6/bin',
    ]
elif system == "darwin":
    options = [
        *common_options,
        "--windowed",
        "--codesign-identity",
        "-",
        "--osx-bundle-identifier",
        "com.jd.account.manager",
    ]
else:
    options = [
        *common_options,
        "--onefile",
    ]

# 运行打包命令
run(options)
