# Agile Branching Strategy & Workflow

Welcome to the HR Management project! To keep our codebase stable, our history clean, and our team moving quickly during Agile sprints, we strictly follow the **GitHub Flow** branching model.

This document serves as the single source of truth for how we manage branches, write code, and merge features.

---

## The Core Philosophy

1. **The `main` branch is sacred.** 
   The `main` branch represents the production-ready state of our application. It must *always* be stable, testable, and deployable. 
2. **Absolutely NO direct commits to `main`.** 
   You cannot push code directly to `main`. All changes—whether it is a massive new feature or a one-line typo fix—must be done in a separate branch and merged via a Pull Request (PR).
3. **Continuous Integration (CI) is the gatekeeper.** 
   When you open a Pull Request, our automated GitHub Actions will test your code and check your formatting. A Pull Request **cannot** be merged if the CI fails.

---

## Branch Naming Conventions

When you pick up a task from the Sprint board, you must create a new branch. The name of the branch immediately tells the rest of the team what you are working on. 

Always use one of the following prefixes:

### 1. `feature/`
**When to use:** You are building a new feature, completing a sprint task, or adding general improvements.
**Examples:**
- `feature/user-login-page`
- `feature/api-endpoints-for-hr`

### 2. `bugfix/`
**When to use:** You are fixing a non-critical bug found during development, testing, or a previous sprint.
**Examples:**
- `bugfix/sidebar-misalignment`
- `bugfix/database-connection-timeout`

### 3. `hotfix/`
**When to use:** Only use this for **critical emergencies** happening in the live production environment that need an immediate patch.
**Examples:**
- `hotfix/fix-production-crash`
- `hotfix/security-vulnerability`

---

## The Step-by-Step Developer Workflow

Follow this exact sequence for every task you take on.

### Step 1: Sync with the Golden Branch
Before you start coding, always make sure you are branching off the absolute latest version of `main`.

```bash
# Switch to the main branch
git checkout main

# Pull the latest changes from your teammates
git pull origin main
```

### Step 2: Create Your Branch
Create and switch to a new branch using the naming conventions above.

```bash
git checkout -b feature/your-feature-name
```

### Step 3: Write Code and Commit
As you work, write clear and concise commit messages. A good commit message explains *what* changed and *why*.

```bash
# Stage your changes
git add .

# Commit your changes with a clear message
git commit -m "Add responsive layout for the HR dashboard"
```

### Step 4: Push to GitHub
When you are ready to share your work or have it reviewed, push your branch to the remote repository. 

*(Note: The `-u` flag links your local branch to the remote branch on GitHub).*

```bash
git push -u origin feature/your-feature-name
```

### Step 5: Open a Pull Request (PR)
1. Go to the project page on GitHub.
2. You will see a green button suggesting you "Compare & pull request" for your recently pushed branch. Click it.
3. Add a clear title and description explaining what your code does.
4. Submit the Pull Request.

### Step 6: Pass the CI and Review
Once your PR is open, two things happen:
- **Automated Checks:** Our CI pipeline will automatically run linters (`flake8`, `black`, `oxlint`) and automated tests. You must wait for the green checkmarks. If a check fails, read the logs, fix the code on your machine, commit, and push again.
- **Peer Review:** A teammate will review your code. They might leave comments or request changes. 

### Step 7: Merge and Clean Up
Once the CI is green and your code is approved by a reviewer:
1. Click the **Squash and Merge** button on GitHub. This bundles all your small commits into one clean commit on the `main` branch.
2. Click **Delete branch** on GitHub to keep the remote repository clean.
3. On your local machine, switch back to `main`, pull the new changes, and delete your local branch:

```bash
git checkout main
git pull origin main
git branch -d feature/your-feature-name
```

You are now ready to pick up your next ticket!
