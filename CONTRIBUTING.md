# 🤝 Contributing to Clash of Clans Farming Controller

Thank you for your interest in contributing! Whether you are fixing bugs, improving the deployment heuristics, adding support for new troops/heroes, or optimizing computer vision performance, we appreciate your help.

Follow these guidelines to ensure smooth collaboration and high code quality.

---

## 🛠️ Getting Started

### 1. Fork & Clone
1. Fork the repository on GitHub by clicking the **Fork** button in the upper-right corner.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/coc-farming-controller.git
   cd coc-farming-controller
   ```
3. Set the upstream remote to stay synced with the main project:
   ```bash
   git remote add upstream https://github.com/<original-owner>/coc-farming-controller.git
   ```

### 2. Set Up Your Python Environment
1. Recommended Python version: **3.10 - 3.14 (64-bit)**.
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

---

## 🌿 Branching Strategy

Always create a dedicated feature branch from `main` for your work. Never commit directly to `main`.

```bash
git checkout -b feature/my-new-feature
# or for bugfixes:
git checkout -b fix/issue-description
```

### Branch Naming Conventions:
- `feature/<short-description>`: New features (e.g. `feature/super-troop-support`)
- `fix/<short-description>`: Bug fixes (e.g. `fix/ribbon-deselection-timing`)
- `perf/<short-description>`: Performance optimizations (e.g. `perf/faster-ocr-pipeline`)
- `docs/<short-description>`: Documentation improvements (e.g. `docs/update-operator-guide`)

---

## 🧪 Testing Guidelines

Before opening a Pull Request, **all 39 tests must pass**.

1. Run the full test suite:
   ```bash
   python -m pytest tests/ -v
   ```
2. If you added new features or altered logic (e.g. in `DeploymentPlanner`, `UIStateDetector`, or `StateMachine`), **add corresponding unit tests** in `tests/`.
3. Never commit absolute local file paths (e.g. `C:\Users\username\...`). Always use relative paths:
   ```python
   import os
   img_path = os.path.join(os.path.dirname(__file__), "..", "assets", "test_cases", "my_test.png")
   ```

---

## 🔒 Security & Clean Code Rules

1. **NEVER commit secrets, API keys, or `.env` files**:
   - The `.gitignore` is pre-configured to ignore `.env`, `*.db`, and `temp/*`.
   - Always verify your staged changes before committing:
     ```bash
     git status
     git diff --staged
     ```
2. **Preserve Documentation & Comments**:
   - Keep docstrings and comments intact.
   - If you modify how a state machine transition works or how coordinates are computed, update the docstrings in that module.
3. **Emulator Standard**:
   - All computer vision coordinates are normalized (`norm_x`, `norm_y` $\in [0.0, 1.0]$) relative to a standard **1920 $\times$ 1080 Landscape** canvas.
   - Do not hardcode pixel offsets without normalizing by screen resolution.

---

## 📬 Submitting a Pull Request (PR)

1. Push your branch to your GitHub fork:
   ```bash
   git push -u origin feature/my-new-feature
   ```
2. On GitHub, navigate to your fork. You will see a banner prompting you to **"Compare & pull request"**.
3. Fill out the PR template:
   - **What changed**: Brief 2-3 bullet point summary of your changes.
   - **Why**: The problem or motivation behind the change.
   - **Verification**: Output showing that `pytest tests/ -v` passed.
4. Submit the Pull Request. The maintainer will review your code, request changes if needed, or approve and merge it into `main`!

---

## ❓ Questions or Ideas?
Open an **Issue** on GitHub to discuss proposed architecture changes, report bugs with screenshot evidence, or ask questions before writing large amounts of code.
