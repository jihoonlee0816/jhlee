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
        
        # 1. 기사 제목과 링크를 찾는 가장 확실한 방법 (정규표현식)
        # #### [제목] ... [원문 링크](URL) 구조를 찾습니다.
        pattern = r'#### \[(.*?)\][\s\S]*?\[원문 링크\]\((https?://.*?)\)'
        articles = re.findall(pattern, full_text)

        if not articles:
            # 혹시 위 패턴이 실패할 경우를 대비한 두 번째 패턴 (제목의 링크 추출)
            pattern2 = r'#### \[(.*?)\]\((https?://.*?)\)'
            articles = re.findall(pattern2, full_text)

        if articles:
            # 상단에 오늘 뉴스 시작 알림 한 번
            requests.post(WEBHOOK_URL, json={"text": f"📅 *{today_str} AI 뉴스 배달 시작*"})
            
            # 2. 기사 하나당 메시지 한 개씩 전송 (사용자님이 말씀하신 루프 부분)
            for title, link in articles[:10]: # 너무 많으면 도배되니 일단 10개만
                payload = {
                    "text": f"▶️ *{title.strip()}*\n{link.strip()}"
                }
                requests.post(WEBHOOK_URL, json=payload)
                time.sleep(1) # 슬랙 과부하 방지를 위해 1초 간격
        else:
            # 파싱이 아예 실패했을 때만 링크 전송
            requests.post(WEBHOOK_URL, json={"text": f"⚠️ 기사 분석 실패. 직접 확인: {target_file['html_url']}"})
    else:
        print("오늘자 뉴스 파일이 없습니다.")

if __name__ == "__main__":
    send_to_slack()
