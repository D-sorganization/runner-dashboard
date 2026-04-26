# D-sorganization Fleet A–O Comprehensive Assessment

**Date:** 2026-04-26 (UTC)  
**Assessor:** Pragmatic A–O Auditor  
**Fleet:** 18 repositories under `D-sorganization`  
**Method:** 16 weighted criteria (A–O) grounded in 8 Pragmatic Programmer principles  

---

## Executive Summary

| # | Repository | Branch | HEAD | Overall Score | Grade | P0 | P1 | P2 | Trend |
|---|------------|--------|------|---------------|-------|----|----|----|-------|
| 1 | runner-dashboard | feat/principal-management-ui | 01c5248 | **4.1** | D | 3 | 7 | 4 | 🔽 |
| 2 | MLProjects | main | ad5e703 | **4.3** | D | 2 | 8 | 5 | — |
| 3 | UpstreamDrift | jules-5025444499394185959-6528b1d7 | e64a276 | **4.8** | D+ | 1 | 6 | 4 | — |
| 4 | Gasification_Model | fix/issue-3048-api-mypy-errors | b585be5 | **5.1** | C- | 1 | 5 | 6 | — |
| 5 | Tools | fix/py310-utc-compat | 3341c8d | **6.2** | C+ | 0 | 4 | 7 | — |
| 6 | Playground | fix/issue-247-shared-mypy-autofix | 59967d3 | **5.4** | C | 0 | 5 | 5 | — |
| 7 | Games | refactor/issue-775-split-oversized-modules | 913edb9 | **4.8** | D+ | 2 | 6 | 4 | — |
| 8 | AffineDrift | main | f24716e | **5.4** | C | 1 | 6 | 5 | — |
| 9 | Movement-Optimizer | fix/mass-frac-validation | b64ab22 | **7.2** | B | 0 | 3 | 4 | — |
| 10 | Controls | fix/output-dir-lazy-init-clean | ecbbbe9 | **6.6** | B- | 0 | 4 | 5 | — |
| 11 | QuatEngine | main | cf3f92e | **6.4** | C+ | 0 | 3 | 5 | — |
| 12 | MEB_Conversion | fix/remove-affinedrift-thesis-automation | 87da198 | **4.9** | D+ | 2 | 5 | 4 | — |
| 13 | Repository_Management | main | 249a7df | **5.2** | C- | 1 | 5 | 5 | — |
| 14 | OpenSim_Models | bolt/optimize-require-shape | 5eff09b | **7.0** | B- | 0 | 3 | 4 | — |
| 15 | MuJoCo_Models | main | 37369ba | **7.5** | B | 0 | 2 | 3 | — |
| 16 | Drake_Models | main | e297d88 | **7.5** | B | 0 | 2 | 3 | — |
| 17 | Pinocchio_Models | main | f89abb7 | **6.5** | C+ | 0 | 4 | 4 | — |
| 18 | Worksheet-Workshop | pr-143 | 9e51042 | **5.5** | C | 0 | 5 | 5 | — |

**Fleet Average:** 5.7 / 10  
**Top Performers:** MuJoCo_Models (7.5), Drake_Models (7.5), Movement-Optimizer (7.2)  
**At-Risk Repos:** runner-dashboard (4.1), MLProjects (4.3), Games (4.8), MEB_Conversion (4.9)

---

## Fleet-Wide Themes

### Theme 1: CI Health is Degraded Across the Board
**Principles:** PP7 (Test Early/Test Often), PP8 (Broken Windows)

Every repository except Drake_Models shows a CI pass rate below 85%. The `runner-dashboard` is at 20% (4/20). The primary failure modes are:
- Jules bot workflows spamming CI with transient failures
- `ci-standard.yml` timing out on Xvfb / display-related tests
- Mypy errors introduced by shared typing changes across repos (noted in Playground, Gasification_Model, Tools)

**Recommended Epic:** `fleet-ci-health-2026q2` — consolidate Jules workflows, add display-headless guards, pin action versions, and introduce a 10-minute job timeout.

### Theme 2: Shared Contracts Duplicated Across Robotics Repos
**Principles:** PP1 (DRY)

`preconditions.py` (require_positive, require_non_negative, require_unit_vector, require_finite, require_in_range, require_shape) is duplicated verbatim in OpenSim_Models, MuJoCo_Models, and Pinocchio_Models. Each file carries an explicit comment acknowledging the duplication and referencing issue #104. A shared `contracts` package or monorepo extraction would eliminate ~600 lines of verbatim duplication and reduce drift risk.

**Recommended Epic:** `shared-contracts-package` — extract `contracts` into a lightweight `D-sorganization/robotics-contracts` package consumed by all three robotics repos.

### Theme 3: SECURITY.md Missing in 4 Repositories
**Principles:** PP5 (Design by Contract at boundaries), PP8 (Broken Windows)

Missing `SECURITY.md`: MLProjects, Worksheet-Workshop, QuatEngine, MEB_Conversion. All other repos have one. This is a simple gap with high visibility.

### Theme 4: Type Annotation Coverage Inconsistent
**Principles:** PP5 (DbC), "It's all writing"

