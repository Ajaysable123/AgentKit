---
id: data-modeling
name: Data Modeling
category: db
level1: "For database schema design, normalization, ER diagrams, and table relationships"
platforms: [claude-code, cursor, codex, gemini-cli, antigravity, opencode, aider, windsurf]
priority: 2
keywords: [database, schema, normalization, er-diagram, relational, foreign-key, index, migration]
level1_tokens: 45
level2_tokens: 480
level3_tokens: 2100
author: agentkit-team
version: 1.0.0
---

<!-- LEVEL 1 START -->
## Data Modeling
Activate for: database schema design, normalization, ER diagrams, table relationships, migrations.
<!-- LEVEL 1 END -->

<!-- LEVEL 2 START -->
## Core Instructions

1. **Normalize First**: Start with 3NF. Denormalize only for proven performance issues.
2. **Consistent Naming**: Use snake_case for tables/columns, singular table names, consistent prefixes.
3. **Every Table Needs**: Primary key, created_at, updated_at. Soft deletes use deleted_at.
4. **Index Smart**: Index foreign keys, unique constraints, and frequently queried columns.
5. **Document Relations**: Use ER diagrams. Every FK should have a clear relationship.

### Quick Checklist
- [ ] Tables in 3NF (or justified denormalization)
- [ ] Consistent naming conventions
- [ ] Primary keys and timestamps present
- [ ] Foreign keys indexed
- [ ] Relationships documented
<!-- LEVEL 2 END -->

<!-- LEVEL 3 START -->
## Full Reference

### Normalization Forms

**1NF (First Normal Form)**
- No repeating groups
- Atomic values in each cell
- Unique column names

**2NF (Second Normal Form)**
- In 1NF
- No partial dependencies (all non-key columns depend on entire primary key)

**3NF (Third Normal Form)**
- In 2NF
- No transitive dependencies (non-key columns don't depend on other non-key columns)

### When to Denormalize

Denormalize only when:
1. You have proven performance issues with normalized schema
2. Query patterns are stable and well-understood
3. Read-heavy workloads with specific access patterns

```sql
-- Normalized (3NF)
users (id, name, email)
orders (id, user_id, total, created_at)
order_items (id, order_id, product_id, quantity, price)

-- Denormalized for read performance
order_summary_view (
    order_id, user_name, user_email, 
    total_items, total_amount, created_at
)
```

### Naming Conventions

```sql
-- ✅ Good: snake_case, singular, consistent
CREATE TABLE user_account (
    id              BIGSERIAL PRIMARY KEY,
    email           VARCHAR(255) NOT NULL UNIQUE,
    password_hash   VARCHAR(255) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_profile (
    id              BIGSERIAL PRIMARY KEY,
    user_account_id BIGINT NOT NULL REFERENCES user_account(id),
    display_name    VARCHAR(100),
    avatar_url      VARCHAR(500),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ❌ Bad: inconsistent naming
CREATE TABLE Users (
    Id INT PRIMARY KEY,
    EmailAddress varchar(255),
    pwdHash varchar(255),
    Created DateTime
);
```

### Soft Delete Pattern

```sql
-- Soft delete with deleted_at
CREATE TABLE posts (
    id          BIGSERIAL PRIMARY KEY,
    title       VARCHAR(255) NOT NULL,
    content     TEXT,
    author_id   BIGINT NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ  -- NULL = not deleted
);

-- Query excludes soft-deleted
SELECT * FROM posts WHERE deleted_at IS NULL;

-- Hard delete check before actual delete
UPDATE posts SET deleted_at = NOW() WHERE id = $1;
```

### Audit Trail Pattern

```sql
-- Audit columns on every table
CREATE TABLE orders (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     BIGINT NOT NULL,
    status          VARCHAR(50) NOT NULL,
    total           DECIMAL(10,2) NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    created_by      BIGINT REFERENCES users(id),
    updated_by      BIGINT REFERENCES users(id),
    version         INT DEFAULT 1
);

-- Separate audit log table for sensitive tables
CREATE TABLE audit_log (
    id          BIGSERIAL PRIMARY KEY,
    table_name  VARCHAR(100) NOT NULL,
    record_id   BIGINT NOT NULL,
    action      VARCHAR(20) NOT NULL,  -- INSERT, UPDATE, DELETE
    old_data    JSONB,
    new_data    JSONB,
    changed_by  BIGINT REFERENCES users(id),
    changed_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Foreign Keys and Indexes

```sql
-- Always index foreign keys
CREATE TABLE order_items (
    id          BIGSERIAL PRIMARY KEY,
    order_id    BIGINT NOT NULL REFERENCES orders(id),
    product_id  BIGINT NOT NULL REFERENCES products(id),
    quantity    INT NOT NULL DEFAULT 1,
    unit_price  DECIMAL(10,2) NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for foreign keys
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);

-- Composite index for common query patterns
CREATE INDEX idx_order_items_order_product ON order_items(order_id, product_id);
```

### Polymorphic Associations

```sql
-- Option 1: Separate junction tables (preferred)
CREATE TABLE comments (
    id          BIGSERIAL PRIMARY KEY,
    content     TEXT NOT NULL,
    author_id   BIGINT NOT NULL REFERENCES users(id),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE post_comments (
    post_id     BIGINT REFERENCES posts(id),
    comment_id  BIGINT REFERENCES comments(id),
    PRIMARY KEY (post_id, comment_id)
);

CREATE TABLE video_comments (
    video_id    BIGINT REFERENCES videos(id),
    comment_id  BIGINT REFERENCES comments(id),
    PRIMARY KEY (video_id, comment_id)
);

-- Option 2: Polymorphic (use sparingly)
CREATE TABLE comments (
    id              BIGSERIAL PRIMARY KEY,
    content         TEXT NOT NULL,
    commentable_type VARCHAR(50) NOT NULL,  -- 'post', 'video'
    commentable_id   BIGINT NOT NULL,
    author_id       BIGINT NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_comments_commentable 
    ON comments(commentable_type, commentable_id);
```

### JSON Columns

```sql
-- PostgreSQL JSONB for flexible schemas
CREATE TABLE products (
    id          BIGSERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    price       DECIMAL(10,2) NOT NULL,
    attributes  JSONB DEFAULT '{}',  -- Flexible attributes
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Query JSON
SELECT * FROM products 
WHERE attributes->>'color' = 'red';

-- Index JSON path
CREATE INDEX idx_products_color 
    ON products((attributes->>'color'));
```

### ER Diagram Notation

```
[User] ----< [Order] >---- [Product]
  |            |
  |            |
  v            v
[Profile]   [OrderItem]

Notation:
- ----<  one-to-many
- >----< many-to-many (junction table)
- ----   one-to-one
```
<!-- LEVEL 3 END -->