# OANDA MCP Server — Agent Execution Brief

**Start:** NOW  
**Phase 1 Duration:** 2 weeks  
**End State:** Public GitHub repo with v4.0.0 release  
**Scope:** Foundation + Tier 1 improvements

---

## 🎯 Phase 1 Execution Plan (Weeks 1-2)

### Week 1: Code Cleanup & Preparation

#### Agent 1: Code-Cleaner Agent 🧹

**Mission:** Convert codebase to English-primary, ensure code quality

**Tasks:**
```
English Conversion (All files → English)
├─ [ ] server.py: Replace all Spanish comments/docstrings → English
├─ [ ] dashboard.html: Replace Spanish labels → English
│   ├─ "Saldo" → "Balance"
│   ├─ "Operaciones" → "Trades"
│   ├─ "Órdenes" → "Orders"
│   └─ All UI strings
├─ [ ] MCP_TOOLS_REFERENCE.md: Keep (reference doc, translation planned Phase 7)
├─ [ ] Error messages: Replace Spanish → English (case-insensitive)
├─ [ ] Logging messages: Spanish → English
└─ [ ] Comments in all Python files: Spanish → English

Code Quality Gates
├─ [ ] Black formatting: black src/ server.py
├─ [ ] Type checking: mypy src/ server.py --strict
├─ [ ] Linting: Check for obvious issues
├─ [ ] Grep verification: grep -r "ó\|á\|é" src/ (verify Spanish removed from comments)
└─ [ ] Final verification: No Spanish comments remain

Output Artifacts
├─ [ ] Clean server.py (English comments)
├─ [ ] Clean dashboard.html (English UI)
├─ [ ] List of all changes (for PR description)
└─ [ ] Ready for merge to main
```

**Execution (Parallel possible? No - must be sequential)**
```bash
# Time estimate: 4-6 hours

# Step 1: Create branch
git checkout -b feature/i18n-english-primary

# Step 2: Convert files (use sed/grep + manual review)
# - server.py: 150+ comments/docstrings
# - dashboard.html: 20+ UI strings
# - Other files: remaining Spanish

# Step 3: Verify
black src/ server.py
mypy src/ server.py --strict
grep -r "[áéíóúñ]" src/  # Should return 0 matches for comments

# Step 4: Commit
git commit -m "i18n: Convert all source code to English-primary

- Convert server.py comments/docstrings: Spanish → English
- Convert dashboard.html UI strings: Spanish → English
- Convert logging messages: Spanish → English
- Verify code quality: Black, mypy clean
- All error messages now English
- No breaking changes to API"

# Step 5: Push & await approval
git push origin feature/i18n-english-primary
```

**Success Criteria:**
- ✅ All Python docstrings in English
- ✅ All comments in English
- ✅ All error messages in English
- ✅ Dashboard UI in English
- ✅ Black + mypy passing
- ✅ Ready for review

**Blocker Resolution:**
- Issue: "Can't find all Spanish strings?"  
  Solution: `grep -r "ó\|á\|é\|ñ" src/ dashboard.html`

---

#### Agent 2: GitHub Setup Agent 🔧

**Mission:** Prepare GitHub repository with CI/CD infrastructure

