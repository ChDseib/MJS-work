from flask import Flask, request, jsonify

app = Flask(__name__)

# 存储聊天记录
chat_history = []

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # 简单的回声响应
    bot_response = f"Echo: {user_message}"
    
    # 记录聊天
    chat_history.append({'user': user_message, 'bot': bot_response})
    
    return jsonify({'response': bot_response})

@app.route('/history', methods=['GET'])
def history():
    return jsonify(chat_history)

if __name__ == '__main__':
    app.run(debug=True)