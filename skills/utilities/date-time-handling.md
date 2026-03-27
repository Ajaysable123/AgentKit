---
id: date-time-handling
name: Date & Time Handling
category: utilities
level1: "For datetime parsing, timezone conversion, date arithmetic, and scheduling logic"
platforms: [claude-code, cursor, codex, gemini-cli, antigravity, opencode, aider, windsurf]
priority: 2
keywords: [datetime, timezone, utc, iso8601, date, time, timestamp, scheduling]
level1_tokens: 45
level2_tokens: 480
level3_tokens: 2100
author: agentkit-team
version: 1.0.0
---

<!-- LEVEL 1 START -->
## Date & Time Handling
Activate for: datetime parsing, timezone issues, date arithmetic, scheduling, timestamps.
<!-- LEVEL 1 END -->

<!-- LEVEL 2 START -->
## Core Instructions

1. **UTC Everywhere**: Store all datetimes in UTC. Never store local time in databases.
2. **ISO 8601**: Use ISO 8601 format (`YYYY-MM-DDTHH:MM:SSZ`) for all datetime strings.
3. **Timezone at Display**: Convert to local timezone only at the presentation layer.
4. **Library Choice**: Use `dayjs` (JS) or `pendulum` (Python) over native Date/datetime.
5. **DST Awareness**: Account for daylight saving time transitions in recurring events.

### Quick Checklist
- [ ] All stored timestamps are UTC
- [ ] ISO 8601 format for serialization
- [ ] Timezone conversion happens at display time
- [ ] DST edge cases handled for recurring events
- [ ] No manual timezone offset calculations
<!-- LEVEL 2 END -->

<!-- LEVEL 3 START -->
## Full Reference

### Core Principles

**1. UTC Everywhere**
Never store local time. Local time is for display only.
```python
# Python - Always use UTC
from datetime import datetime, timezone
now_utc = datetime.now(timezone.utc)
```

```javascript
// JavaScript - Always use UTC
const nowUtc = new Date().toISOString();
```

**2. ISO 8601 Format**
The universal format for datetime strings:
- `2026-03-27T14:30:00Z` - UTC time (Z suffix)
- `2026-03-27T14:30:00+08:00` - Time with offset
- `2026-03-27` - Date only

**3. Timezone Conversion**
Convert only at display time:
```python
from zoneinfo import ZoneInfo
utc_time = datetime.now(timezone.utc)
local_time = utc_time.astimezone(ZoneInfo("Asia/Shanghai"))
```

```javascript
// JavaScript with dayjs
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';
import timezone from 'dayjs/plugin/timezone';

dayjs.extend(utc);
dayjs.extend(timezone);

const localTime = dayjs.utc('2026-03-27T14:30:00Z')
  .tz('Asia/Shanghai')
  .format('YYYY-MM-DD HH:mm:ss');
```

### Common Pitfalls

**Pitfall 1: Storing Local Time**
```python
# ❌ Wrong - stores local time
now = datetime.now()

# ✅ Correct - stores UTC
now = datetime.now(timezone.utc)
```

**Pitfall 2: Manual Offset Calculation**
```python
# ❌ Wrong - brittle, doesn't handle DST
offset_hours = 8
result = base_time + timedelta(hours=offset_hours)

# ✅ Correct - use proper timezone conversion
from zoneinfo import ZoneInfo
result = base_time.astimezone(ZoneInfo("Asia/Shanghai"))
```

**Pitfall 3: DST Edge Cases**
```python
# Schedule that fails during DST transition
from datetime import datetime
from zoneinfo import ZoneInfo

tz = ZoneInfo("America/New_York")
# March 2026: 2:00 AM doesn't exist (spring forward)
# November 2026: 1:00 AM exists twice (fall back)

# Solution: Use UTC for storage, convert for display
```

### Library Recommendations

| Language | Recommended Library | Why |
|----------|---------------------|-----|
| JavaScript | dayjs + plugins | Lightweight, timezone-aware |
| Python | pendulum or zoneinfo | Intuitive API, DST-safe |
| Java | java.time (Java 8+) | Built-in, immutable |
| Go | time package | Built-in, timezone support |
| SQL | TIMESTAMP WITH TIME ZONE | Store UTC, query with offset |

### SQL Timestamp Types

```sql
-- PostgreSQL: Use TIMESTAMPTZ for UTC storage
CREATE TABLE events (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    scheduled_for TIMESTAMPTZ NOT NULL
);

-- Query with timezone
SELECT created_at AT TIME ZONE 'Asia/Shanghai' FROM events;
```

### Date Arithmetic

```python
from datetime import datetime, timedelta, timezone

# Add days
future = datetime.now(timezone.utc) + timedelta(days=30)

# Difference between dates
diff = end_date - start_date
days_between = diff.days

# Business days (use library)
import pendulum
start = pendulum.now()
end = start.add(business_days=5)  # Skips weekends
```

### Testing Tips

Always test with:
1. DST transition dates
2. Leap years (Feb 29)
3. Year boundaries (Dec 31 → Jan 1)
4. Different timezones
<!-- LEVEL 3 END -->