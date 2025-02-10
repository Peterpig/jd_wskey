@echo off

REM 如果虚拟环境已存在，就不重新创建
if not exist venv (
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)

REM 清理旧的构建文件但保留缓存
rmdir /s /q dist
rmdir /s /q "build\JD账户管理器"

REM 运行打包
python build.py
deactivate