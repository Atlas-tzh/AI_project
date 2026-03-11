#!/bin/bash

# 启动AI财务分析助手Web应用

export PYTHONPATH=/workspace/projects/src:$PYTHONPATH
export COZE_WORKSPACE_PATH=/workspace/projects

cd /workspace/projects/web

echo "Starting AI财务分析助手 on http://0.0.0.0:5000"
python app.py
