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
    마크다운 텍스트에서 '#### [제목]'과 그 안에 있는 '링크'를 
    줄바꿈에 상관없이 유연하게 찾아냅니다.
    """
    articles = []
    # #### [기사 제목] 단위로 텍스트를 자릅니다.
    chunks = text.split('#### [')
    
    for chunk in chunks[1:]:  # 첫 번째 조각은 서론이므로 제외
        try:
            # 1. 제목 추출 (']' 앞까지)
            title = chunk.split(']')[0].strip()
            
            # 2. 링크 추출 (괄호 안의 http로 시작하는 문자열 찾기)
            url_match = re.search(r'\((https?://[^\)]+)\)', chunk)
            if url_match:
                link = url_match.group(1).strip()
                articles.append({"title": title, "link": link})
        except Exception:
            continue
            
    return articles

def send_to_slack():
    res = requests.get(API_URL)
    if res.status_code != 200: return

    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    target_file = next((f for f in files if today_str in f['name']), None)

    if target_file:
        content_res = requests.get(target_file['download_url'])
        full_text = content_res.text
        
        # 기사 파싱
        news_list = parse_articles(full_text)
        
        if news_list:
            attachments = []
            # 최대 15개 기사까지만 발송 (슬랙 메시지 용량 제한 방지)
            for item in news_list[:15]:
                attachments.append({
                    "color": "#2EB67D", # GeekNews 스타일 초록색
                    "title": item['title'],
                    "title_link": item['link'],
                    "text": f"🔗 원문 보기: {item['link']}"
                })
            
            payload = {
                "text": f"📢 *{today_str} 오늘의 AI 뉴스레터 도착 (기사별 요약)*",
                "attachments": attachments
            }
            
            # 슬랙 전송
            response = requests.post(WEBHOOK_URL, json=payload)
            if response.status_code == 200:
                print(f"성공적으로 {len(news_list)}개의 기사를 보냈습니다.")
        else:
            # 파싱 실패 시 알림
            requests.post(WEBHOOK_URL, json={"text": f"⚠️ 기사 파싱에 실패했습니다. 링크를 확인해 주세요: {target_file['html_url']}"})
    else:
        print(f"{today_str} 날짜의 파일이 아직 없습니다.")

if __name__ == "__main__":
    send_to_slack()
