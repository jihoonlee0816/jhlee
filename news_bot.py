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

    if not target_file:
        print("파일 없음")
        return

    # md 파일 원문 가져오기
    raw_text = requests.get(target_file['download_url']).text
    
    # #### 를 기준으로 텍스트를 강제로 자름 (파싱의 핵심)
    sections = raw_text.split('#### ')
    count = 0

    # [중요] 이 문구가 슬랙에 보이면 새 코드가 실행된 것입니다!
    requests.post(WEBHOOK_URL, json={"text": f"🔥 *{today_str} 기사 단위 배달 테스트 시작!*"})
    time.sleep(1)

    for section in sections[1:]:
        # 제목: [ ] 사이의 글자 추출
        title_match = re.search(r'\[(.*?)\]', section)
        # 링크: http로 시작하는 URL 추출
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', section)
        
        if title_match and url_match:
            title = title_match.group(1).strip()
            url = url_match.group(1).strip()
            
            # Rich Format 구성 (버튼 형태)
            payload = {
                "blocks": [
                    {
                        "type": "section",
                        "text": { "type": "mrkdwn", "text": f"*📍 {title}*" }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": { "type": "plain_text", "text": "기사 읽기 ↗️" },
                                "url": url,
                                "style": "primary"
                            }
                        ]
                    },
                    { "type": "divider" }
                ]
            }
            # [개별 전송] 루프 안에서 하나씩 쏩니다
            requests.post(WEBHOOK_URL, json=payload)
            count += 1
            time.sleep(1.5)

    if count == 0:
        requests.post(WEBHOOK_URL, json={"text": "❌ 기사를 하나도 찾지 못했습니다. 파일 구조를 확인해 주세요."})

if __name__ == "__main__":
    send_to_slack()
