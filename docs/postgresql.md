# Database Migration: SQLite to PostgreSQL

## Overview
Migrate the existing database layer from SQLite to PostgreSQL while maintaining all existing functionality and improving scalability for production use.

## Goals
- Replace SQLite with PostgreSQL as the primary database
- Maintain backward compatibility with existing application code
- Preserve all existing data during migration
- Improve database performance and scalability
- Add proper connection pooling and error handling
- Ensure type safety and proper PostgreSQL data types

## Context
- Current database: SQLite (file-based)
- Target database: PostgreSQL (server-based)
- Application likely uses an ORM or direct SQL queries
- Need to handle differences in SQL dialects and features

## Requirements

### 1. Database Setup
- [ ] Install and configure PostgreSQL locally/on server
- [ ] Create new PostgreSQL database and user with appropriate permissions
- [ ] Set up connection string configuration (environment variables)
- [ ] Configure connection pooling (e.g., using pgBouncer or built-in pooling)

### 2. Schema Migration
- [ ] Analyze existing SQLite schema
- [ ] Convert SQLite data types to PostgreSQL equivalents:
  - INTEGER → INTEGER or BIGINT
  - TEXT → VARCHAR, TEXT, or CHAR
  - REAL → FLOAT, DOUBLE PRECISION, or NUMERIC
  - BLOB → BYTEA
  - DATETIME → TIMESTAMP or TIMESTAMPTZ
- [ ] Handle SQLite-specific features:
  - AUTOINCREMENT → SERIAL or IDENTITY
  - Default values and constraints
  - Indexes and triggers
- [ ] Create PostgreSQL schema migration scripts
- [ ] Add proper primary keys, foreign keys, and indexes

### 3. Code Changes
- [ ] Update database connection configuration
- [ ] Replace SQLite-specific SQL syntax with PostgreSQL equivalents:
  - Date/time functions (datetime() → NOW(), CURRENT_TIMESTAMP)
  - String concatenation (|| works in both, but check usage)
  - LIMIT/OFFSET syntax
  - AUTOINCREMENT handling
  - Boolean type handling (0/1 vs true/false)
- [ ] Update query placeholders if needed:
  - SQLite: `?` positional parameters
  - PostgreSQL: `$1, $2, $3` or `:param` named parameters (depends on driver)
- [ ] Add proper error handling for PostgreSQL-specific errors
- [ ] Update any raw SQL queries in the codebase
- [ ] If using an ORM, update configuration and dialect

### 4. Data Migration
- [ ] Export existing data from SQLite
- [ ] Transform data if needed for PostgreSQL compatibility
- [ ] Create data migration script
- [ ] Import data into PostgreSQL
- [ ] Verify data integrity and completeness
- [ ] Update sequences/auto-increment values if needed

### 5. Testing
- [ ] Create test database environment
- [ ] Run existing test suite against PostgreSQL
- [ ] Test all CRUD operations
- [ ] Test transactions and rollbacks
- [ ] Test concurrent access scenarios
- [ ] Performance testing and benchmarking
- [ ] Test connection pooling behavior
- [ ] Verify error handling

### 6. Configuration Management
- [ ] Add PostgreSQL connection details to environment variables:
  ```
  DATABASE_URL=postgresql://user:password@localhost:5432/dbname
  # Or separate variables:
  DB_HOST=localhost
  DB_PORT=5432
  DB_NAME=mydb
  DB_USER=myuser
  DB_PASSWORD=mypassword
  ```
- [ ] Support for different environments (dev, staging, prod)
- [ ] Document configuration requirements
- [ ] Add connection retry logic and timeouts

### 7. Deployment
- [ ] Create deployment checklist
- [ ] Plan for zero-downtime migration if needed
- [ ] Backup existing SQLite database
- [ ] Run migration scripts in production
- [ ] Monitor for errors post-migration
- [ ] Create rollback plan

## Key Differences to Handle

### SQL Syntax
| Feature | SQLite | PostgreSQL |
|---------|--------|------------|
| Auto-increment | AUTOINCREMENT | SERIAL or IDENTITY |
| Boolean | 0/1 | true/false |
| String concat | `||` | `||` or CONCAT() |
| Date/Time | datetime('now') | NOW() or CURRENT_TIMESTAMP |
| Limit | LIMIT n | LIMIT n |
| Case sensitivity | Configurable | Column names case-insensitive, values case-sensitive |

### Data Types
- SQLite is dynamically typed; PostgreSQL is strictly typed
- Need explicit type casting in PostgreSQL
- BLOB → BYTEA requires different handling
- JSON support is native in PostgreSQL (better performance)

### Features to Leverage
- Use PostgreSQL's native JSON/JSONB types if applicable
- Implement full-text search using PostgreSQL's tsvector
- Add proper indexes for better query performance
- Use PostgreSQL's advanced data types (arrays, hstore, etc.) where beneficial
- Consider using PostgreSQL-specific features (window functions, CTEs, etc.)

## Dependencies
List specific packages/libraries needed:
- [ ] PostgreSQL driver (e.g., `psycopg2`, `asyncpg`, `pg8000`)
- [ ] Connection pooling library if needed
- [ ] Migration tool (e.g., `alembic`, `flyway`, `migrate`) if not already in place
- [ ] PostgreSQL client for manual operations

## Success Criteria
- All existing functionality works with PostgreSQL
- All tests pass with the new database
- Data migration is complete and verified
- Performance is equal to or better than SQLite (for production workloads)
- Documentation is updated
- Team is trained on PostgreSQL operations

## Rollback Plan
- Keep SQLite database backup
- Document steps to revert code changes
- Have tested rollback procedure
- Monitor application closely after migration

## Notes
- Consider using a database abstraction layer to ease future migrations
- Document all PostgreSQL-specific optimizations made
- Plan for regular backups and point-in-time recovery
- Set up monitoring for database performance and errors
- Consider using PostgreSQL-specific features for long-term benefits

## Additional Considerations
- **Security**: Ensure PostgreSQL has proper authentication and SSL/TLS
- **Backups**: Set up automated backup strategy
- **Monitoring**: Add database performance monitoring
- **Documentation**: Update all developer documentation
- **Training**: Ensure team knows PostgreSQL administration basics