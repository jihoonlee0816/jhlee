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
    
    # 시작 알림
    requests.post(WEBHOOK_URL, json={
        "text": f"🚀 *{today_str} AI 뉴스 배달 시작!*"
    })
    time.sleep(1)

    sections = re.split(r'\n#+\s*', raw_text)
    pending_image = None

    for i in range(len(sections)):
        section = sections[i]
        
        img_match = re.search(r'!\[.*?\]\((.*?)\)', section)
        current_image = pending_image
        
        if img_match:
            pending_image = img_match.group(1)
        else:
            pending_image = None

        text_only = re.sub(r'!\[.*?\]\(.*?\)', '', section).strip()
        lines = [l.strip() for l in text_only.split('\n') if l.strip()]
        
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', text_only)
        if not url_match:
            continue

        # 1. 제목 추출 및 중복 제거
        raw_title = lines[0]
        bracket_match = re.search(r'\[(.*?)\]', raw_title)
        clean_title = bracket_match.group(1) if bracket_match else raw_title
        clean_title = re.sub(r'^\*?\*?제목\s*:\s*\*?\*?', '', clean_title)
        clean_title = re.sub(r'[#\*]', '', clean_title).strip()
        
        # 2. 본문 추출 (중요도 부분 제외)
        url = url_match.group(1).strip()
        content_lines = []
        for line in lines[1:]:
            # URL 제외 + '중요도'로 시작하는 줄 제외
            is_importance_line = line.strip().startswith("중요도") or line.strip().startswith("**중요도")
            if (url not in line or len(line) > len(url) + 10) and not is_importance_line:
                c_line = re.sub(r'[#\*]', '', line).strip()
                if c_line: content_lines.append(c_line)
        
        full_content = "\n".join(content_lines)

        blocks = []
        if current_image:
            blocks.append({"type": "image", "image_url": current_image, "alt_text": "기사 이미지"})
        
        blocks.append({
            "type": "section",
            "text": { "type": "mrkdwn", "text": f"*📍 제목: {clean_title}*" }
        })
        
        blocks.append({
            "type": "section",
            "text": { "type": "mrkdwn", "text": f"{full_content if full_content else '내용은 버튼을 통해 확인해 주세요.'}" }
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
        time.sleep(1.5)

if __name__ == "__main__":
    send_to_slack()
