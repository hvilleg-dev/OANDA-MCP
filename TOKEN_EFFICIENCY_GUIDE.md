# OANDA MCP Server — Token Efficiency & Memory Management Guide

**Purpose:** Retomar trabajo sin perder contexto, minimizando uso de tokens  
**Updated:** November 3, 2026

---

## 🎯 TL;DR (30 segundos)

**Sistema de 3 capas para eficiencia máxima:**

1. **PROJECT_PROGRESS.md** — Local, git-tracked (retomar en 2 min)
2. **Claude Memory** — Persistente entre sesiones (estrategia + decisiones)
3. **GitHub Issues** — Público, searchable (tracking visible)

**No necesitas releer todo al volver. Sólo 5 min de contexto.**

---

## 💾 LAYER 1: PROJECT_PROGRESS.md (Local)

### ¿Qué es?
Archivo local en el repo que rastrea:
- Estado de cada tarea
- Commits recientes
- Blockers activos
- Último log diario

### ¿Por qué es eficiente?
✅ **Gratis** — No consume tokens (es local)  
✅ **Rápido** — Retomar en 2 minutos  
✅ **Git-tracked** — Parte del repo, versionado  
✅ **Human-readable** — Puedes leer en cualquier editor

### Cómo usarlo

**Al empezar tu día:**
```bash
# 1. Abre PROJECT_PROGRESS.md
cat PROJECT_PROGRESS.md | less

# 2. Lee "DAILY LOG" (última entrada)
# 3. Mira "Next 24 Hours Plan"
# 4. Verifica git status
git status
git log -n 5

# 5. Empieza trabajando (time spent: 2 min, tokens: 0)
```

**Al terminar tu día:**
```bash
# 1. Actualiza PROJECT_PROGRESS.md
# Añade entrada en "DAILY LOG":
#   - What was completed
#   - Current status (% done)
#   - Next steps
#   - Any blockers
#   - Time spent

# 2. Commit
git add PROJECT_PROGRESS.md
git commit -m "chore: Day X progress update - [summary]"

# 3. Push (optional if remote)
git push origin main
```

### Plantilla Daily Log Entry

```markdown
### [DATE] — Day X — [AGENT/TASK]

**Morning Report:**
- Yesterday completed: Convert 70% of server.py comments to English
- Time spent: 3.2 hours
- Remaining: 30% of comments + docstrings

**Current Status:**
- Task: Converting dashboard.html to English
- % complete: 45%
- ETA: 2 more hours

**Blockers:**
- None

**Next 24 Hours Plan:**
- [ ] Finish dashboard.html conversion
- [ ] Run Black formatter
- [ ] Run mypy type check
- [ ] Commit feature/i18n-english-primary

**Code Changes:**
- Files modified: server.py, dashboard.html
- Lines added: 0 (translations only)
- Tests passing: N/A (not yet)
- Commits: 2 commits today
```

---

## 🧠 LAYER 2: Claude Memory (Persistent)

### ¿Qué es?
Sistema de persistencia que Claude mantiene entre sesiones en archivos `.claude/projects/*/memory/`

### ¿Por qué es útil?
✅ **Contexto estratégico** — Decisiones, cambios de dirección  
✅ **No re-derivar** — No repites análisis hecho antes  
✅ **Personalizacion** — Preferencias, feedback acumulado  
✅ **Async teams** — Si coordinan múltiples agentes

### Qué guardar en Memory

**Memory Type 1: Project Decisions**
```
Name: phase-1-decisions
Type: project
Content:
- English-primary decision locked (Spanish secondary in Phase 7)
- Rate limiting target: 100 req/min per endpoint
- Circuit breaker failure threshold: 5 errors
- Test coverage target: 80%+ minimum
- GitHub public announcement: After v4.0.0 tag only
```

