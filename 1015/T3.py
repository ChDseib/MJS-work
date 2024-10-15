# 安装说明：
# 执行如下命令，快速安装Python语言的最新版本AppBuilder-SDK（要求Python >= 3.9)：
# pip install --upgrade appbuilder-sdk
import appbuilder
import os

# 设置环境中的TOKEN，以下TOKEN请替换为您的个人TOKEN，个人TOKEN可通过该页面【获取鉴权参数】或控制台页【密钥管理】处获取
os.environ["APPBUILDER_TOKEN"] = "bce-v3/ALTAK-PbnNQPoBU2iQNqLfyaB6l/a46a7d779bff4c0359d5a7ba3fe867f8f83c88b7"

# 从AppBuilder控制台【个人空间】-【应用】网页获取已发布应用的ID
app_id = "b58f7742-2963-4d5d-a75f-33477c283afe"

app_builder_client = appbuilder.AppBuilderClient(app_id)
conversation_id = app_builder_client.create_conversation()

resp = app_builder_client.run(conversation_id, "你好，你能做什么？")
print(resp.content.answer)