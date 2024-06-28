from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os
import traceback
import time


app = Flask(__name__)




# 從環境變數中取得 OpenAI API 金鑰、Channel Secret 和 Channel Access Token
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')

# 設定 Line Bot API 和 Webhook Handler
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 設定 OpenAI API 金鑰
openai.api_key = OPENAI_API_KEY

# 創建 OpenAI 客戶端
client = openai.OpenAI()

# 創建或獲取向量儲存
def get_or_create_vector_store():
    try:
        vector_stores = client.beta.vector_stores.list()
        for store in vector_stores.data:
            if store.name == "LineBot_Knowledge_Base":
                print(f"使用現有的向量儲存: {store.id}")
                return store
        print("創建新的向量儲存")
        new_store = client.beta.vector_stores.create(name="LineBot_Knowledge_Base")
        print(f"新向量儲存 ID: {new_store.id}")
        return new_store
    except Exception as e:
        print(f"獲取或創建向量儲存時發生錯誤: {e}")
        raise

# 上傳文件到向量儲存
def upload_files_to_vector_store(vector_store, file_paths):
    try:
        file_ids = []
        for path in file_paths:
            with open(path, "rb") as file:
                uploaded_file = client.files.create(file=file, purpose="assistants")
                file_ids.append(uploaded_file.id)
                print(f"文件上傳成功，ID: {uploaded_file.id}")
        
        file_batch = client.beta.vector_stores.file_batches.create(
            vector_store_id=vector_store.id,
            file_ids=file_ids
        )
        
        # 等待文件處理完成
        while True:
            status = client.beta.vector_stores.file_batches.retrieve(
                vector_store_id=vector_store.id,
                file_batch_id=file_batch.id
            )
            if status.status == 'completed':
                break
            time.sleep(5)  # 等待5秒後再次檢查
        
        print(f"文件批次狀態: {status.status}")
        print(f"文件數量: {status.file_counts}")
        return file_ids
    except Exception as e:
        print(f"上傳文件到向量儲存時發生錯誤: {e}")
        raise

# 創建助手
def create_assistant(vector_store_id):
    try:
        assistant = client.beta.assistants.create(
            name="LineBot 助手",
            instructions="你是一個幫助回答問題的助手。使用上傳的文件來回答問題。如果找到相關信息，請詳細說明。如果無法在上傳的文件中找到相關信息，請明確說明並解釋可能的原因。",
            model="gpt-3.5-turbo",
            tools=[{"type": "file_search"}],
            tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}}
        )
        print(f"助手創建成功，ID: {assistant.id}")
        return assistant
    except Exception as e:
        print(f"創建助手時發生錯誤: {e}")
        raise

# 初始化向量儲存、上傳文件和創建助手
vector_store = get_or_create_vector_store()
file_paths = ["data/基因檢測類型與說明_CGP Patient Infographics-Slide M-TW-00001418.pdf", "data/基因檢測服務流程_檢測結果對癌症治療之效益_Patient brochure(A4)_M-TW-00001452.pdf"]
file_ids = upload_files_to_vector_store(vector_store, file_paths)
assistant = create_assistant(vector_store.id)

# 用戶ID到Thread ID的映射
user_threads = {}

@app.route("/callback", methods=['POST'])
def callback():
    # 獲取 X-Line-Signature 標頭
    signature = request.headers['X-Line-Signature']
    # 獲取請求主體
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        # 處理 Webhook 主體
        handler.handle(body, signature)
    except InvalidSignatureError:
        # 如果簽名無效，返回 400 錯誤
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

        # 回應用戶訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_message)
        )
    except Exception as e:
        error_message = f"An error occurred: {str(e)}\n\nTraceback:\n{traceback.format_exc()}"
        # 如果發生錯誤，回應用戶錯誤訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=error_message)
        )

if __name__ == "__main__":
    # 設定 Flask 應用的埠號，預設為 5000
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
