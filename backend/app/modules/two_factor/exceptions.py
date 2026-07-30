"""Two-Factor specific exceptions."""


class TwoFactorError(Exception):
    """Base error for 2FA module."""


class InvalidTwoFactorCodeError(TwoFactorError):
    """Provided 2FA verification code is invalid."""


class SetupTokenError(TwoFactorError):
    """Setup token missing or invalid."""
