# //home/ubuntu/api/logic/UrlLoader.py

import os
import re
import json
import base64
import shutil
import time
import brotli
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from PIL import Image, PngImagePlugin
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.id3 import ID3, TXXX, COMM, USLT
import sys
import requests

class MakeFileByUrl:

    def __init__(self, base_url):
        self.base_url = base_url
        self.parsed = urlparse(base_url)
        self.folder_name = "downloaded"
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.SAVE_DIR = os.path.join(BASE_DIR, self.folder_name)
        self.js_content = []
        self.report = []

        self.JS_PATTERNS = [
            r'function\s+\w*\s*\(',         # 그대로 유지 (식별자용)
            r'eval\s*\([^)]*\)',            # eval(...) 전체 추출
            r'document\.[\w\.]+',           # document.xxx
            r'window\.[\w\.]+',             # window.xxx
            r'<script>', r'</script>',
            r'\.innerHTML',
            r'setTimeout\s*\([^)]*\)',      # setTimeout(...)
            r'=>',
            r'new\s+Function\s*\([^)]*\)',  # new Function(...)
            r'unescape\s*\([^)]*\)',        # unescape(...)
            r'atob\s*\([^)]*\)'             # atob(...)
        ]
        self.js_regexes = [re.compile(p, re.IGNORECASE) for p in self.JS_PATTERNS]

    def make_folder(self):
        if os.path.exists(self.SAVE_DIR):
            shutil.rmtree(self.SAVE_DIR)
            print("[🧹] 기존 폴더 삭제")
        os.makedirs(self.SAVE_DIR, exist_ok=True)
        print("[📁] 새 폴더 생성 완료")

    def getUrl(self):
        self.parsed = urlparse(self.base_url)
        if self.parsed.scheme not in ["http", "https"] or not self.parsed.netloc:
            print("❌ URL의 형식이 잘못되었습니다.")
            sys.exit(1)
        #사이트존재 여부 확인(404응답만 체크)
        try:
            response = requests.head(self.base_url, timeout=5)
            if response.status_code == 404:
                print("❌ 요청한 URL은 존재하지 않습니다. (404 Not Found)")
                sys.exit(1)
        except:
            pass
        print("✅ 유효한 URL이며 사이트가 응답합니다.")

    def download_page_resources(self):
        self.make_folder()
        self.getUrl()

        options = Options()
        options.add_argument("--headless=chrome")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--ignore-certificate-errors")
        options.add_argument("--ignore-ssl-errors")
        options.add_argument("--ignore-certificate-errors-spki-list")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-web-security")
        options.add_argument("--accept-insecure-certs")
        options.add_argument("--user-agent=Mozilla/5.0")
        options.add_experimental_option("useAutomationExtension", False)
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        options.set_capability('acceptInsecureCerts', True)
        options.page_load_strategy = 'eager'

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(6000)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        driver.execute_cdp_cmd('Network.enable', {})
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": "Mozilla/5.0"})
        print(f"[🌐] 접속 중: {self.base_url}")
        driver.get(self.base_url)
        time.sleep(3)

        with open(f"{self.SAVE_DIR}/index.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)

        resources = {
            p['requestId']: p['response']
            for log in driver.get_log('performance')
            if (msg := json.loads(log['message'])['message'])['method'] == 'Network.responseReceived'
            and (p := msg['params'])
        }

        for rid, res in resources.items():
            try:
                resp = driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': rid})
                name = os.path.basename(urlparse(res['url']).path) or f"file_{hash(res['url']) % 1000}"
                ext = '.js' if 'javascript' in res.get('mimeType', '') else '.css' if 'css' in res.get('mimeType', '') else ''
                name = name + ext if '.' not in name and ext else name
                save_path = os.path.join(self.SAVE_DIR, name)
                with open(save_path, 'wb' if resp.get('base64Encoded') else 'w',
                            encoding=None if resp.get('base64Encoded') else 'utf-8') as f:
                    f.write(base64.b64decode(resp['body']) if resp.get('base64Encoded') else resp['body'])
                print(f"[📥] 저장됨: {name}")
            except:
                pass

        driver.quit()
        print("[✅] 리소스 다운로드 완료\n")

    def extract_javascript(self):
        folder_path = self.SAVE_DIR
        seen = set()
        patterns = [
            r'<script[^>]*>(.*?)</script>',
            r'<script\s+[^>]*src\s*=\s*["\'](.*?)["\']',
            r'<iframe\s+[^>]*src\s*=\s*["\'](.*?)["\']', #추가
            r'<iframe[^>]*>(.*?)</iframe>',  #추가
            r'(?:function\s+\w+\s*\([^)]*\)\s*\{[^}]*\}' +
            r'|(?:var|let|const)\s+\w+\s*=\s*[^;]+;' +
            r'|[\w.]+\s*=\s*function[^}]*\})'
        ]
        excluded_exts = {'.jpg', '.jpeg', '.png', '.mp4', '.mp3', '.woff', '.woff2'}
        self.js_content = [
            f"\n// ==== {fname} ====\n" + "\n".join(unique_blocks)
            for fname in os.listdir(folder_path)
            if os.path.isfile(os.path.join(folder_path, fname))
            and os.path.splitext(fname)[1].lower() not in excluded_exts
            and (content := open(os.path.join(folder_path, fname), 'r', encoding='utf-8', errors='ignore').read())
            and (unique_blocks := [
                block.strip()
                for p in patterns
                for block in re.findall(p, content, re.DOTALL | re.IGNORECASE | re.MULTILINE)
                if block.strip() not in seen and not seen.add(block.strip())
            ])
        ]
        print(f"[🧠] JS 블록 {len(self.js_content)}개 추출 완료")

    def extract_matches(self, texts):
        results = []
        for t in texts:
            for r in self.js_regexes:
                if r.search(t):
                    results.append(t.strip())
                    break
        return results

    def scan_steganography(self):       #스테가노그래피 데이터 추출 전용 함수 (함수 선언)
        report = []     #스태가노그래피 데이터 결과 여기에 들어옴

        for fname in os.listdir(self.SAVE_DIR): #기존 방식으로 파일 open(SQVE_DIR에 존재하는 파일 반복 탐색 및 수행)
            path = os.path.join(self.SAVE_DIR, fname)   #절대 경로 (기존방식 --> 모든 파일 경로에는 이 방식 사용 ==> 공통됨)
            ext = os.path.splitext(fname)[1].lower().strip(".")     #소문자 변환(확장자)

            if not os.path.isfile(path):    #path 가 파일이 아닐 경우 continue
                continue

            extracted_text = "" #숨겨진 텍스트 데이터를 저장 할 수 있게 함(ex , 크립토재킹 키워드 등)

            try:
                if ext in ["png", "jpg"]: #확장자 지정 -> 확장자 추가할거면 ext 리스트에 넣으면 됨
                    print(f" {fname} → 이미지 파일 처리중 ({ext.upper()})")
                    img = Image.open(path).convert("RGB")
                    pixels = list(img.getdata())    #이미지 전체 픽셀 데이터를 리스트 형태로 --> pixels 변수에 할당 

                    binary_str = "" 
                    for pixel in pixels:    #픽셀 rgb를 순회 해서 추출하는 방식 --> 서칭 시에 가장 안정적으로 사용되는 방식이라 사용함
                        for channel in pixel[:3]:
                            binary_str += str(channel & 1)

                    chars = []
                    for i in range(0, len(binary_str), 8):
                        byte = binary_str[i:i+8]
                        if len(byte) < 8:
                            continue
                        char = chr(int(byte, 2))
                        if char == '\x00':  #널 문자가 나오면 그냥 바로 종료 시킴(끝, 데이터 종료 신호)
                            break 
                        chars.append(char)

                    extracted_text = ''.join(chars)     #나온 값들을 전부 하나로 합침(join을 사용하면 다 하나로 합쳐짐)

                    #전체 나온 결과물 (text)의 길이로 판단함 
                    if len(extracted_text.strip()) >= 5:   #길이 판단 기준을 5로 지정
                        report.append(f"\n// ==== {fname} ====\n\n스테가노그래피 추출 결과:\n{extracted_text}")
                    else:
                        print(f"{fname} → 유효한 스테가노그래피 데이터 없음 (길이 부족)")

            except Exception as e:
                print(f"{fname} 처리 중 오류 발생: {e}")
                continue

        return report




    def make_combined_file(self):
        self.extract_javascript()
        self.report = self.scan_steganography()
        combined_path = self.get_combined_path()   #get_combined_path 함수 사용
        with open(combined_path, "w", encoding="utf-8") as f:
            f.write("".join(self.report))
            f.write("\n==================\n")
            f.write("".join(self.js_content))
        print(f"[📦] 추출된 파일 개수 : {len(self.js_content) + len(self.report)}")

	#combined.txt 파일 위치를 지정함 -> 이 함수때문에 다른 함수들에서 일일이 계속해서 다시 combiend.txgt파일 경로를 지정할 필요가 없어짐

    def get_combined_path(self):
        return os.path.join(self.SAVE_DIR, "combined.txt")



