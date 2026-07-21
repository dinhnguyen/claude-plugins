---
name: diffsense
description: Structured inline code review of a local git diff or a GitHub PR. Produces the full structured review format - an end-user "Summary", a top-level "Actionable comments posted" count comment with a combined AI-agent fix prompt plus walkthrough, and inline findings tagged two-dimensionally by issue type (Functional Correctness, Security & Privacy, Data Integrity & Integration, Maintainability, Test Coverage) and severity (Minor/Major/Critical, with "Quick win" / "Heavy lift" sub-tags), each with a Proposed fix, a Committable suggestion patch, and a per-finding AI-Agents prompt. Report-only by default (prints in terminal; never edits code); can optionally post to a PR and run the confirm-on-fix resolve loop. Use when the user says "diffsense", "DiffSense", "review my changes / diff / PR", "self-review before push", "review before I commit / open a PR", "check my code", or re-review after fixing.
---

# DiffSense

Produce a structured, severity-tagged review of changed code. **Report only - do not edit, commit, or push code.** Default output is the terminal (a self-review before pushing). Posting to a GitHub PR is opt-in (see Posting).

## 1. Get the diff

Resolve the target from the user's request:

- **Local, uncommitted** ("review my changes"): `git diff HEAD` (staged + unstaged). If empty, fall back to branch mode.
- **Local, branch** ("review before push/PR"): `git diff $(git merge-base main HEAD)...HEAD`. Use the repo's default branch if not `main`.
- **PR** ("review PR 123"): `gh pr diff <N>` (detect N via `gh pr list --head $(git branch --show-current) --json number --jq '.[0].number'` if not given); `gh pr view <N> --json files,title,body`.

Read the full changed files with surrounding context - a diff line alone cannot confirm a bug. Read `CLAUDE.md`/`AGENTS.md` and a neighboring file to learn the repo's conventions before flagging style. For a large diff (>~30 files), review by dimension in parallel subagents, then merge.

## 2. Review across four dimensions

For every changed hunk look for: **Functional Correctness** (logic, off-by-one, null/undefined, unhandled async, races, error handling, edge cases) · **Security & Privacy** (injection, missing authz, secrets/PII in logs or URLs, unvalidated input) · **Data Integrity & Integration** (non-atomic multi-write / missing transaction, fail-open, cross-process cache staleness, contract breaks) · **Maintainability & Code Quality** (duplication, naming, dead code, needless complexity, deviations from the repo's own conventions) · **Test Coverage** (new branches / bug fixes with no test).

## 3. Verify before reporting

Signal, not noise. For each candidate: re-read the surrounding code and construct the concrete failure (specific input/state -> wrong output/crash); if you cannot, it is not a Major. Confirm it is inside the diff (or the diff triggers it) - do not flag untouched pre-existing code. Drop speculative/taste-only items or downgrade to Nitpick. Prefer 3 verified findings over 15 shaky ones.

The most common false positives to self-check before reporting: (a) claiming X is missing when X is already handled a few lines away or in a helper - read the whole function, not the hunk; (b) referencing a symbol/entity/type that does not exist in this codebase - verify every name you cite; (c) flagging code that is dead/unused after this very diff; (d) intentional behavior documented in CLAUDE.md, a comment, or an ADR.

## 4. Produce the output

Follow the exact structure in **[references/output-format.md](references/output-format.md)** - read it before writing the review. It defines:
- the end-user **Summary** (New Features / Bug Fixes / Improvements / Tests / Documentation),
- the top-level **`Actionable comments posted: N`** comment with the combined AI-agent fix prompt + walkthrough,
- the **inline finding template**: `_<emoji Issue Type>_ | _<emoji Severity>_ | _<sub-tag>_` header (e.g. `_🎯 Functional Correctness_ | _🟠 Major_ | _⚡ Quick win_`), bold problem title, why-it-matters citing concrete names, then Proposed fix / Committable suggestion (diff) / per-finding Prompt for AI Agents, with `Also applies to: <lines>` when the same issue repeats elsewhere,
- the **Analysis chain** block for complex findings.

Order findings Critical -> Major -> Minor -> Nitpick. Nitpicks go in the top-level comment under a `🧹 Nitpick comments (N)` section, not as inline findings, and do not count toward the actionable total. Close with what was reviewed and anything not verifiable from the diff. If nothing is actionable, say so plainly rather than inventing findings.

## 5. Confirmation loop (re-review after a fix)

When the user says they fixed something (or a new commit lands), re-review per section 5 of the format reference: diff current code against each finding's suggestion, prepend `✅ Addressed in commit <sha7>` (or `✅ Addressed in commits <sha7> to <sha7>` when the fix spans several commits) and resolve the ones now satisfied, keep the rest open with what is still missing, and report `addressed x · still-open y`. Repeat until clear or the user stops.

## Posting to a PR (opt-in)

Default is terminal output. Only when the user explicitly asks to post ("post it to the PR", "comment on the PR"):
- Summary -> a PR comment (`gh pr comment <N> --body`).
- Inline findings -> a review via `gh api repos/{owner}/{repo}/pulls/<N>/reviews` (or `pull_request_review_write`), one comment per finding at its `path`/`line`.
- Confirmation loop -> resolve threads via GraphQL `resolveReviewThread`.

Note before posting: if this repo already runs an automated review bot on PRs, posting duplicates it - confirm the user wants a second review on the PR rather than a terminal self-review.

## Guardrails

- Report-only: never Edit/Write/commit/push code as part of this skill. Posting review comments (opt-in) is allowed; changing source is not.
- Do not restate the whole diff; only the findings.
- Respect the project's conventions over personal preference.
