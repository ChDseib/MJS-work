from flask import Flask, request, jsonify # type: ignore

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

@app.route('/chatbox', methods=['GET'])
def chatbox():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Chatbox</title>
    </head>
    <body>
        <h1>Chatbox</h1>
        <div id="chatbox"></div>
        <input type="text" id="message" placeholder="Type your message here">
        <button onclick="sendMessage()">Send</button>
        <script>
            function sendMessage() {
                var message = document.getElementById('message').value;
                fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({message: message})
                })
                .then(response => response.json())
                .then(data => {
                    var chatbox = document.getElementById('chatbox');
                    chatbox.innerHTML += '<p><strong>You:</strong> ' + message + '</p>';
                    chatbox.innerHTML += '<p><strong>Bot:</strong> ' + data.response + '</p>';
                });
            }
        </script>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True)