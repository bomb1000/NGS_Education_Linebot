from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os
from typing_extensions import override
from openai import AssistantEventHandler

app = Flask(__name__)

# 從 Render 環境變量中獲取必要的金鑰
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# 設置 OpenAI API 金鑰
openai.api_key = OPENAI_API_KEY

# 創建 OpenAI 客戶端
client = openai.OpenAI()

# 設置 Line Bot API 和 Webhook Handler
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 全局變量來存儲 vector store 和 assistant
vector_store = None
assistant = None

# 用戶ID到Thread ID的映射
user_threads = {}

# 創建或獲取向量儲存
def get_or_create_vector_store():
    global vector_store
    if vector_store is None:
        try:
            vector_stores = client.beta.vector_stores.list()
            for store in vector_stores.data:
                if store.name == "基因檢測知識庫":
                    print(f"使用現有的向量儲存: {store.id}")
                    vector_store = store
                    return vector_store
            print("創建新的向量儲存")
            vector_store = client.beta.vector_stores.create(name="基因檢測知識庫")
            print(f"新向量儲存創建成功，ID: {vector_store.id}")
        except Exception as e:
            print(f"獲取或創建向量儲存時發生錯誤: {e}")
            raise
    return vector_store

# 上傳文件到向量儲存
def upload_files_to_vector_store(vector_store, file_paths):
    try:
        file_streams = [open(path, "rb") for path in file_paths]
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=file_streams
        )
        print(f"文件批次狀態: {file_batch.status}")
        print(f"文件數量: {file_batch.file_counts}")
        return file_batch
    except Exception as e:
        print(f"上傳文件到向量儲存時發生錯誤: {e}")
        raise

# 創建或獲取助手
def get_or_create_assistant(vector_store_id):
    global assistant
    if assistant is None:
        try:
            assistant = client.beta.assistants.create(
                name="基因檢測專家助手",
                instructions="您是一位專業的基因檢測專家。使用您的知識庫來回答關於基因檢測的問題。",
                model="gpt-3.5-turbo",
                tools=[{"type": "file_search"}],
                tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
            )
            print(f"助手創建成功，ID: {assistant.id}")
        except Exception as e:
            print(f"創建助手時發生錯誤: {e}")
            raise
    return assistant

class EventHandler(AssistantEventHandler):
    def __init__(self):
        self.full_response = ""

    @override
    def on_text_created(self, text) -> None:
        self.full_response += text.value

    @override
    def on_tool_call_created(self, tool_call):
        pass

    @override
    def on_message_done(self, message) -> None:
        pass

def ask_assistant(assistant, thread, question):
    try:
        # 添加用戶消息到線程
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )

        # 運行助手並使用 EventHandler 來處理輸出
        event_handler = EventHandler()
        with client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=assistant.id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()

        return event_handler.full_response

    except Exception as e:
        print(f"處理問題時發生錯誤: {e}")
        return f"發生錯誤: {str(e)}"

# 初始化向量儲存、上傳檔案和創建助手
print("開始初始化應用...")
file_paths = ["data/基因檢測類型與說明_CGP Patient Infographics-Slide M-TW-00001418.pdf", "data/基因檢測服務流程_檢測結果對癌症治療之效益_Patient brochure(A4)_M-TW-00001452.pdf"]
vector_store = get_or_create_vector_store()
upload_files_to_vector_store(vector_store, file_paths)
assistant = get_or_create_assistant(vector_store.id)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    user_message = event.message.text

    # 獲取或創建用戶的Thread
    if user_id not in user_threads:
        thread = client.beta.threads.create()
        user_threads[user_id] = thread.id
    thread_id = user_threads[user_id]

    # 獲取助手的回覆
    response = ask_assistant(assistant, client.beta.threads.retrieve(thread_id), user_message)

    # 回應用戶消息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=response)
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)









# from flask import Flask, request, abort 
# from linebot import (
#     LineBotApi, WebhookHandler
# )
# from linebot.exceptions import (
#     InvalidSignatureError, LineBotApiError
# )
# from linebot.models import (
#     MessageEvent, TextMessage, ImageMessage, TextSendMessage
# )
# import openai
# import os
# import base64
# import traceback

