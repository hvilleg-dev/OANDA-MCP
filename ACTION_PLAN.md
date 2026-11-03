# OANDA MCP Server — Implementation Action Plan

**Created:** 2026-11-03  
**Timeline:** 2 weeks to GitHub launch  
**Owner:** Your Name  
**Status:** READY TO EXECUTE

---

## 📋 Master Checklist

### Phase 1: GitHub Preparation (Days 1-3)

```
LEGAL & SETUP
├─ [ ] Create GitHub repository (public)
├─ [ ] Add LICENSE file (GNU 3.0)
├─ [ ] Configure .gitignore (ignore .env, __pycache__, etc.)
├─ [ ] Create CONTRIBUTING.md
└─ [ ] Setup GitHub Actions for CI/CD

DOCUMENTATION
├─ [ ] Replace README.md with README_PROFESSIONAL.md
├─ [ ] Add GETTING_STARTED.md
├─ [ ] Create ARCHITECTURE.md
├─ [ ] Create TROUBLESHOOTING.md
├─ [ ] Create CHANGELOG.md (v4.0.0 entry)
├─ [ ] Add API_REFERENCE.md
└─ [ ] Copy ANALYSIS_AND_RECOMMENDATIONS.md as reference

CODE CLEANUP
├─ [ ] Run Black formatter (black src/)
├─ [ ] Run mypy type checker (mypy src/ --strict)
├─ [ ] Verify all docstrings present
├─ [ ] Update server.py version = "4.0.0"
└─ [ ] Ensure no credentials in code

TESTING
├─ [ ] Create tests/test_server.py (basic health checks)
├─ [ ] Create tests/test_mcp_tools.py (tool execution)
├─ [ ] Create tests/test_oanda_client.py (client wrapper)
├─ [ ] Run pytest with coverage report
├─ [ ] Update CI workflow to run tests
└─ [ ] Ensure 80%+ coverage

CONFIG FILES
├─ [ ] Finalize .env.example with comments
├─ [ ] Verify docker-compose.yml
├─ [ ] Create .dockerignore
├─ [ ] Test Docker build: docker build -t oanda-mcp .
└─ [ ] Test Docker Compose: docker-compose up && curl health
```

**Estimated Time:** 8-10 hours

---

### Phase 2: Tier 1 Technical Improvements (Days 3-5)

```
RATE LIMITING
├─ [ ] Install slowapi: pip install slowapi
├─ [ ] Create src/rate_limiter.py
├─ [ ] Implement token bucket limiter
├─ [ ] Apply to 10 high-frequency endpoints
├─ [ ] Add rate limit headers to responses
├─ [ ] Test: Verify 429 response after limit
└─ [ ] Document in API reference

INPUT VALIDATION
├─ [ ] Create src/validators.py
├─ [ ] Add validation for:
│   ├─ Candle params (count ≤ 5000, valid granularity)
│   ├─ Order params (units > 0, valid instruments)
│   ├─ Trade params (valid trade IDs)
│   ├─ Price params (valid instrument names)
│   └─ Datetime params (RFC3339 format)
├─ [ ] Add pre-flight checks in handlers
├─ [ ] Return 422 with clear messages
└─ [ ] Test: Verify validation errors are helpful

CIRCUIT BREAKER
├─ [ ] Create src/circuit_breaker.py
├─ [ ] Implement states: CLOSED → OPEN → HALF_OPEN → CLOSED
├─ [ ] Configure for OANDA client
├─ [ ] Exponential backoff retry logic (2^n * 100ms, max 60s)
├─ [ ] Add retry metrics logging
├─ [ ] Test: Simulate OANDA timeout, verify retry behavior
└─ [ ] Document retry behavior in README
```

**Estimated Time:** 12-15 hours

---

### Phase 3: GitHub Push & Community Launch (Days 5-7)