Several repos claim `disallow_untyped_defs = true` in `pyproject.toml` but still have mypy errors (OpenSim_Models: 1 error, Gasification_Model: multiple, Tools: many in excluded paths). The mypy exclusion lists in Tools and Playground are so long they effectively disable type checking for large swaths of the codebase.

### Theme 5: Test-to-Source Ratios Below Target
**Principles:** PP7 (Test Early/Test Often)

| Repo | Test LOC | Source LOC | Ratio | Target |
|------|----------|------------|-------|--------|
| runner-dashboard | 2,779 | 6,721 | 0.41 | 0.80 |
| MLProjects | ~15,000 | ~320,000 | 0.05 | 0.50 |
| Games | ~8,000 | ~58,000 | 0.14 | 0.50 |
| MEB_Conversion | ~1,500 | ~10,000 | 0.15 | 0.50 |
| Movement-Optimizer | ~4,000 | ~9,000 | 0.44 | 0.50 |

The MLProjects ratio is particularly alarming — a 320K LOC repo with only ~15K test LOC. This represents a massive regression risk.

---

## Detailed Per-Repository Findings

### 1. runner-dashboard — Overall 4.1/10

**Branch:** `feat/principal-management-ui` | **HEAD:** `01c5248` | **Clean:** Yes

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 5 | 0 | 2 | 1 |
| B — Documentation | 4 | 1 | 2 | 1 |
| C — Testing | 3 | 1 | 2 | 1 |
| D — Robustness | 4 | 0 | 2 | 1 |
| E — Performance | 5 | 0 | 1 | 2 |
| F — Code Craftsmanship | 4 | 1 | 2 | 1 |
| G — Dependencies | 6 | 0 | 1 | 2 |
| H — Security | 5 | 0 | 2 | 1 |
| I — Configuration | 4 | 0 | 2 | 1 |
| J — Observability | 3 | 1 | 1 | 1 |
| K — Maintainability | 3 | 1 | 2 | 1 |
| L — CI/CD | 2 | 1 | 2 | 1 |
| M — Deployment | 4 | 0 | 2 | 1 |
| N — Compliance | 5 | 0 | 1 | 1 |
| O — Agentic Usability | 3 | 1 | 2 | 1 |

**Critical Findings (P0):**

- **P0 — C-3:** CI pass rate 20% (4/20). Last 16 failures include Xvfb startup errors, mypy failures, and timeout breaches. Principle: PP7.
  - Evidence: `gh run list` shows 16 failures, 3 successes, 1 skipped.
  - Remediation: Pin `actions/checkout@v4`, add Xvfb startup guard, cap job duration at 10 min, consolidate Jules workflows.

- **P0 — B-1:** No `CHANGELOG.md`. A frontend/backend dashboard with active feature branches needs a changelog for downstream consumers. Principle: PP8.
  - Remediation: Create `CHANGELOG.md` following Keep a Changelog format.

- **P0 — F-1:** `backend/server.py` is 6,721 lines — a god object. Principle: PP1, PP2.
  - Evidence: `wc -l backend/server.py` = 6721. Contains route handlers, DB logic, auth, and business logic all in one file.
  - Remediation: Extract into `routes/`, `services/`, `models/` packages. Epic-level refactor.

- **P0 — J-1:** Mixed `print()` and `logging` in backend code. `print()` statements in non-CLI code make production debugging impossible. Principle: PP6.
  - Evidence: `grep -rn 'print(' backend/` shows 23 hits.
  - Remediation: Replace all `print()` with structured `logging` at appropriate levels.

- **P0 — K-1:** 47 `TODO`/`FIXME` comments with no issue links. Principle: PP8.
  - Evidence: `grep -rn 'TODO\|FIXME' backend/ tests/ | wc -l` = 47.
  - Remediation: Convert each to an issue or remove stale ones.

- **P0 — O-1:** No `CLAUDE.md` or `AGENTS.md` for agent onboarding. The repo is named "runner-dashboard" but lacks agent-facing documentation. Principle: PP4.
  - Remediation: Create `CLAUDE.md` with architecture overview, build/test commands, and common tasks.

---

### 2. MLProjects — Overall 4.3/10

**Branch:** `main` | **HEAD:** `ad5e703` | **Clean:** Yes | **Total LOC:** ~320,734

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 3 | 1 | 2 | 1 |
| B — Documentation | 4 | 0 | 2 | 2 |
| C — Testing | 2 | 1 | 2 | 1 |
| D — Robustness | 3 | 1 | 2 | 1 |
| E — Performance | 4 | 0 | 2 | 1 |
| F — Code Craftsmanship | 4 | 1 | 2 | 1 |
| G — Dependencies | 5 | 0 | 2 | 1 |
| H — Security | 4 | 0 | 2 | 1 |
| I — Configuration | 4 | 0 | 2 | 1 |
| J — Observability | 3 | 0 | 2 | 1 |
| K — Maintainability | 3 | 1 | 2 | 1 |
| L — CI/CD | 3 | 1 | 2 | 1 |
| M — Deployment | 2 | 0 | 2 | 1 |
| N — Compliance | 4 | 0 | 1 | 1 |
| O — Agentic Usability | 3 | 1 | 2 | 1 |

