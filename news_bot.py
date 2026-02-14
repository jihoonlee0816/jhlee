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
    
    requests.post(WEBHOOK_URL, json={
        "text": f"🚀 *{today_str} AI 뉴스 배달 시작! (제목 추출 강화)* \n👉 <{full_newsletter_url}|전체 뉴스레터 원문 보기>"
    })
    time.sleep(1)

    sections = re.split(r'\n#+\s*', raw_text)
    pending_image = None
    
    # 첫 섹션에서 이미지 미리 찾기
    first_img = re.search(r'!\[.*?\]\((.*?)\)', sections[0])
    if first_img:
        pending_image = first_img.group(1)

    count = 0
    for i in range(1, len(sections)):
        section = sections[i]
        
        # [핵심] 제목 추출 로직 강화
        # 이미지 태그를 먼저 제거하고 텍스트만 남깁니다.
        text_only_section = re.sub(r'!\[.*?\]\(.*?\)', '', section).strip()
        lines = [l.strip() for l in text_only_section.split('\n') if l.strip()]
        
        if not lines: continue
        
        # 1. 제목 결정: 첫 번째 유효한 줄을 가져옵니다.
        raw_title = lines[0]
        # 만약 제목이 [제목](링크) 형태라면 '제목' 글자만 추출합니다.
        bracket_title = re.search(r'\[(.*?)\]', raw_title)
        if bracket_title:
            clean_title = bracket_title.group(1)
        else:
            clean_title = raw_title
        
        # 제목에서 불필요한 마크다운 기호 제거
        clean_title = re.sub(r'[#\*]', '', clean_title).strip()
        
        # 2. 링크 추출
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', text_only_section)
        
        if clean_title and url_match:
            url = url_match.group(1).strip()
            if any(x in url for x in ["instagram.com", "cdninstagram.com"]): continue

            # 3. 요약 추출
            summary_lines = []
            for line in lines[1:]:
                if url not in line:
                    c_line = re.sub(r'[\[\]\(\)\*#]', '', line).strip()
                    if c_line: summary_lines.append(c_line)
            
            summary = " ".join(summary_lines)
            summary = (summary[:250] + '...') if len(summary) > 250 else summary

            # 이미지 매칭 (이전 섹션의 이미지를 가져옴)
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
                "text": { "type": "mrkdwn", "text": f"> {summary if summary else '원문 링크를 확인해 주세요.'}" }
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
