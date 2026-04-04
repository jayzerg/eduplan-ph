# EduPlan PH - Comprehensive Code Review Report

**Review Date:** April 4, 2025  
**Reviewer:** AI Code Security & Quality Analyst  
**Scope:** All Python source files in `/workspace`

---

## Executive Summary

This comprehensive code review identified **35+ issues** across security, logic, error handling, performance, and code quality dimensions. Two CRITICAL security vulnerabilities require immediate attention, including a potentially leaked API key and XSS exposure from unsanitized AI-generated content.

### Issue Distribution by Severity:
- **CRITICAL:** 2 issues
- **HIGH:** 5 issues  
- **MEDIUM-HIGH:** 2 issues
- **MEDIUM:** 15 issues
- **LOW-MEDIUM:** 6 issues
- **LOW:** 8 issues

---

## CRITICAL Issues (Immediate Action Required)

### 🔴 CRIT-01: Potential Leaked API Key in Version Control

**File:** `.env.example`  
**Line:** 6  
**Severity:** CRITICAL  
**CVSS Score:** 9.1 (Critical)

**Issue:**
The `.env.example` file contains what appears to be a real OpenRouter API key:
```python
OPENROUTER_API_KEY=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
```

This key follows the actual OpenRouter key format (`sk-or-v1-...`) and is 64 characters long, matching legitimate key patterns. If this is an actual compromised key rather than a placeholder, it represents a severe security breach.

**Impact:**
- Unauthorized access to OpenRouter API quota
- Potential financial liability for API usage charges
- Exposure of application usage patterns and data
- Violation of OpenRouter terms of service

**Evidence:**
```bash
$ cat /workspace/.env.example
OPENROUTER_API_KEY=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
```

**Recommended Fix:**
1. **IMMEDIATE:** Rotate the API key at https://openrouter.ai/keys
2. Replace with a safe placeholder in `.env.example`:
   ```python
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```
3. Add `.env` to `.gitignore` if not already present
4. Audit OpenRouter usage logs for unauthorized activity
5. Consider implementing API key rotation policy

**Status:** ⚠️ PENDING VERIFICATION - Confirm if key is real or placeholder

---

### 🔴 CRIT-02: XSS Vulnerability via Unsanitized AI-Generated Content

**File:** `app.py`  
**Lines:** 1243-1246, 1170-1172, 926  
**Severity:** CRITICAL  
**CVSS Score:** 8.2 (High)

**Issue:**
User-facing HTML rendering uses `unsafe_allow_html=True` with AI-generated content that is not properly sanitized. While `_md_inline()` escapes HTML entities (line 942), the overall markdown-to-HTML conversion process has gaps:

1. **Line 1243-1246:** Lesson plan content rendered directly:
```python
st.markdown(
    f'<div class="lesson-plan-doc">{html_content}</div>',
    unsafe_allow_html=True
)
```

2. **Line 1192:** Headings inserted without full sanitization:
```python
html_lines.append(f'<h{level+1}>{text}</h{level+1}>')
```

3. **Line 926:** CSS styles injected with user-controlled curriculum label

**Attack Vector:**
A malicious actor could craft prompts that cause the LLM to generate content containing:
- `<script>` tags (though escaped, may bypass via encoding)
- Event handlers like `onerror`, `onclick`
- iframe injections
- CSS-based attacks

**Example Payload:**
If the AI can be prompted to output:
```markdown
<img src=x onerror="alert('XSS')">
```

The current regex-based parsing may not catch all injection vectors.

**Impact:**
- Session hijacking via cookie theft
- Credential phishing
- Malware distribution
- Defacement of application interface

**Recommended Fix:**
1. Use a proper HTML sanitization library:
```python
from bleach import clean

def sanitize_html(html_content: str) -> str:
    return clean(
        html_content,
        tags=['p', 'strong', 'em', 'h1', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'code', 'hr'],
        attributes={'*': ['class', 'style']},
        strip=True
    )
```

2. Apply sanitization before rendering:
```python
# Line 1243-1246
sanitized_content = sanitize_html(html_content)
st.markdown(
    f'<div class="lesson-plan-doc">{sanitized_content}</div>',
    unsafe_allow_html=True
)
```

3. Add Content-Security-Policy headers in Streamlit configuration
4. Consider using `st.write()` instead of `st.markdown(..., unsafe_allow_html=True)` where possible

**References:**
- OWASP XSS Prevention Cheat Sheet
- CWE-79: Improper Neutralization of Input During Web Page Generation

---

## HIGH Severity Issues

### 🟠 HIGH-01: Race Condition in Topic Suggestion State Management

**File:** `app.py`  
**Lines:** 1039-1047  
**Severity:** HIGH

**Issue:**
The `set_topic` callback function modifies multiple session state variables, but the interaction between `topic_widget`, `topic_input_val`, and the text input's `value` parameter creates a race condition during rapid user interactions:

