import requests
import os


def main():
    url = "https://qianfan.baidubce.com/v2/app/conversation/file/upload"

    payload = {
        'app_id': 'b58f7742-2963-4d5d-a75f-33477c283afe',
        'conversation_id': 'a6b0b3b6-975c-4181-9157-af29ff09622b'
    }

    headers = {
        # 移除 'Content-Type'，让 requests 自动处理
        'X-Appbuilder-Authorization': 'Bearer bce-v3/ALTAK-PbnNQPoBU2iQNqLfyaB6l/a46a7d779bff4c0359d5a7ba3fe867f8f83c88b7'
    }

    file_path = '/Users/chauncey/Library/CloudStorage/OneDrive-个人/待处理/2022以前/photo/图片/屏幕快照/截屏2024-10-12 下午10.45.16.png'

    # 检查文件是否存在
    if not os.path.isfile(file_path):
        print(f"文件不存在: {file_path}")
        return

    # 使用 with 语句以二进制模式打开文件
    try:
        with open(file_path, 'rb') as f:
            files = {
                'file': ('IMG_3630.jpeg', f, 'image/png')
            }
            response = requests.post(url, headers=headers, data=payload, files=files)
            response.raise_for_status()  # 检查请求是否成功
            print("上传成功:", response.text)
    except UnicodeDecodeError as e:
        print(f"文件解码错误: {e}")
    except requests.exceptions.RequestException as e:
        print(f"请求错误: {e}")
    except Exception as e:
        print(f"发生其他错误: {e}")


if __name__ == '__main__':
    main()