**Tasks (Parallel to Code-Cleaner, starts Week 1 Day 2):**
```
Repository Creation
├─ [ ] Create repository on GitHub (yourusername/oanda-mcp)
├─ [ ] Set to PUBLIC
├─ [ ] Initialize with README (will be replaced)
├─ [ ] Clone locally: git clone https://...
└─ [ ] Verify local repo configured

GitHub Configuration
├─ [ ] Add repository description
│   └─ "Production-grade MCP server for OANDA v20 trading automation with Claude AI"
├─ [ ] Add topics: mcp, oanda, trading, ai, claude, automation, fintech
├─ [ ] Configure settings:
│   ├─ Require status checks before merge (main branch)
│   ├─ Auto-delete head branches after merge
│   ├─ Require code reviews? (optional for now)
│   └─ Branch protection: main branch
├─ [ ] Setup GitHub Actions secrets (empty for now, prepare for CI):
│   └─ Add placeholder: DOCKER_TOKEN (for future Docker Hub push)
└─ [ ] Enable Discussions (for community)

Documentation Files
├─ [ ] Add LICENSE file: GNU 3.0
├─ [ ] Add CHANGELOG.md (v4.0.0 initial entry)
├─ [ ] Add CODE_OF_CONDUCT.md
├─ [ ] Add CONTRIBUTING.md
├─ [ ] Add .gitignore (use provided version)
└─ [ ] Add .env.example (use provided version)

GitHub Actions CI/CD
├─ [ ] Create .github/workflows/ci.yml
│   ├─ Trigger: push + pull_request
│   ├─ Job 1: Black (code formatting)
│   ├─ Job 2: mypy (type checking)
│   ├─ Job 3: pytest (unit tests)
│   └─ Job 4: Coverage report
├─ [ ] Ensure workflow passes locally first
└─ [ ] Test: Push dummy commit, verify CI runs

Issue Templates
├─ [ ] Create .github/ISSUE_TEMPLATE/bug_report.md
├─ [ ] Create .github/ISSUE_TEMPLATE/feature_request.md
├─ [ ] Create .github/ISSUE_TEMPLATE/question.md
└─ [ ] Create .github/ISSUE_TEMPLATE/config.yml

Repository Metadata
├─ [ ] Add GitHub Pages links (if using)
├─ [ ] Set default branch to main
├─ [ ] Add collaborators (if applicable)
└─ [ ] Verify all settings saved

Output Artifacts
├─ [ ] GitHub repo fully configured
├─ [ ] CI/CD pipelines ready
├─ [ ] Documentation structure in place
└─ [ ] Ready for code push
```

**Execution:**
```bash
# Time estimate: 3-4 hours (mostly GitHub UI clicks + git operations)

# Step 1: Create repo on GitHub web UI
# - Navigate to GitHub → New Repository
# - Name: oanda-mcp
# - Public
# - Initialize with README (will replace)

# Step 2: Clone locally
git clone https://github.com/yourusername/oanda-mcp.git
cd oanda-mcp

# Step 3: Add files from provided templates
cp /local/path/LICENSE .
cp /local/path/.gitignore .
cp /local/path/.env.example .
cp /local/path/CHANGELOG.md .

# Step 4: Create CI workflow
mkdir -p .github/workflows
# Create ci.yml with provided content

# Step 5: Initial commit
git add .
git commit -m "chore: Setup GitHub infrastructure and CI/CD

- Add GitHub Actions workflows (Black, mypy, pytest)
- Add LICENSE (GNU 3.0)
- Add .gitignore and .env.example
- Add CHANGELOG and documentation templates
- Setup issue templates
- Configure branch protection"

git push origin main
```

**Success Criteria:**
- ✅ Repository exists + is public
- ✅ All documentation files present
- ✅ CI/CD workflows configured + passing
- ✅ GitHub settings optimized
- ✅ Repo shows "healthy" on GitHub

**Parallel with:** Code-Cleaner (independent tasks)

---

### Week 2: Testing & Pre-Launch

#### Agent 3: Testing & CI Agent 🧪

**Mission:** Build comprehensive test suite, verify CI/CD

**Tasks:**
```
Test Infrastructure
├─ [ ] Create tests/ directory
├─ [ ] Create tests/__init__.py
├─ [ ] Create tests/conftest.py (pytest fixtures)
│   ├─ Mock OANDA client
│   ├─ Mock database (asyncpg)
│   ├─ Test data fixtures
│   └─ Setup/teardown helpers
└─ [ ] Create pytest.ini configuration

Unit Tests
├─ [ ] tests/test_health.py
│   ├─ Test GET /health endpoint
│   ├─ Test GET / endpoint
│   └─ Verify response format
├─ [ ] tests/test_account.py
│   ├─ Test GET /account
│   ├─ Test GET /account/summary
│   ├─ Test GET /account/instruments
│   └─ Test PATCH /account/configuration
├─ [ ] tests/test_orders.py
│   ├─ Test GET /orders
│   ├─ Test POST /order/market
│   ├─ Test POST /order/limit
│   ├─ Test PATCH /order/{id}
│   └─ Test DELETE /order/{id}
├─ [ ] tests/test_trades.py
│   ├─ Test GET /trades
│   ├─ Test GET /trade/{id}
│   ├─ Test PATCH /trade/{id}
│   └─ Test PUT /trade/{id}/close
└─ [ ] tests/test_mcp_tools.py
    ├─ Test MCP initialize
    ├─ Test tools/list
    └─ Test tools/call

Coverage Analysis
├─ [ ] Run: pytest --cov=src --cov-report=html
├─ [ ] Target: 80%+ coverage
├─ [ ] Identify uncovered lines
├─ [ ] Add tests for critical paths
└─ [ ] Generate coverage badge for README

CI/CD Verification
├─ [ ] Push test commit
├─ [ ] Verify GitHub Actions runs
├─ [ ] Check Black passes
├─ [ ] Check mypy passes
├─ [ ] Check pytest passes
├─ [ ] Check coverage meets threshold
└─ [ ] Verify badges display in README

Output Artifacts
├─ [ ] tests/ directory with 20+ test cases
├─ [ ] 80%+ code coverage
├─ [ ] All CI/CD checks passing
├─ [ ] Coverage badge working
└─ [ ] Test documentation for developers
```

