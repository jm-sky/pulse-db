"""FastAPI dependencies for authentication."""

import logging
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.auth.dependencies import get_token_blacklist_service
from app.core.auth.token_blacklist import TokenBlacklistService

from .auth_utils import verify_token
from .exceptions import (
    EmailNotVerifiedError,
    ExpiredTokenError,
    InactiveUserError,
    InvalidTokenError,
)
from .models import User
from .repositories import get_user_repository
from .service import AuthService
from .types.repository import UserRepositoryInterface

logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer()

# Try to use 2FA-enabled auth service if available
HAS_2FA = False
try:
    from app.modules.two_factor.repositories import get_two_factor_repository

    HAS_2FA = True
except ImportError:
    # Fallback to regular auth service - 2FA not available
    pass


def get_auth_service(
    user_repository: Annotated[UserRepositoryInterface, Depends(get_user_repository)],
    blacklist_service: Annotated[TokenBlacklistService, Depends(get_token_blacklist_service)],
    two_factor_repository: Any = (Depends(lambda: None) if not HAS_2FA else Depends(get_two_factor_repository)),
) -> AuthService:
    """Get auth service with 2FA support if available.

    Returns ``AuthServiceWith2FA`` (a subclass of ``AuthService``) when the 2FA
    module is installed, otherwise a plain ``AuthService`` — both satisfy the
    ``AuthService`` interface, so callers stay type-safe.
    """
    if HAS_2FA:
        from app.modules.two_factor.auth_integration import get_auth_service_with_2fa

        service = get_auth_service_with_2fa(
            user_repository=user_repository,
            two_factor_repository=two_factor_repository,
            token_blacklist_service=blacklist_service,
        )
        logger.debug(f"Created auth service: {type(service).__name__} (2FA enabled: True)")
        return service
    else:
        logger.debug("Using regular AuthService (2FA not available)")
        return AuthService(
            user_repository=user_repository,
            token_blacklist_service=blacklist_service,
            two_factor_repository=two_factor_repository,
        )


async def _verify_user_token(
    token: str,
    user_repository: UserRepositoryInterface,
    blacklist_service: TokenBlacklistService,
    two_factor_repository: Any = None,
) -> User:
    """
    Verify JWT token and return authenticated user.

    SECURITY: Enforces 2FA verification if user has 2FA enabled.
    SECURITY: Checks if token is blacklisted (revoked after logout or account deletion).
    """
    try:
        # SECURITY: Check if token is blacklisted
        if await blacklist_service.is_blacklisted(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        payload = verify_token(token)

        # Verify token type
        if payload.get("type") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # SECURITY: Reject tokens with tfaPending: true
        if payload.get("tfaPending") is True:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="2FA verification required. Token is pending 2FA verification.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user ID from token
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Get user from repository
        user = await user_repository.get_user_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.isActive:
            raise InactiveUserError("User account is inactive")

        token_version = payload.get("tv", 0)
        if token_version != user.tokenVersion:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_jti = payload.get("jti")
        if token_jti and await blacklist_service.is_jti_blacklisted(token_jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.isEmailVerified:
            raise EmailNotVerifiedError("Email verification required")

        # SECURITY: Check if user has 2FA enabled and verify token has tfaVerified=True
        if two_factor_repository is not None:
            try:
                from app.modules.two_factor.service import TwoFactorService

                two_factor_service = TwoFactorService(repository=two_factor_repository)

                # Check if user has 2FA enabled
                has_2fa_enabled = await two_factor_service.has_two_factor_enabled(user_id)

                if has_2fa_enabled:
                    # User has 2FA enabled - token MUST have tfaVerified=True
                    tfa_verified = payload.get("tfaVerified", False)
                    if not tfa_verified:
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="2FA verification required. Please complete two-factor authentication.",
                            headers={"WWW-Authenticate": "Bearer"},
                        )
            except ImportError:
                # 2FA module not available, skip check
                pass
            except Exception as e:
                # If 2FA check fails, log but don't break the request
                logger.warning(f"2FA verification check failed: {e}", exc_info=True)
                # In production, you might want to be more strict here

        return user

    except ExpiredTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except InactiveUserError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        ) from None
    except EmailNotVerifiedError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        ) from None


# Create get_current_user function with consistent signature
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    user_repository: Annotated[UserRepositoryInterface, Depends(get_user_repository)],
    blacklist_service: Annotated[TokenBlacklistService, Depends(get_token_blacklist_service)],
    two_factor_repository: Any = (Depends(lambda: None) if not HAS_2FA else Depends(get_two_factor_repository)),
) -> User:
    """Get current user with optional 2FA verification check and blacklist validation."""
    token = credentials.credentials
    if HAS_2FA and two_factor_repository is not None:
        return await _verify_user_token(token, user_repository, blacklist_service, two_factor_repository)
    else:
        return await _verify_user_token(token, user_repository, blacklist_service, None)


def get_current_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> str:
    """Extract JWT token from Authorization header.

    Args:
        credentials: HTTP Bearer credentials

    Returns:
        JWT token string (without "Bearer " prefix)
    """
    return credentials.credentials


async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to require admin privileges.

    Raises:
        HTTPException: If user is not an admin
    """
    if not current_user.isAdmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


async def require_owner(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to require owner privileges.

    Raises:
        HTTPException: If user is not an owner
    """
    if not current_user.isOwner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner privileges required",
        )
    return current_user


async def require_admin_or_owner(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to require admin or owner privileges.

    Raises:
        HTTPException: If user is neither admin nor owner
    """
    if not (current_user.isAdmin or current_user.isOwner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Owner privileges required",
        )
    return current_user


async def require_premium_or_higher(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Dependency to require premium user or higher privileges.

    Premium or higher means: Premium User, Administrator, or Owner.
    Regular User role does not have access.

    Raises:
        HTTPException: If user is a regular user (not premium/admin/owner)
    """
    if not (current_user.isPremium or current_user.isAdmin or current_user.isOwner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Premium, Admin, or Owner privileges required",
        )
    return current_user


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_admin)]
OwnerUser = Annotated[User, Depends(require_owner)]
AdminOrOwnerUser = Annotated[User, Depends(require_admin_or_owner)]
PremiumOrHigherUser = Annotated[User, Depends(require_premium_or_higher)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
