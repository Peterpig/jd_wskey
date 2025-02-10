#!/bin/bash

# 如果虚拟环境已存在，就不重新创建
if [ ! -d "venv" ]; then
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# 清理旧的构建文件但保留缓存
rm -rf dist/
rm -rf build/JD账户管理器/

# 运行打包
python build.py
deactivate