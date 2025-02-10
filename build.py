import os
import platform
import shutil

import PyInstaller.__main__


def build_application():
    # 基础配置
    app_name = "JD助手"
    main_script = "QT_jd.py"

    # 通用打包参数
    common_args = [
        main_script,
        "-F",
        "--name=" + app_name,
        "--noconfirm",  # 覆盖输出目录
        "--clean",  # 清理临时文件
        "--windowed",  # GUI模式
        "--add-data=auto_set_jd_cookie.py:.",  # 添加依赖文件
    ]

    # 根据操作系统添加特定参数
    system = platform.system()
    if system == "Windows":
        # Windows特定配置
        PyInstaller.__main__.run(common_args)
        print("Windows版本打包完成")

    elif system == "Darwin":  # macOS
        # macOS特定配置
        PyInstaller.__main__.run(common_args)
        print("macOS版本打包完成")

    # 清理打包后的临时文件
    if os.path.exists("build"):
        shutil.rmtree("build")

    print(f"打包完成！输出目录: dist/{app_name}")


if __name__ == "__main__":
    build_application()