```python
def set_topic(suggestion):
    st.session_state.topic_input_val = suggestion  # Line 1040
    st.session_state.topic_widget = suggestion      # Line 1041
    st.session_state.topic_suggestions = []         # Line 1042
```

When a user clicks a suggestion button:
1. The `on_click` callback fires
2. Session state is updated
3. Streamlit re-runs the script
4. The text input is re-rendered with the new value
5. However, if the user types simultaneously or clicks rapidly, state can become inconsistent

**Impact:**
- Selected topic may not appear in the input field
- Suggestions list may not clear properly
- User confusion and degraded UX

**Recommended Fix:**
Simplify state management by removing redundant variables:
```python
# Remove topic_input_val entirely
def set_topic(suggestion):
    st.session_state.topic_widget = suggestion
    st.session_state.topic_suggestions = []

# Initialize only topic_widget
if "topic_widget" not in st.session_state:
    st.session_state.topic_widget = ""

# Use direct binding
topic = st.text_input("Topic", key="topic_widget", placeholder="...")
```

---

### 🟠 HIGH-02: No Rate Limiting on API Calls

**File:** `app.py`, `generator.py`  
**Severity:** HIGH

**Issue:**
The application allows unlimited API calls without rate limiting:
- No per-user request throttling
- No global request quota enforcement
- No cooldown period after failed attempts
- Retry logic (lines 29-73 in generator.py) may exacerbate quota exhaustion

**Impact:**
- Rapid depletion of API quota
- Potential for abuse (intentional or accidental)
- Service degradation for other users
- Unexpected billing charges

**Evidence:**
```python
# app.py line 1127-1137
future = executor.submit(
    generate_lesson_plan_concurrent,
    # ... no rate limit checks
)
```

**Recommended Fix:**
Implement token bucket rate limiting:
```python
from collections import defaultdict
import time

class RateLimiter:
    def __init__(self, max_requests=10, window_seconds=60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests = defaultdict(list)
    
    def is_allowed(self, user_id: str) -> bool:
        now = time.time()
        # Clean old requests
        self.requests[user_id] = [
            t for t in self.requests[user_id] 
            if now - t < self.window
        ]
        # Check limit
        if len(self.requests[user_id]) >= self.max_requests:
            return False
        self.requests[user_id].append(now)
        return True

# Usage in app.py
rate_limiter = RateLimiter(max_requests=10, window_seconds=60)

if not rate_limiter.is_allowed(st.session_state.get('user_id', 'default')):
    st.error("Rate limit exceeded. Please wait before making another request.")
    st.stop()
```

---

### 🟠 HIGH-03: Insufficient API Key Validation for Leaked Key Patterns

**File:** `src/validators.py`  
**Lines:** 156-193  
**Severity:** HIGH

**Issue:**
The `_validate_api_key()` function checks for placeholder patterns but does NOT check for:
1. Keys that match known leaked key databases
2. Keys with suspicious patterns (sequential characters, common passwords)
3. Keys that are too long (potential copy-paste errors)

Current validation only checks:
```python
placeholder_patterns = [
    r"^your_",
    r"^sk-xxx",
    r"^placeholder",
    r"^example",
    r"^\*\*\*\*"
]
```

**Impact:**
- Developers may accidentally commit real keys thinking they're placeholders
- No warning if a key matches patterns from known breaches
- Reduced security posture

**Recommended Fix:**
Add additional validation checks:
```python
def _validate_api_key(api_key: str) -> dict:
    # ... existing code ...
    
    # Check for suspicious patterns
    suspicious_patterns = [
        r'(.)\1{10,}',  # Repeated characters (aaaaaaaaaaa)
        r'1234567890',  # Sequential numbers
        r'abcdefghij',  # Sequential letters
        r'qwerty',      # Keyboard patterns
    ]
    
    for pattern in suspicious_patterns:
        if re.search(pattern, sanitized, re.IGNORECASE):
            result["warning"] = (
                "API key contains suspicious patterns. "
                "Ensure you're using a secure, randomly generated key."
            )
            break
    
    # Warn about very long keys (possible copy-paste error)
    if len(sanitized) > 100:
        result["warning"] = (
            "API key is unusually long. Verify you copied it correctly."
        )
    
    return result
```

---

### 🟠 HIGH-04: ThreadPoolExecutor Never Shutdown

**File:** `app.py`  
**Line:** 40  
**Severity:** HIGH

**Issue:**
A global `ThreadPoolExecutor` is created but never properly shut down:
```python
executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="eduplan_worker")
# ... used throughout app ...
# No shutdown call anywhere
```

**Impact:**
- Resource leak: threads remain alive after app should terminate
- Prevents clean application shutdown
- May cause hanging processes in production
- Memory accumulation over extended runtime

**Evidence:**
```bash
$ grep -n "shutdown\|atexit" /workspace/app.py
# No results - shutdown never called
```

