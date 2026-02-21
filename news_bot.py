import requests
import os
import re
from datetime import datetime, timedelta  # timedelta 추가됨
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

    # [핵심 수정] 서버 시간(UTC)에 9시간을 더해 한국 시간(KST) 날짜를 만듭니다.
    today_now = datetime.utcnow() + timedelta(hours=9)
    today_str = today_now.strftime("%Y-%m-%d")
    
    target_file = next((f for f in files if today_str in f['name']), None)
    
    # 만약 오늘 날짜 파일이 없으면 종료 (중복 배달 방지)
    if not target_file: 
        print(f"[{today_str}] 날짜의 파일을 아직 찾을 수 없습니다.")
        return

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

        # 1. 제목 찾기 로직
        clean_title = ""
        title_line_idx = -1
        
        for idx, line in enumerate(lines):
            t = re.sub(r'^\*?\*?제목\s*:\s*\*?\*?|[#\*\[\]]', '', line).strip()
            if t and len(t) > 2 and "http" not in t:
                clean_title = t
                title_line_idx = idx
                break
        
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', clean_text)
        if not clean_title or not url_match:
            continue

        url = url_match.group(1).strip()

        # 2. 본문 추출 (중요도 등 제외)
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
