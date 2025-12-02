from fastapi import FastAPI, Request
import uvicorn
import requests
import os
import openai
import json

app = FastAPI()

# 環境變數
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# JSON 檔保存最強隊伍
BEST_TEAM_FILE = "best_team.json"

# 初始最強隊伍
INITIAL_BEST_TEAM = [
    "Michael Jordan",
    "Scottie Pippen",
    "Dennis Rodman",
    "Jrue Holiday",
    "Steve Novak"
]

# 檢查或建立 JSON
if not os.path.exists(BEST_TEAM_FILE):
    with open(BEST_TEAM_FILE, "w") as f:
        json.dump(INITIAL_BEST_TEAM, f)

def get_best_team():
    with open(BEST_TEAM_FILE, "r") as f:
        return json.load(f)

def update_best_team(new_team):
    with open(BEST_TEAM_FILE, "w") as f:
        json.dump(new_team, f)

def reply(reply_token, text):
    url = "https://api.line.me/v2/bot/message/reply"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"
    }
    body = {
        "replyToken": reply_token,
        "messages": [{"type": "text", "text": text}]
    }
    requests.post(url, headers=headers, json=body)

@app.post("/callback")
async def callback(request: Request):
    body = await request.json()
    event = body["events"][0]
    reply_token = event["replyToken"]
    user_text = event["message"]["text"]

    # 取得目前最強隊伍
    best_team = get_best_team()
    best_team_str = "\n".join(best_team)

    # 準備 OpenAI prompt
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

    response = openai.chat.completions.create(
        model="gpt-5.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    result = response.choices[0].message["content"]

    # 嘗試抓取挑戰者勝利並更新最強隊伍
    try:
        # 找 JSON 陣列在最後一行
        lines = result.strip().split("\n")
        last_line = lines[-1].strip()
        if last_line.startswith("[") and last_line.endswith("]"):
            new_team = json.loads(last_line)
            update_best_team(new_team)
            reply_text = "\n".join(lines[:-1]) + "\n\n🏆 挑戰者已成為新最強隊伍！"
        else:
            reply_text = result
    except Exception as e:
        reply_text = result

    reply(reply_token, reply_text)
    return "OK"