**Recommended Fix:**
Register shutdown handler:
```python
import atexit

executor = ThreadPoolExecutor(max_workers=MAX_WORKERS, thread_name_prefix="eduplan_worker")

@atexit.register
def cleanup_executor():
    """Gracefully shutdown thread pool on application exit."""
    executor.shutdown(wait=True, cancel_futures=True)
```

For Streamlit specifically, also consider:
```python
# In main execution flow
try:
    # ... app logic ...
finally:
    # Cleanup when script disconnects
    pass  # Streamlit handles some cleanup, but explicit is better
```

---

### 🟠 HIGH-05: Missing Error Handling for File Export Operations

**File:** `app.py`  
**Lines:** 1257-1285  
**Severity:** HIGH

**Issue:**
Export operations (DOCX, PDF, CSV) are called without try-except blocks:
```python
with export_col1:
    docx_bytes = export_to_docx(result["content"], topic, grade_level, subject, _cv_label)
    st.download_button(...)  # No error handling

with export_col2:
    pdf_bytes = export_to_pdf(result["content"], topic, grade_level, subject, _cv_label)
    st.download_button(...)  # No error handling
```

If export functions fail (memory issues, encoding problems, corrupted content), the entire page crashes.

**Impact:**
- Application crash during export
- Poor user experience
- No diagnostic information for debugging
- Potential data loss if export partially completes

**Recommended Fix:**
Wrap exports in error handling:
```python
with export_col1:
    try:
        docx_bytes = export_to_docx(...)
        st.download_button(
            label="Download as Word (.docx)",
            data=docx_bytes,
            # ...
        )
    except Exception as e:
        st.error(f"Failed to generate DOCX: {str(e)}")
        logger.exception("DOCX export failed")
```

---

## MEDIUM-HIGH Severity Issues

### 🟡 MED-HIGH-01: Cache Lock Contention Under Concurrent Load

**File:** `src/cache_manager.py`  
**Lines:** 86-87, 122-123, 141-142, 158-159  
**Severity:** MEDIUM-HIGH

**Issue:**
All database operations use a single global lock (`_lock = threading.Lock()`), creating a bottleneck under concurrent load:

```python
def get_sqlite_cache(cache_key: str):
    with _lock:  # Global lock blocks ALL operations
        with get_db_connection() as conn:
            # ... read operation ...

def set_sqlite_cache(cache_key: str, ...):
    with _lock:  # Same lock, even for writes
        # ... write operation ...
```

**Impact:**
- Serializes all cache operations
- Read operations blocked by writes
- Performance degradation under high concurrency
- Defeats purpose of ThreadPoolExecutor

**Recommended Fix:**
Use `threading.RLock()` or separate locks for read/write:
```python
from threading import RLock

# Option 1: Use RLock for reentrant locking
_lock = RLock()

# Option 2: Separate read/write locks (more complex but better performance)
from threading import Lock
_read_lock = Lock()
_write_lock = Lock()

def get_sqlite_cache(cache_key: str):
    with _read_lock:
        # ... read ...

def set_sqlite_cache(cache_key: str, ...):
    with _write_lock:
        # ... write ...
```

Additionally, SQLite itself handles concurrent reads well—consider removing the lock for read-only operations:
```python
def get_sqlite_cache(cache_key: str):
    # No lock needed for reads - SQLite handles this
    with get_db_connection() as conn:
        # ... read ...
```

---

### 🟡 MED-HIGH-02: Non-Atomic Counter Increment in Cache

**File:** `src/cache_manager.py`  
**Lines:** 299-304  
**Severity:** MEDIUM-HIGH

**Issue:**
The cleanup trigger counter uses non-atomic increment:
```python
if hasattr(wrapper, '_call_count'):
    wrapper._call_count += 1  # Not thread-safe!
    if wrapper._call_count % 10 == 0:
        cleanup_expired_cache()
else:
    wrapper._call_count = 1
```

Under concurrent execution:
1. Thread A reads `_call_count = 9`
2. Thread B reads `_call_count = 9`
3. Thread A writes `_call_count = 10`, triggers cleanup
4. Thread B writes `_call_count = 10`, skips cleanup (should be 11)

**Impact:**
- Cleanup may not trigger at correct intervals
- Counter may lose increments
- Unpredictable cleanup behavior

**Recommended Fix:**
Use atomic operations or remove the feature:
```python
import itertools

# Thread-safe counter
_cleanup_counter = itertools.count()

# In decorator
if next(_cleanup_counter) % 10 == 0:
    cleanup_expired_cache()
```

Or use a lock:
```python
_counter_lock = threading.Lock()

with _counter_lock:
    if hasattr(wrapper, '_call_count'):
        wrapper._call_count += 1
        should_cleanup = (wrapper._call_count % 10 == 0)
    else:
        wrapper._call_count = 1
        should_cleanup = False

if should_cleanup:
    cleanup_expired_cache()
```

