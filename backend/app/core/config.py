"""Application configuration using Pydantic Settings with modular structure."""

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.helpers import parse_bool_value, parse_list_value

# Shared config for all nested settings
_base_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")


class Environment(StrEnum):
    """Application environment."""

    LOCAL = "local"
    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class AppSettings(BaseSettings):
    """Application configuration."""

    model_config = _base_config

    name: str = Field(default="backend", validation_alias="APP_NAME", description="Application name")
    display_name: str = Field(
        default="PulseDB",
        validation_alias="APP_DISPLAY_NAME",
        description="Application display name for emails and UI",
    )
    version: str = Field(
        default="0.1.2",
        validation_alias="APP_VERSION",
        description="Application version",
    )
    debug: bool = Field(default=False, validation_alias="DEBUG", description="Debug mode")
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        validation_alias="ENVIRONMENT",
        description="Environment (local, development, test, production)",
    )

    item_promotion_threshold: int = Field(
        default=10,
        validation_alias="ITEM_PROMOTION_THRESHOLD",
        description="Number of promotions required to add item to global catalogue",
        gt=0,
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: Environment) -> Environment:
        """Validate environment is one of allowed values."""
        if v not in Environment:
            allowed = {e.value for e in Environment}
            raise ValueError(f"Environment must be one of {allowed}, got: {v}")
        return v


class ServerSettings(BaseSettings):
    """Server configuration."""

    model_config = _base_config

    host: str = Field(default="0.0.0.0", validation_alias="HOST", description="Server host")
    port: int = Field(default=8000, validation_alias="PORT", description="Server port")
    reload: bool = Field(
        default=True,
        validation_alias="RELOAD",
        description="Auto-reload on code changes",
    )
    cors_origins: str | list[str] = Field(
        default='["http://localhost:3000"]',
        validation_alias="CORS_ORIGINS",
        description="Allowed CORS origins",
    )
    cors_credentials: bool = Field(
        default=True,
        validation_alias="CORS_CREDENTIALS",
        description="Allow credentials",
    )
    cors_methods: str | list[str] = Field(
        default='["*"]',
        validation_alias="CORS_METHODS",
        description="Allowed HTTP methods",
    )
    cors_headers: str | list[str] = Field(
        default='["*"]',
        validation_alias="CORS_HEADERS",
        description="Allowed HTTP headers",
    )
    allowed_hosts: str | list[str] = Field(
        default='["localhost", "127.0.0.1"]',
        validation_alias="ALLOWED_HOSTS",
        description="Allowed hosts for TrustedHostMiddleware (production security)",
    )

    @field_validator("cors_origins", "cors_methods", "cors_headers", "allowed_hosts", mode="after")
    @classmethod
    def parse_list_fields(cls, v: str | list[str]) -> list[str]:
        """Parse list fields from JSON array or comma-separated string."""
        return parse_list_value(v)

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got: {v}")
        return v