```
FINAL PREP
├─ [ ] Remove sensitive data from all files
├─ [ ] Verify .env.example has NO real credentials
├─ [ ] Double-check all documentation links are valid
├─ [ ] Update README with GitHub URL
├─ [ ] Verify Swagger docs work (/docs endpoint)
├─ [ ] Take screenshot of dashboard for README
└─ [ ] Create demo trade scenario for docs

GIT WORKFLOW
├─ [ ] git init (if not already)
├─ [ ] git add . (exclude .env, *.log)
├─ [ ] git commit -m "Initial: OANDA MCP v4.0.0 - production ready"
├─ [ ] git remote add origin https://github.com/user/oanda-mcp
├─ [ ] git push -u origin main
└─ [ ] Verify repository is public

GITHUB CONFIGURATION
├─ [ ] Add repository description: "Production MCP server for OANDA v20 trading automation with Claude AI"
├─ [ ] Add topics: mcp, oanda, trading, ai, claude, automation
├─ [ ] Enable GitHub Pages (optional) for docs
├─ [ ] Setup GitHub Actions secret: DOCKER_TOKEN (for future)
├─ [ ] Enable Discussions for community
├─ [ ] Add Links section with Swagger URL
└─ [ ] Create milestone: v4.0.0 Complete, v4.1.0 Planned

COMMUNITY LAUNCH
├─ [ ] Post on r/algotrading with demo
├─ [ ] Post on r/oanda with "Built MCP server" pitch
├─ [ ] Share in trading Discord communities
├─ [ ] Post on Twitter/X with demo GIF/screenshot
├─ [ ] Add to Awesome MCP list (GitHub) if exists
├─ [ ] Email alpha users (if any) for feedback
└─ [ ] Setup Google Alerts for "OANDA MCP" mentions
```

**Estimated Time:** 4-5 hours

---

### Phase 4: Feedback & Iteration (Days 7-14)

```
MONITORING
├─ [ ] Watch GitHub notifications religiously
├─ [ ] Respond to issues within 24 hours
├─ [ ] Track community feedback
├─ [ ] Monitor performance metrics
└─ [ ] Collect feature requests

QUICK WINS (Response to feedback)
├─ [ ] Fix critical bugs immediately
├─ [ ] Add clarifying documentation as needed
├─ [ ] Create examples based on common questions
├─ [ ] Optimize performance bottlenecks
└─ [ ] Implement highest-voted features

CONTENT CREATION
├─ [ ] Create demo video (5 min): Setup to first trade
├─ [ ] Write blog post: "Why I Built OANDA MCP Server"
├─ [ ] Create tutorial: "Trading EUR/USD via Claude"
├─ [ ] Document common patterns/recipes
└─ [ ] Collect testimonials from early users

ROADMAP PLANNING
├─ [ ] Create ROADMAP.md with:
│   ├─ Short-term (1 mo): Bug fixes, docs
│   ├─ Medium-term (3 mo): Backtest simulator, webhooks
│   ├─ Long-term (6+ mo): Other brokers, ML features
│   └─ Community voting on priorities
└─ [ ] Create GitHub Projects board for tracking
```

**Estimated Time:** Ongoing, 2-3 hours daily

---

## 🎯 Detailed Implementation Tasks

### Task 1: README Migration

**Current State:** Multiple README variants  
**Target:** Single `README.md` = `README_PROFESSIONAL.md`

```bash
# Action
cp README_PROFESSIONAL.md README.md
rm README_PROFESSIONAL.md

# Verify
# - Open README.md locally
# - Click all markdown links
# - Verify Swagger/docs URLs
# - Test command examples (copy-paste friendly)
```

**Owner:** You  
**Time:** 30 min  
**Validation:** README renders perfectly on GitHub, all links valid

---

### Task 2: Implement Rate Limiting

**Current State:** No rate limiting → OANDA can rate-limit/ban  
**Target:** Token bucket + 429 responses

```python
# New file: src/rate_limiter.py

from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime, timedelta

class OANDALimiter:
    def __init__(self, requests_per_minute=100):
        self.limiter = Limiter(key_func=get_remote_address)
        self.rpm = requests_per_minute
    
    def enforce(self, endpoint):
        # Apply to endpoint
        pass

# In server.py
limiter = OANDALimiter(requests_per_minute=100)

@app.get("/orders")
@limiter.enforce
async def get_orders():
    ...
```

