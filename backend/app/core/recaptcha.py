"""Google reCAPTCHA v3 verification service.

This module provides reCAPTCHA verification for protecting sensitive endpoints
from bots and automated attacks. It's an optional security feature that can be
enabled via configuration.

Usage:
    from app.core.recaptcha import verify_recaptcha

    # In your endpoint:
    await verify_recaptcha(token, action="login")
"""

import logging
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class RecaptchaError(Exception):
    """Exception raised for reCAPTCHA verification errors."""

    pass


async def verify_recaptcha(token: str, action: str = "submit") -> dict[str, Any]:
    """
    Verify reCAPTCHA token with Google's API.

    Args:
        token: The reCAPTCHA token from the client
        action: The expected action name (should match client-side action)

    Returns:
        Dict containing verification results with keys:
        - success: bool
        - score: float (0.0-1.0)
        - action: str
        - challenge_ts: str
        - hostname: str

    Raises:
        RecaptchaError: If verification fails or score is too low

    Example:
        try:
            result = await verify_recaptcha(token, action="register")
            logger.info(f"reCAPTCHA score: {result['score']}")
        except RecaptchaError as e:
            logger.warning(f"reCAPTCHA failed: {e}")
            raise HTTPException(status_code=400, detail="Bot detected") from e
    """
    # Log reCAPTCHA configuration
    logger.info(f"reCAPTCHA verification called - enabled: {settings.recaptcha.enabled}, action: {action}")
    logger.debug(f"reCAPTCHA config - secret_key present: {bool(settings.recaptcha.secret_key)}, " f"site_key present: {bool(settings.recaptcha.site_key)}, " f"min_score: {settings.recaptcha.min_score}, " f"verify_url: {settings.recaptcha.verify_url}")

    # Skip verification if reCAPTCHA is disabled (for development/testing)
    if not settings.recaptcha.enabled:
        logger.debug("reCAPTCHA verification skipped (disabled in settings)")
        return {"success": True, "score": 1.0, "action": action, "skipped": True}

    if not token:
        logger.error("reCAPTCHA token is missing")
        raise RecaptchaError("reCAPTCHA token is required")

    logger.debug(f"reCAPTCHA token received - length: {len(token)}, first 20 chars: {token[:20]}...")

    try:
        logger.info(f"Sending reCAPTCHA verification request to {settings.recaptcha.verify_url}")
        async with httpx.AsyncClient() as client:
            request_data = {
                "secret": settings.recaptcha.secret_key,
                "response": token,
            }
            logger.debug(
                f"Request data - secret present: {bool(request_data['secret'])}, "
                f"secret length: {len(request_data['secret']) if request_data['secret'] else 0}, "
                f"response present: {bool(request_data['response'])}, "
                f"response length: {len(request_data['response']) if request_data['response'] else 0}"
            )

            response = await client.post(
                settings.recaptcha.verify_url,
                data=request_data,
                timeout=10.0,
            )
            logger.info(f"reCAPTCHA API response status: {response.status_code}")
            response.raise_for_status()
            result = response.json()
            logger.debug(f"reCAPTCHA API raw response: {result}")

        # Log the result for debugging
        logger.info(f"reCAPTCHA verification: success={result.get('success')}, " f"score={result.get('score')}, action={result.get('action')}, " f"hostname={result.get('hostname')}")

        # Check if verification was successful
        if not result.get("success"):
            error_codes = result.get("error-codes", [])
            error_message = ", ".join(error_codes) if error_codes else "unknown error"
            logger.error(f"reCAPTCHA verification failed: {error_message}. " f"Token length: {len(token)}, Action: {action}, " f"Full error codes: {error_codes}")
            raise RecaptchaError(f"reCAPTCHA verification failed: {error_message}")

        # Verify action matches (prevents token reuse across different forms)
        if result.get("action") != action:
            logger.warning(f"reCAPTCHA action mismatch: expected '{action}', " f"got '{result.get('action')}'")
            raise RecaptchaError("reCAPTCHA action mismatch")

        # Check score threshold
        score = result.get("score", 0.0)
        if score < settings.recaptcha.min_score:
            logger.warning(f"reCAPTCHA score too low: {score} < {settings.recaptcha.min_score}")
            raise RecaptchaError(f"reCAPTCHA verification failed: score too low ({score})")

        return result  # type: ignore[no-any-return]

    except httpx.HTTPError as e:
        logger.error(f"reCAPTCHA HTTP error: {e}")
        raise RecaptchaError(f"reCAPTCHA service error: {e}") from e
    except RecaptchaError:
        # Re-raise RecaptchaError as is
        raise
    except Exception as e:
        logger.error(f"reCAPTCHA verification error: {e}")
        raise RecaptchaError(f"reCAPTCHA verification error: {e}") from e