class DatabaseSettings(BaseSettings):
    """Database configuration."""

    model_config = _base_config

    url: str = Field(
        default="sqlite+aiosqlite:///./data/app.db",
        validation_alias="DATABASE_URL",
        description="Database connection URL",
    )
    pool_size: int = Field(
        default=5,
        validation_alias="DATABASE_POOL_SIZE",
        description="Database connection pool size",
    )
    max_overflow: int = Field(
        default=10,
        validation_alias="DATABASE_MAX_OVERFLOW",
        description="Max database connections overflow",
    )
    pool_recycle: int = Field(
        default=3600,
        validation_alias="DATABASE_POOL_RECYCLE",
        description="Database pool recycle time (seconds)",
    )
    echo: bool = Field(default=False, validation_alias="DATABASE_ECHO", description="Echo SQL queries")

    @field_validator("url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL format."""
        if not v:
            raise ValueError("Database URL cannot be empty")
        # Support both sqlite and postgresql
        if not (v.startswith("sqlite") or v.startswith("postgresql")):
            raise ValueError("Only SQLite and PostgreSQL databases are supported")
        return v


class SecuritySettings(BaseSettings):
    """Security and authentication configuration."""

    model_config = _base_config

    secret_key: str = Field(
        default="change-me-in-production-min-32-chars!",
        validation_alias="SECRET_KEY",
        description="Secret key for JWT and other crypto operations",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias="JWT_ALGORITHM",
        description="JWT signing algorithm",
    )
    jwt_issuer: str = Field(
        default="pulse-db",
        validation_alias="JWT_ISSUER",
        description="JWT 'iss' claim; verified on decode to bind tokens to this deployment",
    )
    jwt_audience: str = Field(
        default="pulse-db",
        validation_alias="JWT_AUDIENCE",
        description="JWT 'aud' claim; verified on decode to bind tokens to this deployment",
    )
    access_token_expires_minutes: int = Field(
        default=30,
        validation_alias="ACCESS_TOKEN_EXPIRES_MINUTES",
        description="Access token expiration in minutes",
    )
    refresh_token_expires_days: int = Field(
        default=7,
        validation_alias="REFRESH_TOKEN_EXPIRES_DAYS",
        description="Refresh token expiration in days",
    )
    password_reset_token_expires_hours: int = Field(
        default=1,
        validation_alias="PASSWORD_RESET_TOKEN_EXPIRES_HOURS",
        description="Password reset token expiration in hours",
    )
    email_verification_token_expires_hours: int = Field(
        default=24,
        validation_alias="EMAIL_VERIFICATION_TOKEN_EXPIRES_HOURS",
        description="Email verification token expiration in hours",
    )
    superadmin_email: str | None = Field(
        default=None,
        validation_alias="SUPERADMIN_EMAIL",
        description="Email address of the super admin user (owner) - cannot be deleted or demoted",
    )
    protected_user_email: str | None = Field(
        default=None,
        validation_alias="PROTECTED_USER_EMAIL",
        description="Protected user email - this user cannot be deleted",
    )
    credentials_encryption_key: str | None = Field(
        default=None,
        validation_alias="CREDENTIALS_ENCRYPTION_KEY",
        description="Fernet key (urlsafe base64, 32 bytes) used to encrypt monitored-instance credentials at rest. Generate with `Fernet.generate_key()`.",
    )

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key strength and security."""
        if "change-me" in v.lower() or "change-this" in v.lower():
            raise ValueError("Secret key must be changed from default value in production. " "Set SECRET_KEY environment variable with a secure random string.")

        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long for security. " "Use a cryptographically secure random string.")

        # Check for basic entropy (not all same character)
        if len(set(v)) < 8:
            raise ValueError("Secret key must have sufficient entropy. " "Use a truly random string with varied characters.")

        return v


class RateLimitSettings(BaseSettings):
    """Rate limiting configuration."""

    model_config = _base_config

    enabled: bool = Field(
        default=True,
        validation_alias="RATE_LIMIT_ENABLED",
        description="Enable rate limiting",
    )
    default_per_minute: int = Field(
        default=60,
        validation_alias="RATE_LIMIT_DEFAULT_PER_MINUTE",
        description="Default rate limit per minute",
    )
    default_per_hour: int = Field(
        default=1000,
        validation_alias="RATE_LIMIT_DEFAULT_PER_HOUR",
        description="Default rate limit per hour",
    )
    auth_register: str = Field(
        default="5/minute",
        validation_alias="AUTH_REGISTER_RATE_LIMIT",
        description="Registration rate limit",
    )
    auth_login: str = Field(
        default="10/minute",
        validation_alias="AUTH_LOGIN_RATE_LIMIT",
        description="Login rate limit",
    )
    auth_refresh: str = Field(
        default="20/minute",
        validation_alias="AUTH_REFRESH_RATE_LIMIT",
        description="Token refresh rate limit",
    )
    auth_password_change: str = Field(
        default="3/minute",
        validation_alias="AUTH_PASSWORD_CHANGE_RATE_LIMIT",
        description="Password change rate limit",
    )


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    model_config = _base_config

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(default="INFO", validation_alias="LOG_LEVEL", description="Logging level")
    format: str = Field(
        default="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        validation_alias="LOG_FORMAT",
        description="Log format",
    )
    file: str | None = Field(default=None, validation_alias="LOG_FILE", description="Log file path")


class RecaptchaSettings(BaseSettings):
    """Google reCAPTCHA v3 configuration."""

    model_config = _base_config

    enabled: bool = Field(
        default=False,
        validation_alias="RECAPTCHA_ENABLED",
        description="Enable reCAPTCHA verification (optional security feature)",
    )
    secret_key: str = Field(
        default="",
        validation_alias="RECAPTCHA_SECRET_KEY",
        description="Google reCAPTCHA v3 secret key",
    )
    site_key: str = Field(
        default="",
        validation_alias="RECAPTCHA_SITE_KEY",
        description="Google reCAPTCHA v3 site key (for frontend)",
    )
    min_score: float = Field(
        default=0.5,
        validation_alias="RECAPTCHA_MIN_SCORE",
        description="Minimum reCAPTCHA score to accept (0.0-1.0)",
    )
    verify_url: str = Field(
        default="https://www.google.com/recaptcha/api/siteverify",
        validation_alias="RECAPTCHA_VERIFY_URL",
        description="reCAPTCHA verification endpoint",
    )

    @field_validator("enabled", mode="before")
    @classmethod
    def parse_enabled(cls, v: str | bool) -> bool:
        """Parse enabled field from string or bool."""
        return parse_bool_value(v)

    @field_validator("min_score")
    @classmethod
    def validate_min_score(cls, v: float) -> float:
        """Validate reCAPTCHA score is in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"reCAPTCHA min_score must be between 0.0 and 1.0, got: {v}")
        return v