**Owner:** You  
**Time:** 3-4 hours  
**Validation:**
```bash
# Test rate limiting
for i in {1..150}; do curl http://localhost:8000/orders; done
# Should see 429 after 100 requests
```

---

### Task 3: Input Validation Layer

**Current State:** Some validation, inconsistent  
**Target:** Comprehensive pre-flight checks

```python
# New file: src/validators.py

def validate_candle_params(granularity, count, from_time, to_time):
    VALID_GRANULARITIES = ['S5', 'S10', ..., 'M']
    
    if granularity not in VALID_GRANULARITIES:
        raise ValueError(f"Invalid granularity. Must be one of: {VALID_GRANULARITIES}")
    
    if count and (count < 1 or count > 5000):
        raise ValueError("count must be between 1 and 5000")
    
    if from_time and to_time:
        # Validate RFC3339 format
        # Ensure from < to
        pass
    
    return True

# Usage in endpoint
@app.get("/instruments/{instrument}/candles")
async def get_candles(...):
    validate_candle_params(granularity, count, from_time, to_time)
    ...
```

**Owner:** You  
**Time:** 4-5 hours  
**Validation:** Test with invalid inputs, expect clear 422 errors

---

### Task 4: Circuit Breaker Implementation

**Current State:** Simple try-catch, no adaptive retry  
**Target:** Intelligent backoff, state management

```python
# New file: src/circuit_breaker.py

from enum import Enum
import asyncio

class CircuitState(Enum):
    CLOSED = "closed"      # Normal
    OPEN = "open"          # Failing, reject fast
    HALF_OPEN = "half_open" # Testing recovery

class OANDACircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
    
    async def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
            raise
```

**Owner:** You  
**Time:** 5-6 hours  
**Validation:** Simulate OANDA outage, verify automatic recovery

---

### Task 5: GitHub Actions CI/CD

**Current State:** None  
**Target:** Auto-test, auto-lint on push

```yaml
# File: .github/workflows/ci.yml

name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt pytest pytest-cov
      - run: black --check src/
      - run: mypy src/ --strict
      - run: pytest tests/ --cov=src/
      - run: pytest tests/ --cov-report=xml
      - uses: codecov/codecov-action@v3
```

**Owner:** You  
**Time:** 1-2 hours  
**Validation:** Push to GitHub, watch workflow run automatically

---

## 📅 Master Timeline

```
┌─────────────────────────────────────────────────────────────────────┐
│ WEEK 1 (Days 1-7)                                                   │
├─────────────────────────────────────────────────────────────────────┤
│ Mon-Tue (Days 1-2): GitHub prep + docs                              │
│ Wed-Thu (Days 3-4): Rate limiting + validation                      │
│ Fri (Day 5): Circuit breaker                                        │
│ Sat (Day 6): Final cleanup + GitHub push                            │
│ Sun (Day 7): Community launch + monitoring                          │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ WEEK 2 (Days 8-14)                                                  │
├─────────────────────────────────────────────────────────────────────┤
│ Mon-Fri (Days 8-12): Iterate on feedback, fix bugs                  │
│ Sat-Sun (Days 13-14): Content creation (blog, video)                │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🎬 Launch Day Checklist

```
24 HOURS BEFORE LAUNCH
├─ [ ] Final test: docker-compose up → health check passes
├─ [ ] Final test: Create test trade → verify logging
├─ [ ] Final review: All documentation links work
├─ [ ] Backup: Git tag v4.0.0-pre-launch
└─ [ ] Notify: Anyone who's seen this project

LAUNCH DAY MORNING
├─ [ ] git push to GitHub (main branch)
├─ [ ] Verify repository is public
├─ [ ] Verify all docs render correctly on GitHub
├─ [ ] Test Swagger docs: http://localhost:8000/docs
├─ [ ] Create GitHub discussion: "Welcome!"
└─ [ ] Test MCP in Claude Desktop (if available)

