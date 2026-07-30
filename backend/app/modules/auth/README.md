# Authentication Module

JWT-based authentication module with user management, refresh tokens, and password reset functionality.

## Features

- ✅ **User Registration** - Create new user accounts with email/password
- ✅ **Login/Logout** - JWT access tokens and refresh tokens
- ✅ **Token Refresh** - Automatic token renewal without re-login
- ✅ **Password Reset** - Secure password reset flow with JWT tokens
- ✅ **Password Change** - Change password with current password verification
- ✅ **Database Support** - PostgreSQL and SQLite with async SQLAlchemy
- ✅ **In-Memory Mode** - Quick development without database setup

## Architecture

This module follows the **Repository Pattern** for flexible storage:

```
┌─────────────┐
│   Router    │  ← API endpoints
└──────┬──────┘
       │
┌──────▼──────┐
│   Service   │  ← Business logic
└──────┬──────┘
       │
┌──────▼──────────────────┐
│  Repository Interface   │  ← Abstract interface
└─────────┬───────────────┘
          │
   ┌──────┴──────┐
   │             │
┌──▼───────┐ ┌──▼──────────┐
│ Memory   │ │  Database   │
│  Store   │ │ Repository  │
└──────────┘ └─────────────┘
```

## Installation

### 1. Database Setup

#### Option A: SQLite (Development)
```bash
# No setup needed! Just set DATABASE_URL in .env:
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
```

#### Option B: PostgreSQL (Production)
```bash
# Install PostgreSQL and create database
createdb myapp_db

# Set DATABASE_URL in .env:
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/myapp_db
```

### 2. Environment Variables

Create a `.env` file in your project root:

```bash
# Security
SECRET_KEY=your-super-secret-key-min-32-chars-change-me
JWT_ALGORITHM=HS256

# Token Expiration
ACCESS_TOKEN_EXPIRES_MINUTES=30
REFRESH_TOKEN_EXPIRES_DAYS=7
PASSWORD_RESET_TOKEN_EXPIRES_HOURS=1

# Database (choose one)
DATABASE_URL=sqlite+aiosqlite:///./data/app.db
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/dbname

# Environment
ENVIRONMENT=development
```

### 3. Run Migrations

```bash
# Initialize Alembic (first time only)
alembic init alembic

# Create migration for users table
alembic revision --autogenerate -m "Create users table"

# Apply migrations
alembic upgrade head
```

Or for quick development, uncomment auto-init in `app_factory.py`:

```python
# In app/core/app_factory.py lifespan function:
from app.core.database import init_db
await init_db()  # Auto-create tables on startup
```

## Usage

### Switching Between Memory and Database Storage

The module uses **memory storage by default** for quick development. To switch to database:

#### Step 1: Update `service.py`

```python
# fastapi_registry/example_project/app/modules/auth/service.py

# FOR IN-MEMORY STORAGE (development/testing):
from .memory_stores import user_repository

# FOR DATABASE STORAGE (production):
# from .repositories import user_repository  # ← Uncomment this
```

#### Step 2: Update `dependencies.py`

For database mode with dependency injection:

```python
# fastapi_registry/example_project/app/modules/auth/dependencies.py

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from .repositories import UserRepository, get_user_repository

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    repo: UserRepository = Depends(get_user_repository)  # ← Inject repository
) -> User:
    # ... validation logic
    user = await repo.get_user_by_id(user_id)
    return user
```

### API Endpoints

Once installed, the module provides these endpoints:

```
POST   /auth/register          - Register new user
POST   /auth/login             - Login and get tokens
POST   /auth/refresh           - Refresh access token
POST   /auth/password-reset/request  - Request password reset
POST   /auth/password-reset/confirm  - Confirm password reset
POST   /auth/password/change   - Change password (authenticated)
GET    /auth/me                - Get current user info
```

### Example Usage

#### Register a New User

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!",
    "name": "John Doe"
  }'
```

#### Login

```bash
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "SecurePass123!"
  }'
