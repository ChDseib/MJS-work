import requests
import json

# 请求的URL
url = "https://m.ctrip.com/restapi/soa2/13444/json/getCommentCollapseList?_fxpcqlniredt=09031159319944730109&x-traceID=09031159319944730109-1731978681614-3565416"

# 请求头
headers = {
    "accept": "*/*",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
    "cache-control": "no-cache",
    "content-type": "application/json",
    "cookie": "GUID=09031159319944730109; nfes_isSupportWebP=1; UBT_VID=1731376607957.63baatMA3xAT; _RSG=HlqLsOgNifEoAWNKHuP.g8; _RDG=28852ceb73c29221f41ac287334db9cc95; _RGUID=ea6c5ea6-3657-4bd1-8abe-6784545e02b2; _RF1=38.147.161.167; MKT_CKID=1731978648850.rknv7.87gg; _bfa=1.1731376607957.63baatMA3xAT.1.1731978645900.1731978649224.1.2.290510; _jzqco=%7C%7C%7C%7C1731978650463%7C1.517685591.1731978648854.1731978648854.1731978651271.1731978648854.1731978651271.undefined.0.0.2.2",
    "origin": "https://you.ctrip.com",
    "referer": "https://you.ctrip.com/",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
}

# 请求体模板
payload_template = {
    "arg": {
        "channelType": 2,
        "collapseType": 0,
        "commentTagId": 0,
        "pageIndex": 1,  # 分页索引
        "pageSize": 10,  # 每页评论数量
        "poiId": 13412802,  # 上海迪士尼度假区的poiId
        "sortType": 3,
        "sourceType": 1,
        "starType": 0
    },
    "head": {
        "cid": "09031159319944730109",
        "ctok": "",
        "cver": "1.0",
        "lang": "01",
        "sid": "8888",
        "syscode": "09",
        "auth": "",
        "xsid": ""
    }
}

# 爬取评论
def fetch_comments(page_index):
    payload = payload_template.copy()
    payload["arg"]["pageIndex"] = page_index  # 更新分页索引
    try:
        # 发送请求
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            # 提取评论内容
            if "result" in data and "items" in data["result"]:
                comments = [
                    item["content"] for item in data["result"]["items"] if "content" in item
                ]
                return comments
            else:
                print(f"数据结构异常，返回内容：{data}")
                return []
        else:
            print(f"请求失败，状态码：{response.status_code}")
            return []
    except requests.RequestException as e:
        print(f"请求发生错误：{e}")
        return []

# 主程序
if __name__ == "__main__":
    all_comments = []
    for page in range(1, 50):  # 假设爬取前 5 页
        print(f"正在爬取第 {page} 页评论...")
        comments = fetch_comments(page)
        if comments:
            all_comments.extend(comments)
        else:
            print(f"第 {page} 页无有效评论，停止爬取。")
            break

    # 输出结果
    print(f"共爬取到 {len(all_comments)} 条评论：")
    for i, comment in enumerate(all_comments, 1):
        print(f"{i}: {comment}")

    # 保存评论到文件
    with open("disney_comments.txt", "w", encoding="utf-8") as f:
        for comment in all_comments:
            f.write(comment + "\n")