import requests
import os
import re
from datetime import datetime
import time

# 1. 설정
TARGET_REPO = "GENEXIS-AI/DailyNews"
FOLDER_PATH = "%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0" 
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/{FOLDER_PATH}"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def send_to_slack():
    res = requests.get(API_URL)
    if res.status_code != 200: return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    target_file = next((f for f in files if today_str in f['name']), None)

    if not target_file: return

    raw_text = requests.get(target_file['download_url']).text
    
    # [시작 알림]
    requests.post(WEBHOOK_URL, json={"text": f"✅ *{today_str} 기사 배달을 다시 시도합니다!*" })
    time.sleep(1)

    # 파싱 로직: '####'로 기사 섹션을 쪼갭니다.
    sections = raw_text.split('####')
    count = 0

    for section in sections[1:]: # 헤더 부분 제외
        lines = section.strip().split('\n')
        if not lines: continue
        
        # 1. 제목: #### 바로 뒤에 오는 첫 번째 줄 (대괄호가 있어도 없어도 내용만 추출)
        raw_title = lines[0].strip()
        # 제목에서 [, ], (, ) 같은 마크다운 기호 제거
        clean_title = re.sub(r'[\[\]\(\)]', '', raw_title)
        
        # 2. 링크: 해당 섹션 안에서 http로 시작하는 첫 번째 URL 추출
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', section)
        
        if clean_title and url_match:
            url = url_match.group(1).strip()
            
            # 배너 이미지 등 기사가 아닌 것은 제외
            if "instagram" in url or "cdninstagram" in url or "Image" in clean_title:
                continue
            
            # 슬랙 Rich Format (Block Kit)
            payload = {
                "blocks": [
                    {
                        "type": "section",
                        "text": { "type": "mrkdwn", "text": f"*📍 {clean_title}*" }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": { "type": "plain_text", "text": "원문 읽기 ↗️" },
                                "url": url,
                                "style": "primary"
                            }
                        ]
                    },
                    { "type": "divider" }
                ]
            }
            requests.post(WEBHOOK_URL, json=payload)
            count += 1
            time.sleep(1.2)

    if count == 0:
        # 그래도 실패하면 원문 전체를 아주 짧게 보여줌
        requests.post(WEBHOOK_URL, json={"text": f"❌ 기사 인식 실패. 구조를 다시 분석해야 합니다.\n내용 앞부분: {raw_text[:100]}"})

if __name__ == "__main__":
    send_to_slack()
