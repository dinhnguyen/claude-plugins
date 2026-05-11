---
name: pr-via
description: Create a pull request via GitHub Actions workflow_dispatch. Use when the user says "create pr", "tạo pr cho con thỏ", "pr-via", or wants to open a PR for a branch. Triggers the create-pr.yml workflow.
---

# PR Via GitHub Actions

Create a PR by triggering the `create-pr.yml` workflow via `gh` CLI.

## Usage

```
/pr-via [branch-name] [base-branch]
```

- `branch-name`: head branch (default: current git branch)
- `base-branch`: target branch to merge into (default: `main`)

## Steps

1. Determine branches:
   - `head_branch`: use arg if provided, otherwise `git branch --show-current`
   - `base_branch`: use second arg if provided, otherwise `main`
   - Abort if head equals base: "Head branch is the same as base, nothing to PR"

2. Abort if an open PR already exists for this head→base pair (the workflow will fail anyway):
   ```bash
   gh pr list --head <head> --base <base> --state open --json number,url --jq '.[0]'
   ```
   If a PR is returned, report it and stop.

3. Check for unpushed commits:
   ```bash
   git log @{u}..HEAD --oneline 2>/dev/null
   ```
   - If there are unpushed commits, push first: `git push -u origin <head_branch>`
   - If upstream not set (command errors), push with: `git push -u origin <head_branch>`

4. Build PR title + body from the branch's commits (so the PR has a real summary instead of the workflow's "Auto-created by GitHub Actions." default):

   - Inspect the commit range and diff:
     ```bash
     git fetch origin <base> --quiet
     git log --no-merges --pretty=format:'%s%n%n%b%n---' origin/<base>..HEAD
     git diff --stat origin/<base>...HEAD
     ```
   - **Title**: keep ≤70 chars. If only one commit, reuse its subject. Otherwise synthesize a Conventional-Commits-style title (`type(scope): short summary`) that covers the branch. Do **not** prepend `@coderabbitai` — the workflow only adds that when no title is supplied.
   - **Body**: use this template, populated from the commit messages and diff:
     ```markdown
     ## Summary
     - <bullet 1>
     - <bullet 2>
     - <bullet 3>

     ## Test plan
     - [ ] <verification step>
     - [ ] <verification step>
     ```
     Bullets explain the *why*, not a file-by-file changelog. Skip the `Test plan` block only if there is genuinely nothing to verify (rare).
   - Skip this step (let the workflow auto-generate) only if the user explicitly asked for a bare/auto PR.

5. Trigger the workflow, passing the generated title and body:
   ```bash
   gh workflow run create-pr.yml \
     -f head_branch=<branch> \
     -f base_branch=<base> \
     -f pr_title="<title>" \
     -f pr_body="$(cat <<'EOF'
   <body>
   EOF
   )"
   ```
   Use a HEREDOC for `pr_body` so multi-line markdown survives shell escaping.

6. Get the workflow run URL:
   ```bash
   gh run list --workflow=create-pr.yml --limit=1 --json databaseId,status,url --jq '.[0]'
   ```
   - If status is not yet available, retry once after 2s
   - Report the run URL and status to the user. Once the run finishes, surface the resulting PR URL too:
     ```bash
     gh pr list --head <head> --base <base> --state open --json number,url --jq '.[0]'
     ```
