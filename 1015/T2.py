import requests
import json


def main():
    url = "https://qianfan.baidubce.com/v2/app/conversation/runs"

    payload = json.dumps({
        "app_id": "b58f7742-2963-4d5d-a75f-33477c283afe",
        "query": "你好",
        "stream": False,
        "conversation_id": "03dcaae3-ebb0-4b0a-8c8d-77851ac76124",
        "file_ids": [
            "1b47ba7d-120a-4318-90b8-dd4dbb6db836"
        ]

    })
    headers = {
        'Content-Type': 'application/json',
        'X-Appbuilder-Authorization': 'Bearer bce-v3/ALTAK-PbnNQPoBU2iQNqLfyaB6l/a46a7d779bff4c0359d5a7ba3fe867f8f83c88b7'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    print(response.text)


if __name__ == '__main__':
    main()
