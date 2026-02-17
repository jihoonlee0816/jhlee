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
    
    # [정리] 시작 알림: 깔끔한 문구로 변경
    requests.post(WEBHOOK_URL, json={
        "text": f"🚀 *{today_str} AI 뉴스 배달 시작!* \n👉 <{full_newsletter_url}|전체 뉴스레터 원문 보기>"
    })
    time.sleep(1)

    sections = re.split(r'\n#+\s*', raw_text)
    pending_image = None
    
    # 헤더 섹션에서 첫 번째 이미지 미리 찾기
    first_img = re.search(r'!\[.*?\]\((.*?)\)', sections[0])
    if first_img:
        pending_image = first_img.group(1)

    count = 0
    for i in range(1, len(sections)):
        section = sections[i]
        
        # 텍스트 추출 (이미지 태그 제거)
        text_only_section = re.sub(r'!\[.*?\]\(.*?\)', '', section).strip()
        lines = [l.strip() for l in text_only_section.split('\n') if l.strip()]
        
        if not lines: continue
        
        # 1. 제목 추출 및 "제목:" 중복 제거
        raw_title = lines[0]
        bracket_title = re.search(r'\[(.*?)\]', raw_title)
        clean_title = bracket_title.group(1) if bracket_title else raw_title
        clean_title = re.sub(r'^제목\s*:\s*', '', clean_title) # "제목:" 필터링
        clean_title = re.sub(r'[#\*]', '', clean_title).strip()
        
        # 2. 링크 추출
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', text_only_section)
        
        if clean_title and url_match:
            url = url_match.group(1).strip()
            if any(x in url for x in ["instagram.com", "cdninstagram.com"]): continue

            # 3. 본문 전체 추출 (요약하지 않음)
            content_lines = []
            for line in lines[1:]:
                # URL만 있는 줄은 버튼이 대신하므로 제외, 나머지는 모두 포함
                if url not in line or len(line) > len(url) + 5:
                    c_line = re.sub(r'[#\*]', '', line).strip()
                    if c_line: content_lines.append(c_line)
            
            # 모든 문장을 줄바꿈(\n)으로 합쳐서 원문 구조 유지
            full_content = "\n".join(content_lines)
            
            # 슬랙 메시지 글자 수 제한(3000자)을 위한 안전장치만 유지
            if len(full_content) > 2900:
                full_content = full_content[:2900] + "..."

            # 이미지 매칭 로직
            current_image = pending_image
            next_img_match = re.search(r'!\[.*?\]\((.*?)\)', section)
            pending_image = next_img_match.group(1) if next_img_match else None

            # 슬랙 블록 구성
            blocks = []
            if current_image:
                blocks.append({"type": "image", "image_url": current_image, "alt_text": "기사 이미지"})
            
            blocks.append({
                "type": "section",
                "text": { "type": "mrkdwn", "text": f"*📍 제목: {clean_title}*" }
            })
            
            blocks.append({
                "type": "section",
                "text": { "type": "mrkdwn", "text": f"{full_content if full_content else '본문 내용은 아래 버튼을 통해 확인해 주세요.'}" }
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
            count += 1
            time.sleep(1.5)

if __name__ == "__main__":
    send_to_slack()
