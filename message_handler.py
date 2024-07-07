from linebot.models import (
    TextSendMessage, TemplateSendMessage, ButtonsTemplate, PostbackTemplateAction,
    QuickReply, QuickReplyButton, MessageAction
)
from config import OPENAI_ASSISTANT_ID, FRIENDLY_ASSISTANT_ID
import openai

# 全局變量
user_states = {}
user_threads = {}

# 主選單的快速回覆選項
main_menu_items = [
    QuickReplyButton(action=MessageAction(label="我想更了解你", text="我想更了解你")),
    QuickReplyButton(action=MessageAction(label="認識NGS", text="認識NGS")),
    QuickReplyButton(action=MessageAction(label="盡情問我吧!", text="盡情問我吧!")),
    QuickReplyButton(action=MessageAction(label="今日學習統整", text="今日學習統整")),
    QuickReplyButton(action=MessageAction(label="來個測驗吧!", text="來個測驗吧!"))
]

# 專家諮詢模式的快速回覆選項
expert_quick_reply_items = [
    QuickReplyButton(action=MessageAction(label="返回主選單", text="返回主選單"))
]

def initialize_user_state(user_id):
    if user_id not in user_states:
        user_states[user_id] = {
            "mode": "normal",
            "chat_history": [],
            "questionnaire": {},
            "ngs_faq": {"current_question": 0, "questions": []},
            "quiz": {"current_question": 0, "correct_count": 0}
        }

def add_to_chat_history(user_id, role, message):
    initialize_user_state(user_id)
    user_states[user_id]["chat_history"].append({
        "role": role,
        "content": message
    })

def handle_text_message(event, line_bot_api):
    user_id = event.source.user_id
    user_message = event.message.text

    initialize_user_state(user_id)
    add_to_chat_history(user_id, "user", user_message)

    if user_states[user_id]["mode"] == "questionnaire":
        handle_questionnaire(event, line_bot_api, user_id, user_message)
    elif user_states[user_id]["mode"] == "ngs_faq":
        handle_ngs_faq(event, line_bot_api, user_id, user_message)
    elif user_states[user_id]["mode"] == "expert_consultation":
        handle_expert_consultation(event, line_bot_api, user_id, user_message)
    else:
        handle_main_menu(event, line_bot_api, user_id, user_message)

def handle_main_menu(event, line_bot_api, user_id, user_message):
    immediate_response = ""
    if user_message == "我想更了解你":
        immediate_response = "好的，讓我們開始問卷調查。請稍等，我將為您準備第一個問題。"
        user_states[user_id]["mode"] = "questionnaire"
        user_states[user_id]["questionnaire"] = {}
    elif user_message == "認識NGS":
        immediate_response = "好的，讓我們開始了解NGS。請稍等，我將為您準備第一個問題。"
        user_states[user_id]["mode"] = "ngs_faq"
    elif user_message == "盡情問我吧!":
        immediate_response = "您現在進入了專家諮詢模式。請稍等，我將為您準備諮詢環境。"
        user_states[user_id]["mode"] = "expert_consultation"
    elif user_message == "今日學習統整":
        immediate_response = "正在為您生成今日學習摘要，請稍候..."
    elif user_message == "來個測驗吧!":
        immediate_response = "好的，讓我們開始NGS測驗。請稍等，我將為您準備第一道題目。"
        user_states[user_id]["mode"] = "quiz"
    else:
        immediate_response = "請選擇以下選項：\n1. 我想更了解你\n2. 認識NGS\n3. 盡情問我吧!\n4. 今日學習統整\n5. 來個測驗吧!"

    # 立即發送回應
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=immediate_response, quick_reply=QuickReply(items=main_menu_items))
    )
    add_to_chat_history(user_id, "assistant", immediate_response)

    # 在發送即時回應後執行後續操作
    if user_message == "我想更了解你":
        start_questionnaire(line_bot_api, user_id)
    elif user_message == "認識NGS":
        start_ngs_faq(line_bot_api, user_id)
    elif user_message == "盡情問我吧!":
        start_expert_consultation(line_bot_api, user_id)
    elif user_message == "今日學習統整":
        summarize_conversation(line_bot_api, user_id)
    elif user_message == "來個測驗吧!":
        start_ngs_quiz(line_bot_api, user_id)

