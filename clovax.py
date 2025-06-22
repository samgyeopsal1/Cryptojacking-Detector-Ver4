# //home/ubuntu/api/logic/Clovax.py — strict prompt 적용된 버전
from openai import OpenAI
import time
import os
import sys

# 콘솔 출력 인코딩 설정
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

class ClovaXScanner:
    def __init__(self, api_key, base_url="https://clovastudio.stream.ntruss.com/v1/openai/"):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.max_len = 2500
        self.final_result = []


    def load_file(self, path="combined.txt"):
        while True:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    self.full_code = f.read()
                break
            except Exception as e:
                print(f"[!] 파일 열기 실패 : {e}")

        print(f"읽은 파일 크기: {len(self.full_code)} bytes")
        self.chunks = [self.full_code[i:i+self.max_len] for i in range(0, len(self.full_code), self.max_len)]

        print(f"총 {len(self.chunks)}개의 조각으로 분할 완료\n")


    def analyze_chunks(self):
        SYSTEM_PROMPT = (
            "당신은 사이버 보안 전문가입니다. 아래 JavaScript 코드를 분석하세요.\n\n"
            " 분석 목적:\n"
            "JavaScript 코드 내에 크립토재킹과 관련된 위험 요소가 **실제로 존재할 경우에만**, 이를 탐지하고 JSON 형식으로 출력하세요.\n\n"
            " 분석 규칙:\n"
            "1. 아래 위험 요소 중 하나라도 코드 안에 '정확히 포함'되어 있으면 반드시 탐지 결과를 출력하세요.\n"
            "2. 코드에 해당 문자열이 없으면 절대로 추측하지 말고 빈 JSON `{}`만 출력하세요.\n"
            "3. '유사해 보이는 코드', '가능성이 있어 보임', '추정됨' 같은 해석은 모두 금지입니다.\n"
            "4. 반드시 **문자열이 텍스트로 포함되어 있는지 여부만** 기준으로 판단하십시오.\n\n"
            "5. 난독화가 되어 있을경우, 사람이 읽을 수 있는 언어로 복원한 뒤, 복원된 코드 안에서 크립토재킹과 관련된 요소만을 탐지 해주세요. \n"
            "결과는 다음과 같이 출력 해주세요: \n"
            " 위험 요소 목록:\n"
            "- 'startMining'\n"
            "- 'throttle'\n"
            "- 'CoinHive'\n"
            "- 'deepMiner'\n"
            "- 'miner'\n"
            "- 'monero'\n"
            "- 'webminepool'\n"
            "- 'coinhive.com'\n"
            "- 'wss://'\n"
            "- 'new Worker'\n"
            "- 'requestAnimationFrame'\n"
            "- 'setInterval'\n\n"
            " 출력 형식 (감지된 경우):\n"
            "{\n"
            "  \"reason\": \"cryptojacking detected\",\n"
            "  \"code\": \"[탐지된 코드 조각]\",\n"
            "  \"code_context\": \"[탐지된 이유 요약, 예: 'startMining 함수가 있음']\"\n"
            "}\n\n"
            " 출력 형식 (감지되지 않은 경우):\n"
            "{}\n\n"
            " 금지 사항:\n"
            "- 추측, 유사성, 해석, 상상 절대 금지\n"
            "- 실제로 존재하지 않으면 반드시 `{}` 출력"
        )

        for idx, chunk in enumerate(self.chunks, 1):
            print(f"[{idx}/{len(self.chunks)}] 조각 이중 분석 중...")
            meaningful_result = None

            for trial in range(2):  # 두 번 분석
                for retries in range(3):  # 최대 3회 재시도
                    # 정상적인 response라면
                    try:
                        response = self.client.chat.completions.create(
                            model="HCX-005",
                            messages=[
                                {"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": chunk}
                            ]
                        )
                        result = response.choices[0].message.content.strip()

                        if result: # json형태의 response
                            meaningful_result = result
                            print(f"    [시도 {trial+1}] 분석 성공")
                            break

                    # 예외 발생
                    except Exception as e:
                        print(f"    [시도 {trial+1}] 분석 실패 (재시도 {retries+1}): {e}")
                        if "429" in str(e) or "rate" in str(e).lower(): # too many requests
                            wait = 2 ** retries
                            print(f"    {wait}초 대기 후 재시도")
                            time.sleep(wait)
                        else: pass

                # 에러메시지가 아닌 정상적인 response가 담긴다면 조각 분석 완료
                if meaningful_result:
                    break

            # 이중 분석이 모두 완료되고, 여전히 에러 메시지만 존재한다면 빈 json만
            self.final_result.append(meaningful_result or "{}")

    def save_results(self, output_path="/tmp/clovax_analysis_result.txt"):
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, res in enumerate(self.final_result, 1):
                f.write(f"\n[조각 {idx} 결과]\n{res}\n")
        print("📁 분석 결과가 저장되었습니다:", output_path)


    def show_results(self):
        print("\n📊 전체 분석 결과:")
        for idx, res in enumerate(self.final_result, 1):
            print(f"\n[조각 {idx} 결과]")
            print(res)


    def save_chunks(self, output_path="/tmp/chunks_raw.txt"):
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, chunk in enumerate(self.chunks, 1):
                f.write(f"\n[조각 {idx}]\n{chunk}\n")
        print("📁 원본 분할 조각들이 저장되었습니다:", output_path)

def main(path="combined.txt"):
    api_key = os.getenv("OPEN_API_KEY")  # 또는 환경변수 사용 가능  
    scanner = ClovaXScanner(api_key)
    scanner.load_file(path)
    scanner.analyze_chunks()
    scanner.save_results()
    scanner.save_chunks()

if __name__ == "__main__":
    main()
