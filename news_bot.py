import requests
import os
from datetime import datetime

# 설정
TARGET_REPO = "GENEXIS-AI/DailyNews"
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def send_to_slack():
    # 1. 파일 목록 가져오기
    res = requests.get(API_URL)
    if res.status_code != 200:
        print("파일 목록을 가져오는데 실패했습니다.")
        return

    files = res.json()
    # 오늘 날짜(예: 2026-02-13) 문자열 생성
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # 오늘 날짜가 포함된 파일 찾기
    target_file = next((f for f in files if today_str in f['name']), None)

    if target_file:
        payload = {
            "text": f"📢 *오늘의 AI 뉴스레터가 도착했습니다! ({today_str})*",
            "attachments": [{
                "color": "#00C73C", # KREAM 브랜드 느낌의 초록색
                "title": f"뉴스레터 확인하기: {target_file['name']}",
                "title_link": target_file['html_url'],
                "footer": "GENEXIS-AI Daily News"
            }]
        }
        requests.post(WEBHOOK_URL, json=payload)
        print("슬랙 전송 성공!")
    else:
        print(f"{today_str} 날짜의 뉴스가 아직 업로드되지 않았습니다.")

if __name__ == "__main__":
    send_to_slack()
