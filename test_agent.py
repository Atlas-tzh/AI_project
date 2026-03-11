"""
测试Agent是否正常工作
"""
import os
import sys

# 设置路径
workspace_path = "/workspace/projects"
sys.path.insert(0, workspace_path)
sys.path.insert(0, os.path.join(workspace_path, "src"))
os.environ["COZE_WORKSPACE_PATH"] = workspace_path

# 导入必要的模块
from agents.agent import build_agent
from coze_coding_utils.runtime_ctx.context import new_context
from langchain_core.messages import HumanMessage

def test_agent():
    """测试Agent基本功能"""
    print("开始测试Agent...")
    
    try:
        # 创建上下文
        ctx = new_context(method="test")
        
        # 构建Agent
        print("正在构建Agent...")
        agent = build_agent(ctx=ctx)
        print("✓ Agent构建成功")
        
        # 测试简单对话
        print("\n测试对话功能...")
        test_message = "你好，请介绍一下你自己"
        print(f"用户: {test_message}")
        
        # 调用Agent
        config = {'configurable': {'thread_id': 'test-session'}}
        result = agent.invoke(
            {'messages': [HumanMessage(content=test_message)]},
            config=config
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
        
        print(f"助手: {response[:200]}...")
        print("✓ 对话功能正常")
        
        print("\n✅ 所有测试通过！Agent工作正常")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_agent()
