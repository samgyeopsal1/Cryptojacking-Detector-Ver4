#//home/ubuntu/api/logic/Pattern
import re
import json

PATTERNS = [
    # 새로 추가된 키워드들
    r'deepminer', r'webminepool', r'monero', r'webminer',
    r'mining', r'moneroocean', r'walletAddress', r'workerId',
    r'startMining', r'throttleMiner', r"Client.Anonymous",
    r'wss'
]

class SignatureDetector:
    def __init__(self):
        self.hits_count = []
        self.content = ""

    def scan_file(self, path="combined.txt"):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                self.content = f.read()
        except Exception as e:
            print(f"[!] 파일 열기 실패: {path} ({e})")

    def process_patterns(self):
        for pattern in PATTERNS:
            matches = re.findall(pattern, self.content, re.IGNORECASE)
            if matches:
                hit_count = len(matches)
                self.hits_count.append((pattern, hit_count))
        return len(self.hits_count)

    def make_file(self):
        try:
            result_list = [
                {"signature": pattern, "count": hit_count}
                for pattern, hit_count in self.hits_count
            ]
            with open("/tmp/signature_result.json", "w", encoding="utf-8") as f:
                json.dump(result_list, f, ensure_ascii=False, indent=2)
            print(f"signature_result.json 파일이 저장되었습니다.") #/tmp/signature_result.json파일

        except Exception as e:
            print(f"[!] 파일 저장 실패 : {e}")




























