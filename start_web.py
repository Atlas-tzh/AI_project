"""
AI财务分析智能助手 - Web应用启动脚本
"""
import os
import sys

# 设置路径（必须在其他导入之前）
workspace_path = "/workspace/projects"
sys.path.insert(0, workspace_path)
sys.path.insert(0, os.path.join(workspace_path, "src"))
os.environ["COZE_WORKSPACE_PATH"] = workspace_path

# 导入Flask应用
from web.app import app

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    print(f"Starting AI财务分析助手 on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True, use_reloader=False)