LAUNCH DAY AFTERNOON
├─ [ ] Reddit post on r/algotrading (title: "I built an MCP server...")
├─ [ ] Reddit post on r/oanda (title: "Claude + OANDA integration...")
├─ [ ] Twitter post with demo screenshot
├─ [ ] Discord communities: Share link
├─ [ ] Monitor first reactions
└─ [ ] Respond to first questions <30 min

LAUNCH DAY EVENING
├─ [ ] Collect feedback in Discussions
├─ [ ] Plan response to top questions
├─ [ ] Check stats: stars, forks, watch count
├─ [ ] Journal: What's working, what needs improvement
└─ [ ] Commit: "Launch day - initial community feedback"
```

---

## 📊 Success Metrics (First 2 Weeks)

### Quantitative

| Metric | Target | Success |
|--------|--------|---------|
| GitHub Stars | 100+ | ✅ 250+ |
| Forks | 10+ | ✅ 20+ |
| Commits | 5+ | ✅ 10+ |
| Issues Opened | 5+ | ✅ 5+ |
| Code Coverage | 80%+ | ✅ 85%+ |

### Qualitative

| Metric | Evidence |
|--------|----------|
| Code Quality | All tests pass, mypy clean, Black formatted |
| Documentation | No "confused" issues, positive feedback |
| Usability | Users report successful setup |
| Engagement | Discussion threads, positive reactions |
| Community Interest | Mentions in Discord, Twitter retweets |

---

## 🚨 Risk Mitigation

### Risk: Database Connection Issues

**Prevention:** 
- Test with PostgreSQL down
- Implement graceful degradation (server works without DB)

### Risk: OANDA API Breaking Change

**Prevention:**
- Pin oandapyV20 version
- Create branch for v0.7.x when released
- Monitor release notes

### Risk: Security Vulnerability in Dependencies

**Prevention:**
- Run `pip audit` weekly
- Setup Dependabot on GitHub
- Quick patch policy

### Risk: Users Share API Keys Publicly

**Prevention:**
- BOLD warning in README
- Add secret detection in .env template
- Public docs: "Never share API keys"

---

## 👥 Support & Ownership

### Your Responsibilities

1. **Respond to issues** <24 hours during business days
2. **Monitor performance** daily (first month)
3. **Triage bugs** vs. feature requests
4. **Prioritize fixes** based on impact
5. **Create roadmap** based on feedback
6. **Review PRs** promptly

### Community Contributions Welcome

- Encourage fork + PR flow
- Provide CONTRIBUTING.md guidelines
- Review external code carefully
- Credit contributors in CHANGELOG

---

## 📈 Post-Launch Strategy (Week 3+)

### Short-term (1 month)
1. Fix critical bugs
2. Improve documentation based on feedback
3. Create advanced examples
4. Establish monthly metrics

### Medium-term (3 months)
1. Implement Tier 2 features (webhooks, advanced analytics)
2. Consider freemium SaaS layer
3. Explore partnerships (trading communities, brokers)
4. Plan Series A if metrics support

### Long-term (6+ months)
1. Expand to other brokers (IB, Kraken, etc.)
2. Build ecosystem of MCP tools
3. Establish as reference implementation
4. Consider funding/acquisition

---

## ✅ Final Validation

Before launch, verify:

- [ ] **Code:** No `print()` statements, only logging
- [ ] **Secrets:** No API keys, passwords in codebase
- [ ] **Docs:** All links work, examples are copy-paste ready
- [ ] **Tests:** 80%+ coverage, all pass
- [ ] **Performance:** <100ms response time, handles 100 req/s
- [ ] **Security:** Rate limiting active, input validation tight
- [ ] **Compliance:** License clear, ToS/Privacy policy (if SaaS)

---

**Ready to launch? Let's execute! 🚀**

Questions or blockers? Document them and we iterate.

