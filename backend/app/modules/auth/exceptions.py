"""Custom exceptions for authentication module."""


class AuthException(Exception):
    """Base exception for authentication errors."""

    pass


class UserAlreadyExistsError(AuthException):
    """Raised when attempting to create a user that already exists."""

    pass


class InvalidCredentialsError(AuthException):
    """Raised when login credentials are invalid."""

    pass


class UserNotFoundError(AuthException):
    """Raised when user is not found."""

    pass


class InvalidTokenError(AuthException):
    """Raised when JWT token is invalid."""

    pass


class ExpiredTokenError(AuthException):
    """Raised when JWT token has expired."""

    pass


class InactiveUserError(AuthException):
    """Raised when user account is inactive."""

    pass


class EmailNotVerifiedError(AuthException):
    """Raised when user email is not verified."""

    pass
