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
    
    requests.post(WEBHOOK_URL, json={"text": f"🚀 *{today_str} AI 뉴스 배달 시작!*"})
    time.sleep(1)

    # [핵심] 기사 분리: 가로줄(---)이나 샵(#)을 기준으로 나눔
    sections = re.split(r'\n-{3,}\s*|\n#+\s*', raw_text)
    
    for section in sections:
        if not section.strip(): continue
        
        # 1. 이미지 추출 및 제거 (텍스트 분석을 위해)
        images = re.findall(r'!\[.*?\]\((.*?)\)', section)
        current_image = images[0] if images else None
        
        # 텍스트에서 모든 이미지 태그 제거
        clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', section).strip()
        lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
        
        # 2. 제목 찾기
        clean_title = ""
        content_start_idx = 0
        
        for idx, line in enumerate(lines):
            # '제목:', '전체링크:', '중요도:' 등 불필요한 태그 제거 및 순수 텍스트 추출
            t = re.sub(r'^\*?\*?제목\s*:\s*\*?\*?|[#\*\[\]]', '', line).strip()
            
            # '제목:' 이라는 글자만 있는 줄은 건너뛰고, 실제 제목이 있는 줄을 찾음
            if t and len(t) > 2 and "http" not in t:
                clean_title = t
                content_start_idx = idx + 1
                break
        
        # 기사 링크 찾기
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', clean_text)
        
        # 제목과 링크가 모두 있어야 기사로 간주
        if not clean_title or not url_match:
            continue

        url = url_match.group(1).strip()

        # 3. 본문 추출 (중요도 제외)
        content_lines = []
        for line in lines[content_start_idx:]:
            # 중요도 제외 및 링크만 있는 줄 제외
            if any(x in line for x in ["중요도", "전체링크"]): continue
            if url in line and len(line) < len(url) + 10: continue
            
            c_line = re.sub(r'[#\*]', '', line).strip()
            if c_line: content_lines.append(c_line)
        
        full_content = "\n".join(content_lines)

        # 슬랙 발송
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
        time.sleep(1.2)

if __name__ == "__main__":
    send_to_slack()
