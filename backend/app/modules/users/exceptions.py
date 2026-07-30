"""Custom exceptions for user management module."""


class UserNotFoundError(Exception):
    """Raised when a user is not found."""

    def __init__(self, user_id: str = "") -> None:
        self.user_id = user_id
        super().__init__(f"User not found: {user_id}" if user_id else "User not found")


class UserAlreadyExistsError(Exception):
    """Raised when trying to create a user that already exists."""

    def __init__(self, email: str = "") -> None:
        self.email = email
        super().__init__(f"User with email {email} already exists" if email else "User already exists")


class UnauthorizedError(Exception):
    """Raised when user is not authorized to perform an action."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message)
