from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import openai
import os

app = Flask(__name__)

# 從環境變量中獲取必要的金鑰
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# 設置 OpenAI API 金鑰
openai.api_key = OPENAI_API_KEY 

# 創建 OpenAI 客戶端
client = openai.OpenAI()

# 設置 Line Bot API 和 Webhook Handler
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# 用戶ID到Thread ID的映射
user_threads = {}

def ask_assistant(thread, question):
    try:
        # 添加用戶消息到線程
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )

        # 運行助手
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=OPENAI_ASSISTANT_ID
        )

        # 等待運行完成
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == 'completed':
                break

        # 獲取助手的回覆
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        response = messages.data[0].content[0].text.value

        return response

    except Exception as e:
        print(f"處理問題時發生錯誤: {e}")
        return f"發生錯誤: {str(e)}"

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
    response = ask_assistant(client.beta.threads.retrieve(thread_id), user_message)

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