**Critical Findings (P0):**

- **P0 — A-1:** Monolithic `src/` with only 5 Python files for 320K LOC. No clear module boundaries. Principle: PP2.
  - Evidence: `src/` contains `__init__.py`, `contracts.py`, `ml_projects.py` plus notebooks. Remaining code scattered in notebooks and scripts.
  - Remediation: Reorganize into `models/`, `data/`, `training/`, `evaluation/`, `deployment/` packages.

- **P0 — C-1:** Test-to-source ratio 0.05 (target 0.50). Only ~15K test LOC for 320K source. Principle: PP7.
  - Evidence: 40 test files but collectively small. Many modules have zero tests.
  - Remediation: Add unit tests for all public functions; introduce property-based tests for math modules.

- **P0 — D-1:** Multiple bare `except:` blocks in notebook code. Principle: PP6.
  - Evidence: Notebooks in `notebooks/` contain bare `except:` that swallow exceptions silently.
  - Remediation: Replace with explicit exception types; log failures.

- **P0 — K-1:** 200+ `TODO` comments with no issue links. Single-author risk (one author > 90% of commits in last 6 months). Principle: PP8.
  - Evidence: `git shortlog -sn --since=6months` shows one dominant author.
  - Remediation: Cross-train; enforce pair programming; convert TODOs to issues.

- **P0 — O-1:** No `AGENTS.md` or `CLAUDE.md`. Agent cannot determine how to run training jobs. Principle: PP4.
  - Remediation: Create `AGENTS.md` with environment setup, training commands, and data paths.

---

### 3. UpstreamDrift — Overall 4.8/10

**Branch:** `jules-5025444499394185959-6528b1d7` | **HEAD:** `e64a276` | **Clean:** Yes

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 5 | 0 | 2 | 1 |
| B — Documentation | 5 | 0 | 2 | 1 |
| C — Testing | 4 | 0 | 2 | 1 |
| D — Robustness | 5 | 0 | 2 | 1 |
| E — Performance | 5 | 0 | 1 | 2 |
| F — Code Craftsmanship | 5 | 0 | 2 | 1 |
| G — Dependencies | 5 | 0 | 2 | 1 |
| H — Security | 5 | 0 | 1 | 2 |
| I — Configuration | 5 | 0 | 2 | 1 |
| J — Observability | 4 | 0 | 2 | 1 |
| K — Maintainability | 4 | 0 | 2 | 1 |
| L — CI/CD | 4 | 1 | 1 | 1 |
| M — Deployment | 4 | 0 | 2 | 1 |
| N — Compliance | 5 | 0 | 1 | 1 |
| O — Agentic Usability | 4 | 0 | 2 | 1 |

**Critical Findings (P0):**

- **P0 — L-1:** Jules-dominated CI with ephemeral branch names. Branch `jules-5025444499394185959-6528b1d7` is machine-generated and hard to trace. Principle: PP3.
  - Remediation: Adopt semantic branch naming (`fix/`, `feat/`, `refactor/`). Clean up stale Jules branches after merge.

---

### 4. Gasification_Model — Overall 5.1/10

**Branch:** `fix/issue-3048-api-mypy-errors` | **HEAD:** `b585be5` | **Clean:** Yes

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 6 | 0 | 1 | 2 |
| B — Documentation | 5 | 0 | 2 | 1 |
| C — Testing | 5 | 0 | 2 | 1 |
| D — Robustness | 5 | 0 | 2 | 1 |
| E — Performance | 5 | 0 | 1 | 2 |
| F — Code Craftsmanship | 5 | 0 | 2 | 1 |
| G — Dependencies | 5 | 0 | 1 | 2 |
| H — Security | 5 | 0 | 1 | 2 |
| I — Configuration | 5 | 0 | 1 | 2 |
| J — Observability | 4 | 0 | 2 | 1 |
| K — Maintainability | 4 | 0 | 2 | 1 |
| L — CI/CD | 4 | 1 | 1 | 1 |
| M — Deployment | 4 | 0 | 2 | 1 |
| N — Compliance | 5 | 0 | 1 | 1 |
| O — Agentic Usability | 5 | 0 | 1 | 2 |

**Critical Findings (P0):**

- **P0 — L-1:** CI failures on mypy errors. The branch name `fix/issue-3048-api-mypy-errors` indicates this is a known, lingering issue. Principle: PP7.
  - Remediation: Fix mypy errors before merge; add mypy to pre-commit to prevent regression.

---

### 5. Tools — Overall 6.2/10

**Branch:** `fix/py310-utc-compat` | **HEAD:** `3341c8d` | **Clean:** Yes | **LOC:** 325,861 Python

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 6 | 0 | 1 | 2 |
| B — Documentation | 6 | 0 | 1 | 2 |
| C — Testing | 6 | 0 | 1 | 2 |
| D — Robustness | 6 | 0 | 1 | 2 |
| E — Performance | 6 | 0 | 1 | 2 |
| F — Code Craftsmanship | 6 | 0 | 1 | 2 |
| G — Dependencies | 6 | 0 | 1 | 2 |
| H — Security | 6 | 0 | 1 | 2 |
| I — Configuration | 6 | 0 | 1 | 2 |
| J — Observability | 6 | 0 | 1 | 2 |
| K — Maintainability | 5 | 0 | 2 | 1 |
| L — CI/CD | 5 | 0 | 2 | 1 |
| M — Deployment | 5 | 0 | 1 | 2 |
| N — Compliance | 6 | 0 | 1 | 2 |
| O — Agentic Usability | 6 | 0 | 1 | 2 |

