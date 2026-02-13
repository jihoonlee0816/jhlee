import requests
import os
import re
from datetime import datetime
import time

# 1. 설정 (타겟 경로 고정)
TARGET_REPO = "GENEXIS-AI/DailyNews"
# '뉴스레터' 폴더명을 인코딩한 경로입니다.
FOLDER_PATH = "%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0" 
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/{FOLDER_PATH}"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def send_to_slack():
    # GitHub에서 파일 목록 가져오기
    res = requests.get(API_URL)
    if res.status_code != 200:
        print("GitHub 접속 실패")
        return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    # 오늘 날짜 파일 찾기
    target_file = next((f for f in files if today_str in f['name']), None)

    if not target_file:
        print(f"{today_str} 파일을 찾을 수 없습니다.")
        return

    # 파일 내용(Raw) 가져오기
    raw_text = requests.get(target_file['download_url']).text
    
    # 파싱 로직: '####'를 기준으로 기사를 쪼갭니다.
    # 이전의 복잡한 정규식 대신, 텍스트를 물리적으로 잘라서 제목과 링크를 발라냅니다.
    sections = raw_text.split('####')
    articles_sent = 0

    # 배달 시작 알림 (한 번만)
    requests.post(WEBHOOK_URL, json={"text": f"📢 *{today_str} AI 뉴스 배달을 시작합니다!*"})
    time.sleep(1)

    for section in sections[1:]: # 첫 섹션은 헤더이므로 제외
        # 제목 추출: [ ] 사이의 글자
        title_match = re.search(r'\[(.*?)\]', section)
        # 링크 추출: http로 시작하는 URL
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', section)
        
        if title_match and url_match:
            title = title_match.group(1).strip()
            url = url_match.group(1).strip().replace(')', '').replace('>', '')
            
            # --- 슬랙 Rich Format (Block Kit) 구성 ---
            # 기사 하나당 이 덩어리 하나가 하나의 메시지로 나갑니다.
            block_payload = {
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*📍 {title}*"
                        }
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
            
            # 전송! (루프 안에서 각각 전송)
            requests.post(WEBHOOK_URL, json=block_payload)
            articles_sent += 1
            time.sleep(1.2) # 슬랙 서버를 위해 1.2초씩 간격 유지

    if articles_sent == 0:
        # 이 메시지가 뜨면 제가 정말 코드를 잘못 짠 겁니다.
        requests.post(WEBHOOK_URL, json={"text": "❌ 기사를 한 개도 파싱하지 못했습니다. 형식을 다시 확인해야 합니다."})

if __name__ == "__main__":
    send_to_slack()
