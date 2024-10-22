import os
import uuid  # 用于生成唯一文件名
from flask import Flask, render_template, request, jsonify, session, url_for
import logging
from dotenv import load_dotenv
from threading import Thread
from flask_cors import CORS
import requests
import json
from werkzeug.utils import secure_filename

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)  # 启用 CORS
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # 从环境变量加载 SECRET_KEY

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# 配置上传文件夹
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # 如果目录不存在则创建
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 存储所有消息，每条消息包含唯一的 id、文本内容、角色和可选的 file_ids
messages = {}
next_id = 1  # 用于分配唯一的消息 ID
message_file = os.path.join(app.root_path, 'messages.txt')  # 存储消息的文件路径

# 确保 '1022' 目录存在
os.makedirs(os.path.dirname(message_file), exist_ok=True)

# 环境变量配置
SPARKAI_APP_ID = os.getenv('SPARKAI_APP_ID')
SPARKAI_AUTH_TOKEN = os.getenv('SPARKAI_AUTH_TOKEN')
SPARKAI_URL = os.getenv('SPARKAI_URL')  # 创建对话的 URL
SPARKAI_RUNS_URL = os.getenv('SPARKAI_RUNS_URL')  # 发送消息的 URL
SPARKAI_UPLOAD_URL = os.getenv('SPARKAI_UPLOAD_URL')  # 上传文件的 URL

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
                    if len(parts) >= 4:
                        try:
                            conversation_id = parts[0]
                            message_id = int(parts[1])
                            message_text = parts[2]
                            message_role = parts[3]
                            file_ids = json.loads(parts[4]) if len(parts) > 4 else []
                            if conversation_id not in messages:
                                messages[conversation_id] = []
                            messages[conversation_id].append({
                                'id': message_id,
                                'text': message_text,
                                'role': message_role,
                                'file_ids': file_ids
                            })
                            if message_id >= next_id:
                                next_id = message_id + 1  # 更新下一个 ID
                        except ValueError:
                            continue
        logging.debug(f"从 {message_file} 加载了消息")
    else:
        logging.debug(f"在 {message_file} 没有找到消息文件")

def save_messages_to_file():
    """
    将当前消息列表保存到文件。
    """
    with open(message_file, 'w', encoding='utf-8') as file:
        for conv_id, msgs in messages.items():
            for message in msgs:
                file.write(f"{conv_id}|{message['id']}|{message['text']}|{message['role']}|{json.dumps(message.get('file_ids', []))}\n")
    logging.debug(f"已将消息保存到 {message_file}")

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
        logging.debug(f"创建了新的对话，ID 为: {conversation_id}")
        return conversation_id
    except requests.exceptions.RequestException as e:
        logging.error(f"创建对话失败: {e}")
        return None

def extract_image_expert_model_text(text):
    """
    从AI响应中提取 '# 图像专家模型：' 后面的文本。
    """
    marker = "# 图像专家模型："
    if marker in text:
        start = text.find(marker) + len(marker)
        # 提取从标记位置到下一个换行符或文本末尾
        end = text.find('\n', start)
        if end == -1:
            end = len(text)
        return text[start:end].strip()
    return text  # 如果没有找到标记，返回原始文本