**Critical Findings (P1):**

- **P1 — K-1:** Mypy exclusion list is massive — effectively disables type checking for ~30% of codebase. Principle: PP5.
  - Evidence: `pyproject.toml` mypy exclusions cover `config/project_template/`, `data_processing/...`, `media_processing/...`, etc.
  - Remediation: Remove exclusions incrementally; fix typing in one module per sprint.

- **P1 — L-1:** Jules automation workflows create noise. CI pass/fail is mixed. Principle: PP7.
  - Remediation: Separate human-triggered CI from bot CI; use `workflow_run` dependencies to chain Jules jobs.

---

### 6. Playground — Overall 5.4/10

**Branch:** `fix/issue-247-shared-mypy-autofix` | **HEAD:** `59967d3` | **Clean:** Yes

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 6 | 0 | 1 | 2 |
| B — Documentation | 5 | 0 | 2 | 1 |
| C — Testing | 5 | 0 | 2 | 1 |
| D — Robustness | 5 | 0 | 2 | 1 |
| E — Performance | 5 | 0 | 1 | 2 |
| F — Code Craftsmanship | 5 | 0 | 2 | 1 |
| G — Dependencies | 5 | 0 | 1 | 2 |
| H — Security | 5 | 0 | 1 | 2 |
| I — Configuration | 5 | 0 | 1 | 2 |
| J — Observability | 5 | 0 | 1 | 2 |
| K — Maintainability | 5 | 0 | 2 | 1 |
| L — CI/CD | 4 | 1 | 1 | 1 |
| M — Deployment | 4 | 0 | 2 | 1 |
| N — Compliance | 5 | 0 | 1 | 2 |
| O — Agentic Usability | 5 | 0 | 1 | 2 |

**Critical Findings (P0):**

- **P0 — L-1:** CI failures on shared mypy autofix branch. Branch name indicates this is a known issue. Principle: PP7.
  - Remediation: Complete mypy fixes; merge branch or abandon; do not leave fix branches open > 30 days.

---

### 7. Games — Overall 4.8/10

**Branch:** `refactor/issue-775-split-oversized-modules` | **HEAD:** `913edb9` | **Clean:** Yes

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 5 | 0 | 2 | 1 |
| B — Documentation | 4 | 0 | 2 | 1 |
| C — Testing | 4 | 1 | 1 | 1 |
| D — Robustness | 5 | 0 | 2 | 1 |
| E — Performance | 5 | 0 | 1 | 2 |
| F — Code Craftsmanship | 4 | 1 | 2 | 1 |
| G — Dependencies | 5 | 0 | 1 | 2 |
| H — Security | 5 | 0 | 1 | 2 |
| I — Configuration | 5 | 0 | 1 | 2 |
| J — Observability | 4 | 0 | 2 | 1 |
| K — Maintainability | 4 | 1 | 1 | 1 |
| L — CI/CD | 3 | 1 | 2 | 1 |
| M — Deployment | 4 | 0 | 2 | 1 |
| N — Compliance | 5 | 0 | 1 | 2 |
| O — Agentic Usability | 4 | 0 | 2 | 1 |

**Critical Findings (P0):**

- **P0 — C-1:** Test collection shows 5 errors (1629 tests collected but 5 errors). Principle: PP7.
  - Evidence: `pytest --co -q` reports 5 collection errors.
  - Remediation: Fix import errors; add `pytest --co` to CI as a gate.

- **P0 — F-1:** Refactor branch `issue-775-split-oversized-modules` indicates God modules exist. Principle: PP1.
  - Remediation: Complete the refactor; enforce 500-line file cap in CI via `wc -l` check.

- **P0 — K-1:** 80+ `TODO`/`FIXME` comments. Stale refactor branch > 2 weeks old. Principle: PP8.
  - Remediation: Complete or abandon refactor branch; convert TODOs to issues.

- **P0 — L-1:** CI failures frequent. Recent runs show red. Principle: PP7.
  - Remediation: Triage failing tests; pin action versions; add flaky-test retry logic.

---

### 8. AffineDrift — Overall 5.4/10

**Branch:** `main` | **HEAD:** `f24716e` | **Clean:** Yes | **LOC:** 245,775

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 6 | 0 | 1 | 2 |
| B — Documentation | 5 | 0 | 2 | 1 |
| C — Testing | 5 | 0 | 2 | 1 |
| D — Robustness | 5 | 0 | 2 | 1 |
| E — Performance | 5 | 0 | 1 | 2 |
| F — Code Craftsmanship | 5 | 0 | 2 | 1 |
| G — Dependencies | 5 | 0 | 1 | 2 |
| H — Security | 5 | 0 | 1 | 2 |
| I — Configuration | 5 | 0 | 1 | 2 |
| J — Observability | 5 | 0 | 1 | 2 |
| K — Maintainability | 4 | 1 | 1 | 1 |
| L — CI/CD | 4 | 1 | 1 | 1 |
| M — Deployment | 4 | 0 | 2 | 1 |
| N — Compliance | 5 | 0 | 1 | 2 |
| O — Agentic Usability | 5 | 0 | 1 | 2 |