def ask_question(line_bot_api, user_id, question):
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text=question)
    )
    add_to_chat_history(user_id, "assistant", question)
    
def start_questionnaire(line_bot_api, user_id):
    questions = ["您的年齡是？", "您的性別是？", "您的職業是？", "您的興趣是？", "您的最高學歷是？"]
    user_states[user_id]["questionnaire"]["questions"] = questions
    user_states[user_id]["questionnaire"]["current_question"] = 0
    ask_question(line_bot_api, user_id, questions[0])

def handle_questionnaire(event, line_bot_api, user_id, user_message):
    questions = user_states[user_id]["questionnaire"]["questions"]
    current_question = user_states[user_id]["questionnaire"]["current_question"]
    
    user_states[user_id]["questionnaire"][questions[current_question]] = user_message
    current_question += 1
    
    if current_question < len(questions):
        user_states[user_id]["questionnaire"]["current_question"] = current_question
        ask_question(line_bot_api, user_id, questions[current_question])
    else:
        complete_questionnaire(line_bot_api, user_id)

def ask_assistant(user_id, prompt, assistant_id=OPENAI_ASSISTANT_ID):
    try:
        if user_id not in user_threads:
            thread = openai.beta.threads.create()
            user_threads[user_id] = thread.id

        openai.beta.threads.messages.create(
            thread_id=user_threads[user_id],
            role="user",
            content=prompt
        )

        run = openai.beta.threads.runs.create(
            thread_id=user_threads[user_id],
            assistant_id=assistant_id
        )

        while True:
            run_status = openai.beta.threads.runs.retrieve(thread_id=user_threads[user_id], run_id=run.id)
            if run_status.status == 'completed':
                break

        messages = openai.beta.threads.messages.list(thread_id=user_threads[user_id])
        return messages.data[0].content[0].text.value
    except Exception as e:
        print(f"Error in ask_assistant: {str(e)}")
        return f"很抱歉，在處理您的請求時發生了錯誤。錯誤信息：{str(e)}"

def ask_friendly_assistant(user_id, expert_response, user_info):
    prompt = f"""
    作為一個友善的醫療助手，請您根據以下資訊，用更平易近人、生動有趣的方式解釋給病友聽：

    病友資訊：{user_info}

    專家回答：{expert_response}

    請用比喻或日常生活中的例子來解釋，確保病友能夠輕鬆理解。
    """
    return ask_assistant(user_id, prompt, FRIENDLY_ASSISTANT_ID)

def handle_expert_consultation(event, line_bot_api, user_id, user_message):
    if user_message.lower() == "返回主選單":
        user_states[user_id]["mode"] = "normal"
        response = "返回主選單"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=QuickReply(items=main_menu_items))
        )
        add_to_chat_history(user_id, "assistant", response)
    else:
        try:
            # 首先獲取專家回答
            expert_response = ask_assistant(user_id, user_message)
            
            # 然後使用友善助手提供更平易近人的解釋
            user_info = user_states[user_id].get("questionnaire", {})
            friendly_response = ask_friendly_assistant(user_id, expert_response, user_info)
    
            # 組合回答
            combined_response = f"專家解答：\n{expert_response}\n\n友善解釋：\n{friendly_response}"
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=combined_response, quick_reply=QuickReply(items=expert_quick_reply_items))
            )
            add_to_chat_history(user_id, "assistant", combined_response)
        except Exception as e:
            error_message = f"很抱歉，在處理您的請求時發生了錯誤。錯誤信息：{str(e)}"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=error_message, quick_reply=QuickReply(items=expert_quick_reply_items))
            )
            add_to_chat_history(user_id, "assistant", error_message)