class OAuthSettings(BaseSettings):
    """OAuth authentication configuration."""

    model_config = _base_config

    # Google OAuth
    google_client_id: str = Field(
        default="",
        validation_alias="GOOGLE_OAUTH_CLIENT_ID",
        description="Google OAuth client ID",
    )
    google_client_secret: str = Field(
        default="",
        validation_alias="GOOGLE_OAUTH_CLIENT_SECRET",
        description="Google OAuth client secret",
    )
    google_redirect_uri: str = Field(
        default="",
        validation_alias="GOOGLE_OAUTH_REDIRECT_URI",
        description="Google OAuth redirect URI",
    )

    # Facebook OAuth
    facebook_client_id: str = Field(
        default="",
        validation_alias="FACEBOOK_OAUTH_CLIENT_ID",
        description="Facebook OAuth client ID (App ID)",
    )
    facebook_client_secret: str = Field(
        default="",
        validation_alias="FACEBOOK_OAUTH_CLIENT_SECRET",
        description="Facebook OAuth client secret (App Secret)",
    )
    facebook_redirect_uri: str = Field(
        default="",
        validation_alias="FACEBOOK_OAUTH_REDIRECT_URI",
        description="Facebook OAuth redirect URI",
    )

    # GitHub OAuth (login callback: /auth/callback/github)
    github_client_id: str = Field(
        default="",
        validation_alias="GITHUB_OAUTH_CLIENT_ID",
        description="GitHub OAuth client ID for login",
    )
    github_client_secret: str = Field(
        default="",
        validation_alias="GITHUB_OAUTH_CLIENT_SECRET",
        description="GitHub OAuth client secret for login",
    )
    github_redirect_uri: str = Field(
        default="",
        validation_alias="GITHUB_OAUTH_REDIRECT_URI",
        description="GitHub login callback URL (e.g. /auth/callback/github)",
    )


class EmailSettings(BaseSettings):
    """Email service configuration."""

    model_config = _base_config

    enabled: bool = Field(
        default=True,
        validation_alias="EMAIL_ENABLED",
        description="Enable email service",
    )
    adapter: Literal["file", "smtp"] = Field(
        default="file",
        validation_alias="EMAIL_ADAPTER",
        description="Email adapter type (file or smtp)",
    )
    file_path: str = Field(
        default="./emails",
        validation_alias="EMAIL_FILE_PATH",
        description="Path for file email adapter",
    )
    smtp_host: str = Field(
        default="localhost",
        validation_alias="SMTP_HOST",
        description="SMTP server host",
    )
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT", description="SMTP server port")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER", description="SMTP username")
    smtp_password: str = Field(default="", validation_alias="SMTP_PASSWORD", description="SMTP password")
    smtp_from: str = Field(
        default="noreply@example.com",
        validation_alias="SMTP_FROM",
        description="Default from email address",
    )
    smtp_use_tls: bool = Field(
        default=True,
        validation_alias="SMTP_USE_TLS",
        description="Use TLS for SMTP connection",
    )
    enable_audit: bool = Field(
        default=True,
        validation_alias="EMAIL_ENABLE_AUDIT",
        description="Enable email audit logging to database",
    )
    enable_retry: bool = Field(
        default=False,
        validation_alias="EMAIL_ENABLE_RETRY",
        description="Enable retry logic for SMTP (with exponential backoff)",
    )
    max_retries: int = Field(
        default=5,
        validation_alias="EMAIL_MAX_RETRIES",
        description="Maximum retry attempts for SMTP",
    )


