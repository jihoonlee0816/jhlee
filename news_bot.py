import requests
import os
import re
from datetime import datetime
import time

TARGET_REPO = "GENEXIS-AI/DailyNews"
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def send_to_slack():
    res = requests.get(API_URL)
    if res.status_code != 200: return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    target_file = next((f for f in files if today_str in f['name']), None)

    if target_file:
        content_res = requests.get(target_file['download_url'])
        full_text = content_res.text
        
        # 1. 기사 단위로 쪼개기 (#### 기준)
        sections = full_text.split('#### ')
        articles = []

        for section in sections[1:]: # 첫 섹션은 제목이므로 제외
            lines = section.split('\n')
            if not lines: continue
            
            # 첫 줄에서 [제목] 추출
            title_match = re.search(r'\[(.*?)\]', lines[0])
            title = title_match.group(1) if title_match else lines[0][:50]
            
            # 섹션 전체에서 http로 시작하는 링크 추출
            link_match = re.search(r'(https?://[^\s\)]+)', section)
            link = link_match.group(1) if link_match else None
            
            if title and link:
                articles.append((title.strip(), link.strip()))

        # 2. 기사 전송 (뭉텅이 방지: 루프 안에서 각각 전송)
        if articles:
            # 시작 알림
            requests.post(WEBHOOK_URL, json={"text": f"📅 *{today_str} AI 뉴스 배달을 시작합니다! (총 {len(articles)}건)*"})
            time.sleep(1)

            for title, link in articles[:15]: # 도배 방지를 위해 상위 15개만
                # 기사 하나씩 개별 메시지로 쏩니다
                message = {
                    "text": f"📍 *{title}*\n<{link}|원문 기사 읽기 ↗️>"
                }
                requests.post(WEBHOOK_URL, json=message)
                time.sleep(1.5) # 슬랙 서버를 위해 1.5초 간격 유지
        else:
            # 여기까지 왔는데 articles가 비어있다면 진짜 구조가 바뀐 것
            requests.post(WEBHOOK_URL, json={"text": f"❌ 기사를 추출하지 못했습니다. 확인용 링크: {target_file['html_url']}"})
    else:
        print("오늘자 뉴스가 아직 올라오지 않았습니다.")

if __name__ == "__main__":
    send_to_slack()
