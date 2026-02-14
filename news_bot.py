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
    
    # 시작 알림
    requests.post(WEBHOOK_URL, json={
        "text": f"🚀 *{today_str} AI 뉴스 배달 시작!* \n👉 <{full_newsletter_url}|전체 뉴스레터 원문 보기>"
    })
    time.sleep(1)

    # 섹션 분리 (샵 개수 무관)
    sections = re.split(r'\n#+\s*', raw_text)
    count = 0

    for section in sections:
        if not section.strip(): continue
        
        # 1. 이미지 추출 (![alt](url) 형태 찾기)
        img_match = re.search(r'!\[.*?\]\((.*?)\)', section)
        img_url = img_match.group(1) if img_match else None
        
        # 기사 내용에서 이미지 태그 제거 (텍스트만 남기기 위함)
        section_clean = re.sub(r'!\[.*?\]\(.*?\)', '', section)
        valid_lines = [l.strip() for l in section_clean.strip().split('\n') if l.strip()]
        if not valid_lines: continue
        
        # 2. 제목 추출
        title_line = valid_lines[0]
        clean_title = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', title_line)
        clean_title = re.sub(r'[#\*]', '', clean_title).strip()
        
        # 3. 링크 추출
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', section_clean)
        
        if clean_title and url_match:
            url = url_match.group(1).strip()
            # 썸네일로 부적합한 주소 필터링
            if any(x in url for x in ["instagram.com", "cdninstagram.com"]): url_check = False
            else: url_check = True
            
            if not url_check: continue

            # 4. 요약 추출
            summary_lines = []
            for line in valid_lines[1:]:
                if url not in line:
                    c_line = re.sub(r'[\[\]\(\)\*#]', '', line).strip()
                    if c_line: summary_lines.append(c_line)
            
            summary = " ".join(summary_lines)
            summary = (summary[:250] + '...') if len(summary) > 250 else summary

            # 슬랙 메시지 블록 구성
            blocks = []
            
            # 이미지가 있다면 상단에 추가
            if img_url:
                blocks.append({
                    "type": "image",
                    "image_url": img_url,
                    "alt_text": "기사 이미지"
                })

            # 제목 추가
            blocks.append({
                "type": "section",
                "text": { "type": "mrkdwn", "text": f"*📍 {clean_title}*" }
            })

            # 요약 추가
            blocks.append({
                "type": "section",
                "text": { "type": "mrkdwn", "text": f"> {summary if summary else '내용은 원문 읽기 버튼을 확인해 주세요.'}" }
            })

            # 버튼 추가
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": { "type": "plain_text", "text": "기사 원문 읽기 ↗️" },
                        "url": url,
                        "style": "primary"
                    }
                ]
            })
            blocks.append({ "type": "divider" })

            requests.post(WEBHOOK_URL, json={"blocks": blocks})
            count += 1
            time.sleep(1.5)

if __name__ == "__main__":
    send_to_slack()