**Memory Type 2: Agent Status**
```
Name: active-agents-status
Type: project
Content:
- Code-Cleaner: Ready to spawn
- GitHub Setup: Ready to spawn (parallel)
- Rate Limiter: Blocked until Testing completes
- Current phase: 1 (Foundation)
- Last checkpoint: Day 5, code-cleaner merged
```

**Memory Type 3: Feedback Loop**
```
Name: execution-adjustments
Type: feedback
Content:
- If task takes >20% longer than estimate: Reassess scope
- If blocker unsolvable locally: Escalate to Claude
- Update PROJECT_PROGRESS.md daily (critical for retomar)
- Run full test suite before each merge (prevent regressions)
```

### Cómo usar Memory (Opcional pero Recomendado)

**Al empezar sesión:**
```
Tell Claude:
"Load my project memory for OANDA MCP. 
Where are we in Phase 1? What's the current blocker?"

Claude reads memory files automatically.
```

**Al final de sesión:**
```
Tell Claude:
"Save to memory:
- Phase 1 status: [current]
- Today completed: [list]
- Next blockers: [list]
- Decisions made: [list]"

Claude saves to memory files.
```

**Eficiencia:**
✅ First mention: ~500 tokens to establish context  
✅ Subsequent mentions: ~50 tokens (cached)  
✅ Each day you return: Cache hit if memory fresh

---

## 📊 LAYER 3: GitHub Issues & Projects (Visible)

### ¿Qué es?
GitHub Issues + Projects board para tracking público

### ¿Cuándo usar?
- **Bloqueadores** que necesiten feedback
- **External contributors** que quieran ayudar
- **Milestone tracking** (público para credibilidad)
- **Week 3+** después del lanzamiento público

### Estructura (Phase 3 onwards)

**GitHub Issues (Phase 3):**
```
- Título: [Phase 1] Code cleanup - English conversion
- Label: phase-1, task, in-progress
- Milestone: v4.0.0
- Description: Link to PROJECT_PROGRESS.md + current status
```

**GitHub Projects Board (Phase 3):**
```
Columns: Backlog → In Progress → Review → Done
Cards: Issues + PRs (auto-populate)
View: Public + readonly for community
```

---

## ⚡ EFFICIENCY STRATEGY: RETOMAR SIN TOKENS

### Scenario 1: Cerraste la consola, vuelves mañana

**Time: 2 minutes | Tokens: ~50 (git commands only)**

```bash
# 1. Lee PROJECT_PROGRESS.md (local, no tokens)
cat PROJECT_PROGRESS.md | tail -50  # Last 50 lines

# 2. Verifica git status (local, no tokens)
git status

# 3. Si necesitas saber qué HACER:
# Read "Next 24 Hours Plan" en PROJECT_PROGRESS.md

# 4. Start working
# That's it! No need to call Claude yet.
```

### Scenario 2: Necesitas contexto de decisiones previas

**Time: 5 minutes | Tokens: ~200 (loading memory)**

```bash
# Use Claude Memory (if saved)
Tell Claude: "Load OANDA MCP memory. Summarize Phase 1 status."
Claude loads memory files + provides summary (50 tokens)
```

### Scenario 3: Tienes un blocker, necesitas ayuda

**Time: 10 minutes | Tokens: ~500 (fresh context)**

```bash
# You: "I'm stuck on [specific problem]. 
#       Check PROJECT_PROGRESS.md for context.
#       Here's my error: [error message]"

# Claude:
# 1. Reads PROJECT_PROGRESS.md (local, includes recent work)
# 2. Reads error message (yours)
# 3. Provides solution (~300 tokens)

# Much cheaper than re-explaining from scratch (~1500 tokens)
```

---

## 📋 EFFICIENCY CHECKLIST

### Daily (No Token Cost)
```
☐ Update PROJECT_PROGRESS.md (2 min)
☐ Read yesterday's log before starting (1 min)
☐ Check git status (local) (30 sec)
Total time: 3.5 minutes | Tokens: 0
```