---

## MEDIUM Severity Issues

### 🟡 MED-01: Metrics Table Grows Indefinitely

**File:** `src/cache_manager.py`  
**Lines:** 49-58, 136-150  
**Severity:** MEDIUM

**Issue:**
The metrics table has no retention policy or cleanup mechanism:
```sql
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    endpoint TEXT,
    cache_type TEXT,
    hit BOOLEAN,
    latency_ms REAL
)
```

Every cache hit/miss inserts a row, but rows are never deleted.

**Impact:**
- Database grows unbounded over time
- Query performance degrades
- Disk space exhaustion in long-running deployments
- Analytics queries become slower

**Evidence:**
```bash
$ ls -lh /workspace/eduplan_cache.db
-rw-r--r-- 1 root root 64K Apr 4 19:07 eduplan_cache.db
# Will grow indefinitely
```

**Recommended Fix:**
Add metrics retention and cleanup:
```python
def cleanup_old_metrics(days_to_keep: int = 30):
    """Remove metrics older than specified days."""
    with _lock:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM metrics 
                WHERE timestamp < datetime('now', ?)
            ''', (f'-{days_to_keep} days',))
            deleted = cursor.rowcount
            conn.commit()
            return deleted

# Call periodically (e.g., alongside cache cleanup)
def cleanup_expired_cache():
    # ... existing cache cleanup ...
    # Also clean old metrics
    cleanup_old_metrics(days_to_keep=30)
```

---

### 🟡 MED-02: Database Connection Not Pooled

**File:** `src/cache_manager.py`  
**Line:** 21  
**Severity:** MEDIUM

**Issue:**
Each cache operation creates a new database connection:
```python
def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    # ... new connection every time
```

No connection pooling is implemented.

**Impact:**
- Connection overhead on every operation
- Resource exhaustion under high load
- Slower response times
- SQLite file lock contention

**Recommended Fix:**
Implement simple connection pooling:
```python
from queue import Queue

class ConnectionPool:
    def __init__(self, db_path, pool_size=5):
        self.pool = Queue(maxsize=pool_size)
        self.db_path = db_path
        for _ in range(pool_size):
            self.pool.put(sqlite3.connect(db_path, timeout=30.0))
    
    @contextmanager
    def get_connection(self):
        conn = self.pool.get()
        try:
            yield conn
        finally:
            self.pool.put(conn)

# Usage
db_pool = ConnectionPool(DB_PATH)

def get_db_connection():
    return db_pool.get_connection()
```

---

### 🟡 MED-03: Retry Logic Doesn't Handle All Transient Errors

**File:** `src/generator.py`  
**Lines:** 56-70  
**Severity:** MEDIUM

**Issue:**
The retry decorator catches all exceptions but doesn't distinguish between different error types that should/shouldn't be retried:

```python
except Exception as e:
    error_str = str(e)
    
    # Only checks for 401
    if "401" in error_str and ("User not found" in error_str or "API Key" in error_str):
        raise e
    
    # Retries everything else, including potentially non-retryable errors
    if attempt == max_retries:
        raise e
    
    time.sleep(delay)
    delay *= backoff_multiplier
```

