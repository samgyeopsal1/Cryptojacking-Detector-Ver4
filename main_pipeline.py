#  main_pipeline.py
#//home/ubuntu/api/main_pipeline.py
import sys
import os
import traceback
import logging

#https 로그들을 막아야함
#로그 출력 막는 설정



# === 로거 설정 ===
LOG_FILE_PATH = "/tmp/streamlog.txt"

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE_PATH, mode="a", encoding="utf-8")
    ]
)

logger = logging.getLogger(__name__)

from logic.Clovax import main as clova_main
from logic.Pattern import SignatureDetector
from logic.UrlLoader import MakeFileByUrl
from logic.Result import FinalResult

def run_full_detection(target_url: str) -> tuple[str, str]:
    """
    전체 크립토재킹 탐지 파이프라인 실행 함수.
    :param target_url: 사용자가 입력한 검사 대상 URL
    :return: 분석 결과 요약 메시지와 위험 수준 문자열 (summary, level)
    """

    # 로그 파일 초기화
    with open(LOG_FILE_PATH, "w", encoding="utf-8") as f:
        f.write("")

    logger.info(f"🔍 분석 시작 - 대상 URL: {target_url}")

    try:
        # 1. JS 수집 및 combined.txt 생성
        loader = MakeFileByUrl(target_url)
        loader.folder_name = "downloaded"
        loader.download_page_resources()
        loader.make_combined_file()	#추가
        combined_path = loader.get_combined_path()
        logger.info(f"✅ [STEP 1 완료] JS 수집 및 병합 완료 ")  #파일경로 : combiend_path

        # 2. Clova X 기반 정적 분석
        logger.info("🧠 [STEP 2 시작] Clova X 분석 실행 중...")
        clova_main(combined_path)
        logger.info("✅ [STEP 2 완료] Clova X 분석 완료")

        # 3. 시그니처 기반 탐지
        logger.info("🔍 [STEP 3 시작] 시그니처 분석 실행 중...")
        detector = SignatureDetector()
        detector.scan_file(combined_path)
        sig_count = detector.process_patterns()
        detector.make_file()
        logger.info(f"✅ [STEP 3 완료] 시그니처 탐지 완료 - 총 {sig_count}건 감지")

        # 4. 결과 요약 및 위험도 판단
        result = FinalResult()
        result.extract_from_clovax()

        if not result.clovax_summary or not result.clovax_level:
            logger.error("❌ ClovaX 결과가 비어 있음")
            return "분석 실패: ClovaX 결과 없음", "다시 시도 해주시길 바랍니다..."

        summary, level = result.combine_results(sig_count)
        logger.info(f"📝 [요약] {summary}")
        logger.info(f"🛡️ [위험도] {level}")

        # ✅ final.txt 내용 로그로 출력
        try:
            with open("/tmp/final.txt", "r", encoding="utf-8") as f:
                final_content = f.read()
            logger.info(f"\n📄 Final.txt 결과:\n{final_content}")
        except FileNotFoundError:
            logger.error("❌ final.txt 파일을 읽을 수 없습니다.")

        return summary, level

    except Exception as e:
        logger.error(f"🔥 분석 중 예외 발생: {e}")
        logger.error(traceback.format_exc())
        return f"분석 실패: {str(e)}", "다시 시도 해주시길 바랍니다...."

if __name__ == "__main__":
    if len(sys.argv) != 2:
        logger.error("❗ 사용법: python3 main_pipeline.py [URL]")
    else:
        url = sys.argv[1].strip('"').strip("'").strip()
        logger.info(f"받은 URL: {url}")
        summary, level = run_full_detection(url)
        logger.info(f"🏁 [최종 요약] {summary}")
        logger.info(f"🏁 [최종 위험도] {level}")