### Weekly (Low Token Cost)
```
☐ Summarize weekly progress
☐ Update GitHub Issues (if started)
☐ Calculate velocity metrics
☐ Adjust next week plan
Total time: 15 min | Tokens: ~100 (Claude review optional)
```

### As Needed (Variable Cost)
```
☐ Consult Claude on blockers (~300 tokens)
☐ Load memory for strategy questions (~200 tokens)
☐ Ask for code review (~500 tokens)
```

---

## 🔄 RETOMAR WORKFLOW (Detailed)

### MORNING: Start of Day

**Step 1: (0 min, 0 tokens)**
```bash
# Wake up your local repo
git pull origin main  # Get any remote updates
```

**Step 2: (2 min, 0 tokens)**
```bash
# Read your progress file
cat PROJECT_PROGRESS.md | grep -A 20 "DAILY LOG"
# This shows: yesterday's work, blockers, today's plan
```

**Step 3: (1 min, 0 tokens)**
```bash
# Check git status
git status
# Shows uncommitted changes from yesterday
git log -n 3
# Shows recent commits
```

**Step 4: (2 min, if needed)**
```bash
# If you forgot what you were doing:
# Read the "Next 24 Hours Plan" section

# If that's not clear enough:
# Ask Claude: "I closed yesterday after work. 
#             What should I do today? 
#             (Check PROJECT_PROGRESS.md)"
# Token cost: ~100 (Claude reads your progress file)
```

**Step 5: START WORKING**
- No more context needed
- You know what to do
- No token waste

---

### END OF DAY: Wrap Up

**Step 1: (5 min)**
```bash
# Update PROJECT_PROGRESS.md
nano PROJECT_PROGRESS.md

# Add entry:
### [TODAY] — Day X — [AGENT]
**Morning Report:**
- Yesterday completed: [summary]
- Time spent: X hours
- Remaining: [what's left]
[... rest of template ...]

# Save and exit
```

**Step 2: (2 min)**
```bash
# Commit your progress tracking
git add PROJECT_PROGRESS.md
git commit -m "chore: Day X progress update

- Completed: [task summary]
- Time: X hours
- Status: [% complete]
- Next: [what's next]"

# Optional: push
git push origin main
```

**Step 3: (1 min, if strategic decision needed)**
```bash
# If you need to save strategic decision to memory:
Tell Claude: "Save to memory for OANDA MCP:
- Completed today: [X]
- Current blocker: [X]  
- Next priority: [X]"

# Claude saves (~50 tokens)
```

**TOTAL END-OF-DAY:** 8 min | ~50 tokens (optional)

---

## 📊 TOKEN CONSUMPTION EXAMPLE (Week 1)

### Day 1 (Start Phase 1)

```
Morning: Claude explains Phase 1 start: 400 tokens
Morning: Code-Cleaner begin: 200 tokens
Evening: Update PROJECT_PROGRESS.md: 0 tokens (local)
TOTAL: 600 tokens
```

### Day 2 (Continuing Phase 1)

```
Morning: Read PROJECT_PROGRESS.md: 0 tokens (local)
Morning: Continue code cleanup: 100 tokens (status check)
Evening: Update PROJECT_PROGRESS.md: 0 tokens (local)
TOTAL: 100 tokens
```

### Day 3-5 (Similar pattern)

```
Average per day: 100-150 tokens (just status checks)
```

### Week 1 TOTAL: ~1,500 tokens

**vs. WITHOUT tracking:** ~4,000-5,000 tokens (re-explaining context daily)

**Savings: 65% reduction in tokens**

---

## 🛡️ FAILURE SCENARIOS & RECOVERY

### Scenario A: Lost your PROJECT_PROGRESS.md

**Recovery:**
```bash
# 1. Check git log
git log --oneline | head -20

# 2. Find recent commits with descriptions
# They'll tell you what was completed

# 3. Reconstruct PROJECT_PROGRESS.md from git history
# Should take ~10 min max
```