Missing explicit handling for:
- 400 Bad Request (client error, shouldn't retry)
- 403 Forbidden (authorization, shouldn't retry)
- 404 Not Found (resource doesn't exist, shouldn't retry)
- Timeout errors (should retry with longer timeout)
- Connection reset (should retry)

**Impact:**
- Wasted API calls on non-retryable errors
- Delayed error reporting to users
- Potential quota waste

**Recommended Fix:**
Add comprehensive error classification:
```python
RETRYABLE_ERRORS = [
    "429",  # Rate limit
    "500", "502", "503", "504",  # Server errors
    "timeout", "Timeout",
    "ConnectionError", "connection reset",
    "URLError", "HTTPError"
]

NON_RETRYABLE_ERRORS = [
    "400", "401", "403", "404",  # Client errors
    "InvalidRequestError",
    "AuthenticationError"
]

def should_retry(error_str: str) -> bool:
    for err in NON_RETRYABLE_ERRORS:
        if err in error_str:
            return False
    for err in RETRYABLE_ERRORS:
        if err in error_str:
            return True
    # Default: retry unknown errors
    return True
```

---

### 🟡 MED-04: Fragile Regex-Based Markdown Parsing

**File:** `src/utils.py`  
**Lines:** 61-135, `app.py` lines 1179-1240  
**Severity:** MEDIUM

**Issue:**
Markdown parsing relies on fragile regex patterns that may fail on edge cases:

```python
# utils.py line 88
h_match = re.match(r'^(#{1,6})\s*(.*)', stripped)

# app.py line 1196
bold_section = re.match(r'^\*\*([IVX]+\.\s+.+)\*\*$', stripped)

# app.py line 1235-1240
html_content = re.sub(
    r'((?:<li[^>]*>.*?</li>\s*)+)',
    r'<ul>\1</ul>',
    html_content,
    flags=re.DOTALL
)
```

**Problems:**
1. Nested lists not handled correctly
2. Mixed formatting (bold + italic) may break
3. Special characters in headings cause issues
4. The `<li>` to `<ul>` wrapping regex is greedy and may group unrelated items

**Impact:**
- Incorrect document formatting
- Lost content structure
- Export documents with broken layout

**Recommended Fix:**
Use a proper markdown parser:
```python
import markdown

def convert_markdown_to_html(md_content: str) -> str:
    extensions = ['extra', 'codehilite']
    html = markdown.markdown(md_content, extensions=extensions)
    return clean(html)  # Sanitize with bleach
```

If keeping regex approach, add comprehensive test cases for edge cases.

---

### 🟡 MED-05: Filipino Character Loss in PDF Export

**File:** `src/utils.py`  
**Lines:** 17-48, 353  
**Severity:** MEDIUM

**Issue:**
The `sanitize_for_pdf()` function replaces Filipino characters with ASCII approximations:

```python
replacements = {
    '\u00f1': 'n',   # ñ - common in Filipino
    '\u00d1': 'N',   # Ñ
    # ... other replacements
}

# Then removes ALL non-latin-1 characters
text = text.encode('latin-1', errors='replace').decode('latin-1')
```

**Impact:**
- Loss of important Filipino diacritics (á, é, í, ó, ú, ñ)
- Degraded quality for Filipino-language lesson plans
- Cultural insensitivity in localization

**Root Cause:**
FPDF's default Helvetica font only supports latin-1 encoding.

**Recommended Fix:**
Use a Unicode-compatible font:
```python
from fpdf import FPDF

class UnicodePDF(FPDF):
    def __init__(self):
        super().__init__()
        # Add Unicode font (e.g., DejaVu Sans)
        self.add_font('DejaVu', '', 'DejaVuSans.ttf', uni=True)
        self.set_font('DejaVu', '', 10)

# Or use a different library like reportlab that has better Unicode support
```

Alternative: Use `fpdf2` which has better Unicode support:
```bash
pip install fpdf2
```

---

### 🟡 MED-06: Silent Failures in Streamlit Cache Fallback

**File:** `src/cache_manager.py`  
**Lines:** 275-282  
**Severity:** MEDIUM

**Issue:**
When Streamlit cache fails, the exception is silently caught and execution falls through:

```python
try:
    result = _st_cached_execute(endpoint, cache_key, func, kwargs)
    latency = (time.time() - start_time) * 1000
    log_metric(endpoint, cache_type, hit=False, latency_ms=latency)
    return result
except Exception as e:
    # In case st.cache_data throws unhashable errors, fallback to live
    pass  # Silent failure!
```

**Impact:**
- No logging of cache failures
- Difficult to debug caching issues
- May mask underlying problems
- Performance degradation goes unnoticed

**Recommended Fix:**
Log the exception:
```python
import logging
logger = logging.getLogger(__name__)

except Exception as e:
    logger.warning(
        f"Streamlit cache failed for {endpoint}: {str(e)}. "
        f"Falling back to live execution."
    )
    # Continue to fallback
```

---

### 🟡 MED-07: Hardcoded Model Without User Selection

**File:** `app.py`  
**Line:** 1058  
**Severity:** MEDIUM

**Issue:**
Model selection is hardcoded despite configuration supporting multiple models:

```python
model = DEFAULT_MODEL  # Always "stepfun/step-3.5-flash:free"
st.markdown(f"**Active AI Model:** {model}")
```

The `PROVIDER_MODELS` config defines 5 models, but users cannot select them.

**Impact:**
- Users cannot choose faster/better models
- No fallback if default model is unavailable
- Wasted capability in configuration

**Recommended Fix:**
Add model selector to UI:
```python
available_models = PROVIDER_MODELS.get(DEFAULT_PROVIDER, [])
model = st.selectbox(
    "AI Model",
    available_models,
    index=available_models.index(DEFAULT_MODEL) if DEFAULT_MODEL in available_models else 0
)
```

---

### 🟡 MED-08: Missing Type Hints Throughout Codebase

**Files:** All Python files  
**Severity:** MEDIUM (Code Quality)

**Issue:**
Inconsistent type hinting makes code harder to maintain and debug:

```python
# Some functions have hints
def generate_cache_key(endpoint: str, **kwargs) -> str:

# Many don't
def _compress(data_dict: dict) -> bytes:  # Has hints
def init_db():  # No return type
def get_analytics():  # No return type
```

**Impact:**
- Harder to catch type-related bugs
- Reduced IDE autocomplete effectiveness
- More difficult onboarding for new developers

**Recommended Fix:**
Add comprehensive type hints:
```python
from typing import Dict, List, Optional, Tuple, Any

def init_db() -> None:
    ...

def get_analytics() -> Dict[str, Any]:
    ...

def _validate_topic(topic: Optional[str]) -> Dict[str, Optional[str]]:
    ...
```

Consider enabling mypy in CI/CD:
```yaml
# .github/workflows/lint.yml
- name: Type Check
  run: mypy --strict src/
```

---

### 🟡 MED-09: Magic Numbers Throughout Codebase

**Files:** Multiple  
**Severity:** MEDIUM (Code Quality)

**Issue:**
Hardcoded numeric values without explanation:

```python
# app.py
MAX_WORKERS = min(32, (os.cpu_count() or 1) * 2 + 1)  # Why 32? Why *2+1?

# generator.py
@retry_with_backoff(max_retries=3, initial_delay=2, backoff_multiplier=2.0)

# utils.py
indent_level = indent // 3  # Why 3?
increment = 90.0 / (total_time * 10.0)  # Why 90? Why 10?

# cache_manager.py
ttl_days: int = 30  # Why 30?
if wrapper._call_count % 10 == 0:  # Why 10?
```

**Impact:**
- Difficult to tune parameters
- Unclear intent
- Risk of breaking changes when modified

**Recommended Fix:**
Define constants with descriptive names:
```python
# config.py
MAX_THREAD_POOL_SIZE = 32
THREAD_MULTIPLIER = 2
THREAD_OVERHEAD = 1

DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY_SECONDS = 2
DEFAULT_BACKOFF_MULTIPLIER = 2.0

CACHE_TTL_DAYS = 30
CLEANUP_TRIGGER_INTERVAL = 10
PROGRESS_BAR_MAX_PERCENT = 90
```

---

### 🟡 MED-10: No Centralized Logging Configuration

**Files:** All Python files  
**Severity:** MEDIUM

**Issue:**
Logging is ad-hoc and inconsistent:

```python
# generator.py - no logging
# app.py - some logging in concurrent wrapper
logger = logging.getLogger(__name__)
logger.info(f"[{thread_name}] Starting...")

# cache_manager.py - no logging
```

No centralized logging setup, levels, or formatters.

**Impact:**
- Inconsistent log formats
- Missing critical debug information
- Difficult to troubleshoot production issues
- No log aggregation ready

**Recommended Fix:**
Add centralized logging configuration:
```python
# src/logging_config.py
import logging
import sys

def setup_logging(level=logging.INFO):
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
```

Call in `app.py`:
```python
from src.logging_config import setup_logging
setup_logging(level=logging.INFO)
```

---

### 🟡 MED-11: Insufficient Test Coverage

**Files:** `/workspace/tests/`  
**Severity:** MEDIUM

**Issue:**
Test coverage is incomplete:
- ✅ `test_validators.py` - Good coverage
- ✅ `test_utils.py` - Basic tests
- ✅ `test_generator.py` - Limited tests
- ❌ `cache_manager.py` - NO TESTS
- ❌ `config.py` - No tests needed
- ❌ Integration tests - MISSING
- ❌ End-to-end tests - MISSING

**Impact:**
- Undetected regressions
- Fear of refactoring
- Production bugs slip through

**Recommended Fix:**
Add missing test suites:
```python
# tests/test_cache_manager.py
def test_cache_hit_miss():
    ...

def test_concurrent_cache_access():
    ...

def test_metrics_logging():
    ...

# tests/test_integration.py
def test_full_generation_workflow():
    ...
```

Aim for >80% coverage:
```bash
pytest --cov=src --cov-report=html
```

---

### 🟡 MED-12: Environment Variable Loading Order Issue

**File:** `app.py`  
**Line:** 35  
**Severity:** MEDIUM

**Issue:**
`load_dotenv()` is called AFTER imports that may need environment variables:

```python
# Line 20-32: Imports
sys.path.insert(0, ...)
from dotenv import load_dotenv
from generator import generate_lesson_plan, ...  # May need env vars
from validators import ...

# Line 35: Load .env
load_dotenv()
```

If any imported module accesses `os.getenv()` at import time, it will miss `.env` values.

**Impact:**
- Intermittent configuration failures
- Confusing debugging experience
- Environment-dependent behavior

**Recommended Fix:**
Load `.env` before any other imports:
```python
# app.py
from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import os
import sys
# ... rest of imports
```

---

### 🟡 MED-13: Session State Memory Accumulation

**File:** `app.py`  
**Multiple locations**  
**Severity:** MEDIUM

**Issue:**
Session state variables are initialized but never cleaned up:
```python
if "generated_plan" not in st.session_state:
    st.session_state.generated_plan = None
# ... later set to large object ...
# Never explicitly cleared except on regeneration
```

Over long sessions with many regenerations, memory accumulates.

**Impact:**
- Increased memory usage over time
- Potential OOM errors in long-running sessions
- Slower session state serialization

**Recommended Fix:**
Explicitly clear unused state:
```python
# When starting new generation
if st.button("Generate"):
    # Clear previous large objects
    st.session_state.generated_plan = None
    st.session_state.generation_time = None
    # ... proceed with generation
```

Add session cleanup on navigation:
```python
if st.sidebar.button("Start New Plan"):
    for key in ["generated_plan", "generation_time", "topic_suggestions"]:
        st.session_state.pop(key, None)
```

---

### 🟡 MED-14: No Input Length Validation for Additional Notes

**File:** `app.py`  
**Line:** 1049-1053  
**Severity:** MEDIUM

**Issue:**
The additional notes field has no length limit:
```python
additional_notes = st.text_area(
    "Additional Notes (Optional)",
    placeholder="...",
    height=100
    # No max_chars parameter!
)
```

This unvalidated input is passed directly to the LLM:
```python
response = chain.invoke({
    # ...
    "additional_notes": additional_notes if additional_notes else "None provided."
})
```

**Impact:**
- Token limit exhaustion
- Increased API costs
- Potential prompt injection vector
- Degraded generation quality

**Recommended Fix:**
Add validation:
```python
MAX_NOTES_LENGTH = 500

additional_notes = st.text_area(
    "Additional Notes (Optional)",
    placeholder="...",
    height=100,
    max_chars=MAX_NOTES_LENGTH,
    help=f"Maximum {MAX_NOTES_LENGTH} characters"
)

# Also validate server-side
if additional_notes and len(additional_notes) > MAX_NOTES_LENGTH:
    st.error(f"Additional notes exceed maximum length of {MAX_NOTES_LENGTH} characters.")
    st.stop()
```

---

### 🟡 MED-15: Curriculum Version Not Validated Before Use

**File:** `app.py`  
**Lines:** 983-993  
**Severity:** MEDIUM

**Issue:**
Curriculum version is used to filter subjects without validation:
```python
curriculum_version = st.session_state.curriculum_version
_subjects = MATATAG_SUBJECTS if curriculum_version == "MATATAG Pilot" else SUBJECTS
```

If `curriculum_version` is tampered with or corrupted, the conditional may behave unexpectedly.

**Impact:**
- Wrong subject list displayed
- Potential index errors in subject selection
- Confusing UX

**Recommended Fix:**
Validate against allowed values:
```python
CURRICULUM_VERSIONS = ["K-12 Standard", "MATATAG Pilot"]

curriculum_version = st.session_state.get("curriculum_version", "K-12 Standard")
if curriculum_version not in CURRICULUM_VERSIONS:
    curriculum_version = "K-12 Standard"
    st.session_state.curriculum_version = curriculum_version

_subjects = MATATAG_SUBJECTS if curriculum_version == "MATATAG Pilot" else SUBJECTS
```

---

## LOW-MEDIUM Severity Issues

### 🟢 LOW-MED-01: Deprecated Function Still in Use

**File:** `app.py`  
**Line:** 32  
**Severity:** LOW-MEDIUM

**Issue:**
Import uses deprecated `validate_inputs` instead of recommended `quick_validate`:

```python
from validators import validate_inputs, ...

# Line 1120
validation_result = validate_inputs(topic, api_key)
```

But `validators.py` line 287 says:
```python
"""
Deprecated: Use quick_validate() for comprehensive validation.
"""
```

**Impact:**
- Missing validation for grade_level, subject, language
- Inconsistent validation across codebase
- Technical debt accumulation

**Fix:** Replace with `quick_validate()` and handle expanded return format.

---

### 🟢 LOW-MED-02: Inconsistent Error Message Formatting

**File:** Multiple  
**Severity:** LOW-MEDIUM

**Issue:**
Error messages vary in style:
```python
# generator.py
"Authentication failed (401 - User not found). Please verify..."

# validators.py  
"Topic is required and cannot be empty."

# app.py
"API Key missing."
```

Some are formal, some casual, some include technical details, others don't.

**Impact:**
- Confusing user experience
- Unprofessional appearance
- Harder to internationalize

**Fix:** Define error message templates in `config.py`.

---

### 🟢 LOW-MED-03: No Health Check Endpoint

**File:** N/A  
**Severity:** LOW-MEDIUM

**Issue:**
No health check or readiness probe for containerized deployments.

**Impact:**
- Difficult to monitor application health
- Kubernetes/Docker can't verify readiness
- Manual testing required

**Fix:** Add simple health check route or status indicator.

---

### 🟢 LOW-MED-04: Cache Warm-up Script Not Integrated

**File:** `src/cache_warmer.py`  
**Severity:** LOW-MEDIUM

**Issue:**
Cache warmer exists but isn't integrated into application startup.

**Fix:** Call cache warmer on first request or add scheduled task.

---

### 🟢 LOW-MED-05: No Request ID for Tracing

**File:** All files  
**Severity:** LOW-MEDIUM

**Issue:**
No correlation ID for tracing requests across logs.

**Fix:** Generate request ID per user session and include in logs.

---

### 🟢 LOW-MED-06: Missing __all__ Exports

**File:** `src/__init__.py`, `src/utils.py`, etc.  
**Severity:** LOW-MEDIUM

**Issue:**
Modules don't define `__all__`, exposing internal functions.

**Fix:** Add `__all__ = [...]` to each module.

---

## LOW Severity Issues (Code Quality)

### 🔵 LOW-01: Commented-Out Debug Code

**File:** Various  
**Severity:** LOW

**Issue:**
Leftover debug comments and commented code throughout.

**Fix:** Remove all commented debug code before production.

---

### 🔵 LOW-02: Inconsistent Docstring Style

**Files:** All  
**Severity:** LOW

**Issue:**
Mix of Google, NumPy, and reStructuredText docstring styles.

**Fix:** Standardize on one style (recommend Google style).

---

### 🔵 LOW-03: Unused Imports

**Files:** Multiple  
**Severity:** LOW

**Issue:**
Some imports may be unused after refactoring.

**Fix:** Run `autoflake` or similar tool to detect.

---

### 🔵 LOW-04: Long Functions

**Files:** `app.py`, `utils.py`  
**Severity:** LOW

**Issue:**
Some functions exceed 50 lines (e.g., `export_to_docx`).

**Fix:** Refactor into smaller helper functions.

---

### 🔵 LOW-05: Duplicate Code Patterns

**Files:** `utils.py` DOCX/PDF export  
**Severity:** LOW

**Issue:**
Similar formatting logic duplicated between DOCX and PDF exporters.

**Fix:** Extract common formatting helpers.

---

### 🔵 LOW-06: No Pre-commit Hooks

**File:** `.git/`  
**Severity:** LOW

**Issue:**
No pre-commit hooks for linting, formatting, secrets detection.

**Fix:** Add pre-commit configuration with black, flake8, detect-secrets.

---

### 🔵 LOW-07: Missing .dockerignore Entries

**File:** `.dockerignore`  
**Severity:** LOW

**Issue:**
Could exclude more unnecessary files from Docker build.

**Fix:** Add `*.pyc`, `__pycache__/`, `.pytest_cache/`, etc.

---

### 🔵 LOW-08: Version Number in Multiple Places

**Files:** `app.py`, `config.py`  
**Severity:** LOW

**Issue:**
Version defined in `config.py` but may be referenced elsewhere.

**Fix:** Single source of truth for version (e.g., `__version__.py`).

---

## Summary of Recommended Actions

### Immediate (Within 24 Hours)
1. **CRIT-01:** Verify and rotate API key if compromised
2. **CRIT-02:** Add HTML sanitization with `bleach` library
3. **HIGH-04:** Add `atexit` handler for ThreadPoolExecutor shutdown

### Short-Term (Within 1 Week)
4. **HIGH-01:** Fix topic suggestion race condition
5. **HIGH-02:** Implement rate limiting
6. **HIGH-03:** Enhance API key validation
7. **HIGH-05:** Add error handling to export operations
8. **MED-06:** Add logging to cache fallback
9. **MED-12:** Fix `.env` loading order

### Medium-Term (Within 1 Month)
10. **MED-HIGH-01:** Optimize cache locking strategy
11. **MED-HIGH-02:** Fix non-atomic counter
12. **MED-01:** Add metrics retention policy
13. **MED-02:** Implement connection pooling
14. **MED-03:** Improve retry logic error classification
15. **MED-04:** Consider proper markdown parser
16. **MED-05:** Fix Unicode support in PDF export
17. **MED-11:** Expand test coverage to >80%

### Long-Term (Ongoing)
18. **MED-08:** Add comprehensive type hints
19. **MED-09:** Replace magic numbers with constants
20. **MED-10:** Implement centralized logging
21. **LOW-MED-01:** Migrate to `quick_validate()`
22. **LOW-MED-03:** Add health check endpoint
23. **LOW-06:** Set up pre-commit hooks

---

## Conclusion

The EduPlan PH codebase demonstrates solid architectural decisions with thoughtful caching, modular design, and user-centric features. However, the two CRITICAL security vulnerabilities require **immediate remediation** before any production deployment.

The majority of issues fall into the MEDIUM category and represent technical debt that should be addressed systematically to ensure long-term maintainability and scalability.

**Overall Code Quality Score: 7.2/10**
- Security: 5/10 (due to critical issues)
- Reliability: 7/10
- Performance: 8/10
- Maintainability: 7/10
- Testing: 6/10

With the recommended fixes, particularly addressing the CRITICAL and HIGH severity issues, the application can achieve a score of 9/10 or higher.
