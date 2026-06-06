---
name: skill-vetter
version: 1.0.0
description: 技能安全检查：安装前查红旗/权限/模式
license: MIT
author: Hermes Agent
metadata:
  hermes:
    tags: [security, vetting, skills, evaluation, github]
    related_skills: [skill-creator, skill-extraction-workflow, hermes-agent-skill-authoring]
---

# Skill Vetter 🔒

Security-first vetting protocol for AI agent skills. **Never install a skill without vetting it first.**

## When to Use

- Before installing any skill from ClawdHub
- Before running skills from GitHub repos
- When evaluating skills shared by other agents
- Anytime you're asked to install unknown code

## Vetting Protocol

### Step 1: Source Check

```
Questions to answer:
- [ ] Where did this skill come from?
- [ ] Is the author known/reputable?
- [ ] How many downloads/stars does it have?
- [ ] When was it last updated?
- [ ] Are there reviews from other agents?
```

### Step 2: Code Review (MANDATORY)

Read ALL files in the skill. Check for these **RED FLAGS**:

```
🚨 REJECT IMMEDIATELY IF YOU SEE:
─────────────────────────────────────────
• curl/wget to unknown URLs
• Sends data to external servers
• Requests credentials/tokens/API keys
• Reads ~/.ssh, ~/.aws, ~/.config without clear reason
• Accesses MEMORY.md, USER.md, SOUL.md, IDENTITY.md
• Uses base64 decode on anything
• Uses eval() or exec() with external input
• Modifies system files outside workspace
• Installs packages without listing them
• Network calls to IPs instead of domains
• Obfuscated code (compressed, encoded, minified)
• Requests elevated/sudo permissions
• Accesses browser cookies/sessions
• Touches credential files
─────────────────────────────────────────
```

### Step 3: Permission Scope

```
Evaluate:
- [ ] What files does it need to read?
- [ ] What files does it need to write?
- [ ] What commands does it run?
- [ ] Does it need network access? To where?
- [ ] Is the scope minimal for its stated purpose?
```

### Step 4: Risk Classification

| Risk Level | Examples | Action |
|------------|----------|--------|
| 🟢 LOW | Notes, weather, formatting | Basic review, install OK |
| 🟡 MEDIUM | File ops, browser, APIs | Full code review required |
| 🔴 HIGH | Credentials, trading, system | Human approval required |
| ⛔ EXTREME | Security configs, root access | Do NOT install |

### Step 5: Functional Evaluation (MANDATORY)

A skill can pass all security checks and still be the WRONG choice to install.
**Security is necessary but not sufficient.** Always run functional evaluation:

```
Questions to answer:
- [ ] What problem does this skill solve? Is it a problem we actually have?
- [ ] Does our environment already have this capability? (check skills_list + skill_view)
- [ ] Can the capability be added to an existing skill instead of creating new?
- [ ] Directory structure fit: does the skill's path/file assumptions match our setup?
      (e.g. skills flat vs categorized, config file locations, venv paths)
- [ ] Maintenance cost: will this skill need regular updates? By who?
- [ ] How many users benefit? (general-purpose > one-off for a specific task)
- [ ] Is the skill's approach aligned with our conventions and quality standards?
```

**Concrete example** (from real session evaluation of skill-auto-maintain):
- Security: Passed — pure Python stdlib, no network calls, no credential access
- Functional: FAILED — designed for categorized skill dirs (creative/, devops/), our 60+ skills are flat at skills/ root with version suffixes. Running it would trigger mass migration of all skills into user_skills/, causing chaos. Our existing skill_manage + skill-vetter + skill-creator already cover the maintenance needs.
- Verdict: Do NOT install, despite passing all security checks.

## Output Format

After vetting, produce this report:

```
SKILL VETTING REPORT
═══════════════════════════════════════
Skill: [name]
Source: [ClawdHub / GitHub / other]
Author: [username]
Version: [version]
───────────────────────────────────────
METRICS:
• Downloads/Stars: [count]
• Last Updated: [date]
• Files Reviewed: [count]
───────────────────────────────────────
RED FLAGS: [None / List them]

PERMISSIONS NEEDED:
• Files: [list or "None"]
• Network: [list or "None"]
• Commands: [list or "None"]
───────────────────────────────────────
RISK LEVEL: [🟢 LOW / 🟡 MEDIUM / 🔴 HIGH / ⛔ EXTREME]

VERDICT: [✅ SAFE TO INSTALL / ❌ DO NOT INSTALL / ⚠️ FUNCTIONAL MISMATCH]

NOTES: [Any observations about security, architecture, or environment fit]
═══════════════════════════════════════
```

> For a concrete walkthrough of evaluating a real-world GitHub skill (including the security-failed-but-functional-mismatch scenario), see `references/functional-evaluation.md`.

## Quick Vet Commands

For GitHub-hosted skills, use the **raw-content curl pattern** (faster than browser for text files):

```bash
# Phase 1 — Overview (README + repo stats)
curl -s "https://raw.githubusercontent.com/OWNER/REPO/main/README.md" | head -80
curl -s "https://api.github.com/repos/OWNER/REPO" | jq '{stars: .stargazers_count, forks: .forks_count, updated: .updated_at, desc: .description}'

# Phase 2 — Architecture (SKILL.md + source code)
curl -s "https://raw.githubusercontent.com/OWNER/REPO/main/skill-name/SKILL.md"
curl -s "https://raw.githubusercontent.com/OWNER/REPO/main/skill-name/main.py"   # or .js, .ts, etc.

# Phase 3 — Maturity (CHANGELOG + history)
curl -s "https://raw.githubusercontent.com/OWNER/REPO/main/CHANGELOG.md"
curl -s "https://api.github.com/repos/OWNER/REPO/commits?per_page=5" | jq '.[].commit.message'

# Phase 4 — Additional docs
curl -s "https://raw.githubusercontent.com/OWNER/REPO/main/README_CN.md"
curl -s "https://raw.githubusercontent.com/OWNER/REPO/main/LICENSE"
```

Star counts alone are misleading — a 3-star repo can be excellent (author just published it).
Always read source code and evaluate architecture, not just security.

## Common Pitfalls

1. **Installing without verifying environment compatibility.** A skill's directory assumptions (flat vs nested, file paths, config locations) must match your setup. skill-auto-maintain would have migrated 60+ skills to user_skills/ in our environment, causing chaos despite passing all security checks.

2. **Confusing "safe" with "useful."** A skill can have zero security red flags and still solve a problem you don't have, or duplicate existing capabilities. Security pass is the floor, not the ceiling.

3. **Over-relying on star count for quality judgment.** Small repos with recent commits often contain better architecture than stale high-star repos. Evaluate the code, not the badge.

4. **Skipping functional evaluation when security is clean.** A clean security report creates a false sense of "should install." Always run Step 5 (Functional Evaluation) regardless of Step 4 risk level.

5. **Not checking whether an existing skill can be extended instead.** Creating a new skill for every discovered tool fragments the library and increases load overhead. Prefer patching an existing skill to cover the gap.

## Trust Hierarchy

1. **Official / trusted framework skills** → Lower scrutiny (still review)
2. **High-star repos (1000+)** → Moderate scrutiny
3. **Known authors** → Moderate scrutiny
4. **New/unknown sources** → Maximum scrutiny
5. **Skills requesting credentials** → Human approval always

## Remember

- No skill is worth compromising security
- When in doubt, don't install
- Ask your human for high-risk decisions
- Document what you vet for future reference

---

*Paranoia is a feature.* 🔒🦀
