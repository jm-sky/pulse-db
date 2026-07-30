# Database Migrations

This directory contains database migration scripts for the application.

## Migration Files

Each migration has two files:
- `XXX_migration_name.sql` - Raw SQL migration (for reference/manual application)
- `XXX_migration_name.py` - Python script for automatic migration

## Available Migrations

### 000_create_schema_migrations
- **Created**: 2025-01-XX
- **Description**: Creates `schema_migrations` table for tracking migration history

### 001_add_email_audit_log
- **Created**: 2025-11-13
- **Description**: Adds `email_audit_log` table for tracking sent emails
- **Model**: `app.common.models.EmailAuditLog`

### 001.5_create_users_table
- **Created**: 2025-01-27
- **Description**: Creates `users` table for authentication (required before gear tables)
- **Model**: `app.modules.auth.db_models.UserDB`

### 002_add_gear_tables
- **Created**: 2025-11-19
- **Description**: Adds `gear_containers` and `gear_items` tables for gear management
- **Models**: `app.modules.gear.db_models.GearContainerDB`, `app.modules.gear.db_models.GearItemDB`

### 003_add_missing_gear_fields
- **Created**: 2025-XX-XX
- **Description**: Adds missing fields to gear tables (hide_when_nested, weight, weight_unit, etc.)

## Usage

### Option 1: CLI Migration Commands (Recommended)

Run all pending migrations automatically:

```bash
cd backend
python cli.py db migrate
```

Check migration status:

```bash
python cli.py db migrate-status
```

The CLI automatically:
- Discovers all migrations in the `migrations/` directory
- Checks which migrations have already been applied
- Runs only pending migrations in order
- Tracks applied migrations in the `schema_migrations` table

### Option 2: Automatic Table Creation (Alternative for Development)

If you're using `db init`, the `schema_migrations` table is automatically created:

```bash
python cli.py db init
```

This will create all tables including `schema_migrations` and mark migration 000 as applied.

### Option 3: Run Individual Migration Script

Apply specific migration manually:

```bash
cd backend
source ../.venv/bin/activate
python migrations/001_add_email_audit_log.py upgrade
```

Rollback migration:

```bash
python migrations/001_add_email_audit_log.py downgrade
```

**Note:** When running migrations manually, they won't be tracked in `schema_migrations` table. Use `cli.py db migrate` for automatic tracking.

### Option 4: Manual SQL Migration

For production environments, you may want to review and apply SQL manually:

```bash
# PostgreSQL
psql -d your_database -f migrations/001_add_email_audit_log.sql

# SQLite
sqlite3 your_database.db < migrations/001_add_email_audit_log.sql
```

## Migration Tracking

The application uses a `schema_migrations` table to track which migrations have been applied. This table is automatically created:

- When you run `cli.py db init` (and migration 000 is marked as applied)
- When you run `cli.py db migrate` for the first time
- When you run `cli.py db migrate-status` for the first time

The table structure:
- `version` (PRIMARY KEY): Migration version number (e.g., '001', '002')
- `name`: Migration name (e.g., 'add_email_audit_log')
- `applied_at`: Timestamp when migration was applied

To see which migrations have been applied:

```bash
python cli.py db migrate-status
```

## Migration History

| Version | Date       | Description                        | Status |
|---------|------------|------------------------------------|--------|
| 000     | 2025-01-XX | Create schema_migrations table     | ✓      |
| 001     | 2025-11-13 | Add email_audit_log table          | ✓      |
| 001.5   | 2025-01-27 | Create users table                 | ✓      |
| 002     | 2025-11-19 | Add gear tables                    | ✓      |
| 003     | 2025-01-27 | Add missing gear fields            | ✓      |

## Future: Setting Up Alembic

For production, consider initializing Alembic for better migration management:

```bash
cd backend
source ../.venv/bin/activate

# Initialize Alembic
alembic init alembic

# Edit alembic.ini and alembic/env.py to configure database URL
# Then generate migrations:
alembic revision --autogenerate -m "Add email_audit_log table"

# Apply migrations:
alembic upgrade head
```

## Notes

- The email audit log system is enabled by default (`EMAIL_ENABLE_AUDIT=true`)
- Audit logging wraps any email adapter (SMTP, File, etc.)
- Email bodies are stored in the database for compliance (configurable)
- Failed emails can be retried using the retry mechanism
