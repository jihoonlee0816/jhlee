import requests
import os
import re
from datetime import datetime
import time

# 1. 설정: 말씀하신 그 레포지토리 경로가 맞습니다.
TARGET_REPO = "GENEXIS-AI/DailyNews"
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def extract_articles(text):
    """마크다운 본문에서 기사 제목과 URL을 무조건 찾아내는 강력한 로직"""
    items = []
    # '#### '를 기준으로 기사 단위를 쪼갭니다.
    sections = text.split('#### ')
    
    for section in sections[1:]: # 첫 번째 조각(헤더)은 제외
        try:
            # 제목 추출: 첫 번째 나타나는 '[' 와 ']' 사이의 글자
            title_match = re.search(r'\[(.*?)\]', section)
            # 링크 추출: http로 시작하는 모든 URL 중 가장 먼저 나오는 것
            url_match = re.search(r'(https?://[^\s\)\>\]]+)', section)
            
            if title_match and url_match:
                title = title_match.group(1).strip()
                url = url_match.group(1).strip().replace(')', '') # 괄호 찌꺼기 제거
                items.append({"title": title, "url": url})
        except:
            continue
    return items

def send_to_slack():
    # 깃허브 API로 파일 목록 가져오기
    res = requests.get(API_URL)
    if res.status_code != 200: return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    # 오늘 날짜로 된 그 md 파일을 찾습니다.
    target_file = next((f for f in files if today_str in f['name']), None)

    if target_file:
        # 파일의 실제 텍스트 데이터(Raw) 가져오기
        raw_text = requests.get(target_file['download_url']).text
        articles = extract_articles(raw_text)

        if articles:
            # [시작 알림]
            requests.post(WEBHOOK_URL, json={"text": f"📅 *{today_str} AI 뉴스레터 배달 시작*"})
            time.sleep(1)

            # [기사별 전송] 여기서 루프를 돌며 각각 전송합니다!
            for item in articles[:15]: # 너무 많으면 슬랙이 차단할 수 있어 15개로 제한
                # Rich Format(Block Kit) 구성
                payload = {
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*📍 {item['title']}*"
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": { "type": "plain_text", "text": "원문 기사 읽기 ↗️" },
                                    "url": item['url'],
                                    "style": "primary"
                                }
                            ]
                        },
                        { "type": "divider" }
                    ]
                }
                # 개별 메시지 발송
                requests.post(WEBHOOK_URL, json=payload)
                time.sleep(1.5) # 전송 순서와 안정성을 위해 1.5초 간격
        else:
            # 이 메시지가 뜨면 파싱 로직을 더 넓게 잡아야 합니다.
            requests.post(WEBHOOK_URL, json={"text": f"⚠️ 기사 추출 실패. 원본 확인: {target_file['html_url']}"})
    else:
        print(f"{today_str} 날짜의 파일이 아직 업로드되지 않았습니다.")

if __name__ == "__main__":
    send_to_slack()
