"""
FastAPI 웹 서버

Microsoft 365 인증을 위한 웹 인터페이스를 제공합니다.
"""

import asyncio
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from adapters.web.auth_routes import router as auth_router
from adapters.db.database import initialize_database
from adapters.logger import create_logger
from config.adapters import get_config

# FastAPI 앱 생성
app = FastAPI(
    title="Microsoft 365 Graph API 인증 서비스",
    description="OAuth 2.0 인증을 위한 웹 인터페이스",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 로거 설정
logger = create_logger("web_server")

# 라우터 등록
app.include_router(auth_router)


@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행되는 이벤트"""
    logger.info("FastAPI 웹 서버 시작")
    
    # 데이터베이스 초기화
    config = get_config()
    db_adapter = initialize_database(config)
    await db_adapter.initialize()
    await db_adapter.create_tables()
    
    logger.info(f"환경: {config.get_environment()}")
    logger.info(f"데이터베이스: {config.get_database_url()}")
    logger.info("웹 서버 준비 완료")


@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행되는 이벤트"""
    logger.info("FastAPI 웹 서버 종료")
    
    # 데이터베이스 연결 종료
    from adapters.db.database import get_database_adapter
    db_adapter = get_database_adapter()
    if db_adapter:
        await db_adapter.close()


@app.get("/", response_class=HTMLResponse)
async def root():
    """홈페이지"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Microsoft 365 Graph API 인증 서비스</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 40px;
                max-width: 800px;
                margin: 0 auto;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            h1 {
                color: #0078d4;
                margin-bottom: 30px;
            }
            .auth-methods {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .auth-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
            }
            .auth-card h2 {
                color: #323130;
                margin-bottom: 15px;
            }
            .auth-card p {
                color: #605e5c;
                line-height: 1.5;
            }
            .start-btn {
                display: inline-block;
                margin-top: 15px;
                padding: 10px 20px;
                background: #0078d4;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                transition: background 0.2s;
            }
            .start-btn:hover {
                background: #106ebe;
            }
            .status-check {
                margin-top: 40px;
                padding: 20px;
                background: #e7f3ff;
                border-radius: 8px;
            }
            input[type="email"] {
                padding: 8px 12px;
                border: 1px solid #8a8886;
                border-radius: 4px;
                width: 300px;
                margin-right: 10px;
            }
            .check-btn {
                padding: 8px 16px;
                background: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Microsoft 365 Graph API 인증 서비스</h1>
            <p>Microsoft 365 계정 인증을 위한 웹 인터페이스입니다.</p>
            
            <div class="auth-methods">
                <div class="auth-card">
                    <h2>Authorization Code Flow</h2>
                    <p>웹 애플리케이션에 적합한 표준 OAuth 2.0 인증 방식입니다. 브라우저에서 Microsoft 로그인 페이지로 리디렉션됩니다.</p>
                    <p>먼저 CLI에서 계정을 등록한 후 사용하세요.</p>
                </div>
                
                <div class="auth-card">
                    <h2>Device Code Flow</h2>
                    <p>CLI나 IoT 디바이스에 적합한 인증 방식입니다. 별도 브라우저에서 코드를 입력하여 인증합니다.</p>
                    <p>브라우저가 없는 환경에서도 사용 가능합니다.</p>
                </div>
            </div>
            
            <div class="status-check">
                <h3>인증 상태 확인</h3>
                <p>등록된 계정의 인증 상태를 확인할 수 있습니다.</p>
                <input type="email" id="email" placeholder="이메일 주소 입력">
                <button class="check-btn" onclick="checkStatus()">상태 확인</button>
                <div id="status-result" style="margin-top: 15px;"></div>
            </div>
        </div>
        
        <script>
            async function checkStatus() {
                const email = document.getElementById('email').value;
                if (!email) {
                    alert('이메일을 입력하세요.');
                    return;
                }
                
                const resultDiv = document.getElementById('status-result');
                resultDiv.innerHTML = '확인 중...';
                
                try {
                    const response = await fetch(`/auth/status/${email}`);
                    if (response.ok) {
                        const data = await response.json();
                        resultDiv.innerHTML = `
                            <div style="padding: 15px; background: #f0f0f0; border-radius: 4px;">
                                <p><strong>이메일:</strong> ${data.email}</p>
                                <p><strong>상태:</strong> ${data.status}</p>
                                <p><strong>인증 타입:</strong> ${data.auth_type}</p>
                                <p><strong>토큰 유효:</strong> ${data.token_valid ? '✅ 유효' : '❌ 만료/없음'}</p>
                                ${data.has_token ? `
                                    <a href="/auth/start?email=${email}&flow=${data.auth_type}" 
                                       class="start-btn" style="margin-top: 10px;">재인증</a>
                                ` : `
                                    <a href="/auth/start?email=${email}&flow=${data.auth_type}" 
                                       class="start-btn" style="margin-top: 10px;">인증 시작</a>
                                `}
                            </div>
                        `;
                    } else if (response.status === 404) {
                        resultDiv.innerHTML = '<p style="color: #d32f2f;">계정을 찾을 수 없습니다. CLI에서 먼저 등록하세요.</p>';
                    } else {
                        resultDiv.innerHTML = '<p style="color: #d32f2f;">오류가 발생했습니다.</p>';
                    }
                } catch (error) {
                    resultDiv.innerHTML = '<p style="color: #d32f2f;">서버 연결 오류</p>';
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """API 문서 페이지"""
    return app.swagger_ui_html


if __name__ == "__main__":
    # 설정 로드
    config = get_config()
    
    # 서버 실행
    uvicorn.run(
        "web_server:app",
        host="0.0.0.0",
        port=5000,
        reload=config.is_debug(),
        log_level=config.get_log_level().lower(),
    )
