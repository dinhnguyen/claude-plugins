---
name: rabbit-pr
description: Address CodeRabbit (or similar bot) review comments on a PR. Use when the user says "rabbit-pr", "rabbit-pr-fix", "fix review comments", "address PR feedback", "check coderabbit comments", or asks to verify and fix automated review comments on a pull request. Accepts an optional PR number; otherwise auto-detects from the current branch. Fetches comments, builds a checklist, verifies each against code, applies fixes, resolves conflicts, pushes, replies, and resolves threads.
---

# Rabbit PR — Review Comment Handler

Address automated review comments (CodeRabbit, etc.) on a pull request.

## Trigger examples

- "rabbit-pr 123"
- "rabbit-pr-fix" (auto-detect PR from current branch)
- "fix review comments on PR 456"
- "address coderabbit feedback on this branch"

## Workflow

### 1. Resolve the PR

- If PR number provided, use it
- Otherwise, detect from current branch: `gh pr list --head $(git branch --show-current) --json number --jq '.[0].number'`
- If no PR found, abort

### 2. Fetch PR info and review comments

```bash
gh pr view <number> --json title,headRefName,baseRefName,state,mergeable,mergeStateStatus
# Inline file-level comments
gh api repos/{owner}/{repo}/pulls/<number>/comments
# Review-level comments (body of each review — often contains actionable feedback)
gh api repos/{owner}/{repo}/pulls/<number>/reviews
```

**Important:** Comments can live in two places:
- **Inline comments** (`/comments`): attached to specific file lines
- **Review bodies** (`/reviews`): top-level review summary text, often containing actionable items not tied to specific lines

Fetch both. Filter reviews to those with a non-empty `body` and `state` of `CHANGES_REQUESTED` or `COMMENTED`. Parse review bodies for actionable items (look for bullet points, code suggestions, or imperative statements).

**Skip already-handled comments.** For each inline comment, check whether the authenticated user (`gh api user --jq .login`) already has a reply in its thread — if so, skip it. Otherwise the skill will double-reply when re-run on the same PR.

**Classify CodeRabbit severity.** CodeRabbit tags items with markers like `_⚠️ Potential issue_`, `_🛠️ Refactor suggestion_`, `_🧹 Nitpick_`. Prioritize **Potential issue** and **Refactor suggestion**; treat **Nitpick** as optional unless the user explicitly asks to address them.

**Skip resolved threads.** Use the GraphQL API to fetch thread resolution state and skip resolved ones:

```bash
gh api graphql -f query='query($owner:String!,$repo:String!,$num:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$num){reviewThreads(first:100){nodes{id isResolved comments(first:1){nodes{databaseId}}}}}}}' -F owner=<owner> -F repo=<repo> -F num=<number>
```

### 3. Build the comment checklist

Before doing any work, build a single checklist covering **every** comment to be processed (inline + review body items, after filtering out resolved/already-replied/nitpick-if-skipped). For each entry capture:

- **id** — comment id (or `review-body-<reviewId>-<n>` for review body items)
- **location** — `path:line` or `review body`
- **summary** — one short line of the issue
- **severity** — potential issue / refactor / nitpick
- **status** — one of: `fix needed`, `reply needed`, `both`, `done`

Render it to the user as a markdown checklist (`- [ ] ...`) and use TodoWrite to track it. **Update the checklist after every action** (verify, fix, push, reply, resolve). Show the final checklist state to the user before closing out the workflow in step 9.

### 4. Checkout the PR branch and pull latest

```bash
git checkout <headRefName>
git pull
```

### 5. Verify each comment against current code

**For inline comments:**
1. Read the file and lines referenced
2. Determine if the issue is **valid**, **already fixed**, or **not applicable**
3. Track verdict per comment

**For review body items:**
1. Parse each actionable item from the review body
2. Identify which files/areas of the codebase each item refers to (may require searching)
3. Read the relevant code and determine if the issue is **valid**, **already fixed**, or **not applicable**
4. Track verdict per item

For each entry, mark verdict in the checklist:
- `valid` → keep `fix needed` / `both`
- `already fixed` → flip to `reply needed` (acknowledge in reply)
- `not applicable` → flip to `reply needed` (explain why we're declining)

### 6. Apply fixes for valid issues

- Read surrounding code for context before editing
- Follow existing code patterns and conventions
- Check if the same issue applies to similar code in other files (like ownerId validation across multiple APIs)
- Run linting/typecheck if available to catch issues early
- Update the checklist (mark each item `done` for the fix portion as you finish it)

### 7. Resolve conflicts if needed

Check `mergeStateStatus`:
- If `BEHIND`: `git merge <baseRefName> --no-edit`
- If `CONFLICTING`: merge and resolve conflicts manually
- If `CLEAN`: skip

### 8. Commit and push

```bash
git add <changed-files>
git commit -m "<prefix>: address review feedback on <PR-title-summary>"
git push origin <headRefName>
```

- Match the repo's commit-message convention — inspect `git log --oneline -20` first. Some repos use `fix:`, others use no prefix, others use ticket IDs. Don't hard-code `fix:`.
- **Fork PRs:** check `headRepositoryOwner.login` from `gh pr view`. If it differs from the base repo owner, the push target is the fork remote, not `origin`. Either add the fork as a remote or skip the push step and tell the user to push manually.

### 9. Reply to all comments (batched) and resolve threads

**Batch all replies into a single bash command** to minimize user confirmations. Chain all `gh api` calls in one Bash invocation:

- Use `&&` when each reply must succeed before continuing (rare).
- Use `;` for best-effort: a single failed reply (e.g., 404 on a deleted comment) shouldn't abort the rest.

```bash
gh api repos/{owner}/{repo}/pulls/<number>/comments/<id1>/replies -f body="..." ; \
gh api repos/{owner}/{repo}/pulls/<number>/comments/<id2>/replies -f body="..." ; \
gh pr comment <number> --body "..."
```

- **Inline comments**: `gh api repos/{owner}/{repo}/pulls/<number>/comments/<id>/replies -f body="..."`
- **Review body items**: `gh pr comment <number> --body "..."` referencing the review and listing what was addressed

Each reply should include:
- What was done (fixed / already addressed / not applicable)
- Which commit contains the fix
- Brief explanation of the approach

**Resolve threads after replying.** For each thread we addressed, resolve it via GraphQL (use the `reviewThreads.nodes[].id` collected in step 2):

```bash
gh api graphql -f query='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}' -F id=<threadId>
```

Mark each checklist item `done` after its reply (and resolve, if applicable) succeeds.

### 10. Final checklist & handoff

Before closing out, render the **final checklist state** to the user as a markdown checklist showing every comment with its final status (`done`, or `skipped — <reason>` for nitpicks/already-replied/resolved). Include:

- commit hash(es) pushed
- count of comments fixed / replied / skipped
- any comments that need human follow-up (e.g., disagreed with the bot, fork PR push blocked, merge conflict needing review)

Do not consider the workflow complete until the user has seen this final state.

## Key Principles

- **Verify before fixing** — not all bot comments are valid. Read the actual code first.
- **Checklist is the source of truth** — every comment must appear in it; every state change must update it.
- **Fix broadly** — if a comment identifies an issue in one file, check if the same pattern exists elsewhere
- **Follow project conventions** — match existing error handling, naming, and code style; match commit-message convention from `git log`
- **One commit** — batch all fixes into a single commit unless changes are unrelated
- **Reply concisely** — state what was done, reference the commit hash, explain approach briefly
- **Don't double-reply** — skip comments where the authenticated user already responded