# app = Flask(__name__)

# # 環境變數設定
# # 從環境變數中取得 OpenAI API 金鑰、Channel Secret 和 Channel Access Token
# OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
# CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')

# # 設定 Line Bot API 和 Webhook Handler
# line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
# handler = WebhookHandler(CHANNEL_SECRET)
# # 設定 OpenAI API 金鑰
# openai.api_key = OPENAI_API_KEY

# @app.route("/callback", methods=['POST'])
# def callback():
#     # 獲取 X-Line-Signature 標頭
#     signature = request.headers['X-Line-Signature']
#     # 獲取請求主體
#     body = request.get_data(as_text=True)
#     app.logger.info("Request body: " + body)
#     try:
#         # 處理 Webhook 主體
#         handler.handle(body, signature)
#     except InvalidSignatureError:
#         # 如果簽名無效，返回 400 錯誤
#         abort(400)
#     return 'OK'

# @handler.add(MessageEvent, message=TextMessage)
# def handle_text_message(event):
#     try:
#         # 獲取用戶發送的文字訊息
#         user_message = event.message.text
#         # 呼叫 OpenAI API 的 GPT-4o 模型來生成回應
#         response = openai.chat.completions.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant."},
#                 {"role": "user", "content": user_message}
#             ]
#         )
#         # 獲取 GPT-4o 模型生成的回應訊息
#         reply_message = response.choices[0].message.content
#         # 回應用戶訊息
#         line_bot_api.reply_message(
#             event.reply_token,
#             TextSendMessage(text=reply_message)
#         )
#     except Exception as e:
#         openai_version = openai.__version__
#         error_message = f"An error occurred: {str(e)}\n\nTraceback:\n{traceback.format_exc()}\nOpenAI Version: {openai_version}"
#         # 如果發生錯誤，回應用戶錯誤訊息
#         line_bot_api.reply_message(
#             event.reply_token,
#             TextSendMessage(text=error_message)
#         )

# @handler.add(MessageEvent, message=ImageMessage)
# def handle_image_message(event):
#     try:
#         # 獲取用戶發送的圖片訊息
#         message_content = line_bot_api.get_message_content(event.message.id)
#         image_path = f"/tmp/{event.message.id}.jpg"  # 將圖片儲存到伺服器的臨時目錄
#         with open(image_path, 'wb') as fd:
#             for chunk in message_content.iter_content():
#                 fd.write(chunk)

#         # 將圖片轉換為 base64 字串
#         with open(image_path, 'rb') as image_file:
#             base64_image = base64.b64encode(image_file.read()).decode('utf-8')

#         # 呼叫 OpenAI API 的 GPT-4o 模型來分析圖片
#         response = openai.chat.completions.create(
#             model="gpt-4o",
#             messages=[
#                 {"role": "system", "content": "You are a helpful assistant."},
#                 {"role": "user", "content": "Analyze this image."},
#                 {"role": "user", "content": f"data:image/jpeg;base64,{base64_image}"}
#             ]
#         )
#         # 獲取 GPT-4o 模型生成的回應訊息
#         reply_message = response.choices[0].message.content
#         # 回應用戶訊息
#         line_bot_api.reply_message(
#             event.reply_token,
#             TextSendMessage(text=reply_message)
#         )
#     except Exception as e:
#         openai_version = openai.__version__
#         error_message = f"An error occurred: {str(e)}\n\nTraceback:\n{traceback.format_exc()}\nOpenAI Version: {openai_version}"
#         # 如果發生錯誤，回應用戶錯誤訊息
#         line_bot_api.reply_message(
#             event.reply_token,
#             TextSendMessage(text=error_message)
#         )

# if __name__ == "__main__":
#     # 設定 Flask 應用的埠號，預設為 5000
#     port = int(os.environ.get('PORT', 5000))
#     app.run(host='0.0.0.0', port=port)
