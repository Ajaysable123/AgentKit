---
id: error-handling-patterns
name: Error Handling Patterns
category: quality
level1: "For exception handling, error boundaries, retry logic, and fault tolerance"
platforms: [claude-code, cursor, codex, gemini-cli, antigravity, opencode, aider, windsurf]
priority: 2
keywords: [error, exception, retry, circuit-breaker, fault-tolerance, error-boundary]
level1_tokens: 45
level2_tokens: 480
level3_tokens: 2100
author: agentkit-team
version: 1.0.0
---

<!-- LEVEL 1 START -->
## Error Handling Patterns
Activate for: exception handling, error boundaries, retry logic, circuit breakers, fault tolerance.
<!-- LEVEL 1 END -->

<!-- LEVEL 2 START -->
## Core Instructions

1. **Fail Fast, Fail Explicit**: Catch specific exceptions, not bare `except` or `catch`.
2. **User vs Internal**: Separate user-facing messages from internal error details.
3. **Structured Logging**: Log errors with context (request ID, user, operation).
4. **Graceful Degradation**: Provide fallback behavior when possible.
5. **Retry Smart**: Exponential backoff with jitter for transient failures.

### Quick Checklist
- [ ] Catching specific exceptions only
- [ ] User-facing messages are friendly
- [ ] Errors logged with context
- [ ] Retry logic has backoff
- [ ] Circuit breaker for external services
<!-- LEVEL 2 END -->

<!-- LEVEL 3 START -->
## Full Reference

### Custom Exception Hierarchies

```python
# Python - Custom exception hierarchy
class AppError(Exception):
    """Base exception for all application errors"""
    def __init__(self, message: str, internal_code: str = None):
        self.message = message
        self.internal_code = internal_code
        super().__init__(message)

class ValidationError(AppError):
    """User input validation failed"""
    pass

class NotFoundError(AppError):
    """Requested resource not found"""
    pass

class ExternalServiceError(AppError):
    """External API call failed"""
    pass
```

```typescript
// TypeScript - Custom error classes
class AppError extends Error {
  constructor(
    message: string,
    public internalCode?: string,
    public statusCode: number = 500
  ) {
    super(message);
    this.name = 'AppError';
  }
}

class ValidationError extends AppError {
  constructor(message: string) {
    super(message, 'VALIDATION_ERROR', 400);
  }
}
```

### React Error Boundaries

```tsx
// React - Error boundary for graceful degradation
class ErrorBoundary extends React.Component<
  { fallback: ReactNode; children: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    logError(error, { componentStack: info.componentStack });
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}

// Usage
<ErrorBoundary fallback={<ErrorPage />}>
  <App />
</ErrorBoundary>
```

### Result/Either Pattern

```typescript
// TypeScript - Result type for explicit error handling
type Result<T, E = Error> = 
  | { ok: true; value: T }
  | { ok: false; error: E };

function divide(a: number, b: number): Result<number, string> {
  if (b === 0) {
    return { ok: false, error: 'Division by zero' };
  }
  return { ok: true, value: a / b };
}

// Usage
const result = divide(10, 2);
if (result.ok) {
  console.log(result.value);
} else {
  console.error(result.error);
}
```

### Retry with Exponential Backoff

```python
import asyncio
import random
from functools import wraps

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise
                    # Exponential backoff with jitter
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    jitter = random.uniform(0, delay * 0.1)
                    await asyncio.sleep(delay + jitter)
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3)
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

### Circuit Breaker Pattern

```python
from enum import Enum
from datetime import datetime, timedelta
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject all calls
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None

    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_attempt_recovery():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError("Circuit breaker is open")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _should_attempt_recovery(self):
        return (
            self.last_failure_time and
            datetime.now() - self.last_failure_time > 
            timedelta(seconds=self.recovery_timeout)
        )

    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
```

### Structured Error Logging

```python
import logging
import json
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar('request_id')

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)

    def error(self, message: str, **context):
        log_data = {
            "level": "ERROR",
            "message": message,
            "request_id": request_id_var.get(None),
            **context
        }
        self.logger.error(json.dumps(log_data))

# Usage
logger = StructuredLogger(__name__)
try:
    process_payment(order)
except PaymentError as e:
    logger.error(
        "Payment processing failed",
        order_id=order.id,
        error_code=e.code,
        user_id=order.user_id
    )
```

### User-Facing vs Internal Errors

```python
class ErrorHandler:
    USER_MESSAGES = {
        "PAYMENT_DECLINED": "Your payment could not be processed. Please try a different card.",
        "SERVICE_UNAVAILABLE": "Our service is temporarily unavailable. Please try again in a few minutes.",
        "VALIDATION_ERROR": "Please check your input and try again.",
    }

    @staticmethod
    def handle(error: AppError) -> dict:
        return {
            "user_message": ErrorHandler.USER_MESSAGES.get(
                error.internal_code, 
                "An unexpected error occurred."
            ),
            "internal_code": error.internal_code,
            "trace_id": get_trace_id()
        }
```
<!-- LEVEL 3 END -->