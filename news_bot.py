import requests
import os
import re
from datetime import datetime

# 설정
TARGET_REPO = "GENEXIS-AI/DailyNews"
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/%EB%89%B4%EC%8A%A4%EB%A0%88%ED%84%B0"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def parse_markdown(text):
    # 기사 단위로 쪼개기 (--- 구분선 기준)
    articles = text.split('---')
    parsed_articles = []
    
    for article in articles:
        # 제목, 요약, 링크 추출
        title_match = re.search(r'제목:\s*(.*)', article)
        summary_match = re.search(r'요약:\s*(.*)', article)
        link_match = re.search(r'전체링크\s*:\s*(https?://[^\s\n]+)', article)
        
        if title_match:
            parsed_articles.append({
                "title": title_match.group(1).strip(),
                "summary": summary_match.group(1).strip() if summary_match else "요약 없음",
                "link": link_match.group(1).strip() if link_match else ""
            })
    return parsed_articles

def send_to_slack():
    res = requests.get(API_URL)
    if res.status_code != 200: return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    target_file = next((f for f in files if today_str in f['name']), None)

    if target_file:
        # 파일 원본 내용 가져오기
        content_res = requests.get(target_file['download_url'])
        content_res.encoding = 'utf-8'
        articles = parse_markdown(content_res.text)

        # 슬랙 메시지 구성
        attachments = []
        for art in articles[:5]:  # 너무 길면 슬랙이 거부하므로 상위 5개만 전송
            attachments.append({
                "color": "#00C73C",
                "title": art['title'],
                "title_link": art['link'],
                "text": art['summary'],
                "mrkdwn_in": ["text"]
            })

        payload = {
            "text": f"🚀 *오늘의 주요 AI 뉴스 요약 ({today_str})*",
            "attachments": attachments
        }
        requests.post(WEBHOOK_URL, json=payload)
        
        # 전체 보기 링크 별도 추가
        requests.post(WEBHOOK_URL, json={"text": f"🔗 <{target_file['html_url']}|전체 뉴스레터 읽기>"})

if __name__ == "__main__":
    send_to_slack()
