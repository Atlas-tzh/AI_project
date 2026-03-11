// 全局状态
let currentSessionId = null;
let isStreaming = false;

// DOM元素
const chatContainer = document.getElementById('chatContainer');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const newChatBtn = document.getElementById('newChatBtn');
const sessionList = document.getElementById('sessionList');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 自动调整输入框高度
    messageInput.addEventListener('input', autoResize);
    
    // 加载会话列表
    loadSessions();
    
    // 配置markdown渲染
    marked.setOptions({
        highlight: function(code, lang) {
            if (lang && hljs.getLanguage(lang)) {
                return hljs.highlight(code, { language: lang }).value;
            }
            return hljs.highlightAuto(code).value;
        },
        breaks: true,
        gfm: true
    });
});

// 自动调整输入框高度
function autoResize() {
    messageInput.style.height = 'auto';
    messageInput.style.height = Math.min(messageInput.scrollHeight, 150) + 'px';
}

// 处理键盘事件
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// 发送消息
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || isStreaming) return;
    
    // 清空输入框
    messageInput.value = '';
    autoResize();
    
    // 显示用户消息
    appendMessage('user', message);
    
    // 显示加载状态
    const loadingDiv = showLoading();
    
    try {
        isStreaming = true;
        sendBtn.disabled = true;
        
        // 使用流式API
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: message,
                session_id: currentSessionId
            })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantMessage = null;
        let fullContent = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.type === 'session') {
                            currentSessionId = data.session_id;
                            loadSessions(); // 刷新会话列表
                        } else if (data.type === 'chunk') {
                            // 移除加载动画
                            if (loadingDiv.parentNode) {
                                loadingDiv.remove();
                            }
                            
                            // 创建或更新助手消息
                            if (!assistantMessage) {
                                assistantMessage = createMessageElement('assistant');
                                chatContainer.appendChild(assistantMessage);
                            }
                            
                            fullContent += data.content;
                            updateMessageContent(assistantMessage, fullContent);
                            scrollToBottom();
                        } else if (data.type === 'done') {
                            // 消息完成
                            loadSessions(); // 刷新会话列表
                        } else if (data.type === 'error') {
                            showError(data.error);
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }
        
    } catch (error) {
        showError('发送失败: ' + error.message);
    } finally {
        isStreaming = false;
        sendBtn.disabled = false;
        
        // 移除加载动画（如果还在）
        if (loadingDiv.parentNode) {
            loadingDiv.remove();
        }
    }
}

// 添加消息到聊天容器
function appendMessage(role, content) {
    const messageDiv = createMessageElement(role, content);
    chatContainer.appendChild(messageDiv);
    scrollToBottom();
    return messageDiv;
}

// 创建消息元素
function createMessageElement(role) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message message-${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    messageDiv.appendChild(contentDiv);
    return messageDiv;
}

// 更新消息内容
function updateMessageContent(messageElement, content) {
    const contentDiv = messageElement.querySelector('.message-content');
    if (contentDiv) {
        // 渲染markdown
        contentDiv.innerHTML = marked.parse(content);
        // 高亮代码块
        contentDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
        });
    }
}

// 显示加载动画
function showLoading() {
    const loadingDiv = document.createElement('div');
    loadingDiv.className = 'message message-assistant';
    loadingDiv.innerHTML = `
        <div class="message-content">
            <div class="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    chatContainer.appendChild(loadingDiv);
    scrollToBottom();
    return loadingDiv;
}

// 显示错误消息
function showError(error) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = '❌ ' + error;
    chatContainer.appendChild(errorDiv);
    scrollToBottom();
}

// 滚动到底部
function scrollToBottom() {
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// 加载会话列表
async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const data = await response.json();
        
        if (data.sessions && data.sessions.length > 0) {
            sessionList.innerHTML = '';
            
            data.sessions.forEach(session => {
                const sessionDiv = document.createElement('div');
                sessionDiv.className = `session-item ${session.session_id === currentSessionId ? 'active' : ''}`;
                
                // 获取最后一条消息作为预览
                const preview = `对话 (${session.message_count}条消息)`;
                
                sessionDiv.innerHTML = `
                    <div class="session-item-header">
                        <span class="session-time">${formatTime(session.created_at)}</span>
                    </div>
                    <div class="session-preview">${preview}</div>
                    <div class="session-actions">
                        <button class="session-action-btn load-btn" onclick="loadSession('${session.session_id}')">加载</button>
                        <button class="session-action-btn delete-btn" onclick="deleteSession('${session.session_id}')">删除</button>
                    </div>
                `;
                
                sessionList.appendChild(sessionDiv);
            });
        } else {
            sessionList.innerHTML = `
                <div class="empty-state">
                    <p>暂无对话历史</p>
                    <p class="hint">开始新的对话吧！</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('加载会话列表失败:', error);
    }
}

// 加载会话
async function loadSession(sessionId) {
    try {
        const response = await fetch(`/api/sessions/${sessionId}`);
        const data = await response.json();
        
        if (data.messages) {
            currentSessionId = sessionId;
            
            // 清空当前聊天
            chatContainer.innerHTML = '';
            
            // 显示历史消息
            data.messages.forEach(msg => {
                if (msg.role === 'user' || msg.role === 'assistant') {
                    const messageDiv = createMessageElement(msg.role);
                    updateMessageContent(messageDiv, msg.content);
                    chatContainer.appendChild(messageDiv);
                }
            });
            
            scrollToBottom();
            loadSessions(); // 刷新列表以更新active状态
        }
    } catch (error) {
        showError('加载会话失败: ' + error.message);
    }
}

// 删除会话
async function deleteSession(sessionId) {
    if (!confirm('确定要删除这个对话吗？')) return;
    
    try {
        await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
        
        if (sessionId === currentSessionId) {
            currentSessionId = null;
            chatContainer.innerHTML = getWelcomeMessage();
        }
        
        loadSessions();
    } catch (error) {
        showError('删除会话失败: ' + error.message);
    }
}

// 新建对话
newChatBtn.addEventListener('click', () => {
    currentSessionId = null;
    chatContainer.innerHTML = getWelcomeMessage();
    loadSessions();
});

// 获取欢迎消息HTML
function getWelcomeMessage() {
    return `
        <div class="welcome-message">
            <div class="welcome-icon">📊</div>
            <h2>欢迎使用AI财务分析助手</h2>
            <p>我可以帮您分析公司财务数据、解读年报内容、对比财务指标等</p>
            <div class="example-questions">
                <p class="example-title">试试这些问题：</p>
                <button class="example-btn" onclick="askExample('腾讯2023年的营收情况如何？')">腾讯2023年的营收情况如何？</button>
                <button class="example-btn" onclick="askExample('对比腾讯和阿里的净利润')">对比腾讯和阿里的净利润</button>
                <button class="example-btn" onclick="askExample('苹果公司的最新财报数据')">苹果公司的最新财报数据</button>
            </div>
        </div>
    `;
}

// 使用示例问题
function askExample(question) {
    messageInput.value = question;
    sendMessage();
}

// 格式化时间
function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    // 1小时内
    if (diff < 3600000) {
        const minutes = Math.floor(diff / 60000);
        return minutes <= 1 ? '刚刚' : `${minutes}分钟前`;
    }
    
    // 今天
    if (date.toDateString() === now.toDateString()) {
        return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    }
    
    // 昨天
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
        return '昨天 ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    }
    
    // 更早
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) + ' ' +
           date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
}
