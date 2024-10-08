from flask import Flask, render_template, request, jsonify
import logging
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# 配置日志
logging.basicConfig(level=logging.DEBUG)

# 存储所有消息，每条消息包含唯一的id和文本内容
messages = []
next_id = 1  # 用于分配唯一的消息ID
message_file = 'messages.txt'  # 存储消息的文件路径

# 读取文件并加载消息
def load_messages_from_file():
    global messages, next_id
    if os.path.exists(message_file):
        with open(message_file, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line:
                    parts = line.split('|')
                    if len(parts) == 2:
                        message_id = int(parts[0])
                        message_text = parts[1]
                        messages.append({'id': message_id, 'text': message_text})
                        next_id = message_id + 1  # 更新下一个ID为最新的
    logging.debug(f"Loaded {len(messages)} messages from {message_file}")

# 将当前消息列表保存到文件
def save_messages_to_file():
    with open(message_file, 'w', encoding='utf-8') as file:
        for message in messages:
            file.write(f"{message['id']}|{message['text']}\n")
    logging.debug(f"Saved {len(messages)} messages to {message_file}")

# 在启动时加载消息
load_messages_from_file()

@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    global next_id
    data = request.get_json()
    message_text = data.get('message')
    if message_text:
        message = {'id': next_id, 'text': message_text}
        messages.append(message)
        logging.debug(f"Received message: {message_text} with id {next_id}")
        next_id += 1
        save_messages_to_file()  # 保存消息到文件
        return jsonify({'status': 'success', 'message': message})
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
    app.run(host='0.0.0.0', port=5001, debug=True)

