import requests
import os
import re
from datetime import datetime
import time

# 1. 설정
TARGET_REPO = "GENEXIS-AI/DailyNews"
FOLDER_PATH = "뉴스레터"
API_URL = f"https://api.github.com/repos/{TARGET_REPO}/contents/{FOLDER_PATH}"
WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

def send_to_slack():
    res = requests.get(API_URL)
    if res.status_code != 200: return
    files = res.json()
    today_str = datetime.now().strftime("%Y-%m-%d")
    target_file = next((f for f in files if today_str in f['name']), None)
    if not target_file: return

    raw_text = requests.get(target_file['download_url']).text
    full_newsletter_url = target_file['html_url']
    
    # 시작 알림
    requests.post(WEBHOOK_URL, json={
        "text": f"🚀 *{today_str} AI 뉴스 배달 시작!* \n👉 <{full_newsletter_url}|전체 뉴스레터 원문 보기>"
    })
    time.sleep(1)

    # 이미지 제거
    clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', raw_text)
    # 섹션 분리 (샵 개수 무관)
    sections = re.split(r'\n#+\s*', clean_text)
    count = 0

    for section in sections:
        if not section.strip(): continue
        
        # [핵심 수정] 내용이 있는 줄만 골라내기
        valid_lines = [l.strip() for l in section.strip().split('\n') if l.strip()]
        if not valid_lines: continue
        
        # 1. 제목 추출: 첫 번째 유효한 줄
        title_line = valid_lines[0]
        # [제목](링크) 형태에서 제목만 발라내기
        clean_title = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', title_line)
        clean_title = re.sub(r'[#\*]', '', clean_title).strip()
        
        # 2. 링크 추출
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', section)
        
        if clean_title and url_match:
            url = url_match.group(1).strip()
            if "instagram" in url or "cdn" in url: continue
            
            # 3. 요약 추출: 제목 줄을 제외한 나머지
            summary_lines = []
            for line in valid_lines[1:]:
                if url not in line:
                    c_line = re.sub(r'[\[\]\(\)\*#]', '', line).strip()
                    if c_line: summary_lines.append(c_line)
            
            summary = " ".join(summary_lines)
            summary = (summary[:200] + '...') if len(summary) > 200 else summary

            # 슬랙 전송
            payload = {
                "blocks": [
                    {
                        "type": "section",
                        "text": { "type": "mrkdwn", "text": f"*📍 제목: {clean_title}*" }
                    },
                    {
                        "type": "section",
                        "text": { "type": "mrkdwn", "text": f"> {summary if summary else '내용은 원문 읽기 버튼을 확인해 주세요.'}" }
                    },
                    {
                        "type": "actions",
                        "elements": [
                            {
                                "type": "button",
                                "text": { "type": "plain_text", "text": "기사 원문 읽기 ↗️" },
                                "url": url,
                                "style": "primary"
                            }
                        ]
                    },
                    { "type": "divider" }
                ]
            }
            requests.post(WEBHOOK_URL, json=payload)
            count += 1
            time.sleep(1.2)

if __name__ == "__main__":
    send_to_slack()