**Execution:**
```bash
# Time estimate: 6-8 hours

# Step 1: Create test structure
mkdir -p tests
touch tests/__init__.py tests/conftest.py

# Step 2: Write conftest.py with fixtures
# (Mock OANDA client, fixtures, setup/teardown)

# Step 3: Write unit tests
# - test_health.py
# - test_account.py
# - test_orders.py
# - test_trades.py
# - test_mcp_tools.py

# Step 4: Run locally
pytest tests/ -v
pytest tests/ --cov=src --cov-report=html

# Step 5: Commit & push
git checkout -b feature/testing-framework
git add tests/ pytest.ini
git commit -m "test: Add comprehensive test suite with 80%+ coverage

- Add pytest configuration
- Add 25+ unit tests
- Add fixtures and mocks
- Add conftest.py for test setup
- Coverage report available

Coverage: 80%+ (target)
All tests: PASSING"

git push origin feature/testing-framework
```

**Success Criteria:**
- ✅ 20+ test cases written
- ✅ 80%+ code coverage achieved
- ✅ All tests passing locally + CI/CD
- ✅ Coverage badge displaying
- ✅ Test documentation available

**Dependencies:** Code-Cleaner (must complete first)

---

### Week 2: Tier 1 Improvements (Parallel Streams)

#### Agent 4a: Rate Limiter Agent ⚡

**Mission:** Implement token bucket rate limiting

**Tasks:**
```
Implementation
├─ [ ] Create src/rate_limiter.py
│   ├─ Class: TokenBucketLimiter
│   ├─ Methods:
│   │   ├─ __init__(rate_per_minute, burst_size)
│   │   ├─ is_allowed(client_id) → bool
│   │   └─ get_headers() → dict (X-RateLimit-*)
│   ├─ Data: In-memory dict of client states
│   └─ TTL: Auto-cleanup old entries
├─ [ ] Apply to endpoints:
│   ├─ /orders* (100 req/min)
│   ├─ /trades* (100 req/min)
│   ├─ /price* (100 req/min)
│   ├─ /account* (50 req/min)
│   └─ /instruments* (50 req/min)
└─ [ ] Response headers:
    ├─ X-RateLimit-Limit: 100
    ├─ X-RateLimit-Remaining: 95
    ├─ X-RateLimit-Reset: timestamp
    └─ Retry-After: seconds (on 429)

Testing
├─ [ ] Unit tests: RateLimiter class
├─ [ ] Integration test: Verify 429 after limit
├─ [ ] Load test: 1000 req/s without errors
└─ [ ] Documentation: Update README + API docs

Output Artifacts
├─ [ ] src/rate_limiter.py (~100 LOC)
├─ [ ] Applied to 5 endpoint groups
├─ [ ] Tests passing
└─ [ ] Ready to merge
```

**Execution (Parallel with 4b & 4c):**
```bash
# Time estimate: 3-4 hours

git checkout -b feature/rate-limiting

# Write src/rate_limiter.py
# Write tests/test_rate_limiter.py

# Apply decorator to endpoints
# Test: pytest tests/test_rate_limiter.py

git commit -m "feat: Add token bucket rate limiting

- Implement TokenBucketLimiter class
- Apply to 5 endpoint groups
- Add X-RateLimit-* headers
- Add 429 responses when exceeded
- Tests: 15 cases, all passing"

git push origin feature/rate-limiting
```

**Success Criteria:**
- ✅ Rate limiter working
- ✅ 429 responses after limit
- ✅ Headers present + correct
- ✅ Tests passing

**Parallel:** Yes (independent file)

---

#### Agent 4b: Validator Agent ✔️

**Mission:** Implement comprehensive input validation

