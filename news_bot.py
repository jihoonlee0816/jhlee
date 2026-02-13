import requests
import os
import re
from datetime import datetime
import time

# 1. 설정: 타겟 레포지토리 정보 (정확하게 고정)
TARGET_REPO = "GENEXIS-AI/DailyNews"
FOLDER_PATH = "%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0" 
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/{FOLDER_PATH}"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def send_to_slack():
    # 깃허브 API 호출
    res = requests.get(API_URL)
    if res.status_code != 200:
        requests.post(WEBHOOK_URL, json={"text": "❌ GitHub API 연결에 실패했습니다."})
        return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    # 오늘 날짜 파일 찾기
    target_file = next((f for f in files if today_str in f['name']), None)

    if not target_file:
        requests.post(WEBHOOK_URL, json={"text": f"🔍 {today_str} 날짜의 뉴스 파일을 아직 찾지 못했습니다."})
        return

    # md 파일 원문(Raw) 가져오기
    raw_text = requests.get(target_file['download_url']).text
    
    # --- 파싱 로직 (가장 강력한 버전) ---
    # '####'를 기준으로 기사 섹션을 물리적으로 쪼갭니다.
    sections = raw_text.split('####')
    articles_found = 0

    # 첫 번째 섹션(헤더) 알림 전송
    requests.post(WEBHOOK_URL, json={"text": f"🚀 *{today_str} AI 뉴스 배달을 시작합니다!*"})
    time.sleep(1)

    for section in sections[1:]: # 헤더 이후부터 루프
        try:
            # 1. 제목 추출: 첫 번째 [ ] 사이의 글자
            title_match = re.search(r'\[(.*?)\]', section)
            # 2. 링크 추출: http로 시작하는 첫 번째 URL (괄호나 꺽쇠 제외)
            url_match = re.search(r'(https?://[^\s\)\>\]]+)', section)
            
            if title_match and url_match:
                title = title_match.group(1).strip()
                url = url_match.group(1).strip().replace(')', '').replace('>', '')
                
                # Slack Rich Format (Block Kit) 구성
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
                                    "text": { "type": "plain_text", "text": "원문 기사 읽기 ↗️" },
                                    "url": url,
                                    "style": "primary"
                                }
                            ]
                        },
                        { "type": "divider" }
                    ]
                }
                
                # [핵심] 여기서 하나씩 개별적으로 전송합니다!
                requests.post(WEBHOOK_URL, json=block_payload)
                articles_found += 1
                time.sleep(1.5) # 슬랙 도배 방지용 지연
        except Exception:
            continue

    if articles_found == 0:
        # 이 메시지가 뜨면 파싱 규칙을 다시 점검해야 합니다.
        requests.post(WEBHOOK_URL, json={"text": "❌ 파싱된 기사가 0건입니다. md 파일의 형식이 바뀌었는지 확인이 필요합니다."})

if __name__ == "__main__":
    send_to_slack()