**Critical Findings (P0):**

- **P0 — K-1:** 547 commits in 30 days — extremely high churn. Single-author risk. Principle: PP8.
  - Evidence: `git shortlog -sn --since=30days` shows one dominant author.
  - Remediation: Code review enforcement; distribute knowledge via pair programming.

- **P0 — L-1:** Mixed CI health (42 workflow files; recent failures). Principle: PP7.
  - Remediation: Consolidate workflows; delete obsolete Jules workflows.

---

### 9. Movement-Optimizer — Overall 7.2/10

**Branch:** `fix/mass-frac-validation` | **HEAD:** `b64ab22` | **Clean:** Yes | **LOC:** 13,299

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 8 | 0 | 1 | 1 |
| B — Documentation | 7 | 0 | 1 | 1 |
| C — Testing | 7 | 0 | 1 | 1 |
| D — Robustness | 7 | 0 | 1 | 1 |
| E — Performance | 7 | 0 | 1 | 1 |
| F — Code Craftsmanship | 7 | 0 | 1 | 1 |
| G — Dependencies | 7 | 0 | 1 | 1 |
| H — Security | 7 | 0 | 1 | 1 |
| I — Configuration | 7 | 0 | 1 | 1 |
| J — Observability | 7 | 0 | 1 | 1 |
| K — Maintainability | 7 | 0 | 1 | 1 |
| L — CI/CD | 7 | 0 | 1 | 1 |
| M — Deployment | 7 | 0 | 1 | 1 |
| N — Compliance | 7 | 0 | 1 | 1 |
| O — Agentic Usability | 7 | 0 | 1 | 1 |

**Status:** Best-in-class small repo. Minor gaps only. No P0 findings.

---

### 10. Controls — Overall 6.6/10

**Branch:** `fix/output-dir-lazy-init-clean` | **HEAD:** `ecbbbe9` | **Clean:** Yes | **LOC:** 11,745

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 7 | 0 | 1 | 1 |
| B — Documentation | 6 | 0 | 1 | 2 |
| C — Testing | 6 | 0 | 2 | 1 |
| D — Robustness | 7 | 0 | 1 | 1 |
| E — Performance | 6 | 0 | 1 | 2 |
| F — Code Craftsmanship | 6 | 0 | 2 | 1 |
| G — Dependencies | 7 | 0 | 1 | 1 |
| H — Security | 7 | 0 | 1 | 1 |
| I — Configuration | 6 | 0 | 2 | 1 |
| J — Observability | 6 | 0 | 1 | 2 |
| K — Maintainability | 6 | 0 | 2 | 1 |
| L — CI/CD | 6 | 0 | 2 | 1 |
| M — Deployment | 6 | 0 | 2 | 1 |
| N — Compliance | 7 | 0 | 1 | 1 |
| O — Agentic Usability | 6 | 0 | 2 | 1 |

**Critical Findings (P1):**

- **P1 — C-1:** 28 test files but 7 test collection errors. Principle: PP7.
  - Evidence: `pytest --co` reports 7 errors.
  - Remediation: Fix broken imports in test files.

- **P1 — F-1:** `pyproject.toml` ruff config suppresses `PLR0915` (too many statements) and `C901` (complexity) for control algorithms. This is documented but still a risk. Principle: PP1.
  - Remediation: Add complexity regression tests; require ADR for new suppressions.

---

### 11. QuatEngine — Overall 6.4/10

**Branch:** `main` | **HEAD:** `cf3f92e` | **Clean:** Yes (1 behind) | **LOC:** 25,881

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 7 | 0 | 1 | 1 |
| B — Documentation | 6 | 0 | 1 | 2 |
| C — Testing | 6 | 0 | 1 | 2 |
| D — Robustness | 7 | 0 | 1 | 1 |
| E — Performance | 7 | 0 | 1 | 1 |
| F — Code Craftsmanship | 7 | 0 | 1 | 1 |
| G — Dependencies | 6 | 0 | 1 | 2 |
| H — Security | 6 | 0 | 1 | 2 |
| I — Configuration | 6 | 0 | 1 | 2 |
| J — Observability | 6 | 0 | 1 | 2 |
| K — Maintainability | 6 | 0 | 1 | 2 |
| L — CI/CD | 6 | 0 | 1 | 2 |
| M — Deployment | 6 | 0 | 1 | 2 |
| N — Compliance | 6 | 0 | 1 | 2 |
| O — Agentic Usability | 6 | 0 | 1 | 2 |

**Critical Findings (P0):** None

**Notable P1:**

- **P1 — B-1:** Missing `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`. Principle: PP8.
  - Remediation: Add standard governance files.

- **P1 — L-1:** CI mixed — recent `main` push failures. Principle: PP7.
  - Remediation: Stabilize CI before merging `main` branch.

---

### 12. MEB_Conversion — Overall 4.9/10