**Tasks:**
```
Implementation
├─ [ ] Create src/validators.py
│   ├─ validate_candle_params(granularity, count, from_time, to_time)
│   ├─ validate_order_params(instrument, units, price)
│   ├─ validate_trade_params(trade_id)
│   ├─ validate_instrument_name(instrument)
│   └─ validate_rfc3339_datetime(datetime_str)
├─ [ ] Apply to endpoints:
│   ├─ GET /instruments/{inst}/candles
│   ├─ POST /order/* (all order creation)
│   ├─ PATCH /trade/{id}
│   └─ GET /pricing
└─ [ ] Error messages (clear + actionable):
    ├─ "granularity must be one of: S5, S10, ..., M"
    ├─ "count must be between 1 and 5000"
    └─ "invalid RFC3339 datetime. Example: 2024-01-15T00:00:00Z"

Testing
├─ [ ] Unit tests: Each validator function
├─ [ ] Integration test: Verify 422 on invalid input
├─ [ ] Error message clarity test
└─ [ ] Documentation: Validation rules in API docs

Output Artifacts
├─ [ ] src/validators.py (~150 LOC)
├─ [ ] Applied to 8+ endpoints
├─ [ ] Clear error messages
├─ [ ] Tests passing
└─ [ ] Ready to merge
```

**Execution (Parallel with 4a & 4c):**
```bash
# Time estimate: 4-5 hours

git checkout -b feature/input-validation

# Write src/validators.py
# Write tests/test_validators.py

# Apply to endpoints
# Test: pytest tests/test_validators.py

git commit -m "feat: Add comprehensive input validation

- Create validators.py with 5 validator functions
- Apply pre-flight checks to 8+ endpoints
- Return 422 with clear error messages
- Tests: 20 cases, all passing"

git push origin feature/input-validation
```

**Success Criteria:**
- ✅ Validators working
- ✅ 422 responses on invalid input
- ✅ Error messages clear + helpful
- ✅ Tests passing

**Parallel:** Yes (independent file)

---

#### Agent 4c: Circuit Breaker Agent 🔄

**Mission:** Implement resilient retry logic with circuit breaker

**Tasks:**
```
Implementation
├─ [ ] Create src/circuit_breaker.py
│   ├─ States: CLOSED, OPEN, HALF_OPEN
│   ├─ Failure threshold: 5 errors
│   ├─ Recovery timeout: 60 seconds
│   ├─ Backoff: 2^n * 100ms (max 60s)
│   └─ Methods:
│       ├─ __init__()
│       ├─ call(async_func, *args) → result
│       ├─ reset()
│       └─ get_state()
├─ [ ] Wrap OANDA client calls
├─ [ ] Implement exponential backoff
├─ [ ] Logging: State transitions, retries
└─ [ ] Metrics: Track failures, retries, success rate

Testing
├─ [ ] Unit tests: Circuit breaker state machine
├─ [ ] Simulation: Timeout errors → OPEN state
├─ [ ] Verification: Auto-recovery to CLOSED
├─ [ ] Load test: 100 req/s with transient errors
└─ [ ] Documentation: Retry behavior in README

Output Artifacts
├─ [ ] src/circuit_breaker.py (~200 LOC)
├─ [ ] Applied to OANDA client
├─ [ ] Metrics endpoint (/metrics)
├─ [ ] Tests passing
└─ [ ] Ready to merge
```

**Execution (Parallel with 4a & 4b):**
```bash
# Time estimate: 5-6 hours

git checkout -b feature/circuit-breaker

# Write src/circuit_breaker.py
# Write tests/test_circuit_breaker.py

# Wrap OANDA client
# Add metrics endpoint

# Test: pytest tests/test_circuit_breaker.py

git commit -m "feat: Add circuit breaker with exponential backoff

- Implement CircuitBreaker state machine
- Exponential backoff retry logic (2^n * 100ms)
- Auto-recovery from transient failures
- Metrics endpoint (/metrics)
- Tests: 18 cases, all passing"

git push origin feature/circuit-breaker
```

**Success Criteria:**
- ✅ Circuit breaker state machine working
- ✅ Exponential backoff implemented
- ✅ Auto-recovery functioning
- ✅ Tests passing
- ✅ Metrics tracking

**Parallel:** Yes (independent file)

---

### Week 2: Integration & Release

#### Final Integration (Day 10-12)