class StorageSettings(BaseSettings):
    """Storage configuration for file uploads."""

    model_config = _base_config

    # Storage type
    type: Literal["local", "s3"] = Field(
        default="local",
        validation_alias="STORAGE_TYPE",
        description="Storage backend type (local or s3)",
    )

    # Local storage
    local_path: str = Field(
        default="./uploads",
        validation_alias="STORAGE_LOCAL_PATH",
        description="Local storage base path",
    )
    base_url: str | None = Field(
        default=None,
        validation_alias="STORAGE_BASE_URL",
        description="Base URL for serving uploaded files (e.g., https://api.pulse-db.example.com or http://localhost:8000). If not set, uses relative paths.",
    )

    # S3 storage
    s3_bucket: str = Field(
        default="",
        validation_alias="STORAGE_S3_BUCKET",
        description="S3 bucket name",
    )
    s3_access_key: str = Field(
        default="",
        validation_alias="STORAGE_S3_ACCESS_KEY",
        description="S3 access key ID",
    )
    s3_secret_key: str = Field(
        default="",
        validation_alias="STORAGE_S3_SECRET_KEY",
        description="S3 secret access key",
    )
    s3_region: str = Field(
        default="us-east-1",
        validation_alias="STORAGE_S3_REGION",
        description="S3 region",
    )
    s3_endpoint_url: str | None = Field(
        default=None,
        validation_alias="STORAGE_S3_ENDPOINT_URL",
        description="S3 endpoint URL (for S3-compatible services)",
    )
    s3_public_endpoint_url: str | None = Field(
        default=None,
        validation_alias="STORAGE_S3_PUBLIC_ENDPOINT_URL",
        description="Public S3 endpoint URL for generating accessible URLs (e.g., http://localhost:9000 for MinIO in Docker). If not set, uses s3_endpoint_url.",
    )

    # Upload limits
    max_file_size: int = Field(
        default=20 * 1024 * 1024,  # 20 MB (default for regular users)
        validation_alias="STORAGE_MAX_FILE_SIZE",
        description="Maximum file size in bytes (default for regular users, admins have 50 MB)",
    )
    max_file_size_admin: int = Field(
        default=50 * 1024 * 1024,  # 50 MB (for admins)
        validation_alias="STORAGE_MAX_FILE_SIZE_ADMIN",
        description="Maximum file size in bytes for administrators",
    )
    max_files_per_item: int = Field(
        default=10,
        validation_alias="STORAGE_MAX_FILES_PER_ITEM",
        description="Maximum number of images per item",
    )
    allowed_mime_types: str | list[str] = Field(
        default='["image/jpeg", "image/png", "image/webp", "image/gif"]',
        validation_alias="STORAGE_ALLOWED_MIME_TYPES",
        description="Allowed MIME types for uploads",
    )

    # Image processing
    enable_processing: bool = Field(
        default=True,
        validation_alias="STORAGE_ENABLE_PROCESSING",
        description="Enable auto-resize and optimization",
    )
    max_width: int = Field(
        default=1920,
        validation_alias="STORAGE_MAX_WIDTH",
        description="Maximum image width (auto-resize)",
    )
    max_height: int = Field(
        default=1920,
        validation_alias="STORAGE_MAX_HEIGHT",
        description="Maximum image height (auto-resize)",
    )
    jpeg_quality: int = Field(
        default=85,
        validation_alias="STORAGE_JPEG_QUALITY",
        description="JPEG compression quality (1-100)",
    )
    convert_to_webp: bool = Field(
        default=False,
        validation_alias="STORAGE_CONVERT_TO_WEBP",
        description="Convert images to WebP format",
    )

    @field_validator("allowed_mime_types", mode="after")
    @classmethod
    def parse_mime_types(cls, v: str | list[str]) -> list[str]:
        """Parse MIME types from JSON array or comma-separated string."""
        return parse_list_value(v)

    @field_validator("jpeg_quality")
    @classmethod
    def validate_jpeg_quality(cls, v: int) -> int:
        """Validate JPEG quality is in valid range."""
        if not 1 <= v <= 100:
            raise ValueError(f"JPEG quality must be between 1 and 100, got: {v}")
        return v


