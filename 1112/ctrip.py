import requests
import json
import time
import mysql.connector
from mysql.connector import Error

def create_connection(host_name, user_name, user_password, database=None):
    connection = None
    try:
        conn_params = {
            "host": host_name,
            "port": 3306,
            "user": user_name,
            "passwd": user_password,
        }
        if database:
            conn_params["database"] = database
        connection = mysql.connector.connect(**conn_params)
    except Error as e:
        print(f"The error '{e}' occurred")
    return connection

def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
    except Error as e:
        print(f"The error '{e}' occurred")

# 连接数据库
host_name = "10.200.32.179"
user_name = "root"
user_password = "111111"
database_name = "b23015136"

# 连接到MySQL数据库
connection = create_connection(host_name, user_name, user_password, database=database_name)

# 定义创建表的SQL语句
create_table_query = """
CREATE TABLE IF NOT EXISTS sightseeing_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255),
    english_name VARCHAR(255),
    score FLOAT,
    comment_count INT,
    image_url TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
"""

execute_query(connection, create_table_query)

url = 'https://m.ctrip.com/restapi/soa2/20591/getGsOnlineResult'
headers = {
    'Content-Type': 'application/json',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'Origin': 'https://you.ctrip.com',
    'Referer': 'https://you.ctrip.com/',
}

common_payload = {
    "head": {
        "cid": "09031159319944730109",
        "ctok": "",
        "cver": "1.0",
        "lang": "01",
        "sid": "8888",
        "syscode": "09",
        "auth": "",
        "xsid": "",
        "extension": []
    },
    "keyword": "上海",
    "sourceFrom": "",
    "profile": False,
    "tab": "sight"
}

total_pages = 25

for page in range(1, total_pages + 1):
    payload = common_payload.copy()
    payload.update({
        "pageIndex": page,
        "pageSize": 12
    })

    response = requests.post(url, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        try:
            data = response.json()
            items = data.get('items', [])
            for item in items:
                name = item.get('word', '').split(',')[0].strip()
                english_name = item.get('eName', '').strip()
                score = float(item.get('commentScore', 0))
                comment_count = int(item.get('commentCount', 0))
                image_url = item.get('imageUrl', '')

                insert_query = """
                INSERT INTO sightseeing_data (name, english_name, score, comment_count, image_url)
                VALUES (%s, %s, %s, %s, %s)
                """
                cursor = connection.cursor()
                cursor.execute(insert_query, (name, english_name, score, comment_count, image_url))
                connection.commit()

        except json.JSONDecodeError:
            print(f"第 {page} 页解析JSON失败")
    else:
        print(f"第 {page} 页请求失败，状态码：{response.status_code}")
    time.sleep(1)

# 关闭数据库连接
connection.close()
print("数据已成功插入到 sightseeing_data 表中")