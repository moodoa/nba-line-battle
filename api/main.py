from fastapi import FastAPI, Request
import requests
import os
import openai
import json
import threading

app = FastAPI()

# 環境變數
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

BEST_TEAM_FILE = "best_team.json"

INITIAL_BEST_TEAM = [
    "stephen curry",
    "ray allen",
    "cooper flagg",
    "amen thompson",
    "hakeem olajuwon"
]

if not os.path.exists(BEST_TEAM_FILE):
    with open(BEST_TEAM_FILE, "w") as f:
        json.dump(INITIAL_BEST_TEAM, f)

def get_best_team():
    with open(BEST_TEAM_FILE, "r") as f:
        return json.load(f)

def update_best_team(new_team):
    with open(BEST_TEAM_FILE, "w") as f:
        json.dump(new_team, f)

def push_message(user_id, text):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(url, headers=headers, json=body)

def simulate_and_reply(user_text, user_id):
    best_team = get_best_team()
    best_team_str = "\n".join(best_team)

    prompt = f"""
你現在是 NBA 模擬引擎。所有球員皆為巔峰。
規則：每隊最多 3 個全明星。若使用者的球隊違規，請回報並拒絕模擬。

目前最強隊伍（歷史）為：
{best_team_str}

使用者挑戰隊伍為：
{user_text}

請：
1. 檢查是否符合「最多 3 全明星」。
2. 若違規 → 回傳「違規」訊息。
3. 若合法 → 模擬一場 48 分鐘正式比賽。
4. 產生比分、各球員數據、MVP、短評（100 字內）。
5. 若挑戰者勝利，告訴我「挑戰者勝利」，並在最後一行輸出 JSON 陣列格式的挑戰者球員名稱，用來更新最強隊伍。
6. 請簡潔輸出適合 LINE 的格式。
"""

    try:
        response = openai.chat.completions.create(
            model="gpt-5.1-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        result = response.choices[0].message["content"]
    except Exception as e:
        result = f"模擬出錯: {e}"

    # 嘗試更新最強隊伍
    try:
        lines = result.strip().split("\n")
        last_line = lines[-1].strip()
        if last_line.startswith("[") and last_line.endswith("]"):
            new_team = json.loads(last_line)
            update_best_team(new_team)
            reply_text = "\n".join(lines[:-1]) + "\n\n🏆 挑戰者已成為新最強隊伍！"
        else:
            reply_text = result
    except Exception:
        reply_text = result

    # Push Message 回覆
    push_message(user_id, reply_text)

@app.post("/callback")
async def callback(request: Request):
    try:
        body = await request.json()
        event = body["events"][0]
        user_id = event["source"]["userId"]
        user_text = event["message"]["text"]
        threading.Thread(target=simulate_and_reply, args=(user_text, user_id)).start()
    except Exception as e:
        print(f"Callback error: {e}")
    return {"status": "ok"}