```bash
# Merge all feature branches to main

# 1. Merge rate-limiting
git checkout main
git merge feature/rate-limiting --ff

# 2. Merge input-validation
git merge feature/input-validation --ff

# 3. Merge circuit-breaker
git merge feature/circuit-breaker --ff

# 4. Integration test: All 3 together
pytest tests/ -v
# Verify no conflicts, all tests pass

# 5. Tag release candidate
git tag v4.0.0-rc1
git push origin main --tags

# 6. Final verification
curl http://localhost:8000/health  # Should work
curl http://localhost:8000/account  # Should work with rate limiting
pytest tests/ --cov=src  # 80%+ coverage

# 7. Create GitHub Release (v4.0.0)
# Changelog: List all improvements
# Assets: Docker image (optional)

git tag v4.0.0
git push origin main --tags
```

---

## 📊 Phase 1 Success Checklist

**By End of Week 2 (Day 14):**

```
Code Quality
├─ [ ] All code converted to English
├─ [ ] Black formatting: ✅ Clean
├─ [ ] mypy type checking: ✅ Strict mode
├─ [ ] No security issues: ✅ Verified
└─ [ ] Code review: ✅ Approved

Testing
├─ [ ] Unit tests: 25+ cases
├─ [ ] Integration tests: ✅ Passing
├─ [ ] Coverage: ✅ 80%+
├─ [ ] Performance: <100ms p99
└─ [ ] Load test: ✅ 1000 req/s

GitHub & CI/CD
├─ [ ] Repository: ✅ Public + configured
├─ [ ] CI/CD pipelines: ✅ All passing
├─ [ ] Workflows: ✅ Black, mypy, pytest
├─ [ ] Coverage badge: ✅ Displaying
└─ [ ] Issue templates: ✅ Setup

Tier 1 Improvements
├─ [ ] Rate limiting: ✅ Active + tested
├─ [ ] Input validation: ✅ Applied to endpoints
├─ [ ] Circuit breaker: ✅ Working + metrics
├─ [ ] All three integrated: ✅ No conflicts
└─ [ ] Performance impact: <1ms per request

Documentation
├─ [ ] README: ✅ Updated with improvements
├─ [ ] API docs: ✅ Swagger functional
├─ [ ] Changelog: ✅ v4.0.0 entry
├─ [ ] CONTRIBUTING.md: ✅ Setup
└─ [ ] LICENSE: ✅ GNU 3.0

Release Readiness
├─ [ ] v4.0.0-rc1 tag: ✅ Created
├─ [ ] Final verification: ✅ All green
├─ [ ] Go/no-go decision: ✅ READY
└─ [ ] v4.0.0 tag: ✅ Created for public launch
```

---

## 🚀 Phase 2 Preview (Week 3-4)

After Phase 1 complete:
- Launch Manager Agent: Coordinates public GitHub push + community launch
- Community response: Monitor stars, forks, issues
- Iterate on initial feedback
- Plan Tier 2 improvements (webhooks, analytics)

---

## ⚡ Quick Start Commands

```bash
# Week 1: Code Cleanup
git checkout -b feature/i18n-english-primary
# ... make changes ...
git commit -m "i18n: Convert all Spanish → English"
git push origin feature/i18n-english-primary

# Week 1: GitHub Setup (parallel)
# Create repo on GitHub web UI
# Clone, add files, push

# Week 2: Testing (after Code-Cleaner merges)
git checkout -b feature/testing-framework
# ... write tests ...
git commit -m "test: Add pytest suite with 80%+ coverage"
git push origin feature/testing-framework

# Week 2: Tier 1 Improvements (parallel)
git checkout -b feature/rate-limiting
# ... implement rate limiter ...
git push origin feature/rate-limiting

git checkout -b feature/input-validation
# ... implement validators ...
git push origin feature/input-validation

git checkout -b feature/circuit-breaker
# ... implement circuit breaker ...
git push origin feature/circuit-breaker

# Merge all to main
git checkout main
git merge feature/rate-limiting --ff
git merge feature/input-validation --ff
git merge feature/circuit-breaker --ff
git tag v4.0.0
git push origin main --tags
```

---

## 🎯 Ready?

**This is your execution blueprint. Each agent has:**
- ✅ Clear mission
- ✅ Specific tasks
- ✅ Time estimate
- ✅ Success criteria
- ✅ Example commands

**Start Week 1 NOW with:**
1. Code-Cleaner Agent (convert to English)
2. GitHub Setup Agent (parallel)
3. Then proceed to Week 2

**Questions? Blockers? Let me know before execution.**

🚀 **LET'S BUILD!**