```

Response:
```json
{
  "user": {
    "id": "01HKJM...",
    "email": "user@example.com",
    "name": "John Doe",
    "isActive": true,
    "createdAt": "2025-10-31T12:00:00Z"
  },
  "accessToken": "eyJhbGc...",
  "refreshToken": "eyJhbGc...",
  "tokenType": "bearer",
  "expiresIn": 1800
}
```

#### Protected Endpoint

```bash
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Using in Your Code

```python
from fastapi import APIRouter, Depends
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.models import User

router = APIRouter()

@router.get("/protected")
async def protected_route(
    current_user: User = Depends(get_current_user)
):
    return {
        "message": f"Hello {current_user.name}!",
        "user_id": current_user.id
    }
```

## Module Structure

```
app/modules/auth/
├── __init__.py              # Module exports
├── router.py                # API endpoints
├── service.py               # Business logic
├── dependencies.py          # FastAPI dependencies (auth checks)
├── models.py                # Pydantic User model
├── db_models.py             # SQLAlchemy User table
├── schemas.py               # Request/Response schemas
├── types.py                 # Repository interface
├── memory_stores.py         # In-memory storage implementation
├── repositories.py          # Database storage implementation
├── auth_utils.py            # JWT and password utilities
├── exceptions.py            # Custom exceptions
└── README.md                # This file
```

## Development vs Production

### Development Mode (In-Memory)

**Pros:**
- ✅ No database setup required
- ✅ Instant startup
- ✅ Perfect for prototyping

**Cons:**
- ❌ Data lost on restart
- ❌ Not suitable for production

**Use Cases:**
- Quick prototyping
- Testing
- Demos
- Learning

### Production Mode (Database)

**Pros:**
- ✅ Persistent data
- ✅ Scalable
- ✅ Production-ready

**Cons:**
- ❌ Requires database setup
- ❌ Slower initial development

**Use Cases:**
- Production deployments
- Staging environments
- Multi-user applications

## Security Best Practices

1. **Secret Key**: Use a strong, random SECRET_KEY (min 32 chars)
   ```bash
   # Generate a secure key:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **HTTPS**: Always use HTTPS in production

3. **Token Expiration**:
   - Short access tokens (15-30 minutes)
   - Longer refresh tokens (7-30 days)

4. **Password Requirements**: Enforce strong passwords in frontend

5. **Rate Limiting**: Apply rate limits to auth endpoints

6. **Database**: Never store plain-text passwords (handled by bcrypt)

## Troubleshooting

### Import Errors

```python
# If you see: ModuleNotFoundError: No module named 'app.core.database'
# Make sure database.py exists and contains the Base class:
from app.core.database import Base
```

### Database Connection Errors

```bash
# SQLite: Ensure directory exists
mkdir -p data/

# PostgreSQL: Test connection
psql -U username -d dbname -c "SELECT 1"
```

### Token Validation Errors

- Check SECRET_KEY matches in .env
- Verify token hasn't expired
- Ensure JWT_ALGORITHM is correct (HS256)

## Configuration

All settings use the nested config structure:

```python
from app.core.config import settings

# Security settings
settings.security.secret_key
settings.security.access_token_expires_minutes
settings.security.refresh_token_expires_days

# Database settings
settings.database.url
settings.database.pool_size
```

## Testing

```bash
# Run tests with in-memory storage (fast)
pytest tests/modules/auth/

# Run tests with database
DATABASE_URL=sqlite+aiosqlite:///./test.db pytest
```

## Migration from Other Systems

If you're migrating from another auth system:

1. Export users from old system
2. Hash passwords with bcrypt
3. Create users via `UserRepository.create_user()`
4. Notify users to reset passwords if needed

## Support

For issues and questions:
- Check the [main README](../../../README.md)
- See [CLAUDE.md](../../../CLAUDE.md) for architecture details
- Open an issue on GitHub

## License

Part of FastAPI Blocks Registry - see main project license.
