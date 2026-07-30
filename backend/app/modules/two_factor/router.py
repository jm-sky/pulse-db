"""FastAPI router for TOTP setup (Phase 1 & 2)."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from app.core.auth.dependencies import get_token_blacklist_service
from app.core.auth.token_blacklist import TokenBlacklistService
from app.core.limiter import rate_limit
from app.modules.auth.cookies import set_refresh_cookie
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.repositories import get_user_repository
from app.modules.auth.types.repository import UserRepositoryInterface

from .auth_utils import verify_two_factor_token
from .repositories import get_two_factor_repository
from .schemas import (
    BackupCodesResponse,
    CompletePasskeyAuthenticationRequest,
    CompletePasskeyRegistrationRequest,
    DisableTotpRequest,
    InitiatePasskeyAuthenticationRequest,
    InitiatePasskeyRegistrationRequest,
    PasskeyListResponse,
    PasskeyRegistrationInitiateResponse,
    PasskeyResponse,
    RegenerateBackupCodesRequest,
    TotpInitiateResponse,
    TotpStatusResponse,
    TwoFactorStatusResponse,
    TwoFactorVerifyResponse,
    UpdatePreferredMethodRequest,
    VerifyTotpLoginRequest,
    VerifyTotpSetupRequest,
    VerifyTotpSetupResponse,
    WebAuthnStatusResponse,
)
from .service import TwoFactorService

router = APIRouter(tags=["Two-Factor Authentication"])


async def get_service(
    repo: Any = Depends(get_two_factor_repository),
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
    blacklist_service: TokenBlacklistService = Depends(get_token_blacklist_service),
) -> TwoFactorService:
    """Get TwoFactorService with Redis challenge store.

    user_repo/blacklist_service are required by verify_totp_login and
    complete_passkey_authentication to mint full-claim login tokens (see
    TwoFactorService._issue_login_tokens).
    """
    challenge_store = None
    try:
        # Try to get Redis-based challenge store
        from app.core.config import settings
        from app.core.redis import get_redis_client

        from .challenge_store import WebAuthnChallengeStore

        redis_client = await get_redis_client()
        challenge_store = WebAuthnChallengeStore(
            redis_client=redis_client,
            key_prefix=settings.redis.webauthn_challenge_prefix,
            default_ttl=settings.redis.webauthn_challenge_ttl,
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to initialize challenge store: {e}. WebAuthn will work without server-side challenge storage (INSECURE)")

    return TwoFactorService(
        repository=repo,
        challenge_store=challenge_store,
        user_repository=user_repo,
        token_blacklist_service=blacklist_service,
    )


@router.post("/totp/initiate", response_model=TotpInitiateResponse)
@rate_limit("3/minute")
async def initiate_totp_setup(
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
) -> TotpInitiateResponse:
    _ = request  # required by slowapi rate limiting
    data = await service.initiate_totp_setup(user_id=current_user.id, email=current_user.email)
    return TotpInitiateResponse(**data) if isinstance(data, dict) else data


@router.post("/totp/verify", response_model=VerifyTotpSetupResponse)
@rate_limit("5/minute")
async def verify_totp_setup(
    body: VerifyTotpSetupRequest,
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
) -> VerifyTotpSetupResponse:
    _ = request  # required by slowapi rate limiting
    try:
        result = await service.verify_totp_setup(setup_token=body.setupToken, code=body.code)
        return VerifyTotpSetupResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/totp/status", response_model=TotpStatusResponse)
@rate_limit("10/minute")
async def totp_status(
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
) -> TotpStatusResponse:
    _ = request  # required by slowapi rate limiting
    status_data = await service.get_totp_status(user_id=current_user.id)
    return TotpStatusResponse(**status_data) if isinstance(status_data, dict) else status_data


@router.post("/totp/regenerate-backup-codes", response_model=BackupCodesResponse)
@rate_limit("3/minute")
async def regenerate_backup_codes(
    body: RegenerateBackupCodesRequest,
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
) -> BackupCodesResponse:
    _ = request  # required by slowapi rate limiting
    try:
        result = await service.regenerate_backup_codes(
            user_id=current_user.id,
            password=body.password,
            totp_code=body.totpCode,
            user_repository=user_repo,
        )
        return BackupCodesResponse(**result) if isinstance(result, dict) else result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/totp/disable")
@rate_limit("3/minute")
async def disable_totp(
    body: DisableTotpRequest,
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
    user_repo: UserRepositoryInterface = Depends(get_user_repository),
) -> dict[str, Any]:
    _ = request  # required by slowapi rate limiting
    try:
        return await service.disable_totp(
            user_id=current_user.id,
            password=body.password,
            backup_code=body.backupCode,
            user_repository=user_repo,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/totp/verify-login", response_model=TwoFactorVerifyResponse, response_model_exclude={"refreshToken"})
@rate_limit("5/minute")
async def verify_totp_login(
    body: VerifyTotpLoginRequest,
    request: Request,
    response: Response,
    service: TwoFactorService = Depends(get_service),
) -> TwoFactorVerifyResponse:
    """Verify TOTP code during login and return JWT tokens.

    This endpoint is public (no auth required) as it's part of the login flow.
    Rate limiting is applied both globally and per-user. The refresh token is
    never returned in the body — it's set as an HttpOnly cookie.
    """
    from .decorators import require_2fa_rate_limit

    # Apply per-user rate limiting wrapper
    @require_2fa_rate_limit(max_attempts=5, window_minutes=15)
    async def _verify_with_rate_limit() -> TwoFactorVerifyResponse:
        try:
            result_dict = await service.verify_totp_login(
                two_factor_token=body.twoFactorToken,
                code=body.code,
            )
            # Service always returns dict, convert to response model
            verify_response = TwoFactorVerifyResponse(**result_dict)
            if verify_response.refreshToken:
                set_refresh_cookie(request, response, verify_response.refreshToken)
            return verify_response
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(exc),
            ) from exc

    return await _verify_with_rate_limit()  # type: ignore[no-any-return]


# WebAuthn/Passkey endpoints
@router.post("/webauthn/register/initiate", response_model=PasskeyRegistrationInitiateResponse)
@rate_limit("5/minute")
async def initiate_passkey_registration(
    body: InitiatePasskeyRegistrationRequest,
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
) -> PasskeyRegistrationInitiateResponse:
    _ = request  # required by slowapi rate limiting
    """Initiate passkey registration by generating WebAuthn options."""
    result = await service.initiate_passkey_registration(
        user_id=current_user.id,
        user_email=current_user.email,
        user_name=current_user.name,
        name=body.name,
    )
    return PasskeyRegistrationInitiateResponse(**result) if isinstance(result, dict) else result


@router.post("/webauthn/register/complete", response_model=PasskeyResponse)
@rate_limit("5/minute")
async def complete_passkey_registration(
    body: CompletePasskeyRegistrationRequest,
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
) -> PasskeyResponse:
    _ = request  # required by slowapi rate limiting
    """Complete passkey registration by verifying WebAuthn credential."""
    # Extract user agent from request headers
    user_agent = request.headers.get("User-Agent")
    origin = request.headers.get("Origin") or request.headers.get("Referer")

    try:
        result = await service.complete_passkey_registration(
            registration_token=body.registrationToken,
            credential_json=body.credential,
            name=body.name,
            user_agent=user_agent,
            origin=origin,
        )
        return PasskeyResponse(**result) if isinstance(result, dict) else result
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/webauthn/passkeys", response_model=PasskeyListResponse)
@rate_limit("10/minute")
async def list_passkeys(
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
) -> PasskeyListResponse:
    _ = request  # required by slowapi rate limiting
    """List all passkeys for the current user."""
    passkeys = await service.repository.get_passkeys(current_user.id)

    # Convert to response format
    passkey_list = []
    for pk in passkeys:
        import json

        transports = json.loads(pk.transports) if pk.transports else None
        passkey_list.append(
            PasskeyResponse(
                id=pk.id,
                name=pk.name,
                createdAt=pk.created_at,
                lastUsedAt=pk.last_used_at,
                isEnabled=pk.is_enabled,
                userAgent=pk.user_agent,
                aaguid=pk.aaguid,
                transports=transports,
                backupEligible=pk.backup_eligible,
                backupState=pk.backup_state,
            )
        )

    return PasskeyListResponse(passkeys=passkey_list, total=len(passkey_list))


@router.get("/webauthn/status", response_model=WebAuthnStatusResponse)
@rate_limit("10/minute")
async def webauthn_status(
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
) -> WebAuthnStatusResponse:
    _ = request  # required by slowapi rate limiting
    """Get WebAuthn/Passkey status for the current user."""
    status_data = await service.get_webauthn_status(user_id=current_user.id)
    return WebAuthnStatusResponse(**status_data) if isinstance(status_data, dict) else status_data


@router.get("/status", response_model=TwoFactorStatusResponse)
@rate_limit("10/minute")
async def two_factor_status(
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
) -> TwoFactorStatusResponse:
    _ = request  # required by slowapi rate limiting
    """Get combined 2FA status (TOTP + WebAuthn) for the current user."""
    status_data = await service.get_two_factor_status(user_id=current_user.id)
    return TwoFactorStatusResponse(**status_data) if isinstance(status_data, dict) else status_data


# Additional WebAuthn endpoints
@router.delete(
    "/webauthn/passkeys/{passkey_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
@rate_limit("10/minute")
async def delete_passkey(
    passkey_id: str,
    request: Request,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
) -> None:
    """Delete a passkey for the current user."""
    _ = request  # required by slowapi rate limiting
    try:
        await service.delete_passkey(passkey_id=passkey_id, user_id=current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post("/webauthn/authenticate/initiate")
@rate_limit("5/minute")
async def initiate_passkey_authentication(
    request: Request,
    body: InitiatePasskeyAuthenticationRequest,
    service: TwoFactorService = Depends(get_service),
) -> dict[str, Any]:
    """Initiate passkey authentication during login.

    Public endpoint (no CurrentUser): the caller only holds a 2FA-pending
    token at this point, not a full session — CurrentUser would 401 here.
    """
    _ = request  # required by slowapi rate limiting
    try:
        payload = verify_two_factor_token(body.twoFactorToken)
        return await service.initiate_passkey_authentication(user_id=payload["sub"])
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post(
    "/webauthn/authenticate/complete",
    response_model=TwoFactorVerifyResponse,
    response_model_exclude={"refreshToken"},
)
@rate_limit("5/minute")
async def complete_passkey_authentication(
    request: Request,
    response: Response,
    body: CompletePasskeyAuthenticationRequest,
    service: TwoFactorService = Depends(get_service),
) -> TwoFactorVerifyResponse:
    """Complete passkey authentication during login and return JWT tokens.

    Public endpoint (no CurrentUser), mirroring /totp/verify-login. The
    refresh token is never returned in the body — it's set as an HttpOnly
    cookie.
    """
    _ = request  # required by slowapi rate limiting
    try:
        payload = verify_two_factor_token(body.twoFactorToken)
        result = await service.complete_passkey_authentication(
            challenge_token=body.challengeToken,
            credential_json=body.credential,
            expected_user_id=payload["sub"],
        )
        verify_response = TwoFactorVerifyResponse(**result)
        if verify_response.refreshToken:
            set_refresh_cookie(request, response, verify_response.refreshToken)
        return verify_response
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.patch("/preferred-method")
@rate_limit("10/minute")
async def update_preferred_method(
    request: Request,
    body: UpdatePreferredMethodRequest,
    current_user: CurrentUser,
    service: TwoFactorService = Depends(get_service),
) -> dict[str, str]:
    """Update user's preferred 2FA method."""
    _ = request  # required by slowapi rate limiting
    try:
        method = body.preferredMethod
        if method is not None:
            await service.update_preferred_method(user_id=current_user.id, method=method)
            return {"message": f"Preferred 2FA method updated to {method}"}
        else:
            # Clear preference (set to None)
            await service.update_preferred_method(user_id=current_user.id, method=None)
            return {"message": "Preferred 2FA method cleared"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
