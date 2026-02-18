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
    
    # 🚀 시작 알림
    requests.post(WEBHOOK_URL, json={"text": f"🚀 *{today_str} AI 뉴스 배달 시작!*"})
    time.sleep(1)

    # 기사 분리 (--- 또는 # 기준)
    sections = re.split(r'\n-{3,}\s*|\n#+\s*', raw_text)

    for section in sections:
        if not section.strip(): continue
        
        # [제일 먼저 실행] 이미지 태그 완전 제거
        clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', section).strip()
        lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
        
        if not lines: continue

        # 1. 제목 찾기 로직 (진짜 텍스트가 나올 때까지)
        clean_title = ""
        title_line_idx = -1
        
        for idx, line in enumerate(lines):
            # '제목:', '중요도:', '전체링크:' 머릿말 제거
            t = re.sub(r'^\*?\*?제목\s*:\s*\*?\*?|[#\*\[\]]', '', line).strip()
            
            # 의미 있는 텍스트(제목) 발견 시 채택
            if t and len(t) > 2 and "http" not in t:
                clean_title = t
                title_line_idx = idx
                break
        
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', clean_text)
        
        # 기사가 아니라고 판단되면 건너뜀
        if not clean_title or not url_match:
            continue

        url = url_match.group(1).strip()

        # 2. 본문 추출 (제목 이후 ~ 중요도 이전)
        content_lines = []
        for line in lines[title_line_idx + 1:]:
            if any(x in line for x in ["중요도", "전체링크", "전체 뉴스레터"]): continue
            if url in line and len(line) < len(url) + 10: continue
            
            c_line = re.sub(r'[#\*]', '', line).strip()
            if c_line: content_lines.append(c_line)
        
        full_content = "\n".join(content_lines)

        # 3. 슬랙 발송
        blocks = []
        blocks.append({
            "type": "section",
            "text": { "type": "mrkdwn", "text": f"*📍 제목: {clean_title}*" }
        })
        
        if full_content:
            blocks.append({
                "type": "section",
                "text": { "type": "mrkdwn", "text": full_content }
            })

        blocks.append({
            "type": "actions",
            "elements": [{
                "type": "button",
                "text": { "type": "plain_text", "text": "기사 원문 읽기 ↗️" },
                "url": url,
                "style": "primary"
            }]
        })
        blocks.append({ "type": "divider" })

        requests.post(WEBHOOK_URL, json={"blocks": blocks})
        time.sleep(1)

if __name__ == "__main__":
    send_to_slack()