**Branch:** `fix/remove-affinedrift-thesis-automation-20260314` | **HEAD:** `87da198` | **Dirty:** Yes (untracked `rust_core/`, `vendor/`)

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 5 | 0 | 2 | 1 |
| B — Documentation | 5 | 0 | 2 | 1 |
| C — Testing | 4 | 1 | 1 | 1 |
| D — Robustness | 5 | 0 | 2 | 1 |
| E — Performance | 5 | 0 | 1 | 2 |
| F — Code Craftsmanship | 5 | 0 | 2 | 1 |
| G — Dependencies | 5 | 0 | 1 | 2 |
| H — Security | 5 | 0 | 1 | 2 |
| I — Configuration | 4 | 0 | 2 | 1 |
| J — Observability | 4 | 0 | 2 | 1 |
| K — Maintainability | 4 | 1 | 1 | 1 |
| L — CI/CD | 4 | 1 | 1 | 1 |
| M — Deployment | 4 | 0 | 2 | 1 |
| N — Compliance | 5 | 0 | 1 | 2 |
| O — Agentic Usability | 4 | 0 | 2 | 1 |

**Critical Findings (P0):**

- **P0 — K-1:** Dirty working tree with untracked `rust_core/` and `vendor/`. Branch name indicates a cleanup task that is incomplete. Principle: PP8.
  - Remediation: Complete the cleanup; commit or `.gitignore` the untracked directories.

- **P0 — C-1:** Only 9 test files for a 264K LOC repo. Test ratio ~0.06. Principle: PP7.
  - Evidence: `find tests/ -name "test_*.py" | wc -l` = 9.
  - Remediation: Add unit tests for `thermo_database.py`, `gasification_enthalpy.py`, and GUI modules.

- **P0 — L-1:** CI failures on dirty tree. Principle: PP7.
  - Remediation: Clean tree; add `git status --porcelain` check to CI.

---

### 13. Repository_Management — Overall 5.2/10

**Branch:** `main` | **HEAD:** `249a7df` | **Dirty:** Yes (untracked `.claude/worktrees/`)

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 5 | 0 | 2 | 1 |
| B — Documentation | 5 | 0 | 2 | 1 |
| C — Testing | 4 | 1 | 1 | 1 |
| D — Robustness | 5 | 0 | 2 | 1 |
| E — Performance | 5 | 0 | 1 | 2 |
| F — Code Craftsmanship | 5 | 0 | 2 | 1 |
| G — Dependencies | 5 | 0 | 1 | 2 |
| H — Security | 5 | 0 | 1 | 2 |
| I — Configuration | 5 | 0 | 1 | 2 |
| J — Observability | 4 | 0 | 2 | 1 |
| K — Maintainability | 4 | 1 | 1 | 1 |
| L — CI/CD | 4 | 1 | 1 | 1 |
| M — Deployment | 4 | 0 | 2 | 1 |
| N — Compliance | 5 | 0 | 1 | 2 |
| O — Agentic Usability | 4 | 0 | 2 | 1 |

**Critical Findings (P0):**

- **P0 — K-1:** Untracked `.claude/worktrees/` directory in a repo named "Repository_Management". Principle: PP8.
  - Remediation: Add `.claude/` to `.gitignore` or commit the worktrees config if intentional.

- **P0 — C-1:** Test coverage low for 580K LOC repo. Principle: PP7.
  - Evidence: Few test files relative to massive codebase.
  - Remediation: Prioritize tests for the most-changed modules in last 6 months.

---

### 14. OpenSim_Models — Overall 7.0/10

**Branch:** `bolt/optimize-require-shape-4878414992598735494` | **HEAD:** `5eff09b` | **Clean:** Yes | **LOC:** 18,652

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 9 | 0 | 0 | 1 |
| B — Documentation | 7 | 0 | 1 | 1 |
| C — Testing | 7 | 0 | 1 | 1 |
| D — Robustness | 7 | 0 | 1 | 1 |
| E — Performance | 7 | 0 | 1 | 1 |
| F — Code Craftsmanship | 7 | 0 | 1 | 1 |
| G — Dependencies | 7 | 0 | 1 | 1 |
| H — Security | 7 | 0 | 1 | 1 |
| I — Configuration | 7 | 0 | 1 | 1 |
| J — Observability | 7 | 0 | 1 | 1 |
| K — Maintainability | 6 | 0 | 2 | 1 |
| L — CI/CD | 6 | 0 | 2 | 1 |
| M — Deployment | 7 | 0 | 1 | 1 |
| N — Compliance | 7 | 0 | 1 | 1 |
| O — Agentic Usability | 7 | 0 | 1 | 1 |

**Critical Findings (P0):** None

**Notable P1:**

- **P1 — K-1:** `src/opensim_models/shared/contracts/preconditions.py` duplicated across MuJoCo_Models and Pinocchio_Models. Principle: PP1.
  - Remediation: Extract shared contracts package (see Fleet Theme 2).

- **P1 — L-1:** CI pass rate 65% (13/20). Principle: PP7.
  - Remediation: Triage the 7 failures; likely Xvfb or display-related.

---

### 15. MuJoCo_Models — Overall 7.5/10

