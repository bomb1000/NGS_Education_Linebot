import openai
from config import OPENAI_API_KEY, OPENAI_ASSISTANT_ID

openai.api_key = OPENAI_API_KEY

def ask_assistant(thread_id, question):
    try:
        openai.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=question
        )
        run = openai.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=OPENAI_ASSISTANT_ID
        )
        while True:
            run_status = openai.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status == 'completed':
                break
        messages = openai.beta.threads.messages.list(thread_id=thread_id)
        return messages.data[0].content[0].text.value
    except Exception as e:
        print(f"處理問題時發生錯誤: {e}")
        return f"發生錯誤: {str(e)}"