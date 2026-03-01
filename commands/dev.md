You are entering Project Mode. Follow this workflow exactly to initialize a new git-structured project.

## Step 1: Understand the Project
If the user has described what they want to build, use that. If not, ask for a brief description before doing anything else.

## Step 2: Present a Bullet Plan
Before writing any files or running any commands, present the following in-chat:

- **Goal**: one sentence
- **Structure**: proposed directory tree
- **Approach**: 3–5 key technical decisions or steps
- **Initial tasks**: what you'll build first

Then stop and wait for the user to confirm. Do not proceed until they do.

## Step 3: Initialize the Project
After confirmation, execute these steps in order using Bash:

```bash
# 1. Create repo in current directory
mkdir <project-name>
cd <project-name>
git init

# 2. Create skeleton structure appropriate for the project type
# (see Project Types below)

# 3. Initial commit on main
git add .
git commit -m "chore: scaffold <project-name>"

# 4. Gitignore the worktrees directory
echo ".worktrees/" >> .gitignore
git add .gitignore
git commit -m "chore: gitignore worktrees"

# 5. Create feature worktree — branch name describes the first task
git worktree add .worktrees/<feature-name> -b <feature-name>
```

## Step 4: Confirm Setup
Tell the user:
- Full path to the repo
- Branch they're on
- Worktree path where files will be written

## Working in the Worktree
All subsequent code file writes go to `.worktrees/<feature-name>/`. The guard-main hook will block any attempt to write code directly to main after the scaffold phase.

## Committing During Work
Commit at logical checkpoints without asking for approval each time. Use conventional prefixes:
- `feat:` new capability
- `fix:` bug fix
- `add:` new file or dependency
- `chore:` tooling, config

## Merging When Done
When a feature is complete, merge back to main and clean up:
```bash
git -C <repo-root> merge <feature-name>
git -C <repo-root> worktree remove .worktrees/<feature-name>
```

---

## Project Types — Skeleton Structures

Adapt the scaffold to the project type. Common patterns:

**Security tool (Python)**
```
<name>/
├── src/
├── tests/
├── scripts/
├── output/        ← gitignore this
└── README.md
```

**Fuzzing harness**
```
<name>/
├── harness/
├── corpus/
├── crashes/       ← gitignore this
├── scripts/
└── README.md
```

**Frida / dynamic instrumentation**
```
<name>/
├── hooks/
├── scripts/
├── output/        ← gitignore this
└── README.md
```

**Binary Ninja plugin / script**
```
<name>/
├── plugin/
├── types/
├── samples/       ← gitignore if large
└── README.md
```

**General tool**
```
<name>/
├── src/
├── tests/
├── docs/
└── README.md
```

Always add a `.gitignore` that excludes output dirs, crash dirs, large binaries, and `__pycache__` / `.pyc` files.
