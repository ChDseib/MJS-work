import os
import uuid  # 用于生成唯一文件名
from flask import Flask, render_template, request, jsonify, session, url_for, g
import logging
from dotenv import load_dotenv
from threading import Thread
from flask_cors import CORS
import requests
import json
from werkzeug.utils import secure_filename
import mysql.connector
from mysql.connector import Error

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

# 环境变量配置
SPARKAI_APP_ID = os.getenv('SPARKAI_APP_ID')
SPARKAI_AUTH_TOKEN = os.getenv('SPARKAI_AUTH_TOKEN')
SPARKAI_URL = os.getenv('SPARKAI_URL')  # 创建对话的 URL
SPARKAI_RUNS_URL = os.getenv('SPARKAI_RUNS_URL')  # 发送消息的 URL
SPARKAI_UPLOAD_URL = os.getenv('SPARKAI_UPLOAD_URL')  # 上传文件的 URL

# 数据库配置
DB_HOST = os.getenv('DB_HOST', ' localhost')
DB_USER = os.getenv('DB_USER', 'pysql')
DB_PASSWORD = os.getenv('DB_PASSWORD', '123456')
DB_NAME = os.getenv('DB_NAME', 'b23015136')

def create_connection_db():
    """创建并返回一个数据库连接"""
    try:
        connection = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        if connection.is_connected():
            logging.debug("Connected to MySQL database")
            return connection
    except Error as e:
        logging.error(f"Error connecting to MySQL: {e}")
        return None

def get_db():
    """获取数据库连接，存储在 Flask 的 g 中"""
    if 'db' not in g:
        g.db = create_connection_db()
    return g.db

@app.teardown_appcontext
def close_db(exception):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None and db.is_connected():
        db.close()
        logging.debug("MySQL connection closed")

def execute_query(query, params=None):
    """执行一个写操作的查询"""
    connection = get_db()
    if connection is None:
        raise Exception("Database connection failed")
    cursor = connection.cursor()
    try:
        cursor.execute(query, params)
        connection.commit()
        logging.debug("Query executed successfully")
    except Error as e:
        logging.error(f"Error executing query: {e}")
        connection.rollback()
        raise e
    finally:
        cursor.close()

def fetch_all(query, params=None):
    """执行一个读取操作的查询并返回所有结果"""
    connection = get_db()
    if connection is None:
        raise Exception("Database connection failed")
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(query, params)
        results = cursor.fetchall()
        logging.debug("Fetch all executed successfully")
        return results
    except Error as e:
        logging.error(f"Error fetching data: {e}")
        raise e
    finally:
        cursor.close()

def create_conversation():
    """
    创建一个新的对话，返回 conversation_id。
    """
    url = SPARKAI_URL  # 例如 "https://qianfan.baidubce.com/v2/app/conversation"
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
    url = SPARKAI_RUNS_URL  # 例如 "https://qianfan.baidubce.com/v2/app/conversation/runs"
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

def save_message(conversation_id, message):
    """将消息保存到数据库"""
    query = """
    INSERT INTO messages (conversation_id, message_id, text, role, file_ids)
    VALUES (%s, %s, %s, %s, %s)
    """
    params = (
        conversation_id,
        message['id'],
        message['text'],
        message['role'],
        json.dumps(message.get('file_ids', []))
    )
    execute_query(query, params)

def delete_message_db(conversation_id, message_id):
    """删除指定的消息"""
    query = """
    DELETE FROM messages
    WHERE conversation_id = %s AND message_id = %s
    """
    params = (conversation_id, message_id)
    execute_query(query, params)

def clear_messages_db(conversation_id):
    """清除指定对话的所有消息"""
    query = """
    DELETE FROM messages
    WHERE conversation_id = %s
    """
    params = (conversation_id,)
    execute_query(query, params)