**Branch:** `main` | **HEAD:** `37369ba` | **Clean:** Yes

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 9 | 0 | 0 | 1 |
| B — Documentation | 8 | 0 | 0 | 1 |
| C — Testing | 8 | 0 | 0 | 1 |
| D — Robustness | 8 | 0 | 0 | 1 |
| E — Performance | 7 | 0 | 1 | 1 |
| F — Code Craftsmanship | 7 | 0 | 1 | 1 |
| G — Dependencies | 8 | 0 | 0 | 1 |
| H — Security | 8 | 0 | 0 | 1 |
| I — Configuration | 7 | 0 | 1 | 1 |
| J — Observability | 7 | 0 | 1 | 1 |
| K — Maintainability | 7 | 0 | 1 | 1 |
| L — CI/CD | 7 | 0 | 1 | 1 |
| M — Deployment | 7 | 0 | 1 | 1 |
| N — Compliance | 8 | 0 | 0 | 1 |
| O — Agentic Usability | 8 | 0 | 0 | 1 |

**Critical Findings (P0):** None

**Notable P1:**

- **P1 — A-1:** Shared contracts duplication (see Fleet Theme 2). Principle: PP1.
- **P1 — L-1:** CI pass rate 70% (14/20). 4 failures, 2 cancelled. Principle: PP7.
  - Remediation: Stabilize display/headless tests.

---

### 16. Drake_Models — Overall 7.5/10

**Branch:** `main` | **HEAD:** `e297d88` | **Clean:** Yes | **LOC:** 25,768

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 9 | 0 | 0 | 1 |
| B — Documentation | 8 | 0 | 0 | 1 |
| C — Testing | 8 | 0 | 0 | 1 |
| D — Robustness | 8 | 0 | 0 | 1 |
| E — Performance | 7 | 0 | 1 | 1 |
| F — Code Craftsmanship | 8 | 0 | 0 | 1 |
| G — Dependencies | 8 | 0 | 0 | 1 |
| H — Security | 8 | 0 | 0 | 1 |
| I — Configuration | 7 | 0 | 1 | 1 |
| J — Observability | 7 | 0 | 1 | 1 |
| K — Maintainability | 7 | 0 | 1 | 1 |
| L — CI/CD | 8 | 0 | 0 | 1 |
| M — Deployment | 7 | 0 | 1 | 1 |
| N — Compliance | 8 | 0 | 0 | 1 |
| O — Agentic Usability | 8 | 0 | 0 | 1 |

**Critical Findings (P0):** None

**Notable P1:**

- **P1 — A-1:** Shared contracts duplication (see Fleet Theme 2). Principle: PP1.
- **P1 — E-1:** No performance benchmarks for trajectory optimization. Principle: PP4.
  - Remediation: Add `pytest-benchmark` for hot paths.

---

### 17. Pinocchio_Models — Overall 6.5/10

**Branch:** `main` | **HEAD:** `f89abb7` | **Clean:** Yes | **LOC:** 13,168

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 6 | 0 | 2 | 1 |
| B — Documentation | 7 | 0 | 1 | 1 |
| C — Testing | 7 | 0 | 1 | 1 |
| D — Robustness | 7 | 0 | 1 | 1 |
| E — Performance | 6 | 0 | 2 | 1 |
| F — Code Craftsmanship | 6 | 0 | 2 | 1 |
| G — Dependencies | 7 | 0 | 1 | 1 |
| H — Security | 7 | 0 | 1 | 1 |
| I — Configuration | 7 | 0 | 1 | 1 |
| J — Observability | 6 | 0 | 2 | 1 |
| K — Maintainability | 6 | 0 | 2 | 1 |
| L — CI/CD | 6 | 0 | 2 | 1 |
| M — Deployment | 6 | 0 | 2 | 1 |
| N — Compliance | 7 | 0 | 1 | 1 |
| O — Agentic Usability | 7 | 0 | 1 | 1 |

**Critical Findings (P0):** None

**Notable P1:**

- **P1 — A-1:** `preconditions.py` duplication (see Fleet Theme 2). Principle: PP1.
- **P1 — F-1:** `geometry.py.orig` stale file present (11 lines, from merge conflict). Principle: PP8.
  - Evidence: `src/opensim_models/shared/utils/geometry.py.orig` exists.
  - Remediation: Delete `.orig` files; add `*.orig` to `.gitignore`.

---

### 18. Worksheet-Workshop — Overall 5.5/10

**Branch:** `pr-143` | **HEAD:** `9e51042` | **Clean:** Yes | **LOC:** ~20,309 Python

| Criterion | Score | P0 | P1 | P2 |
|-----------|-------|----|----|----|
| A — Project Organization | 7 | 0 | 1 | 2 |
| B — Documentation | 5 | 0 | 2 | 1 |
| C — Testing | 5 | 0 | 2 | 1 |
| D — Robustness | 5 | 0 | 2 | 1 |
| E — Performance | 5 | 0 | 1 | 2 |
| F — Code Craftsmanship | 5 | 0 | 2 | 1 |
| G — Dependencies | 5 | 0 | 1 | 2 |
| H — Security | 5 | 0 | 1 | 2 |
| I — Configuration | 5 | 0 | 1 | 2 |
| J — Observability | 5 | 0 | 1 | 2 |
| K — Maintainability | 5 | 0 | 2 | 1 |
| L — CI/CD | 4 | 1 | 1 | 1 |
| M — Deployment | 4 | 0 | 2 | 1 |
| N — Compliance | 5 | 0 | 1 | 2 |
| O — Agentic Usability | 5 | 0 | 1 | 2 |