def complete_questionnaire(line_bot_api, user_id):
    user_states[user_id]["mode"] = "normal"
    summary = "感謝您完成問卷！以下是您的回答：\n"
    for question, answer in user_states[user_id]["questionnaire"].items():
        if question != "current_question" and question != "questions":
            summary += f"{question} {answer}\n"
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text=summary, quick_reply=QuickReply(items=main_menu_items))
    )
    add_to_chat_history(user_id, "assistant", summary)

def start_ngs_faq(line_bot_api, user_id):
    questions = [
        "什麼是NGS？",
        "NGS可以用來做什麼？",
        "NGS和傳統測序有什麼不同？",
        "NGS在癌症診斷中的應用是什麼？",
        "NGS的優點和局限性是什麼？"
    ]
    user_states[user_id]["ngs_faq"]["questions"] = questions
    user_states[user_id]["ngs_faq"]["current_question"] = 0
    ask_ngs_question(line_bot_api, user_id, questions[0])

def handle_ngs_faq(event, line_bot_api, user_id, user_message):
    if user_message.lower() == "返回主選單":
        user_states[user_id]["mode"] = "normal"
        response = "返回主選單"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=QuickReply(items=main_menu_items))
        )
        add_to_chat_history(user_id, "assistant", response)
    else:
        current_question = user_states[user_id]["ngs_faq"]["current_question"]
        questions = user_states[user_id]["ngs_faq"]["questions"]
        
        # 使用 OpenAI API 生成回答
        user_info = user_states[user_id].get("questionnaire", {})
        prompt = f"根據以下用戶信息，以簡單易懂的方式解釋NGS相關問題。用戶信息：{user_info}\n\n問題：{questions[current_question]}"
        
        expert_response = ask_assistant(user_id, prompt)
        friendly_response = ask_friendly_assistant(user_id, expert_response, user_info)
        
        combined_response = f"NGS解答：\n{expert_response}\n\n友善解釋：\n{friendly_response}"
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=combined_response)
        )
        add_to_chat_history(user_id, "assistant", combined_response)
        
        current_question += 1
        if current_question < len(questions):
            user_states[user_id]["ngs_faq"]["current_question"] = current_question
            ask_ngs_question(line_bot_api, user_id, questions[current_question])
        else:
            complete_ngs_faq(line_bot_api, user_id)

def ask_ngs_question(line_bot_api, user_id, question):
    buttons_template = ButtonsTemplate(
        title='NGS FAQ',
        text=question,
        actions=[
            PostbackTemplateAction(label="回答這個問題", data=f"answer_ngs_faq"),
            PostbackTemplateAction(label="跳過這個問題", data="skip_ngs_faq"),
            PostbackTemplateAction(label="結束FAQ", data="end_ngs_faq")
        ]
    )
    template_message = TemplateSendMessage(
        alt_text='NGS FAQ問題',
        template=buttons_template
    )
    line_bot_api.push_message(user_id, template_message)
    add_to_chat_history(user_id, "assistant", question)

def complete_ngs_faq(line_bot_api, user_id):
    user_states[user_id]["mode"] = "normal"
    response = "NGS FAQ已完成。您可以選擇其他選項繼續。"
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text=response, quick_reply=QuickReply(items=main_menu_items))
    )
    add_to_chat_history(user_id, "assistant", response)

def start_expert_consultation(line_bot_api, user_id):
    response = "您現在進入了專家諮詢模式。請直接輸入您的問題，我會盡力為您解答。如果想返回主選單，請點擊下方的「返回主選單」按鈕。"
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text=response, quick_reply=QuickReply(items=expert_quick_reply_items))
    )
    add_to_chat_history(user_id, "assistant", response)

