# app.py

from flask import Flask, render_template, request, jsonify
import logging
import os
from dotenv import load_dotenv
from sparkai.llm.llm import ChatSparkLLM, ChunkPrintHandler
from sparkai.core.messages import ChatMessage
from threading import Thread

# 加载环境变量
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # 从环境变量加载 SECRET_KEY

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# 存储所有消息，每条消息包含唯一的id、文本内容和角色
messages = []
next_id = 1  # 用于分配唯一的消息ID
message_file = '1008/messages.txt'  # 存储消息的文件路径


# 读取文件并加载消息
def load_messages_from_file():
    global messages, next_id
    if os.path.exists(message_file):
        with open(message_file, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:
                    parts = line.split('|')
                    if len(parts) == 3:
                        try:
                            message_id = int(parts[0])
                            message_text = parts[1]
                            message_role = parts[2]
                            messages.append({'id': message_id, 'text': message_text, 'role': message_role})
                            if message_id >= next_id:
                                next_id = message_id + 1  # 更新下一个ID为最新的
                        except ValueError:
                            continue
                    elif len(parts) == 2:
                        # 如果缺少role字段，默认分配为'user'
                        try:
                            message_id = int(parts[0])
                            message_text = parts[1]
                            message_role = 'user'  # 默认角色
                            messages.append({'id': message_id, 'text': message_text, 'role': message_role})
                            if message_id >= next_id:
                                next_id = message_id + 1
                        except ValueError:
                            continue
    logging.debug(f"Loaded {len(messages)} messages from {message_file}")


# 将当前消息列表保存到文件
def save_messages_to_file():
    with open(message_file, 'w', encoding='utf-8') as file:
        for message in messages:
            file.write(f"{message['id']}|{message['text']}|{message['role']}\n")
    logging.debug(f"Saved {len(messages)} messages to {message_file}")


# 在启动时加载消息
load_messages_from_file()

# 初始化 Spark AI 客户端
try:
    spark = ChatSparkLLM(
        spark_api_url=os.getenv('SPARKAI_URL'),
        spark_app_id=os.getenv('SPARKAI_APP_ID'),
        spark_api_key=os.getenv('SPARKAI_API_KEY'),
        spark_api_secret=os.getenv('SPARKAI_API_SECRET'),
        spark_llm_domain=os.getenv('SPARKAI_DOMAIN'),
        streaming=False,
    )
    logging.debug("Initialized Spark AI client successfully.")
except Exception as e:
    logging.error(f"Failed to initialize Spark AI client: {e}")
    spark = None

# 打印环境变量以验证
logging.debug(f"SPARKAI_URL: {os.getenv('SPARKAI_URL')}")
logging.debug(f"SPARKAI_APP_ID: {os.getenv('SPARKAI_APP_ID')}")
logging.debug(f"SPARKAI_API_KEY: {os.getenv('SPARKAI_API_KEY')}")
logging.debug(f"SPARKAI_DOMAIN: {os.getenv('SPARKAI_DOMAIN')}")
logging.debug(f"SECRET_KEY: {os.getenv('SECRET_KEY')}")


@app.route('/')
def index():
    return render_template('chat.html')


@app.route('/send_message', methods=['POST'])
def send_message():
    global next_id
    data = request.get_json()
    message_text = data.get('message')
    if message_text:
        # 添加用户消息，确保包含 'role'
        user_message = {'id': next_id, 'text': message_text, 'role': 'user'}
        messages.append(user_message)
        logging.debug(f"Received message: {message_text} with id {next_id}")
        next_id += 1
        save_messages_to_file()  # 保存消息到文件

        def handle_ai_response(message_text):
            global next_id
            if not spark:
                logging.error("Spark AI client is not initialized.")
                ai_text = "抱歉，AI 服务不可用。"
            else:
                try:
                    # 构建对话上下文
                    chat_messages = [
                        ChatMessage(role=msg['role'], content=msg['text'])
                        for msg in messages
                        if msg['role'] in ['user', 'assistant']
                    ]

                    # 发送消息到 AI
                    logging.debug(
                        f"Sending messages to AI: {[{'role': msg.role, 'content': msg.content} for msg in chat_messages]}")
                    ai_response = spark.generate([chat_messages], callbacks=[ChunkPrintHandler()])

                    # 记录原始 AI 响应
                    logging.debug(f"Raw AI response: {ai_response}")

                    # 解析 AI 响应
                    if ai_response and hasattr(ai_response, 'generations') and ai_response.generations:
                        # 获取第一个 ChatGeneration 对象的 text
                        first_generation = ai_response.generations[0][0]
                        ai_text = first_generation.text
                        logging.debug(f"Parsed AI response: {ai_text}")
                    else:
                        ai_text = "抱歉，我无法处理您的请求。"
                        logging.debug("AI response is empty.")
                except Exception as e:
                    logging.error(f"Error generating AI response: {e}")
                    ai_text = "抱歉，我无法处理您的请求。"

            # 添加 AI 回复
            ai_message = {'id': next_id, 'text': ai_text, 'role': 'assistant'}
            messages.append(ai_message)
            logging.debug(f"AI responded: {ai_text} with id {next_id}")
            next_id += 1
            save_messages_to_file()  # 保存消息到文件

        # 启动新线程处理 AI 回复
        ai_thread = Thread(target=handle_ai_response, args=(message_text,))
        ai_thread.start()

        return jsonify({'status': 'success', 'user_message': user_message})
    else:
        logging.debug("No message provided")
        return jsonify({'status': 'error', 'message': 'No message provided'}), 400


@app.route('/delete_message', methods=['POST'])
def delete_message():
    data = request.get_json()
    message_id = data.get('id')
    if message_id is not None:
        global messages
        messages = [msg for msg in messages if msg['id'] != message_id]
        logging.debug(f"Deleted message with id: {message_id}")
        save_messages_to_file()  # 保存消息到文件
        return jsonify({'status': 'success'})
    else:
        logging.debug("No message ID provided for deletion")
        return jsonify({'status': 'error', 'message': 'No message ID provided'}), 400


@app.route('/clear_messages', methods=['POST'])
def clear_messages():
    global messages
    messages = []
    logging.debug("All messages have been cleared")
    save_messages_to_file()  # 保存消息到文件
    return jsonify({'status': 'success'})


@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify({'messages': messages})


if __name__ == '__main__':
    # 运行应用，监听所有可用 IP 地址，使用 5000 端口
    app.run(host='0.0.0.0', port=5000, debug=True)