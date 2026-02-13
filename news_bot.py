import requests
import os
import re
from datetime import datetime
import time

# 설정
TARGET_REPO = "GENEXIS-AI/DailyNews"
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def parse_articles(text):
    """마크다운을 파싱하여 기사 제목과 링크를 추출합니다."""
    articles = []
    # '#### [' 로 시작하는 섹션들을 나눕니다.
    chunks = text.split('#### [')
    
    for chunk in chunks[1:]:
        try:
            # 1. 제목 추출: ']' 앞까지
            title = chunk.split(']')[0].strip()
            # 2. 링크 추출: http로 시작하는 URL 찾기
            url_match = re.search(r'(https?://[^\s\)]+)', chunk)
            if url_match:
                url = url_match.group(1).strip().replace(')', '')
                articles.append({"title": title, "url": url})
        except:
            continue
    return articles

def send_to_slack():
    res = requests.get(API_URL)
    if res.status_code != 200: return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    target_file = next((f for f in files if today_str in f['name']), None)

    if target_file:
        raw_res = requests.get(target_file['download_url'])
        full_text = raw_res.text
        news_list = parse_articles(full_text)

        if news_list:
            # 시작 알림
            requests.post(WEBHOOK_URL, json={"text": f"🚀 *{today_str} AI 뉴스 배달 시작*"})
            time.sleep(1)

            # 기사별로 Rich Format(Blocks) 적용하여 개별 전송
            for item in news_list[:15]: # 도배 방지 상위 15개
                block_payload = {
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*제목: {item['title']}*"
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {
                                        "type": "plain_text",
                                        "text": "원문 기사 읽기 ↗️",
                                        "emoji": True
                                    },
                                    "url": item['url'],
                                    "action_id": "button_click"
                                }
                            ]
                        },
                        {
                            "type": "divider"
                        }
                    ]
                }
                # 개별 메시지로 전송
                requests.post(WEBHOOK_URL, json=block_payload)
                time.sleep(1.2) # 전송 안정성을 위한 딜레이
        else:
            # 파싱 실패 시 안내
            requests.post(WEBHOOK_URL, json={"text": f"⚠️ 내용을 분석할 수 없어 링크를 보냅니다: {target_file['html_url']}"})
    else:
        print("오늘자 뉴스가 없습니다.")

if __name__ == "__main__":
    send_to_slack()