def handle_expert_consultation(event, line_bot_api, user_id, user_message):
    if user_message.lower() == "返回主選單":
        user_states[user_id]["mode"] = "normal"
        response = "返回主選單"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=response, quick_reply=QuickReply(items=main_menu_items))
        )
        add_to_chat_history(user_id, "assistant", response)
    else:
        try:
            response = ask_assistant(user_id, user_message)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response, quick_reply=QuickReply(items=expert_quick_reply_items))
            )
            add_to_chat_history(user_id, "assistant", response)
        except Exception as e:
            error_message = f"很抱歉，在處理您的請求時發生了錯誤。錯誤信息：{str(e)}"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=error_message, quick_reply=QuickReply(items=expert_quick_reply_items))
            )
            add_to_chat_history(user_id, "assistant", error_message)

def summarize_conversation(line_bot_api, user_id):
    chat_history = user_states[user_id]["chat_history"]

    if not chat_history:
        response = "目前沒有可供總結的對話記錄。"
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text=response, quick_reply=QuickReply(items=main_menu_items))
        )
        add_to_chat_history(user_id, "assistant", response)
        return

    # 創建總結提示
    summary_prompt = "請化身為衛教學習小助手，對以下對話進行結構化的摘要，幫助病友了解今天學到了什麼：\n\n"
    for entry in chat_history:
        summary_prompt += f"{entry['role']}: {entry['content']}\n\n"

    # 使用 OpenAI API 生成摘要
    response = ask_assistant(user_id, summary_prompt)

    line_bot_api.push_message(
        user_id,
        TextSendMessage(text=response, quick_reply=QuickReply(items=main_menu_items))
    )
    add_to_chat_history(user_id, "assistant", response)

def start_ngs_quiz(line_bot_api, user_id):
    user_states[user_id]["mode"] = "quiz"
    user_states[user_id]["quiz"]["current_question"] = 0
    user_states[user_id]["quiz"]["correct_count"] = 0
    send_question(line_bot_api, user_id, 0)

def truncate_text(text, max_length=17):
    """截斷文本並添加省略號，確保總長度不超過20個字符"""
    return (text[:max_length] + '...') if len(text) > max_length else text

def send_question(line_bot_api, user_id, question_index):
    questions = [
        {"question": "NGS代表什麼？", "options": ["Next Generation Sequencing", "New Genetic System", "Novel Gene Study"], "correct": 0},
        {"question": "NGS主要用於什麼領域？", "options": ["基因組學", "蛋白質組學", "代謝組學"], "correct": 0},
        {"question": "相比於傳統測序方法，NGS的主要優勢是什麼？", "options": ["成本更低", "速度更快", "可以同時測序多個基因"], "correct": 2},
        {"question": "NGS在癌症研究中的主要應用是什麼？", "options": ["檢測基因突變", "測量蛋白質表達", "分析細胞形態"], "correct": 0},
        {"question": "NGS技術的一個限制是什麼？", "options": ["讀長較短", "無法檢測稀有變異", "只能用於人類樣本"], "correct": 0}
    ]
    
    if question_index < len(questions):
        question = questions[question_index]
        buttons_template = ButtonsTemplate(
            title='NGS學習測驗',
            text=truncate_text(question['question'], max_length=60),  # LINE限制問題文本最多60個字符
            actions=[
                PostbackTemplateAction(
                    label=truncate_text(option),
                    data=f"answer_{question_index}_{i}"
                )
                for i, option in enumerate(question['options'])
            ]
        )
        template_message = TemplateSendMessage(
            alt_text='NGS問題',
            template=buttons_template
        )
        line_bot_api.push_message(user_id, template_message)
        add_to_chat_history(user_id, "assistant", question['question'])
    else:
        complete_quiz(line_bot_api, user_id)

