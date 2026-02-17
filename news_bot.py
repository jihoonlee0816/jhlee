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
    
    # [수정] 시작 알림: 원문 보기 링크 삭제 및 간결하게 변경
    requests.post(WEBHOOK_URL, json={
        "text": f"🚀 *{today_str} AI 뉴스 배달 시작!*"
    })
    time.sleep(1)

    # 샵(#)을 기준으로 나누되, 첫 조각부터 검사하도록 변경
    sections = re.split(r'\n#+\s*', raw_text)
    pending_image = None

    for i in range(len(sections)):
        section = sections[i]
        
        # 1. 이미지 추출 (![alt](url))
        img_match = re.search(r'!\[.*?\]\((.*?)\)', section)
        current_image = pending_image # 이전 섹션에서 발견된 이미지를 현재 기사에 매칭
        
        # 다음 기사를 위해 현재 섹션의 이미지를 저장
        if img_match:
            pending_image = img_match.group(1)
        else:
            pending_image = None

        # 텍스트만 추출 (이미지 태그 제거)
        text_only = re.sub(r'!\[.*?\]\(.*?\)', '', section).strip()
        lines = [l.strip() for l in text_only.split('\n') if l.strip()]
        
        # 링크 추출 (기사임을 판단하는 기준)
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', text_only)
        
        # 링크가 없는 섹션(인사말 등)은 기사가 아니므로 건너뜁니다.
        if not url_match:
            continue

        # 2. 제목 추출 및 중복 제거
        raw_title = lines[0]
        # [제목](링크) 형태에서 제목만 추출
        bracket_match = re.search(r'\[(.*?)\]', raw_title)
        clean_title = bracket_match.group(1) if bracket_match else raw_title
        
        # "제목:" "제목 :" "**제목:**" 등 모든 형태의 머리말 제거
        clean_title = re.sub(r'^\*?\*?제목\s*:\s*\*?\*?', '', clean_title)
        clean_title = re.sub(r'[#\*]', '', clean_title).strip()
        
        # 3. 본문 전체 추출
        url = url_match.group(1).strip()
        content_lines = []
        for line in lines[1:]:
            # URL만 있는 줄은 제외하고 나머지 줄바꿈 유지
            if url not in line or len(line) > len(url) + 10:
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
