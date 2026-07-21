# DiffSense output format

Contents:
1. Summary by DiffSense (end-user view)
2. Top-level review comment (Actionable count + expandables)
3. Inline finding template (two-dim tags + body)
4. Analysis chain (complex findings)
5. Confirmation loop (Addressed badge / resolve)

Render as plain markdown in the terminal by default. When posting to a GitHub PR (opt-in), wrap the expandable parts in `<details><summary>...</summary>...</details>`.

## 1. Summary by DiffSense

A short changelog from the **end-user's perspective** - what changed for users/admins, NOT a technical diff or file list. Only include sections that apply; omit empty ones. Plain-language bullets.

- **New Features** - user-visible capabilities added
- **Bug Fixes** - user-facing fixes
- **Improvements** - enhancements/refactors users may notice
- **Tests** - test additions/changes
- **Documentation** - docs/spec changes

In PR-post mode this goes at the top of the PR description (or a dedicated comment); in terminal mode print it first.

## 2. Top-level review comment

First line is always the count (bold):

```
**Actionable comments posted: N**
```

Then these expandable sections (headings in terminal; `<details>` if posting):

- **🤖 Prompt for all review comments with AI agents** - one combined prompt the user can paste into a coding agent to fix everything at once. Fixed preamble, then findings grouped by file:

  ```
  Verify each finding against current code. Fix only still-valid issues, skip the
  rest with a brief reason, keep changes minimal, and validate.

  Inline comments:
  In `@<file>`:
  - Around line <L>-<M>: <what to change>
  ```

- **🧹 Nitpick comments (N)** - taste-level items that did not make the actionable count, grouped by file. Omit when none.
- **ℹ️ Review info / Walkthrough** - 1-3 sentences describing the change set, the commit range reviewed, the files selected for processing, plus a pre-merge line like `Checks: title ✓ · description ✓ · N actionable`.

## 3. Inline finding template

Header line - two-dimensional tags plus an optional effort sub-tag, italic-underscored, each with its emoji:

```
_<emoji Issue Type>_ | _<emoji Severity>_ | _<emoji sub-tag>_
```

Example: `_🎯 Functional Correctness_ | _🟠 Major_ | _⚡ Quick win_`

- **Issue Type**: `🎯 Functional Correctness` · `🔒 Security & Privacy` · `🔗 Data Integrity & Integration` · `📐 Maintainability & Code Quality` · `🧪 Test Coverage`
- **Severity**: `🔴 Critical` (data loss, security hole, crash on the happy path) · `🟠 Major` · `🟡 Minor`. Nitpicks are not inline findings - they go in the top-level comment's `🧹 Nitpick comments` section.
- **sub-tag** (optional): `⚡ Quick win` (small, obvious fix) · `🏗️ Heavy lift` (large change)

Body:

```
**<Bold one-line title stating the problem.>**

<1-3 sentences on WHY it is a problem, citing the concrete function / variable / type names from the code.>

Also applies to: <lines or file:lines>   <- only when the same issue repeats elsewhere; one finding, not N copies

<details><summary>Proposed fix</summary>
<what to change, in prose>
</details>

<details><summary>📝 Committable suggestion</summary>

```diff
- old line(s)
+ new line(s)
```
</details>

<details><summary>🤖 Prompt for AI Agents</summary>
In `<file>` around lines <L>-<M>, <precise instruction to fix just this one finding>.
</details>
```

Anchor each finding to `file:line` (or `file:startLine-endLine`). In terminal mode, the `<details>` can be flattened to plain sub-bullets.

When posting to a GitHub PR, render the Committable suggestion as a native ` ```suggestion ` block (so it is one-click applyable) instead of a diff, preceded by the caution line: `> ‼️ **IMPORTANT** — Carefully review the code before committing.` A suggestion block replaces the exact commented line range - only emit one when the replacement lines are complete and correctly indented.

## 4. Analysis chain (complex findings only)

For non-obvious findings, precede the conclusion with a brief **🧩 Analysis chain**: the calls traced, the code read, and the reasoning that led to the verdict (a few lines). Skip it for simple/obvious findings.

## 5. Confirmation loop (Addressed badge / resolve)

On a re-review - triggered when the author says "fixed in `<commit>`", or a newer commit touched the finding's code:

1. Diff the current code (or the named commit) against the finding's Proposed fix / Committable suggestion.
2. **If satisfied**: prepend `✅ Addressed in commit <sha7>` (or `✅ Addressed in commits <sha7> to <sha7>` when the fix spans several commits) to the original finding; in PR-post mode also resolve the thread (GraphQL `resolveReviewThread`); in terminal mode list it under a `Resolved` group.
3. **If not satisfied**: keep it open with a one-line note on exactly what is still missing.

Report a per-finding roll-up: `addressed <x> · still-open <y>`. Re-run steps 1-2 until all are addressed or the user stops.
