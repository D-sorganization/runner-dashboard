# Criterion A: Project Organization & Structure

**Date:** 2026-04-26  
**Principle:** PP2 (Orthogonality), PP8 (Broken Windows)

---

## Fleet Scores

| Repo | Score | Findings |
|------|-------|----------|
| runner-dashboard | 5 | God module `backend/server.py` (6721 lines) |
| MLProjects | 3 | Monolithic src/ — 5 Python files for 320K LOC |
| UpstreamDrift | 5 | Acceptable |
| Gasification_Model | 6 | Acceptable |
| Tools | 6 | Acceptable |
| Playground | 6 | Acceptable |
| Games | 5 | God modules under refactor |
| AffineDrift | 6 | Acceptable |
| Movement-Optimizer | 8 | Good modular structure |
| Controls | 7 | Clean src/ layout |
| QuatEngine | 7 | Good C++/Python separation |
| MEB_Conversion | 5 | Mixed Python/VBA/MATLAB; no clear boundaries |
| Repository_Management | 5 | Large monolithic structure |
| OpenSim_Models | 9 | Excellent modular layout |
| MuJoCo_Models | 9 | Excellent modular layout |
| Drake_Models | 9 | Excellent modular layout |
| Pinocchio_Models | 6 | Good structure but contracts duplication |
| Worksheet-Workshop | 7 | Clean structure |

**Fleet Average (A):** 6.2 / 10

---

## P0 Findings

### A-1: MLProjects — Monolithic src/ Structure
- **Repo:** D-sorganization/MLProjects
- **Principle:** PP2 (Orthogonality)
- **Evidence:** `src/` contains only `__init__.py`, `contracts.py`, `ml_projects.py` for a 320K LOC codebase. Remaining code is scattered across notebooks and ad-hoc scripts with no package boundaries.
- **Remediation:** Reorganize into `models/`, `data/`, `training/`, `evaluation/`, `deployment/` packages. Each package should have its own `__init__.py`, tests, and README.

---

## P1 Findings

### A-2: runner-dashboard — God Module `backend/server.py`
- **Repo:** D-sorganization/runner-dashboard
- **Principle:** PP1 (DRY), PP2 (Orthogonality)
- **Evidence:** `backend/server.py` is 6,721 lines. It contains route handlers, database logic, authentication, and business logic all in one file.
- **Remediation:** Extract into `routes/`, `services/`, `models/` packages. Target: no file >500 lines.

### A-3: Games — Oversized Modules Under Refactor
- **Repo:** D-sorganization/Games
- **Principle:** PP1 (DRY)
- **Evidence:** Branch `refactor/issue-775-split-oversized-modules` has been open >2 weeks, indicating God modules exist.
- **Remediation:** Complete the refactor; enforce 500-line file cap in CI.

### A-4: Robotics Repos — Shared Contracts Duplication
- **Repos:** OpenSim_Models, MuJoCo_Models, Pinocchio_Models, Drake_Models
- **Principle:** PP1 (DRY)
- **Evidence:** `preconditions.py` (require_positive, require_non_negative, require_unit_vector, require_finite, require_in_range, require_shape) duplicated verbatim across all four robotics repos. Each file references issue #104 acknowledging the duplication.
- **Remediation:** Extract into `D-sorganization/robotics-contracts` package. See epic `shared-contracts-package`.

---

## P2 Findings

### A-5: MEB_Conversion — Mixed Language Boundaries
- **Repo:** D-sorganization/MEB_Conversion
- **Principle:** PP2 (Orthogonality)
- **Evidence:** Python GUI, VBA macros, MATLAB code, and Excel workbooks all intermixed in `src/`. No clear layer separation.
- **Remediation:** Separate into `python/`, `vba/`, `matlab/`, `workbooks/` top-level directories.

---

## Remediation Tracking

| ID | Priority | Epic | Status |
|----|----------|------|--------|
| A-1 | P0 | `mlprojects-restructure` | 🔴 Open |
| A-2 | P1 | `god-module-refactor-2026q2` | 🔴 Open |
| A-3 | P1 | `god-module-refactor-2026q2` | 🔴 Open |
| A-4 | P1 | `shared-contracts-package` | 🔴 Open |
| A-5 | P2 | `meb-conversion-cleanup` | 🔴 Open |