from flask import Flask, request, abort 
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError, LineBotApiError
)
from linebot.models import (
    MessageEvent, TextMessage, ImageMessage, TextSendMessage
)
import openai
import os
import base64

app = Flask(__name__)

# 環境變數設定
# 從環境變數中取得 OpenAI API 金鑰、Channel Secret 和 Channel Access Token
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
CHANNEL_SECRET = os.getenv('CHANNEL_SECRET')
CHANNEL_ACCESS_TOKEN = os.getenv('CHANNEL_ACCESS_TOKEN')

# 設定 Line Bot API 和 Webhook Handler
line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)
# 設定 OpenAI API 金鑰
openai.api_key = OPENAI_API_KEY

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
        # 獲取用戶發送的文字訊息
        user_message = event.message.text
        # 呼叫 OpenAI API 的 GPT-4o 模型來生成回應
        response = openai.chat.completion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=150
        )
        # 獲取 GPT-4o 模型生成的回應訊息
        reply_message = response.choices[0].message.content
        # 回應用戶訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_message)
        )
    except Exception as e:
        # 如果發生錯誤，回應用戶錯誤訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"An error occurred: {str(e)}")
        )

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    try:
        # 獲取用戶發送的圖片訊息
        message_content = line_bot_api.get_message_content(event.message.id)
        image_path = f"/tmp/{event.message.id}.jpg"  # 將圖片儲存到伺服器的臨時目錄
        with open(image_path, 'wb') as fd:
            for chunk in message_content.iter_content():
                fd.write(chunk)

        # 將圖片轉換為 base64 字串
        with open(image_path, 'rb') as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        # 呼叫 OpenAI API 的 GPT-4o 模型來分析圖片
        response = openai.chat.completion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Analyze this image."},
                {"role": "user", "content": f"data:image/jpeg;base64,{base64_image}"}
            ],
            max_tokens=150
        )
        # 獲取 GPT-4o 模型生成的回應訊息
        reply_message = response.choices[0].message.content
        # 回應用戶訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_message)
        )
    except Exception as e:
        # 如果發生錯誤，回應用戶錯誤訊息
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"An error occurred: {str(e)}")
        )

if __name__ == "__main__":
    # 設定 Flask 應用的埠號，預設為 5000
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