class SentrySettings(BaseSettings):
    """Sentry error monitoring configuration."""

    model_config = _base_config

    enabled: bool = Field(
        default=False,
        validation_alias="SENTRY_ENABLED",
        description="Enable Sentry error monitoring",
    )
    dsn: str = Field(
        default="",
        validation_alias="SENTRY_DSN",
        description="Sentry DSN (Data Source Name) for error reporting",
    )
    environment: str = Field(
        default="development",
        validation_alias="SENTRY_ENVIRONMENT",
        description="Environment name for Sentry (development, staging, production)",
    )
    traces_sample_rate: float = Field(
        default=1.0,
        validation_alias="SENTRY_TRACES_SAMPLE_RATE",
        description="Performance monitoring sample rate (0.0-1.0)",
    )
    profiles_sample_rate: float = Field(
        default=1.0,
        validation_alias="SENTRY_PROFILES_SAMPLE_RATE",
        description="Profiling sample rate (0.0-1.0)",
    )
    release: str | None = Field(
        default=None,
        validation_alias="SENTRY_RELEASE",
        description="Release version for Sentry (e.g., git commit SHA or version number)",
    )

    @field_validator("enabled", mode="before")
    @classmethod
    def parse_enabled(cls, v: str | bool) -> bool:
        """Parse enabled field from string or bool."""
        return parse_bool_value(v)

    @field_validator("traces_sample_rate", "profiles_sample_rate")
    @classmethod
    def validate_sample_rate(cls, v: float) -> float:
        """Validate sample rate is in valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Sample rate must be between 0.0 and 1.0, got: {v}")
        return v


class RedisSettings(BaseSettings):
    """Redis configuration for token blacklist and challenge storage."""

    model_config = _base_config

    url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
        description="Redis connection URL",
    )
    token_blacklist_prefix: str = Field(
        default="blacklist:token:",
        validation_alias="REDIS_TOKEN_BLACKLIST_PREFIX",
        description="Redis key prefix for token blacklist",
    )
    webauthn_challenge_prefix: str = Field(
        default="webauthn:challenge:",
        validation_alias="REDIS_WEBAUTHN_CHALLENGE_PREFIX",
        description="Redis key prefix for WebAuthn challenges",
    )
    webauthn_challenge_ttl: int = Field(
        default=300,
        validation_alias="REDIS_WEBAUTHN_CHALLENGE_TTL",
        description="WebAuthn challenge TTL in seconds (default: 5 minutes)",
    )


class WebAuthnSettings(BaseSettings):
    """WebAuthn configuration."""

    model_config = _base_config

    rp_id: str = Field(
        default="localhost",
        validation_alias="WEBAUTHN_RP_ID",
        description="WebAuthn Relying Party ID (domain)",
    )
    rp_name: str = Field(
        default="PulseDB",
        validation_alias="WEBAUTHN_RP_NAME",
        description="WebAuthn Relying Party Name",
    )
    origin: str = Field(
        default="http://localhost:5176",
        validation_alias="WEBAUTHN_ORIGIN",
        description="WebAuthn expected origin (frontend URL)",
    )


class MonitorSettings(BaseSettings):
    """Monitoring runtime configuration."""

    model_config = _base_config

    check_interval_seconds: int = Field(
        default=10,
        validation_alias="MONITOR_CHECK_INTERVAL_SECONDS",
        description="Scheduler loop interval for due-site checks",
        ge=1,
    )
    live_poll_interval_seconds: int = Field(
        default=30,
        validation_alias="MONITOR_LIVE_POLL_INTERVAL_SECONDS",
        description="Max effective per-site polling interval while live mode is active",
        ge=1,
    )
    live_mode_ttl_seconds: int = Field(
        default=60,
        validation_alias="MONITOR_LIVE_MODE_TTL_SECONDS",
        description="Live mode TTL without heartbeat refresh",
        ge=1,
    )
    ui_background_refetch_seconds: int = Field(
        default=300,
        validation_alias="MONITOR_UI_BACKGROUND_REFETCH_SECONDS",
        description="Frontend monitoring refetch interval outside active monitor view",
        ge=1,
    )
    ui_active_refetch_seconds: int = Field(
        default=120,
        validation_alias="MONITOR_UI_ACTIVE_REFETCH_SECONDS",
        description="Frontend monitoring refetch interval in active monitor view",
        ge=1,
    )
    heartbeat_interval_seconds: int = Field(
        default=30,
        validation_alias="MONITOR_HEARTBEAT_INTERVAL_SECONDS",
        description="Frontend heartbeat interval for live mode keepalive",
        ge=1,
    )
    ssl_expiry_warning_days: int = Field(
        default=30,
        validation_alias="MONITOR_SSL_EXPIRY_WARNING_DAYS",
        description="Days before certificate expiry to switch status to expiring_soon",
        ge=1,
    )


class HealthSettings(BaseSettings):
    """Health/monitoring configuration (PulseDB integration)."""

    model_config = _base_config

    details_token: str = Field(
        default="",
        validation_alias="HEALTH_DETAILS_TOKEN",
        description="Bearer token required to access GET /api/health/details (PulseDB)",
    )


class Settings(BaseSettings):
    """
    Main application settings composed of nested configuration classes.

    All settings can be overridden via environment variables.
    Use nested structure for better organization and clarity.
    """

    model_config = _base_config

    # Nested settings
    app: AppSettings = Field(default_factory=AppSettings)
    server: ServerSettings = Field(default_factory=ServerSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    rate_limit: RateLimitSettings = Field(default_factory=RateLimitSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    recaptcha: RecaptchaSettings = Field(default_factory=RecaptchaSettings)
    oauth: OAuthSettings = Field(default_factory=OAuthSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    sentry: SentrySettings = Field(default_factory=SentrySettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    webauthn: WebAuthnSettings = Field(default_factory=WebAuthnSettings)
    monitor: MonitorSettings = Field(default_factory=MonitorSettings)
    health: HealthSettings = Field(default_factory=HealthSettings)

    # Legacy compatibility - still accessible at root level
    frontend_url: str = Field(
        default="http://localhost:3000",
        validation_alias="FRONTEND_URL",
        description="Frontend application URL for reset links and redirects",
    )

    # Convenience methods
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app.environment in (Environment.LOCAL, Environment.DEVELOPMENT)

    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app.environment == Environment.PRODUCTION

    def is_test(self) -> bool:
        """Check if running in test mode."""
        return self.app.environment == Environment.TEST

    def validate_production(self) -> None:
        """Assert production-safe invariants; raise ``ValueError`` on violation.

        Call once on startup (see app_factory) when ``is_production()``. This is a
        defence-in-depth guardrail against deploying with insecure defaults:

        - ``DEBUG`` must be off (leaks stack traces / error details).
        - ``ALLOWED_HOSTS`` must be a non-empty explicit allow-list (TrustedHost).
        - ``CORS_ORIGINS`` must be a non-empty explicit allow-list, never ``*``
          (a wildcard origin with credentials is a real CSRF/exfiltration hole).

        The secret-key strength is already enforced at field-validation time.
        """
        if not self.is_production():
            return

        errors: list[str] = []

        if self.app.debug:
            errors.append("DEBUG must be false in production (set DEBUG=false).")

        # allowed_hosts / cors_origins are parsed to lists by their validators.
        allowed_hosts = self.server.allowed_hosts
        if not allowed_hosts or "*" in allowed_hosts:
            errors.append("ALLOWED_HOSTS must be a non-empty explicit allow-list " "(no '*') in production.")

        cors_origins = self.server.cors_origins
        if not cors_origins:
            errors.append("CORS_ORIGINS must be set to an explicit allow-list.")
        elif "*" in cors_origins:
            errors.append("CORS_ORIGINS must not contain '*' in production " "(wildcard origins with credentials are unsafe).")

        if errors:
            raise ValueError("Insecure production configuration detected:\n- " + "\n- ".join(errors))


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
