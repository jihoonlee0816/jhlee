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
    requests.post(WEBHOOK_URL, json={
        "text": f"🚀 *{today_str} AI 뉴스 배달 시작!*"
    })
    time.sleep(1)

    # 섹션 나누기 (기존보다 더 유연하게)
    sections = re.split(r'\n#+\s*', raw_text)
    pending_image = None

    for i in range(len(sections)):
        section = sections[i]
        
        # 이미지 추출
        img_match = re.search(r'!\[.*?\]\((.*?)\)', section)
        current_image = pending_image
        if img_match: pending_image = img_match.group(1)
        else: pending_image = None

        # 텍스트 추출 (이미지 제거)
        text_only = re.sub(r'!\[.*?\]\(.*?\)', '', section).strip()
        lines = [l.strip() for l in text_only.split('\n') if l.strip()]
        
        # 링크 추출 (기사 판단 기준)
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', text_only)
        if not url_match or not lines:
            continue

        # [핵심 수정] 진짜 제목 찾기 로직
        # "제목:"만 있는 줄을 건너뛰고 실제 제목 텍스트가 있는 줄을 찾습니다.
        clean_title = ""
        title_line_index = 0
        for idx, line in enumerate(lines):
            # 마크다운 기호 및 "제목:" 단어 제거
            temp_title = re.sub(r'^\*?\*?제목\s*:\s*\*?\*?|[#\*\[\]]', '', line).strip()
            if temp_title and len(temp_title) > 2: # 의미 있는 길이의 제목일 때만 채택
                clean_title = temp_title
                title_line_index = idx
                break
        
        if not clean_title: continue # 제목을 못 찾으면 기사가 아님

        # 3. 본문 전체 추출 (중요도 제외)
        url = url_match.group(1).strip()
        content_lines = []
        # 제목으로 쓴 줄 이후부터 모두 본문으로 간주
        for line in lines[title_line_index + 1:]:
            is_importance_line = line.strip().startswith("중요도") or line.strip().startswith("**중요도")
            # URL만 있는 줄은 제외하고 나머지는 유지
            if (url not in line or len(line) > len(url) + 10) and not is_importance_line:
                c_line = re.sub(r'[#\*]', '', line).strip()
                if c_line: content_lines.append(c_line)
        
        full_content = "\n".join(content_lines)

        # 슬랙 블록 구성
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
        time.sleep(1.5)

if __name__ == "__main__":
    send_to_slack()