def send_query(conversation_id, query, file_ids=None, stream=False):
    """
    发送用户消息到AI，返回AI回复的文本，仅提取图像专家模型部分。
    """
    url = SPARKAI_RUNS_URL  # "https://qianfan.baidubce.com/v2/app/conversation/runs"
    payload = {
        "app_id": SPARKAI_APP_ID,
        "query": query,
        "stream": stream,
        "conversation_id": conversation_id
    }
    if file_ids:
        payload["file_ids"] = file_ids

    payload = json.dumps(payload)
    headers = {
        'Content-Type': 'application/json',
        'X-Appbuilder-Authorization': SPARKAI_AUTH_TOKEN
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        # 提取AI回复的文本
        outputs = data.get("content", [])
        ai_text = ""
        for item in outputs:
            if item.get("content_type") == "text":
                ai_text += item.get("outputs", {}).get("text", "")
        logging.debug(f"AI响应: {ai_text}")
        # 仅提取图像专家模型部分
        extracted_text = extract_image_expert_model_text(ai_text)
        logging.debug(f"提取后的AI响应: {extracted_text}")
        return extracted_text
    except requests.exceptions.RequestException as e:
        logging.error(f"发送查询失败: {e}")
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
    接收用户消息，生成AI回复，并保存到消息列表。
    """
    global next_id
    data = request.get_json()
    message_text = data.get('message')
    max_length = data.get('max_length', 500)  # 默认最大字符数为500
    img_name = data.get('img_name', '')
    img_url = data.get('img_url', '')

    if not message_text and not img_name:
        logging.debug("未提供消息或图片")
        return jsonify({'status': 'error', 'message': '未提供消息或图片'}), 400

    conversation_id = session.get('conversation_id')
    if not conversation_id:
        conversation_id = create_conversation()
        if not conversation_id:
            return jsonify({'status': 'error', 'message': '无法创建对话'}), 500
        session['conversation_id'] = conversation_id
        messages[conversation_id] = []

    # 始终清除 file_id
    file_id = session.pop('file_id', None)
    file_ids = []
    if img_name and img_url and file_id:
        file_ids.append(file_id)

    # 添加用户消息，包含可选的 file_ids
    user_message = {
        'id': next_id,
        'text': message_text,
        'role': 'user',
        'file_ids': file_ids
    }
    messages[conversation_id].append(user_message)
    logging.debug(f"接收到消息: {message_text}，ID 为 {next_id}，对话ID为 {conversation_id}")
    next_id += 1
    save_messages_to_file()  # 保存消息到文件

    def handle_ai_response(message_text, max_length, conversation_id, file_ids):
        """
        处理AI回复的函数。
        """
        global next_id
        ai_text = send_query(conversation_id, message_text, file_ids=file_ids, stream=False)

        # 根据 max_length 限制AI回复的长度
        ai_text = ai_text[:int(max_length)]

        # 添加AI回复
        ai_message = {
            'id': next_id,
            'text': ai_text,
            'role': 'assistant',
            'file_ids': []
        }
        messages[conversation_id].append(ai_message)
        logging.debug(f"AI回应: {ai_text}，ID 为 {next_id}，对话ID为 {conversation_id}")
        next_id += 1
        save_messages_to_file()  # 保存消息到文件

    # 启动新线程处理AI回复
    ai_thread = Thread(target=handle_ai_response, args=(message_text, max_length, conversation_id, file_ids))
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
        logging.debug("未提供消息ID用于删除")
        return jsonify({'status': 'error', 'message': '未提供消息ID'}), 400

    conversation_id = session.get('conversation_id')
    if not conversation_id or conversation_id not in messages:
        return jsonify({'status': 'error', 'message': '未找到对话'}), 400

    original_length = len(messages[conversation_id])
    messages[conversation_id] = [msg for msg in messages[conversation_id] if msg['id'] != message_id]
    if len(messages[conversation_id]) < original_length:
        logging.debug(f"已删除ID为 {message_id} 的消息，来自对话 {conversation_id}")
        save_messages_to_file()  # 保存消息到文件
        return jsonify({'status': 'success'})
    else:
        logging.debug(f"在对话 {conversation_id} 中未找到消息ID {message_id}")
        return jsonify({'status': 'error', 'message': '未找到消息ID'}), 400

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

    # 更新会话ID并清空消息
    session['conversation_id'] = conversation_id
    messages[conversation_id] = []
    logging.debug(f"已清除所有消息并创建新的对话 {conversation_id}")
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
    处理API请求，接收问题并返回AI回复。
    """
    global next_id
    data = request.get_json()
    question = data.get('question')
    max_length = data.get('max_length', 500)  # 默认最大字符数为500

    if not question:
        return jsonify({'status': 'error', 'message': '未提供问题'}), 400

    logging.debug(f"API接收到问题: {question}，最大长度: {max_length}")

    conversation_id = session.get('conversation_id')
    if not conversation_id:
        conversation_id = create_conversation()
        if not conversation_id:
            return jsonify({'status': 'error', 'message': '无法创建对话'}), 500
        session['conversation_id'] = conversation_id
        messages[conversation_id] = []

    # 添加用户消息到消息列表
    user_message = {
        'id': next_id,
        'text': question,
        'role': 'user',
        'file_ids': []
    }
    messages[conversation_id].append(user_message)
    logging.debug(f"已添加用户消息: {user_message} 到对话 {conversation_id}")
    next_id += 1
    save_messages_to_file()

    # 处理AI回复
    ai_text = send_query(conversation_id, question, file_ids=None, stream=False)

    # 根据 max_length 限制AI回复的长度
    ai_text = ai_text[:int(max_length)]

    # 添加AI回复到消息列表
    ai_message = {
        'id': next_id,
        'text': ai_text,
        'role': 'assistant',
        'file_ids': []
    }
    messages[conversation_id].append(ai_message)
    logging.debug(f"API AI回应: {ai_text}，ID为 {next_id}，对话ID为 {conversation_id}")
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
    logging.debug(f"通过API创建了新的对话 {conversation_id}")
    save_messages_to_file()  # 保存消息到文件

    return jsonify({'status': 'success', 'conversation_id': conversation_id})

@app.route('/upload_image', methods=['POST'])
def upload_image():
    """
    处理用户上传的图片，并保存到 static/uploads 文件夹。
    """
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': '请求中没有图片部分'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': '未选择文件'}), 400

    if file:
        filename = secure_filename(file.filename)
        # 生成唯一的文件名以避免冲突
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        try:
            # 保存文件到本地
            file.save(file_path)

            # 构建本地图片URL
            img_url = url_for('static', filename=f'uploads/{unique_filename}', _external=True)

            conversation_id = session.get('conversation_id')
            if not conversation_id:
                conversation_id = create_conversation()
                if not conversation_id:
                    return jsonify({'status': 'error', 'message': '无法创建对话'}), 500
                session['conversation_id'] = conversation_id
                messages[conversation_id] = []

            # 如果需要将图片上传到外部服务，可以保留以下代码
            payload = {
                "app_id": SPARKAI_APP_ID,
                "conversation_id": conversation_id
            }

            headers = {
                'X-Appbuilder-Authorization': SPARKAI_AUTH_TOKEN
                # 'Content-Type' 不需要设置，让requests自动处理
            }

            files = {
                'file': (unique_filename, open(file_path, 'rb'), file.mimetype)
            }

            response = requests.post(SPARKAI_UPLOAD_URL, headers=headers, data=payload, files=files)
            response.raise_for_status()
            data = response.json()
            upload_id = data.get("id")
            request_id = data.get("request_id")
            response_conversation_id = data.get("conversation_id")

            if not upload_id:
                logging.error("上传响应中不包含 'id'")
                return jsonify({'status': 'error', 'message': '上传失败，未收到文件ID'}), 500

            # 将 file_id 存储在会话中，以便与下一条消息关联
            session['file_id'] = upload_id

            logging.debug(f"图片上传成功: {data}")
            return jsonify({
                'status': 'success',
                'img_name': unique_filename,
                'img_url': img_url  # 返回本地图片URL
            })
        except requests.exceptions.RequestException as e:
            logging.error(f"上传图片失败: {e}")
            return jsonify({'status': 'error', 'message': '图片上传失败'}), 500
        except Exception as e:
            logging.error(f"上传图片时发生未知错误: {e}")
            return jsonify({'status': 'error', 'message': '发生未知错误'}), 500

if __name__ == '__main__':
    # 运行应用，监听所有可用IP地址，使用5000端口
    app.run(host='0.0.0.0', port=5001, debug=True)
