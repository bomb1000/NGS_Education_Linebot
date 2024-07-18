# NGS_Education_Linebot

這個專案是一個基於Line平台的聊天機器人,專門設計用於NGS(Next Generation Sequencing)教育。它利用了OpenAI的GPT模型來提供個性化的學習體驗。

## 功能特點

- 🤖 智能對話: 使用OpenAI API生成回答,提供專業且友善的解釋
- 📊 個性化問卷: 收集用戶信息以提供定制化的學習體驗
- 🧬 NGS FAQ: 提供關於NGS的常見問題解答
- 👨‍⚕️ 專家諮詢模式: 允許用戶自由提問NGS相關問題
- 📚 學習總結: 根據對話歷史生成學習摘要
- 🏆 知識測驗: 通過互動式測驗評估用戶對NGS的理解

## 技術棧

- Python 3.x
- Flask: Web應用框架
- Line Messaging API: 實現Line機器人功能
- OpenAI API: 生成智能回答和處理複雜查詢

## 安裝指南

1. 克隆儲存庫:
   ```
   git clone https://github.com/your-username/ngs-linebot.git
   cd ngs-linebot
   ```

2. 安裝依賴:
   ```
   pip install -r requirements.txt
   ```

3. 設置環境變量:
   創建一個`.env`文件,並添加以下內容:
   ```
   OPENAI_API_KEY=your_openai_api_key
   OPENAI_ASSISTANT_ID=your_openai_assistant_id
   FRIENDLY_ASSISTANT_ID=your_friendly_assistant_id
   LINE_CHANNEL_SECRET=your_line_channel_secret
   LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
   ```

4. 運行應用:
   ```
   python app.py
   ```

## 使用說明

1. 掃描Line QR碼添加機器人為好友
2. 發送消息"開始"來啟動機器人
3. 根據提示選擇想要的功能:
   - 填寫個人問卷
   - 瀏覽NGS FAQ
   - 進入專家諮詢模式
   - 查看學習總結
   - 參與NGS知識測驗


## 聯繫方式

如有任何問題或建議,請聯繫: michael491549154915@gmail.com


