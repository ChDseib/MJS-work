# chatbox.py

from flask import Flask, render_template, request, jsonify
from chatbox_get import get_blueprint

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'

# 存储所有消息（在实际应用中，建议使用数据库）
messages = []

# 注册获取消息的蓝图，并传递消息列表
app.register_blueprint(get_blueprint(messages))

@app.route('/')
def index():
    return render_template('chatbox.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    message = data.get('message')
    if message:
        messages.append(message)
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'error', 'message': 'No message provided'}), 400

if __name__ == '__main__':
    # 运行应用，监听所有可用 IP 地址，使用 5000 端口
    app.run(host='0.0.0.0', port=5000)