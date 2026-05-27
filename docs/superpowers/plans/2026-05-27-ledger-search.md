# Ledger Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a full-catalog text search bar above the Ledger so users can look up any beer by name or brewery, with results shown as scored LedgerCards.

**Architecture:** A `searchQuery` state in `page.tsx` drives a `useMemo` that either returns normal top-K recommendations (empty query) or filters the full catalog by substring match and scores all matches via the existing `recommend()` function (non-empty query). A styled search input sits between the charts and the Ledger. No new components or dependencies.

**Tech Stack:** React (useState, useMemo), existing `recommend()` from `lib/recommender.ts`, CSS in `globals.css`

---

## File Map

- **Modify:** `app/globals.css` — add `.ledger-search` styles
- **Modify:** `app/page.tsx` — add search state, search-filtered results memo, search input JSX

---

### Task 1: Add search bar CSS

**Files:**
- Modify: `app/globals.css` (insert after the `.ledger-head .legend` block, around line 1001)

- [ ] **Step 1: Add `.ledger-search` styles**

Insert the following CSS block after the `.ledger-head .legend` rule (after line 1001) and before the `/* Ledger card view */` comment:

```css
/* ───── Ledger search ────────────────────────────────────────────── */
.ledger-search {
    margin-top: 2rem;
    margin-bottom: 0.4rem;
    position: relative;
}
.ledger-search input {
    width: 100%;
    font-family: var(--font-serif);
    font-size: 1.05rem;
    color: var(--color-ink);
    background: transparent;
    border: 0;
    border-bottom: 1px solid var(--color-hairline);
    padding: 0.35rem 2rem 0.35rem 0;
    outline: none;
    transition: border-color 0.2s ease;
}
.ledger-search input:focus {
    border-bottom-color: var(--color-copper);
}
.ledger-search input::placeholder {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--color-ink-faint);
}
.ledger-search__clear {
    position: absolute;
    right: 0;
    top: 50%;
    transform: translateY(-50%);
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--color-ink-faint);
    background: transparent;
    border: 0;
    padding: 0.2rem 0;
    cursor: pointer;
    transition: color 0.15s ease;
}
.ledger-search__clear:hover {
    color: var(--color-oxblood);
}
```

- [ ] **Step 2: Verify dev server picks up the CSS**

Run: Visit `http://localhost:3000` in the browser — page should load without errors. The new styles won't be visible yet since no element uses them.

- [ ] **Step 3: Commit**

```bash
git add app/globals.css
git commit -m "feat: add ledger search bar styles"
```

---

### Task 2: Add search state and filtered results

**Files:**
- Modify: `app/page.tsx`

- [ ] **Step 1: Add `searchQuery` state**

In `app/page.tsx`, add a new state variable after the `loading` state declaration (line 51):

```typescript
const [searchQuery, setSearchQuery] = useState("");
```

- [ ] **Step 2: Add `displayedResults` memo**

After the existing `recommendations` useMemo (after line 83), add:

```typescript
const displayedResults = useMemo(() => {
  const q = searchQuery.trim().toLowerCase();
  if (!q) return recommendations;
  const matched = catalog.filter(
    (b) =>
      b.name.toLowerCase().includes(q) ||
      b.brewery.toLowerCase().includes(q)
  );
  if (matched.length === 0) return [];
  return recommend(matched, profile, matched.length, filters);
}, [searchQuery, catalog, profile, filters, recommendations]);
```

- [ ] **Step 3: Add search input JSX**

In the JSX, between the closing `</div>` of `.charts-row` (line 218) and the `<Ledger` component (line 221), add:

```tsx
<div className="ledger-search">
  <input
    type="text"
    placeholder="Search by name or brewery..."
    value={searchQuery}
    onChange={(e) => setSearchQuery(e.target.value)}
  />
  {searchQuery && (
    <button
      className="ledger-search__clear"
      onClick={() => setSearchQuery("")}
      aria-label="Clear search"
    >
      clear
    </button>
  )}
</div>
```

- [ ] **Step 4: Update `<Ledger>` to use `displayedResults`**

Change the `<Ledger>` component's `recommendations` prop from `recommendations` to `displayedResults`:

```tsx
<Ledger
  recommendations={displayedResults}
  profile={profile}
  ratings={ratings}
  signedIn={!!user}
  onRate={handleRate}
/>
```

- [ ] **Step 5: Verify in browser**

Run: Visit `http://localhost:3000` — the search input should appear between the charts and the Ledger. Type a beer name or brewery — results should filter. Clear button should reset to normal recommendations.

- [ ] **Step 6: Commit**

```bash
git add app/page.tsx
git commit -m "feat: add full-catalog search to the Ledger"
```