def load_messages_db(conversation_id):
    """从数据库加载指定对话的所有消息"""
    query = """
    SELECT * FROM messages
    WHERE conversation_id = %s
    ORDER BY message_id ASC
    """
    params = (conversation_id,)
    return fetch_all(query, params)

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
            return "无法创建对话稍后重试。", 500
        session['conversation_id'] = conversation_id
    return render_template('chat.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    """
    接收用户消息，生成AI回复，并保存到消息列表。
    """
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

    # 始终清除 file_id
    file_id = session.pop('file_id', None)
    file_ids = []
    if img_name and img_url and file_id:
        file_ids.append(file_id)

    # 获取当前消息ID
    query = """
    SELECT MAX(message_id) AS max_id FROM messages
    WHERE conversation_id = %s
    """
    params = (conversation_id,)
    result = fetch_all(query, params)
    current_max_id = result[0]['max_id'] if result and result[0]['max_id'] else 0
    next_id = current_max_id + 1

    # 添加用户消息，包含可选的 file_ids
    user_message = {
        'id': next_id,
        'text': message_text,
        'role': 'user',
        'file_ids': file_ids
    }
    try:
        save_message(conversation_id, user_message)
        logging.debug(f"接收到消息: {message_text}，ID 为 {next_id}，对话ID为 {conversation_id}")
    except Exception as e:
        logging.error(f"保存用户消息失败: {e}")
        return jsonify({'status': 'error', 'message': '保存消息失败'}), 500

    # 启动新线程处理AI回复
    ai_thread = Thread(target=handle_ai_response, args=(message_text, max_length, conversation_id, file_ids))
    ai_thread.start()

    return jsonify({'status': 'success', 'user_message': user_message})

def handle_ai_response(message_text, max_length, conversation_id, file_ids):
    """
    处理AI回复的函数。
    """
    with app.app_context():
        try:
            # 获取下一个消息ID
            query = """
            SELECT MAX(message_id) AS max_id FROM messages
            WHERE conversation_id = %s
            """
            params = (conversation_id,)
            result = fetch_all(query, params)
            next_id = result[0]['max_id'] + 1 if result and result[0]['max_id'] else 1

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
            save_message(conversation_id, ai_message)
            logging.debug(f"AI回应: {ai_text}，ID 为 {next_id}，对话ID为 {conversation_id}")
        except Exception as e:
            logging.error(f"处理AI回复时出错: {e}")

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
    if not conversation_id:
        return jsonify({'status': 'error', 'message': '未找到对话'}), 400

    try:
        delete_message_db(conversation_id, message_id)
        logging.debug(f"已删除ID为 {message_id} 的消息，来自对话 {conversation_id}")
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"删除消息失败: {e}")
        return jsonify({'status': 'error', 'message': '删除消息失败'}), 500

@app.route('/clear_messages', methods=['POST'])
def clear_messages():
    """
    清除所有消息并创建新的对话。
    """
    conversation_id = create_conversation()
    if not conversation_id:
        return jsonify({'status': 'error', 'message': '无法创建新对话'}), 500

    session['conversation_id'] = conversation_id
    try:
        # 清除所有消息
        clear_messages_db(conversation_id)
        logging.debug(f"已清除所有消息并创建新的对话 {conversation_id}")
        return jsonify({'status': 'success', 'conversation_id': conversation_id})
    except Exception as e:
        logging.error(f"清除消息失败: {e}")
        return jsonify({'status': 'error', 'message': '清除消息失败'}), 500

@app.route('/get_messages', methods=['GET'])
def get_messages():
    """
    获取所有消息。
    """
    conversation_id = session.get('conversation_id')
    if not conversation_id:
        return jsonify({'messages': []})

    try:
        messages = load_messages_db(conversation_id)
        return jsonify({'messages': messages})
    except Exception as e:
        logging.error(f"获取消息失败: {e}")
        return jsonify({'status': 'error', 'message': '获取消息失败'}), 500

@app.route('/api/answer', methods=['POST'])
def api_answer():
    """
    处理API请求，接收问题并返回AI回复。
    """
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

    # 获取当前消息ID
    query = """
    SELECT MAX(message_id) AS max_id FROM messages
    WHERE conversation_id = %s
    """
    params = (conversation_id,)
    result = fetch_all(query, params)
    next_id = result[0]['max_id'] + 1 if result and result[0]['max_id'] else 1

    # 添加用户消息到消列表
    user_message = {
        'id': next_id,
        'text': question,
        'role': 'user',
        'file_ids': []
    }
    try:
        save_message(conversation_id, user_message)
        logging.debug(f"已添加用户消息: {user_message} 到对话 {conversation_id}")
    except Exception as e:
        logging.error(f"保存用户消息失败: {e}")
        return jsonify({'status': 'error', 'message': '保存消息失败'}), 500

    # 获取下一个消息ID
    next_id += 1

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
    try:
        save_message(conversation_id, ai_message)
        logging.debug(f"API AI回应: {ai_text}，ID为 {next_id}，对话ID为 {conversation_id}")
    except Exception as e:
        logging.error(f"保存AI消息失败: {e}")
        return jsonify({'status': 'error', 'message': '保存AI消息失败'}), 500

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
    try:
        # 清除所有消息
        clear_messages_db(conversation_id)
        logging.debug(f"通过API创建了新的对话 {conversation_id}")
        return jsonify({'status': 'success', 'conversation_id': conversation_id})
    except Exception as e:
        logging.error(f"创建新对话失败: {e}")
        return jsonify({'status': 'error', 'message': '创建新对话失败'}), 500

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

            # 如果需要将图片上传到外部服务，可以保留以下代码
            payload = {
                "app_id": SPARKAI_APP_ID,
                "conversation_id": conversation_id
            }

            headers = {
                'X-Appbuilder-Authorization': SPARKAI_AUTH_TOKEN
                # 'Content-Type' 不需要设置，让requests自动处理
            }

            with open(file_path, 'rb') as f:
                files = {
                    'file': (unique_filename, f, file.mimetype)
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

@app.route('/get_conversations')
def get_conversations():
    """获取所有对话历史"""
    try:
        # 首先获取所有不同的对话ID和它们的第一条消息时间
        query = """
        SELECT 
            m.conversation_id,
            MIN(m.timestamp) as start_time,
            (
                SELECT text 
                FROM messages 
                WHERE conversation_id = m.conversation_id 
                ORDER BY message_id DESC 
                LIMIT 1
            ) as last_message,
            (
                SELECT timestamp 
                FROM messages 
                WHERE conversation_id = m.conversation_id 
                ORDER BY message_id DESC 
                LIMIT 1
            ) as last_time
        FROM messages m
        GROUP BY m.conversation_id
        ORDER BY last_time DESC
        """
        conversations = fetch_all(query)
        
        # 处理每个对话的预览信息
        for conv in conversations:
            # 确保时间戳是字符串格式
            conv['start_time'] = conv['start_time'].isoformat() if conv['start_time'] else None
            conv['last_time'] = conv['last_time'].isoformat() if conv['last_time'] else None
            # 限制预览文本长度
            if conv['last_message']:
                conv['preview'] = conv['last_message'][:50] + ('...' if len(conv['last_message']) > 50 else '')
            else:
                conv['preview'] = '新对话'
                
        return jsonify({'conversations': conversations})
    except Exception as e:
        logging.error(f"获取对话历史失败: {e}")
        return jsonify({'status': 'error', 'message': '获取对话历史失败'}), 500

@app.route('/switch_conversation/<conversation_id>', methods=['POST'])
def switch_conversation(conversation_id):
    """切换到指定的对话"""
    try:
        session['conversation_id'] = conversation_id
        return jsonify({'status': 'success'})
    except Exception as e:
        logging.error(f"切换对话失败: {e}")
        return jsonify({'status': 'error', 'message': '切换对话失败'}), 500

if __name__ == '__main__':
    # 运行应用，监听所有可用IP地址，使用5001端口
    app.run(host='0.0.0.0', port=5001, debug=True)