### Scenario B: Forgot what you were doing mid-task

**Recovery:**
```bash
# 1. Check git status
git status

# 2. Read the uncommitted changes
git diff

# 3. Check PROJECT_PROGRESS.md last entry
grep -A 30 "Next 24 Hours Plan" PROJECT_PROGRESS.md

# 4. Resume from there
```

### Scenario C: GitHub repo lost (disaster recovery)

**Prevention:**
```bash
# Push PROJECT_PROGRESS.md daily
# It's git-tracked, so it's in remote backup

# To recover:
git clone https://github.com/user/oanda-mcp
cat PROJECT_PROGRESS.md
# Full history available
```

---

## 🎯 RECOMMENDED WORKFLOW

### Option 1: Minimal (My Recommendation)

```
Tool: PROJECT_PROGRESS.md ONLY
Frequency: Update daily (2 min at end of day)
Token savings: 65%
Setup: None (already created)

Daily routine:
  Morning: cat PROJECT_PROGRESS.md (read last entry)
  Work: Use "Next 24 Hours Plan"
  Evening: Update file + commit
```

### Option 2: Medium (With Memory)

```
Tools: PROJECT_PROGRESS.md + Claude Memory
Frequency: Update PROJECT_PROGRESS.md daily
         Update memory weekly
Token savings: 70%
Setup: Tell Claude to save memory 1x/week

Weekly routine:
  Monday morning: Load memory + read progress file
  Daily: Use progress file
  Friday evening: Tell Claude to save memory
```

### Option 3: Maximum (Public Tracking)

```
Tools: PROJECT_PROGRESS.md + Memory + GitHub Issues
Frequency: Daily for progress, Issues for visibility
Token savings: 75% (plus community engagement)
Setup: Create GitHub Issues Phase 3

Daily: Update PROJECT_PROGRESS.md
Weekly: Update GitHub Issues
Public: Show progress (credibility)
```

---

## ✅ FINAL RECOMMENDATION

**Use this setup:**

```
PRIMARY: PROJECT_PROGRESS.md (local)
  └─ Update daily (2 min, 0 tokens)
  └─ Read before starting (1 min, 0 tokens)
  
SECONDARY: Claude Memory (optional)
  └─ Save strategic decisions
  └─ Load once per week (~200 tokens)
  
TERTIARY: GitHub Issues (after Phase 2)
  └─ Public tracking
  └─ Community visibility
```

**Result:**
- ✅ Retomar en <3 minutos
- ✅ Cero tokens wasted
- ✅ Full context maintained
- ✅ Scalable para 8 semanas

---

## 📌 QUICK START TODAY

**Right now:**
1. ✅ PROJECT_PROGRESS.md created (you have it)
2. ✅ Read it to understand format
3. ✅ Start Phase 1 with Code-Cleaner agent
4. ✅ End of Day 1: Update PROJECT_PROGRESS.md
5. ✅ Commit: `git add PROJECT_PROGRESS.md && git commit -m "..."`

**Tomorrow:**
1. Cat PROJECT_PROGRESS.md (shows what to do)
2. Work (no token waste)
3. Update at end of day

**That's it. Efficient. Scalable. Free.**

---

## 🚀 FINAL SUMMARY

| Aspect | What to Do | Cost |
|--------|-----------|------|
| Track progress | Use PROJECT_PROGRESS.md | 2 min/day, 0 tokens |
| Retomar context | Read last daily log entry | 1 min, 0 tokens |
| Strategic memory | Save to Claude Memory 1x/week | 5 min, 50 tokens |
| Blocker help | Ask Claude with context | 10 min, 300 tokens |
| **TOTAL/WEEK** | **~3 hours** | **~1,500 tokens** |

**vs. Without system:** 5+ hours, 4,000+ tokens/week

**Savings: 40% time, 65% tokens**

---

**Ready? Start Phase 1. Update PROJECT_PROGRESS.md daily. That's all you need.**