def handle_quiz_answer(line_bot_api, user_id, data):
    parts = data.split("_")
    if len(parts) != 3 or parts[0] != "answer":
        # 處理無效的數據
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text="抱歉，發生了一個錯誤。請重新開始測驗。", quick_reply=QuickReply(items=main_menu_items))
        )
        user_states[user_id]["mode"] = "normal"
        return

    question_index = int(parts[1])
    answer_index = int(parts[2])
    
    questions = [
        {"question": "NGS代表什麼？", "options": ["Next Generation Sequencing", "New Genetic System", "Novel Gene Study"], "correct": 0},
        {"question": "NGS主要用於什麼領域？", "options": ["基因組學", "蛋白質組學", "代謝組學"], "correct": 0},
        {"question": "相比於傳統測序方法，NGS的主要優勢是什麼？", "options": ["成本更低", "速度更快", "可以同時測序多個基因"], "correct": 2},
        {"question": "NGS在癌症研究中的主要應用是什麼？", "options": ["檢測基因突變", "測量蛋白質表達", "分析細胞形態"], "correct": 0},
        {"question": "NGS技術的一個限制是什麼？", "options": ["讀長較短", "無法檢測稀有變異", "只能用於人類樣本"], "correct": 0}
    ]
    
    if question_index >= len(questions):
        # 處理無效的問題索引
        line_bot_api.push_message(
            user_id,
            TextSendMessage(text="抱歉，發生了一個錯誤。請重新開始測驗。", quick_reply=QuickReply(items=main_menu_items))
        )
        user_states[user_id]["mode"] = "normal"
        return

    question = questions[question_index]
    is_correct = answer_index == question['correct']
    
    if is_correct:
        user_states[user_id]["quiz"]["correct_count"] += 1
    
    response = f"{'正確' if is_correct else '錯誤'}！\n正確答案是：{question['options'][question['correct']]}"
    line_bot_api.push_message(user_id, TextSendMessage(text=response))
    add_to_chat_history(user_id, "assistant", response)
    
    user_states[user_id]["quiz"]["current_question"] += 1
    
    if user_states[user_id]["quiz"]["current_question"] < len(questions):
        send_question(line_bot_api, user_id, user_states[user_id]["quiz"]["current_question"])
    else:
        complete_quiz(line_bot_api, user_id)

def complete_quiz(line_bot_api, user_id):
    correct_count = user_states[user_id]["quiz"]["correct_count"]
    total_questions = 5  # 假設總共有5個問題
    
    final_score = (correct_count / total_questions) * 100
    response = f"測驗完成！\n您的得分是：{final_score:.1f}分\n答對題數：{correct_count}/{total_questions}"
    
    if final_score == 100:
        response += "\n太棒了！您已經完全掌握了NGS的基礎知識！"
    elif final_score >= 80:
        response += "\n很好！您對NGS有了很好的理解。"
    elif final_score >= 60:
        response += "\n不錯的表現！您已經掌握了NGS的一些基本概念。"
    else:
        response += "\n繼續加油！您可以再次學習以鞏固知識。"
    
    line_bot_api.push_message(
        user_id,
        TextSendMessage(text=response, quick_reply=QuickReply(items=main_menu_items))
    )
    add_to_chat_history(user_id, "assistant", response)
    user_states[user_id]["mode"] = "normal"

def handle_postback(event, line_bot_api):
    user_id = event.source.user_id
    data = event.postback.data

    if data.startswith("answer_ngs_"):
        # 這是 NGS FAQ 的回答
        handle_ngs_faq(event, line_bot_api, user_id, "")
    elif data.startswith("answer_"):
        # 這是測驗的回答
        handle_quiz_answer(line_bot_api, user_id, data)
    elif data == "skip_ngs_faq":
        skip_ngs_faq(line_bot_api, user_id)
    elif data == "end_ngs_faq":
        complete_ngs_faq(line_bot_api, user_id)

def skip_ngs_faq(line_bot_api, user_id):
    current_question = user_states[user_id]["ngs_faq"]["current_question"]
    questions = user_states[user_id]["ngs_faq"]["questions"]
    
    current_question += 1
    if current_question < len(questions):
        user_states[user_id]["ngs_faq"]["current_question"] = current_question
        ask_ngs_question(line_bot_api, user_id, questions[current_question])
    else:
        complete_ngs_faq(line_bot_api, user_id)








# 確保在 main.py 中更新 handle_postback_event 函數
# @handler.add(PostbackEvent)
# def handle_postback_event(event):
#     handle_postback(event, line_bot_api)