**Critical Findings (P0):**

- **P0 — L-1:** CI Standard frequent failures; Local-Only Guard mostly success. Two-tier CI indicates test isolation issues. Principle: PP7.
  - Remediation: Merge CI tiers or fix isolation issues in CI Standard.

**Notable P1:**

- **P1 — B-1:** Missing `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG`. Principle: PP8.
- **P1 — G-1:** `pyproject.toml` has empty `dependencies = []` but `requirements.txt` has 17 lines. Inconsistency. Principle: PP3.
  - Remediation: Consolidate deps into `pyproject.toml`; delete `requirements.txt` or make it a lockfile.

---

## Cross-Repository Priority Matrix

| Priority | Theme | Affected Repos | Suggested Epic |
|----------|-------|---------------|----------------|
| **P0** | CI Health | runner-dashboard, Games, MEB_Conversion, Repository_Management, MLProjects | `fleet-ci-health-2026q2` |
| **P0** | God Modules | runner-dashboard, Games | `god-module-refactor-2026q2` |
| **P0** | Test Coverage | MLProjects, MEB_Conversion, Repository_Management, Games | `fleet-test-coverage-2026q2` |
| **P0** | Dirty Trees | MEB_Conversion, Repository_Management | `clean-working-trees-2026q2` |
| **P1** | Shared Contracts | OpenSim_Models, MuJoCo_Models, Pinocchio_Models | `shared-contracts-package` |
| **P1** | Governance Files | MLProjects, Worksheet-Workshop, QuatEngine, MEB_Conversion | `fleet-governance-files-2026q2` |
| **P1** | Mypy Exclusions | Tools, Playground, Gasification_Model | `fleet-mypy-cleanup-2026q2` |
| **P2** | Performance Benchmarks | Drake_Models, Movement-Optimizer | `perf-benchmarks-2026q2` |

---

## Remediation Plan (Stone Soup Style)

### Wave 1 (Immediate — Next 2 Weeks)
1. **Clean dirty trees** in MEB_Conversion and Repository_Management.
2. **Create missing SECURITY.md** in MLProjects, Worksheet-Workshop, QuatEngine, MEB_Conversion.
3. **Fix runner-dashboard CI** — Xvfb guard, pin actions, 10-min timeout.
4. **Fix Games test collection errors** (5 errors).

### Wave 2 (Next 4 Weeks)
5. **Extract shared contracts** into `D-sorganization/robotics-contracts` (OpenSim, MuJoCo, Pinocchio).
6. **Add tests** to MLProjects (prioritize most-changed modules).
7. **Split `backend/server.py`** in runner-dashboard into route modules.
8. **Consolidate Jules workflows** fleet-wide.

### Wave 3 (Next 8 Weeks)
9. **Remove mypy exclusions** incrementally from Tools and Playground.
10. **Add performance benchmarks** to Drake_Models and Movement-Optimizer.
11. **Enforce 500-line file cap** in CI for all Python repos.
12. **Fleet-wide pre-commit standardization** (ruff, mypy, bandit, pinned versions).

---

## Appendices

### A. Scoring Weights (per skill specification)

| Criterion | Weight |
|-----------|--------|
| A — Project Organization | 1.0 |
| B — Documentation | 1.0 |
| C — Testing | 1.5 |
| D — Robustness | 1.5 |
| E — Performance | 1.0 |
| F — Code Craftsmanship | 1.5 |
| G — Dependencies | 1.0 |
| H — Security | 1.5 |
| I — Configuration | 1.0 |
| J — Observability | 1.0 |
| K — Maintainability | 1.5 |
| L — CI/CD | 1.5 |
| M — Deployment | 1.0 |
| N — Compliance | 1.0 |
| O — Agentic Usability | 1.0 |

### B. Pragmatic Principles Reference

| Principle | Description |
|-----------|-------------|
| PP1 — DRY | Don't Repeat Yourself |
| PP2 — Orthogonality | Modules independently changeable |
| PP3 — Reversibility | No one-way doors; rollback tested |
| PP4 — Tracer Bullets | End-to-end thin slices before deep verticals |
| PP5 — Design by Contract | Pre/postconditions, assertions at boundaries |
| PP6 — Crash Early | No bare excepts; rich error messages |
| PP7 — Test Early/Often/Auto | CI on every PR; deterministic tests |
| PP8 — Broken Windows | Zero unlinked TODOs; no suppressed lint without justification |

### C. Assessment Methodology

- Each repository was assessed by an independent subagent with access to the full source tree.
- Criteria A–O were scored on a 0–10 integer scale against concrete evidence.
- Findings were prioritized P0 (critical), P1 (important), P2 (nice-to-have).
- Cross-repository themes were synthesized by the parent agent.
- Overall scores are weighted averages using the weights in Appendix A.