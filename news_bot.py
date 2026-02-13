import requests
import os
import re
from datetime import datetime
import time

# 1. 설정: 타겟 레포지토리 정보
TARGET_REPO = "GENEXIS-AI/DailyNews"
FOLDER_PATH = "%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0" # '뉴스레터' 인코딩
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/{FOLDER_PATH}"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def parse_articles(text):
    """마크다운을 분석해 기사 제목과 원문 URL을 무조건 찾아냅니다."""
    articles = []
    # #### [ 으로 시작하는 섹션들을 나눕니다.
    sections = text.split('#### [')
    
    for section in sections[1:]:
        try:
            # 제목 추출: 첫 번째 ']' 앞까지
            title_part = section.split(']')[0].strip()
            
            # 링크 추출: 해당 섹션 내에서 http로 시작하는 첫 번째 URL
            # 괄호()나 공백 등을 제외한 순수 URL만 추출
            url_match = re.search(r'(https?://[^\s\)\>\]]+)', section)
            
            if title_part and url_match:
                url = url_match.group(1).strip()
                articles.append({"title": title_part, "url": url})
        except:
            continue
    return articles

def send_to_slack():
    # 파일 목록 가져오기
    res = requests.get(API_URL)
    if res.status_code != 200: return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 오늘 날짜가 포함된 파일을 찾습니다.
    target_file = next((f for f in files if today_str in f['name']), None)

    if target_file:
        raw_text = requests.get(target_file['download_url']).text
        news_list = parse_articles(raw_text)

        if news_list:
            # 시작 알림
            requests.post(WEBHOOK_URL, json={"text": f"🚀 *{today_str} 오늘의 AI 뉴스레터 (총 {len(news_list)}건)*"})
            time.sleep(1)

            # 기사별로 개별 메시지(Rich Format) 전송
            for item in news_list:
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
                # 개별 포스트 날리기
                requests.post(WEBHOOK_URL, json=payload)
                time.sleep(1.2) # 슬랙 도배 방지 및 순서 보장
        else:
            # 파싱이 안 되었을 때만 이 메시지가 뜹니다.
            requests.post(WEBHOOK_URL, json={"text": f"⚠️ 구조 파싱 실패. 원문 링크: {target_file['html_url']}"})
    else:
        print(f"{today_str} 날짜의 파일이 아직 없습니다.")

if __name__ == "__main__":
    send_to_slack()
