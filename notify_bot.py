import os
import requests
from datetime import datetime, timedelta, timezone
from ics import Calendar
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError

# 設定區 (GitHub Actions 會自動填入)
LINE_TOKEN = os.environ.get('LINE_TOKEN')
TARGET_ID = os.environ.get('TARGET_ID') # 可是 User ID 或 Group ID
ICS_FILE = 'timetree.ics'
OLD_ICS_FILE = 'timetree_old.ics' # 用來比對舊資料

line_bot_api = LineBotApi(LINE_TOKEN)
tw_tz = timezone(timedelta(hours=8))
now = datetime.now(tw_tz)

def send_line(msg):
    try:
        line_bot_api.push_message(TARGET_ID, TextSendMessage(text=msg))
        print("訊息發送成功")
    except LineBotApiError as e:
        print(f"發送失敗: {e}")

# 1. 讀取現有的 ICS (如果有的話)
old_events = set()
if os.path.exists(ICS_FILE):
    with open(ICS_FILE, 'r', encoding='utf-8') as f:
        try:
            old_cal = Calendar(f.read())
            # 儲存舊活動的 ID (uid) 用來比對
            for e in old_cal.events:
                old_events.add(e.uid)
        except:
            pass

# 2. 執行匯出 (產生新的 ICS)
# 注意：這裡會呼叫系統指令
calendar_code = "JDeuZiz8jWwq" # 請填入你的行事曆代碼 (青商會那個)
email = os.environ.get('TIMETREE_EMAIL')
password = os.environ.get('TIMETREE_PASSWORD')
os.system(f'timetree-exporter --output {ICS_FILE} --calendar_code {calendar_code}')

# 3. 讀取新的 ICS
with open(ICS_FILE, 'r', encoding='utf-8') as f:
    cal = Calendar(f.read())

# 4. 邏輯 A：檢查今日活動
print("正在檢查今日活動...")
today_str = now.strftime('%Y-%m-%d')
msgs = []
for event in cal.events:
    # 轉換時區到台灣時間
    start = event.begin.astimezone(tw_tz)
    if start.strftime('%Y-%m-%d') == today_str:
        time_str = start.strftime('%H:%M')
        msgs.append(f"⏰ 今日活動提醒\n事項：{event.name}\n時間：{time_str}\n地點：{event.location or '無地點'}")

if msgs:
    full_msg = "\n\n".join(msgs)
    # 避免半夜打擾，這裡可以加判斷，例如只在早上 8 點發
    # 但因為 Action 6 小時跑一次，我們假設它是在合理的時段
    send_line(full_msg)

# 5. 邏輯 B：檢查新建立的活動 (比對 UID)
print("正在檢查新活動...")
new_events_found = []
for event in cal.events:
    if event.uid not in old_events and len(old_events) > 0:
        # 發現新活動 (且舊檔案不是空的，避免第一次執行全部通知)
        start = event.begin.astimezone(tw_tz)
        new_events_found.append(f"🆕 新增活動通知\n{event.name}\n日期：{start.strftime('%Y-%m-%d %H:%M')}")

if new_events_found:
    send_line("\n\n".join(new_events_found))

print("完成")
