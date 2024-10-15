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
from werkzeug.utils import secure_filename

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Load SECRET_KEY from environment variables

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Store all messages, each message contains a unique id, text content, role, and optional file_ids
messages = {}
next_id = 1  # For assigning unique message IDs
message_file = '1015/messages.txt'  # Path to store messages

# Environment variables for SPARKAI
SPARKAI_APP_ID = os.getenv('SPARKAI_APP_ID')
SPARKAI_AUTH_TOKEN = os.getenv('SPARKAI_AUTH_TOKEN')
SPARKAI_URL = os.getenv('SPARKAI_URL')  # URL to create conversations
SPARKAI_RUNS_URL = os.getenv('SPARKAI_RUNS_URL')  # URL to send messages
SPARKAI_UPLOAD_URL = os.getenv('SPARKAI_UPLOAD_URL')  # URL to upload files

def load_messages_from_file():
    """
    Load messages from file into memory.
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
                                next_id = message_id + 1  # Update next ID
                        except ValueError:
                            continue
        logging.debug(f"Loaded messages from {message_file}")
    else:
        logging.debug(f"No message file found at {message_file}")

def save_messages_to_file():
    """
    Save the current message list to file.
    """
    with open(message_file, 'w', encoding='utf-8') as file:
        for conv_id, msgs in messages.items():
            for message in msgs:
                file.write(f"{conv_id}|{message['id']}|{message['text']}|{message['role']}|{json.dumps(message.get('file_ids', []))}\n")
    logging.debug(f"Saved messages to {message_file}")

# Load messages at startup
load_messages_from_file()

def create_conversation():
    """
    Create a new conversation and return the conversation_id.
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

def send_query(conversation_id, query, file_ids=None, stream=False):
    """
    Send user message to AI and return AI's reply.
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
        # Extract AI's reply text
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
    Ensure each request has a session.
    """
    session.permanent = True

@app.route('/')
def index():
    """
    Render the chat interface.
    Create a new conversation if the user doesn't have one.
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
    Receive user message, generate AI reply, and save to message list.
    """
    global next_id
    data = request.get_json()
    message_text = data.get('message')
    max_length = data.get('max_length', 500)  # Default max characters is 500
    img_name = data.get('img_name', '')
    img_url = data.get('img_url', '')

    if not message_text and not img_name:
        logging.debug("No message or image provided")
        return jsonify({'status': 'error', 'message': 'No message or image provided'}), 400

    conversation_id = session.get('conversation_id')
    if not conversation_id:
        conversation_id = create_conversation()
        if not conversation_id:
            return jsonify({'status': 'error', 'message': '无法创建对话'}), 500
        session['conversation_id'] = conversation_id
        messages[conversation_id] = []

    # Prepare file_ids if image is present
    file_ids = []
    if img_name and img_url:
        # Retrieve file_id from session
        file_id = session.pop('file_id', None)
        if file_id:
            file_ids.append(file_id)

    # Add user message with optional file_ids
    user_message = {
        'id': next_id,
        'text': message_text,
        'role': 'user',
        'file_ids': file_ids
    }
    messages[conversation_id].append(user_message)
    logging.debug(f"Received message: {message_text} with id {next_id} in conversation {conversation_id}")
    next_id += 1
    save_messages_to_file()  # Save messages to file

    def handle_ai_response(message_text, max_length, conversation_id, file_ids):
        """
        Handle AI's response.
        """
        global next_id
        ai_text = send_query(conversation_id, message_text, file_ids=file_ids, stream=False)

        # Limit AI's response length
        ai_text = ai_text[:int(max_length)]

        # Add AI's reply
        ai_message = {
            'id': next_id,
            'text': ai_text,
            'role': 'assistant',
            'file_ids': []
        }
        messages[conversation_id].append(ai_message)
        logging.debug(f"AI responded: {ai_text} with id {next_id} in conversation {conversation_id}")
        next_id += 1
        save_messages_to_file()  # Save messages to file

    # Start a new thread to handle AI response
    ai_thread = Thread(target=handle_ai_response, args=(message_text, max_length, conversation_id, file_ids))
    ai_thread.start()

    return jsonify({'status': 'success', 'user_message': user_message})

