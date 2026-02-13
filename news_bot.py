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
    full_newsletter_url = target_file['html_url'] # 전체 뉴스레터 링크
    
    # [1. 시작 알림] 전체 뉴스레터 링크 포함
    requests.post(WEBHOOK_URL, json={
        "text": f"🚀 *{today_str} AI 뉴스 배달 시작!* \n👉 <{full_newsletter_url}|전체 뉴스레터 원문 보기>"
    })
    time.sleep(1)

    # 본문 전처리 (이미지 태그 제거)
    clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', raw_text)
    
    # 샵(#) 개수에 상관없이 섹션 분리
    sections = re.split(r'\n#+\s*', clean_text)
    count = 0

    for section in sections:
        if not section.strip(): continue
        
        lines = [l.strip() for l in section.strip().split('\n') if l.strip()]
        if not lines: continue
        
        # 1. 제목 추출
        raw_title = lines[0]
        clean_title = re.sub(r'[\[\]\(\)\*#]', '', raw_title).strip()
        
        # 2. 링크 및 요약 추출
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', section)
        if url_match and len(clean_title) > 2:
            url = url_match.group(1).strip()
            if "instagram" in url or "cdn" in url: continue
            
            # 요약: 제목과 링크를 제외한 나머지 텍스트들을 합침
            summary_content = ""
            for line in lines[1:]:
                # 링크가 포함된 줄은 제외하고 텍스트만 수집
                if url not in line and "![" not in line:
                    clean_line = re.sub(r'[\[\]\(\)\*#]', '', line).strip()
                    if clean_line:
                        summary_content += clean_line + " "
            
            # 요약 내용이 너무 길면 자름 (최대 200자)
            summary = (summary_content[:200] + '...') if len(summary_content) > 200 else summary_content

            # [2. 기사별 Rich Format 전송] 요약(text) 필드 추가
            payload = {
                "blocks": [
                    {
                        "type": "section",
                        "text": { "type": "mrkdwn", "text": f"*📍 {clean_title}*" }
                    },
                    {
                        "type": "section",
                        "text": { "type": "mrkdwn", "text": f"> {summary if summary else '내용은 원문 링크를 확인해 주세요.'}" }
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

    if count == 0:
        requests.post(WEBHOOK_URL, json={"text": "❌ 기사 추출에 실패했습니다."})

if __name__ == "__main__":
    send_to_slack()
