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

    # md 파일 원문(Raw) 가져오기
    raw_text = requests.get(target_file['download_url']).text
    
    # [시작 알림] 이 문구가 보이면 새 코드가 실행된 겁니다.
    requests.post(WEBHOOK_URL, json={"text": f"🔥 *{today_str} 기사 단위 배달 시작! (파싱 로직 대폭 강화)*"})
    time.sleep(1)

    # [핵심 로직] '###' 또는 '####'로 시작하는 모든 기사 섹션을 쪼갭니다.
    sections = re.split(r'#{3,5}\s*', raw_text)
    count = 0

    for section in sections[1:]: # 첫 섹션 제외
        try:
            # 1. 제목: 첫 번째로 나타나는 [ ] 사이의 글자 무조건 추출
            title_match = re.search(r'\[(.*?)\]', section)
            # 2. 링크: http로 시작하는 첫 번째 URL 무조건 추출
            url_match = re.search(r'(https?://[^\s\)\>\]]+)', section)
            
            if title_match and url_match:
                title = title_match.group(1).strip()
                url = url_match.group(1).strip().replace(')', '').replace('>', '')
                
                # 기사 하나당 Rich Format 메시지 하나씩 개별 전송
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
        except:
            continue

    if count == 0:
        # 기사를 하나도 못 찾았다면 텍스트 샘플을 슬랙으로 보내 확인
        sample = raw_text[:150].replace('`', '')
        requests.post(WEBHOOK_URL, json={"text": f"❌ 기사 추출 실패. 파일 샘플:\n```{sample}```"})

if __name__ == "__main__":
    send_to_slack()
