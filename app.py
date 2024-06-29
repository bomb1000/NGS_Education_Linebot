from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI
import os
import traceback
import time
import logging

app = Flask(__name__)

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 從環境變數中獲取金鑰
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')

# 設置 Line Bot API 和 Webhook Handler
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 設置 OpenAI 客戶端
client = OpenAI(api_key=OPENAI_API_KEY)

# 創建向量儲存並上傳檔案
def create_vector_store_and_upload_files(file_paths):
    try:
        # 創建向量儲存
        vector_store = client.beta.vector_stores.create(name="LineBot_Knowledge_Base")
        logger.info(f"向量儲存創建成功，ID: {vector_store.id}")

        # 上傳檔案
        file_ids = []
        for path in file_paths:
            with open(path, "rb") as file:
                uploaded_file = client.files.create(file=file, purpose="assistants")
                file_ids.append(uploaded_file.id)
                logger.info(f"檔案上傳成功，ID: {uploaded_file.id}")
        
        # 使用上傳和輪詢SDK助手來上傳檔案，將它們添加到向量儲存，並輪詢檔案批次的狀態以完成
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            file_ids=file_ids
        )
        
        logger.info(f"檔案批次狀態: {file_batch.status}")
        logger.info(f"檔案數量: {file_batch.file_counts}")
        
        return vector_store
    except Exception as e:
        logger.error(f"創建向量儲存和上傳檔案時發生錯誤: {e}")
        raise

# 創建助手
def create_assistant(vector_store_id):
    try:
        assistant = client.beta.assistants.create(
            name="LineBot 助手",
            instructions="你是一個幫助回答問題的助手。使用上傳的檔案來回答問題。如果找到相關資訊，請詳細說明。如果無法在上傳的檔案中找到相關資訊，請明確說明並解釋可能的原因。",
            model="gpt-3.5-turbo",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
        )
        logger.info(f"助手創建成功，ID: {assistant.id}")
        return assistant
    except Exception as e:
        logger.error(f"創建助手時發生錯誤: {e}")
        raise

# 初始化向量儲存、上傳檔案和創建助手
logger.info("開始初始化應用...")
file_paths = ["data/基因檢測類型與說明_CGP Patient Infographics-Slide M-TW-00001418.pdf", "data/基因檢測服務流程_檢測結果對癌症治療之效益_Patient brochure(A4)_M-TW-00001452.pdf"]
vector_store = create_vector_store_and_upload_files(file_paths)
assistant = create_assistant(vector_store.id)

# 用戶ID到Thread ID的映射
user_threads = {}

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
    try:
        user_id = event.source.user_id
        user_message = event.message.text

        # 獲取或創建用戶的Thread
        if user_id not in user_threads:
            thread = client.beta.threads.create()
            user_threads[user_id] = thread.id
        thread_id = user_threads[user_id]

        # 添加用戶消息到Thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=user_message
        )

        # 運行助手
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant.id
        )

        # 等待運行完成
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == 'completed':
                break
            elif run_status.status in ['failed', 'cancelled', 'expired']:
                raise Exception(f"執行失敗，狀態: {run_status.status}")
            time.sleep(1)

        # 獲取助手的回覆
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        reply_message = messages.data[0].content[0].text.value

        # 回應用戶消息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_message)
        )
    except Exception as e:
        error_message = f"發生錯誤: {str(e)}\n\n追蹤資訊:\n{traceback.format_exc()}"
        logger.error(error_message)
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="抱歉，處理您的請求時發生了錯誤。請稍後再試。")
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
