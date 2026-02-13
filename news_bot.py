import requests
import os
import re
from datetime import datetime

# 설정
TARGET_REPO = "GENEXIS-AI/DailyNews"
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def parse_articles(text):
    """
    마크다운 본문에서 #### [제목] 과 [원문 링크](URL) 패턴을 찾아 리스트로 반환합니다.
    """
    # 패턴: #### [제목] 뒤에 오는 [원문 링크](URL) 추출
    # 실제 소스 구조: #### [제목]\n[원문 링크](URL)
    pattern = r'#### \[(.*?)\]\s*\n\s*\[.*?\]\((.*?)\)'
    return re.findall(pattern, text)

def send_to_slack():
    res = requests.get(API_URL)
    if res.status_code != 200: return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    target_file = next((f for f in files if today_str in f['name']), None)

    if target_file:
        # 1. 파일의 Raw 텍스트 가져오기
        content_res = requests.get(target_file['download_url'])
        full_text = content_res.text
        
        # 2. 기사 단위로 파싱
        articles = parse_articles(full_text)
        
        if not articles:
            # 파싱 실패 시 예비책 (전체 링크 전송)
            payload = {"text": f"📢 오늘 기사 구조가 평소와 다릅니다. 직접 확인하세요: {target_file['html_url']}"}
        else:
            # 3. 슬랙 메시지 구성 (기사별 첨부)
            attachments = []
            for title, link in articles:
                attachments.append({
                    "color": "#2EB67D", # 슬랙 초록색
                    "title": title.strip(),
                    "title_link": link.strip(),
                    "text": "기사 원문 읽기 ↗️"
                })
            
            payload = {
                "text": f"🚀 *오늘의 AI 뉴스레터: 주요 기사 요약 ({today_str})*",
                "attachments": attachments[:20] # 슬랙 제한을 고려해 최대 20개
            }
        
        # 4. 슬랙 전송
        requests.post(WEBHOOK_URL, json=payload)
        print(f"{len(articles)}개의 기사를 전송했습니다.")
    else:
        print(f"{today_str} 날짜의 뉴스가 아직 없습니다.")

if __name__ == "__main__":
    send_to_slack()
