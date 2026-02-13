import requests
import os
import re
from datetime import datetime
import time

# 1. 설정
TARGET_REPO = "GENEXIS-AI/DailyNews"
FOLDER_PATH = "뉴스레터" # 인코딩은 API가 알아서 처리하도록 단순화
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
    
    # 시작 알림 전송
    requests.post(WEBHOOK_URL, json={"text": f"🚀 *{today_str} 기사 배달 최종 시도 (파싱 로직 완전 개편)*"})
    time.sleep(1)

    # [로직 강화] 모든 이미지 태그 제거 (인스타그램 등 노이즈 제거)
    clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', raw_text)
    
    # [로직 강화] # 이 1개 이상 나오는 모든 행을 기사 시작점으로 인식 (샵 개수 상관없음)
    sections = re.split(r'\n#+\s*', clean_text)
    count = 0

    for section in sections:
        if not section.strip(): continue
        
        # 첫 줄을 제목으로 인식
        lines = section.strip().split('\n')
        raw_title = lines[0].strip()
        # 제목에서 마크다운 특수문자([], (), #, *) 싹 제거
        clean_title = re.sub(r'[\[\]\(\)\*#]', '', raw_title).strip()
        
        # 해당 섹션 내에서 첫 번째 http URL 찾기
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', section)
        
        # 유효성 검사: 제목이 존재하고 URL이 인스타그램이 아닐 때만 전송
        if url_match and len(clean_title) > 2:
            url = url_match.group(1).strip()
            if "instagram" in url or "cdn" in url: continue
            
            # 슬랙 Rich Format 전송
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
            time.sleep(1.2) # 슬랙 서버 보호를 위한 딜레이

    if count == 0:
        requests.post(WEBHOOK_URL, json={"text": "❌ 여전히 기사를 찾지 못했습니다. 수동 확인이 필요합니다."})

if __name__ == "__main__":
    send_to_slack()
