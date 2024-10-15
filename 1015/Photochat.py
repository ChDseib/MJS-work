# app.py

from flask import Flask, render_template, request, jsonify, session
import logging
import os
from dotenv import load_dotenv
from threading import Thread
from flask_cors import CORS
import requests
import json
import uuid

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)  # 启用 CORS
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # 从环境变量加载 SECRET_KEY

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# 存储所有消息，每条消息包含唯一的 id、文本内容和角色
# 修改为按 conversation_id 存储
messages = {}
next_id = 1  # 用于分配唯一的消息 ID
message_file = '1015/messages.txt'  # 存储消息的文件路径

# 新增环境变量
SPARKAI_APP_ID = os.getenv('SPARKAI_APP_ID')
SPARKAI_AUTH_TOKEN = os.getenv('SPARKAI_AUTH_TOKEN')
SPARKAI_URL = os.getenv('SPARKAI_URL')  # 创建对话的 URL
SPARKAI_RUNS_URL = os.getenv('SPARKAI_RUNS_URL')  # 发送消息的 URL

def load_messages_from_file():
    """
    从文件中加载消息到内存。
    """
    global messages, next_id
    if os.path.exists(message_file):
        with open(message_file, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:
                    parts = line.split('|')
                    if len(parts) == 4:
                        try:
                            conversation_id = parts[0]
                            message_id = int(parts[1])
                            message_text = parts[2]
                            message_role = parts[3]
                            if conversation_id not in messages:
                                messages[conversation_id] = []
                            messages[conversation_id].append({'id': message_id, 'text': message_text, 'role': message_role})
                            if message_id >= next_id:
                                next_id = message_id + 1  # 更新下一个 ID 为最新的
                        except ValueError:
                            continue
        logging.debug(f"Loaded messages from {message_file}")
    else:
        logging.debug(f"No message file found at {message_file}")

def save_messages_to_file():
    """
    将当前消息列表保存到文件。
    """
    with open(message_file, 'w', encoding='utf-8') as file:
        for conv_id, msgs in messages.items():
            for message in msgs:
                file.write(f"{conv_id}|{message['id']}|{message['text']}|{message['role']}\n")
    logging.debug(f"Saved messages to {message_file}")

# 在启动时加载消息
load_messages_from_file()

def create_conversation():
    """
    创建一个新的对话，返回 conversation_id。
    """
    url = SPARKAI_URL  # "https://qianfan.baidubce.com/v2/app/conversation"
    payload = json.dumps({
        "app_id": SPARKAI_APP_ID
    })
    headers = {
        'Content-Type': 'application/json',
        'X-Appbuilder-Authorization': SPARKAI_AUTH_TOKEN
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        conversation_id = data.get("conversation_id")
        logging.debug(f"Created new conversation with ID: {conversation_id}")
        return conversation_id
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to create conversation: {e}")
        return None

def send_query(conversation_id, query, stream=False):
    """
    发送用户消息到 AI，返回 AI 回复的文本。
    """
    url = SPARKAI_RUNS_URL  # "https://qianfan.baidubce.com/v2/app/conversation/runs"
    payload = json.dumps({
        "app_id": SPARKAI_APP_ID,
        "query": query,
        "stream": stream,
        "conversation_id": conversation_id
    })
    headers = {
        'Content-Type': 'application/json',
        'X-Appbuilder-Authorization': SPARKAI_AUTH_TOKEN
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        # 提取 AI 回复的文本
        outputs = data.get("content", [])
        ai_text = ""
        for item in outputs:
            if item.get("content_type") == "text":
                ai_text += item.get("outputs", {}).get("text", "")
        logging.debug(f"AI response: {ai_text}")
        return ai_text
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to send query: {e}")
        return "抱歉，AI 服务不可用。"

@app.before_request
def make_session_permanent():
    """
    确保每个请求都有会话。
    """
    session.permanent = True

@app.route('/')
def index():
    """
    渲染聊天界面。
    如果用户还没有 conversation_id，则创建一个新的。
    """
    if 'conversation_id' not in session:
        conversation_id = create_conversation()
        if not conversation_id:
            return "无法创建对话，请稍后重试。", 500
        session['conversation_id'] = conversation_id
        messages[conversation_id] = []
    return render_template('chat.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    """
    接收用户消息，生成 AI 回复，并保存到消息列表。
    """
    global next_id
    data = request.get_json()
    message_text = data.get('message')
    max_length = data.get('max_length', 500)  # 默认最大字符数为500
    if not message_text:
        logging.debug("No message provided")
        return jsonify({'status': 'error', 'message': 'No message provided'}), 400

    conversation_id = session.get('conversation_id')
    if not conversation_id:
        conversation_id = create_conversation()
        if not conversation_id:
            return jsonify({'status': 'error', 'message': '无法创建对话'}), 500
        session['conversation_id'] = conversation_id
        messages[conversation_id] = []

    # 添加用户消息，确保包含 'role'
    user_message = {'id': next_id, 'text': message_text, 'role': 'user'}
    messages[conversation_id].append(user_message)
    logging.debug(f"Received message: {message_text} with id {next_id} in conversation {conversation_id}")
    next_id += 1
    save_messages_to_file()  # 保存消息到文件

    def handle_ai_response(message_text, max_length, conversation_id):
        """
        处理 AI 回复的函数。
        """
        global next_id
        ai_text = send_query(conversation_id, message_text, stream=False)

        # 根据 max_length 限制 AI 回复的长度
        ai_text = ai_text[:int(max_length)]

        # 添加 AI 回复
        ai_message = {'id': next_id, 'text': ai_text, 'role': 'assistant'}
        messages[conversation_id].append(ai_message)
        logging.debug(f"AI responded: {ai_text} with id {next_id} in conversation {conversation_id}")
        next_id += 1
        save_messages_to_file()  # 保存消息到文件

    # 启动新线程处理 AI 回复
    ai_thread = Thread(target=handle_ai_response, args=(message_text, max_length, conversation_id))
    ai_thread.start()

    return jsonify({'status': 'success', 'user_message': user_message})

@app.route('/delete_message', methods=['POST'])
def delete_message():
    """
    删除指定 ID 的消息。
    """
    data = request.get_json()
    message_id = data.get('id')
    if message_id is None:
        logging.debug("No message ID provided for deletion")
        return jsonify({'status': 'error', 'message': 'No message ID provided'}), 400

    conversation_id = session.get('conversation_id')
    if not conversation_id or conversation_id not in messages:
        return jsonify({'status': 'error', 'message': 'Conversation not found'}), 400

    original_length = len(messages[conversation_id])
    messages[conversation_id] = [msg for msg in messages[conversation_id] if msg['id'] != message_id]
    if len(messages[conversation_id]) < original_length:
        logging.debug(f"Deleted message with id: {message_id} from conversation {conversation_id}")
        save_messages_to_file()  # 保存消息到文件
        return jsonify({'status': 'success'})
    else:
        logging.debug(f"Message ID {message_id} not found in conversation {conversation_id}")
        return jsonify({'status': 'error', 'message': 'Message ID not found'}), 400

@app.route('/clear_messages', methods=['POST'])
def clear_messages():
    """
    清除所有消息并创建新的对话。
    """
    global next_id
    # 创建新的对话
    conversation_id = create_conversation()
    if not conversation_id:
        return jsonify({'status': 'error', 'message': '无法创建新对话'}), 500

    # 更新会话 ID 并清空消息
    session['conversation_id'] = conversation_id
    messages[conversation_id] = []
    logging.debug(f"Cleared all messages and created new conversation {conversation_id}")
    save_messages_to_file()  # 保存消息到文件

    return jsonify({'status': 'success', 'conversation_id': conversation_id})

@app.route('/get_messages', methods=['GET'])
def get_messages():
    """
    获取所有消息。
    """
    conversation_id = session.get('conversation_id')
    if not conversation_id or conversation_id not in messages:
        return jsonify({'messages': []})
    return jsonify({'messages': messages[conversation_id]})

@app.route('/api/answer', methods=['POST'])
def api_answer():
    """
    处理 API 请求，接收问题并返回 AI 回复。
    """
    global next_id
    data = request.get_json()
    question = data.get('question')
    max_length = data.get('max_length', 500)  # 默认最大字符数为500

    if not question:
        return jsonify({'status': 'error', 'message': 'No question provided'}), 400

    logging.debug(f"API received question: {question} with max_length: {max_length}")

    conversation_id = session.get('conversation_id')
    if not conversation_id:
        conversation_id = create_conversation()
        if not conversation_id:
            return jsonify({'status': 'error', 'message': '无法创建对话'}), 500
        session['conversation_id'] = conversation_id
        messages[conversation_id] = []

    # 添加用户消息到消息列表
    user_message = {'id': next_id, 'text': question, 'role': 'user'}
    messages[conversation_id].append(user_message)
    logging.debug(f"Added user message: {user_message} to conversation {conversation_id}")
    next_id += 1
    save_messages_to_file()

    # 处理 AI 回复
    ai_text = send_query(conversation_id, question, stream=False)

    # 根据 max_length 限制 AI 回复的长度
    ai_text = ai_text[:int(max_length)]

    # 添加 AI 回复到消息列表
    ai_message = {'id': next_id, 'text': ai_text, 'role': 'assistant'}
    messages[conversation_id].append(ai_message)
    logging.debug(f"API AI responded: {ai_text} with id {next_id} in conversation {conversation_id}")
    next_id += 1
    save_messages_to_file()

    return jsonify({'status': 'success', 'answer': ai_text})

@app.route('/create_conversation', methods=['POST'])
def create_new_conversation():
    """
    创建新的对话，切换到新的 conversation_id，并清空当前消息。
    """
    conversation_id = create_conversation()
    if not conversation_id:
        return jsonify({'status': 'error', 'message': '无法创建新对话'}), 500

    session['conversation_id'] = conversation_id
    messages[conversation_id] = []
    logging.debug(f"Created new conversation {conversation_id} via API")
    save_messages_to_file()

    return jsonify({'status': 'success', 'conversation_id': conversation_id})

if __name__ == '__main__':
    # 运行应用，监听所有可用 IP 地址，使用 5000 端口
    app.run(host='0.0.0.0', port=5000, debug=True)