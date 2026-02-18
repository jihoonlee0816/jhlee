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

    # 기사 분리 (가로줄 --- 또는 샵 # 기준)
    sections = re.split(r'\n-{3,}\s*|\n#+\s*', raw_text)

    for section in sections:
        if not section.strip(): continue
        
        # [수정] 모든 이미지 태그(![...](...))를 텍스트에서 완전히 제거
        clean_text = re.sub(r'!\[.*?\]\(.*?\)', '', section).strip()
        lines = [l.strip() for l in clean_text.split('\n') if l.strip()]
        
        if not lines: continue

        # 1. 제목 찾기 로직
        clean_title = ""
        content_start_idx = 0
        
        for idx, line in enumerate(lines):
            # '제목:', '중요도:', '전체링크:' 등의 머릿말과 마크다운 기호 제거
            t = re.sub(r'^\*?\*?제목\s*:\s*\*?\*?|[#\*\[\]]', '', line).strip()
            
            # '제목:' 이라는 글자만 있는 줄은 넘기고, 실제 제목 텍스트가 있는 첫 줄을 제목으로 채택
            if t and len(t) > 2 and "http" not in t:
                clean_title = t
                content_start_idx = idx + 1
                break
        
        # 기사 원문 링크 찾기
        url_match = re.search(r'(https?://[^\s\)\>\]]+)', clean_text)
        
        # 제목과 링크가 없으면 기사가 아닌 것으로 간주
        if not clean_title or not url_match:
            continue

        url = url_match.group(1).strip()

        # 2. 본문 추출 (제목 이후의 모든 문장 포함, '중요도' 등 제외)
        content_lines = []
        for line in lines[content_start_idx:]:
            # 제외할 키워드들
            if any(x in line for x in ["중요도", "전체링크", "전체 뉴스레터"]): continue
            # 링크만 덩그러니 있는 줄은 버튼이 대신하므로 제외
            if url
