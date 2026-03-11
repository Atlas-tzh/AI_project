"""
AI财务分析智能助手 - Web应用
提供Web界面支持多轮对话
"""
import os
import sys
import json
import uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from langchain_core.messages import HumanMessage, AIMessage

from agents.agent import build_agent
from coze_coding_utils.runtime_ctx.context import new_context

app = Flask(__name__,
            template_folder='templates',
            static_folder='static')
CORS(app)

# 存储会话数据（生产环境应使用数据库或Redis）
sessions = {}


def get_or_create_session(session_id=None):
    """获取或创建会话"""
    if session_id and session_id in sessions:
        return session_id, sessions[session_id]
    
    # 创建新会话
    new_session_id = str(uuid.uuid4())
    sessions[new_session_id] = {
        'agent': None,
        'config': {'configurable': {'thread_id': new_session_id}},
        'messages': [],
        'created_at': datetime.now().isoformat()
    }
    
    return new_session_id, sessions[new_session_id]


def get_text_content(content):
    """安全提取文本内容"""
    if isinstance(content, str):
        return content
    elif isinstance(content, list):
        if content and isinstance(content[0], str):
            return " ".join(content)
        else:
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return " ".join(text_parts)
    return str(content)


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天API（非流式）"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id')
        
        if not user_message:
            return jsonify({'error': '消息不能为空'}), 400
        
        # 获取或创建会话
        session_id, session_data = get_or_create_session(session_id)
        
        # 构建Agent（延迟初始化）
        if session_data['agent'] is None:
            ctx = new_context(method="chat")
            session_data['agent'] = build_agent(ctx=ctx)
        
        # 添加用户消息
        session_data['messages'].append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.now().isoformat()
        })
        
        # 调用Agent
        agent = session_data['agent']
        config = session_data['config']
        
        # 创建输入消息
        input_messages = [HumanMessage(content=user_message)]
        
        # 调用Agent（非流式）
        result = agent.invoke({'messages': input_messages}, config=config)
        
        # 提取AI回复
        ai_message = result['messages'][-1]
        ai_content = get_text_content(ai_message.content)
        
        # 添加AI消息到历史
        session_data['messages'].append({
            'role': 'assistant',
            'content': ai_content,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({
            'session_id': session_id,
            'response': ai_content,
            'messages': session_data['messages']
        })
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in chat: {error_detail}")
        return jsonify({'error': str(e), 'detail': error_detail}), 500


@app.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """聊天API（流式）"""
    try:
        data = request.json
        user_message = data.get('message', '')
        session_id = data.get('session_id')
        
        if not user_message:
            return jsonify({'error': '消息不能为空'}), 400
        
        def generate():
            try:
                # 获取或创建会话
                session_id, session_data = get_or_create_session(session_id)
                
                # 发送会话ID
                yield f"data: {json.dumps({'type': 'session', 'session_id': session_id})}\n\n"
                
                # 构建Agent（延迟初始化）
                if session_data['agent'] is None:
                    ctx = new_context(method="chat_stream")
                    session_data['agent'] = build_agent(ctx=ctx)
                
                # 添加用户消息
                session_data['messages'].append({
                    'role': 'user',
                    'content': user_message,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 调用Agent
                agent = session_data['agent']
                config = session_data['config']
                
                # 创建输入消息
                input_messages = [HumanMessage(content=user_message)]
                
                # 流式调用Agent
                full_response = ""
                for chunk in agent.stream({'messages': input_messages}, config=config):
                    # 提取消息内容
                    if 'messages' in chunk:
                        for msg in chunk['messages']:
                            if hasattr(msg, 'content') and msg.type == 'ai':
                                content = get_text_content(msg.content)
                                if content and content != full_response:
                                    # 发送增量内容
                                    new_content = content[len(full_response):]
                                    full_response = content
                                    yield f"data: {json.dumps({'type': 'chunk', 'content': new_content})}\n\n"
                
                # 添加AI消息到历史
                session_data['messages'].append({
                    'role': 'assistant',
                    'content': full_response,
                    'timestamp': datetime.now().isoformat()
                })
                
                # 发送完成信号
                yield f"data: {json.dumps({'type': 'done', 'messages': session_data['messages']})}\n\n"
                
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                print(f"Error in stream: {error_detail}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'detail': error_detail})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"Error in chat_stream: {error_detail}")
        return jsonify({'error': str(e), 'detail': error_detail}), 500


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取会话历史"""
    if session_id in sessions:
        return jsonify({
            'session_id': session_id,
            'messages': sessions[session_id]['messages'],
            'created_at': sessions[session_id]['created_at']
        })
    return jsonify({'error': '会话不存在'}), 404


@app.route('/api/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """删除会话"""
    if session_id in sessions:
        del sessions[session_id]
        return jsonify({'success': True})
    return jsonify({'error': '会话不存在'}), 404


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    """列出所有会话"""
    session_list = []
    for sid, sdata in sessions.items():
        session_list.append({
            'session_id': sid,
            'created_at': sdata['created_at'],
            'message_count': len(sdata['messages'])
        })
    return jsonify({'sessions': session_list})


if __name__ == '__main__':
    # 启动Flask应用
    port = int(os.getenv('PORT', 5000))
    print(f"Starting AI财务分析助手 on http://0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
