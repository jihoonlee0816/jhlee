import requests
import os
import re
from datetime import datetime

TARGET_REPO = "GENEXIS-AI/DailyNews"
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def parse_news_content(text):
    # 1. 기사 단위로 분리 (#### 제목 형태 찾기)
    # 제목과 그 뒤에 따라오는 첫 번째 URL을 추출합니다.
    items = re.findall(r'#### (.*?)\n.*?((?:http|https)://[^\s\)]+)', text, re.DOTALL)
    return items

def send_to_slack():
    res = requests.get(API_URL)
    if res.status_code != 200: return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    target_file = next((f for f in files if today_str in f['name']), None)

    if target_file:
        # Raw 데이터를 가져와서 분석
        content_res = requests.get(target_file['download_url'])
        full_text = content_res.text
        
        news_items = parse_news_content(full_text)
        
        if not news_items:
            # 패턴 매칭 실패 시 안내
            requests.post(WEBHOOK_URL, json={"text": f"⚠️ 구조 분석 실패. 직접 확인: {target_file['html_url']}"})
            return

        # 슬랙 메시지 구성
        attachments = []
        for title, link in news_items:
            # 제목에 포함된 마크다운 링크 기호([, ]) 제거 및 깔끔하게 정리
            clean_title = re.sub(r'[\[\]]', '', title).strip()
            
            attachments.append({
                "color": "#00C73C",
                "title": clean_title,
                "title_link": link.strip(),
                "fallback": clean_title
            })

        # 한 번에 보낼 수 있는 attachment 개수 제한(보통 20개)을 고려해 전송
        payload = {
            "text": f"🚀 *{today_str} 오늘의 주요 AI 뉴스 (기사별 요약)*",
            "attachments": attachments[:20] 
        }
        
        requests.post(WEBHOOK_URL, json=payload)
    else:
        print(f"{today_str} 날짜의 파일을 찾지 못했습니다.")

if __name__ == "__main__":
    send_to_slack()
