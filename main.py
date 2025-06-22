#//home/ubuntu/api/app/main.py

import os
import subprocess
import asyncio
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse

app = FastAPI()

# 프로젝트 경로 및 분석기 경로
PROJECT_DIR = "/home/ubuntu/api"
MAIN_PIPELINE = "/home/ubuntu/api/main_pipeline.py"

# ✅ 루트 엔드포인트
@app.get("/", response_class=JSONResponse)
async def root():
    return JSONResponse(
        content={"message": "✅ 백엔드 서버 정상 작동중 ! "},
        media_type="application/json; charset=utf-8"
    )

# ✅ 분석 요청 (POST 방식)
@app.post("/analyze")
async def analyze(request: Request):
    data = await request.json()
    url = data.get("url")
    if not url:
        return JSONResponse(
            content={"error": "❌ URL이 제공되지 않았습니다."},
            media_type="application/json; charset=utf-8"
        )
    try:
        result = subprocess.check_output(
            ["python3", MAIN_PIPELINE, url],
            text=True,
            stderr=subprocess.STDOUT,
            cwd=PROJECT_DIR,
            timeout=6000
        )
        return JSONResponse(
            content={"output": result},
            media_type="application/json; charset=utf-8"
        )
    except subprocess.CalledProcessError as e:
        return JSONResponse(
            content={"error": "❌ 분석 중 오류", "details": e.output},
            media_type="application/json; charset=utf-8"
        )

# ✅ WebSocket 실시간 로그 전송
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            url = await websocket.receive_text()

            process = await asyncio.create_subprocess_exec(
                "python3", MAIN_PIPELINE, url,
                cwd=PROJECT_DIR,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT
            )

            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                decoded = line.decode().strip()

                # ✅ [INFO]가 포함된 로그는 브라우저로 전송하지 않음
                if "[INFO]" not in decoded:
                    await websocket.send_text(decoded)

            try:
                await websocket.send_text("✅ 분석 완료")
            except Exception:
                pass        #pass시켜서 넘기기

    except WebSocketDisconnect:
        pass  # 연결 종료 무시

# ✅ final.txt 결과 반환
@app.get("/get-final")
async def get_final():
    try:
        with open("/tmp/final.txt", "r", encoding="utf-8") as f:
            content = f.read()
        return PlainTextResponse(content)
    except FileNotFoundError:
        return PlainTextResponse("❌ final.txt 파일이 존재하지 않습니다.")
