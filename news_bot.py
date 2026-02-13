import requests
import os
import re
from datetime import datetime

TARGET_REPO = "GENEXIS-AI/DailyNews"
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def parse_news_content(text):
    # 기사 단위로 쪼개기 (### 제목 형식을 기준으로 나눔)
    items = re.findall(r'### (.*?)\n.*?\[원문 링크\]\((.*?)\)', text, re.DOTALL)
    return items

def send_to_slack():
    res = requests.get(API_URL)
    if res.status_code != 200: return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    target_file = next((f for f in files if today_str in f['name']), None)

    if target_file:
        content_res = requests.get(target_file['download_url'])
        full_text = content_res.text
        
        # 기사 제목과 링크 추출
        news_items = parse_news_content(full_text)
        
        if not news_items:
            # 파싱 실패 시 기본 알림이라도 전송
            requests.post(WEBHOOK_URL, json={"text": f"📢 오늘자 뉴스를 가져왔지만 형식이 달라 링크로 대체합니다: {target_file['html_url']}"})
            return

        # 슬랙 메시지 구성 (Attachment 기능을 활용해 기사별로 나열)
        attachments = []
        for title, link in news_items[:10]: # 너무 많으면 잘리므로 상위 10개만
            attachments.append({
                "color": "#00C73C",
                "title": title.strip(),
                "title_link": link.strip(),
                "text": "위 제목을 클릭하면 원문 기사로 이동합니다."
            })

        payload = {
            "text": f"🚀 *오늘의 주요 AI 뉴스 ({today_str})*",
            "attachments": attachments
        }
        
        requests.post(WEBHOOK_URL, json=payload)
    else:
        print("오늘자 뉴스 파일을 찾지 못했습니다.")

if __name__ == "__main__":
    send_to_slack()
