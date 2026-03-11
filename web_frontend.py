"""
AI财务分析智能助手 - 简化版Web界面
直接使用现有的FastAPI应用
"""
import os
import sys

# 设置路径
workspace_path = "/workspace/projects"
sys.path.insert(0, workspace_path)
sys.path.insert(0, os.path.join(workspace_path, "src"))
os.environ["COZE_WORKSPACE_PATH"] = workspace_path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from main import service
from coze_coding_utils.runtime_ctx.context import new_context
import json

app = FastAPI()

# 挂载静态文件
static_dir = os.path.join(workspace_path, "web", "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# 前端页面路由
@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    index_path = os.path.join(workspace_path, "web", "templates", "index.html")
    with open(index_path, 'r', encoding='utf-8') as f:
        return f.read()

# API路由 - 对话
@app.post("/api/chat")
async def chat(request: Request):
    """聊天API"""
    try:
        body = await request.json()
        message = body.get('message', '')
        session_id = body.get('session_id')
        
        if not message:
            return {"error": "消息不能为空"}
        
        # 创建上下文
        ctx = new_context(method="chat", headers=request.headers)
        thread_id = session_id or ctx.run_id
        
        # 调用Agent
        from agents.agent import build_agent
        from langchain_core.messages import HumanMessage
        
        agent = build_agent(ctx=ctx)
        config = {'configurable': {'thread_id': thread_id}}
        
        result = await agent.ainvoke(
            {'messages': [HumanMessage(content=message)]},
            config=config,
            context=ctx
        )
        
        # 提取回复
        ai_message = result['messages'][-1]
        content = ai_message.content
        
        # 处理不同类型的content
        if isinstance(content, str):
            response = content
        elif isinstance(content, list):
            if content and isinstance(content[0], str):
                response = " ".join(content)
            else:
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                response = " ".join(text_parts)
        else:
            response = str(content)
        
        return {
            "session_id": thread_id,
            "response": response
        }
        
    except Exception as e:
        import traceback
        return {"error": str(e), "detail": traceback.format_exc()}

# API路由 - 流式对话
@app.post("/api/chat/stream")
async def chat_stream(request: Request):
    """流式聊天API"""
    from fastapi.responses import StreamingResponse
    
    async def generate():
        try:
            body = await request.json()
            message = body.get('message', '')
            session_id = body.get('session_id')
            
            # 创建上下文
            ctx = new_context(method="chat_stream", headers=request.headers)
            thread_id = session_id or ctx.run_id
            
            # 发送会话ID
            yield f"data: {json.dumps({'type': 'session', 'session_id': thread_id})}\n\n"
            
            # 调用Agent
            from agents.agent import build_agent
            from langchain_core.messages import HumanMessage
            
            agent = build_agent(ctx=ctx)
            config = {'configurable': {'thread_id': thread_id}}
            
            full_response = ""
            async for chunk in agent.astream(
                {'messages': [HumanMessage(content=message)]},
                config=config,
                context=ctx
            ):
                if 'messages' in chunk:
                    for msg in chunk['messages']:
                        if hasattr(msg, 'content') and msg.type == 'ai':
                            content = msg.content
                            if isinstance(content, str):
                                text = content
                            elif isinstance(content, list):
                                if content and isinstance(content[0], str):
                                    text = " ".join(content)
                                else:
                                    text_parts = []
                                    for item in content:
                                        if isinstance(item, dict) and item.get("type") == "text":
                                            text_parts.append(item.get("text", ""))
                                    text = " ".join(text_parts)
                            else:
                                text = str(content)
                            
                            if text and text != full_response:
                                new_content = text[len(full_response):]
                                full_response = text
                                yield f"data: {json.dumps({'type': 'chunk', 'content': new_content})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            
        except Exception as e:
            import traceback
            yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'detail': traceback.format_exc()})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    port = int(os.getenv('PORT', 5000))
    print(f"Starting AI财务分析助手 on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
