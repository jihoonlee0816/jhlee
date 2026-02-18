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
    
    # [시작 알림]
    requests.post(WEBHOOK_URL, json={"text": f"🚀 *{today_str} AI 뉴스 배달 시작!*"})
    time.sleep(1)

    # [핵심 수정] 기사 분리 기준 강화: # 또는 --- 또는 "제목:" 단어를 기준으로 나눔
    sections = re.split(r'\n#+\s*|\n-{3,}\s*|\n(?=제목:)', raw_text)
    
    pending_image = None

    for section in sections:
        if not section.strip(): continue
        
        # 1. 이미지 미리 추출 (섹션 내 어디든)
        img_match = re.search(r'!\[.*?\]\((.*?)\)', section)
        current_image = pending_image # 이전 섹션의 이미지를 현재 기사에 사용
        pending_image = img_match.group(1) if img_match else None

        # 텍스트만 추출 (이미지 제거)
        text_only = re.sub(r'!\[.*?\]\(.*?\)', '', section).strip()
        lines = [l.strip() for l in text_only.split('\n') if l.strip()]
        if not lines: continue

        # 2. 제목 찾기: "제목:" 줄을 포함해 첫 3줄 안에서 진짜 제목 텍스트를 찾음
        clean_title = ""
        title_line_idx = -1
        for idx, line in enumerate(lines[:3]):
            # 군더더기 제거
            t = re.sub(r'^\*?\*?제목\s*:\s*\*?\*?|[#\*\[\]]', '', line).strip()
            if t and len(t) > 2: # 의미 있는 길이의 텍스트 발견 시 제목으로 채택
                clean_title = t
                title_line_idx = idx
                break
        
        # 제목을 못 찾았거나 기사 링크가 없는 섹션은 건너뜀
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', text_only)
        if not clean_title or not url_match:
            continue

        # 3. 본문 추출 (제목 이후 ~ 중요도 이전까지)
        url = url_match.group(1).strip()
        content_lines = []
        for line in lines[title_line_idx + 1:]:
            # 중요도 제외 로직
            if line.startswith("중요도") or line.startswith("**중요도"): continue
            # 링크만 있는 줄 제외
            if url in line and len(line) < len(url) + 10: continue
            
            c_line = re.sub(r'[#\*]', '', line).strip()
            if c_line: content_lines.append(c_line)
        
        full_content = "\n".join(content_lines)

        # 슬랙 메시지 발송
        blocks = []
        if current_image:
            blocks.append({"type": "image", "image_url": current_image, "alt_text": "기사 이미지"})
        
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
        time.sleep(1.2) # 속도 조절

if __name__ == "__main__":
    send_to_slack()
