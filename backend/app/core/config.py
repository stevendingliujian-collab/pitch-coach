import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://pitchcoach:pitchcoach_dev@localhost:5432/pitchcoach"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO / OSS
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"
    minio_bucket: str = "pitchcoach"
    minio_secure: bool = False

    # JWT
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 120   # 2 hours (设计文档要求)
    refresh_token_expire_days: int = 30

    # SMS 验证码
    sms_provider: str = "stub"               # stub（开发）/ aliyun / tencent
    sms_access_key: str = ""
    sms_secret_key: str = ""
    sms_sign_name: str = "OTD述标教练"
    sms_template_id: str = ""
    sms_code_ttl: int = 300                  # 5 分钟
    sms_resend_interval: int = 60            # 60s 内不可重发
    sms_ip_rate_limit: int = 5               # 同 IP 10 分钟内最多 5 条

    # 微信开放平台（PC 扫码登录）
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_redirect_uri: str = "http://localhost:5173/auth/wechat/callback"
    wechat_qrcode_ttl: int = 300             # 二维码 5 分钟过期

    # 企业微信（P1）
    wecom_corp_id: str = ""
    wecom_agent_id: str = ""
    wecom_secret: str = ""
    wecom_redirect_uri: str = "http://localhost:5173/auth/wecom/callback"

    # 飞书（P1）
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    feishu_redirect_uri: str = "http://localhost:5173/auth/feishu/callback"

    # LLM (DashScope / Qwen)
    llm_api_key: str = ""
    llm_base_url: str = "https://coding.dashscope.aliyuncs.com/v1"
    llm_model: str = "qwen3.6-plus"
    llm_max_tokens: int = 8192
    llm_temperature: float = 0.3
    # Bypass proxy for domestic API endpoints
    no_proxy: str = "localhost,127.0.0.1,::1,.local,dashscope.aliyuncs.com,coding.dashscope.aliyuncs.com"

    # Knowledge base
    qdrant_url: str = "http://localhost:6333"
    embedding_model: str = "qwen3-embedding-8b"
    embedding_base_url: str = "https://aihubmix.com/v1"
    embedding_api_key: str = ""   # falls back to llm_api_key if empty
    embedding_dim: int = 4096     # qwen3-embedding-8b native dimension

    # TTS — provider: "fish_audio" | "xfyun" | "stub"
    tts_provider: str = "fish_audio"
    # Fish Audio
    fish_audio_api_key: str = ""
    fish_audio_base_url: str = "https://api.fish.audio/v1"
    # 科大讯飞在线语音合成 WebAPI
    # 控制台: https://console.xfyun.cn/app/myapp → 语音合成（流式版）
    xfyun_app_id: str = ""
    xfyun_api_key: str = ""
    xfyun_api_secret: str = ""

    # ASR
    asr_provider: str = "paraformer"
    paraformer_api_key: str = ""

    # App
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # File upload limits
    max_ppt_size_mb: int = 50
    max_ppt_pages: int = 100


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # Merge our domains into existing NO_PROXY so domestic APIs bypass the system proxy
    existing = os.environ.get("NO_PROXY", "") or os.environ.get("no_proxy", "")
    extra = [d for d in s.no_proxy.split(",") if d not in existing]
    merged = ",".join(filter(None, [existing] + extra))
    os.environ["NO_PROXY"] = merged
    os.environ["no_proxy"] = merged
    return s