@app.route('/delete_message', methods=['POST'])
def delete_message():
    """
    Delete a message by its ID.
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
        save_messages_to_file()  # Save messages to file
        return jsonify({'status': 'success'})
    else:
        logging.debug(f"Message ID {message_id} not found in conversation {conversation_id}")
        return jsonify({'status': 'error', 'message': 'Message ID not found'}), 400

@app.route('/clear_messages', methods=['POST'])
def clear_messages():
    """
    Clear all messages and create a new conversation.
    """
    global next_id
    # Create a new conversation
    conversation_id = create_conversation()
    if not conversation_id:
        return jsonify({'status': 'error', 'message': '无法创建新对话'}), 500

    # Update conversation ID and clear messages
    session['conversation_id'] = conversation_id
    messages[conversation_id] = []
    logging.debug(f"Cleared all messages and created new conversation {conversation_id}")
    save_messages_to_file()  # Save messages to file

    return jsonify({'status': 'success', 'conversation_id': conversation_id})

@app.route('/get_messages', methods=['GET'])
def get_messages():
    """
    Get all messages for the current conversation.
    """
    conversation_id = session.get('conversation_id')
    if not conversation_id or conversation_id not in messages:
        return jsonify({'messages': []})
    return jsonify({'messages': messages[conversation_id]})

@app.route('/api/answer', methods=['POST'])
def api_answer():
    """
    Handle API requests, receive a question, and return AI's answer.
    """
    global next_id
    data = request.get_json()
    question = data.get('question')
    max_length = data.get('max_length', 500)  # Default max characters is 500

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

    # Add user message to message list
    user_message = {
        'id': next_id,
        'text': question,
        'role': 'user',
        'file_ids': []
    }
    messages[conversation_id].append(user_message)
    logging.debug(f"Added user message: {user_message} to conversation {conversation_id}")
    next_id += 1
    save_messages_to_file()

    # Handle AI's response
    ai_text = send_query(conversation_id, question, file_ids=None, stream=False)

    # Limit AI's response length
    ai_text = ai_text[:int(max_length)]

    # Add AI's reply to message list
    ai_message = {
        'id': next_id,
        'text': ai_text,
        'role': 'assistant',
        'file_ids': []
    }
    messages[conversation_id].append(ai_message)
    logging.debug(f"API AI responded: {ai_text} with id {next_id} in conversation {conversation_id}")
    next_id += 1
    save_messages_to_file()

    return jsonify({'status': 'success', 'answer': ai_text})

@app.route('/create_conversation', methods=['POST'])
def create_new_conversation():
    """
    Create a new conversation, switch to the new conversation_id, and clear current messages.
    """
    conversation_id = create_conversation()
    if not conversation_id:
        return jsonify({'status': 'error', 'message': '无法创建新对话'}), 500

    session['conversation_id'] = conversation_id
    messages[conversation_id] = []
    logging.debug(f"Created new conversation {conversation_id} via API")
    save_messages_to_file()

    return jsonify({'status': 'success', 'conversation_id': conversation_id})

@app.route('/upload_image', methods=['POST'])
def upload_image():
    """
    Handle image uploads from the user.
    """
    if 'image' not in request.files:
        return jsonify({'status': 'error', 'message': 'No image part in the request'}), 400

    file = request.files['image']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        mime_type = file.mimetype or 'application/octet-stream'

        conversation_id = session.get('conversation_id')
        if not conversation_id:
            conversation_id = create_conversation()
            if not conversation_id:
                return jsonify({'status': 'error', 'message': '无法创建对话'}), 500
            session['conversation_id'] = conversation_id
            messages[conversation_id] = []

        payload = {
            "app_id": SPARKAI_APP_ID,
            "conversation_id": conversation_id
        }

        headers = {
            'X-Appbuilder-Authorization': SPARKAI_AUTH_TOKEN
            # 'Content-Type' is not set to let requests handle it
        }

        files = {
            'file': (filename, file.stream, mime_type)
        }

        try:
            response = requests.post(SPARKAI_UPLOAD_URL, headers=headers, data=payload, files=files)
            response.raise_for_status()
            data = response.json()
            upload_id = data.get("id")
            request_id = data.get("request_id")
            response_conversation_id = data.get("conversation_id")

            if not upload_id:
                logging.error("Upload response does not contain 'id'")
                return jsonify({'status': 'error', 'message': '上传失败，未收到文件ID'}), 500

            # Optionally, construct img_url if available
            # Assuming SPARKAI provides a URL or you need to construct it
            img_url = f"https://your-image-host.com/{upload_id}"  # Replace with actual logic if available

            # Store file_id in session to associate with the next message
            session['file_id'] = upload_id

            logging.debug(f"Uploaded image successfully: {data}")
            return jsonify({
                'status': 'success',
                'img_name': filename,
                'img_url': img_url
            })
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to upload image: {e}")
            return jsonify({'status': 'error', 'message': '图片上传失败'}), 500
        except Exception as e:
            logging.error(f"An unexpected error occurred during image upload: {e}")
            return jsonify({'status': 'error', 'message': '发生未知错误'}), 500

if __name__ == '__main__':
    # Run the application, listening on all available IP addresses, using port 5000
    app.run(host='0.0.0.0', port=5000, debug=True)