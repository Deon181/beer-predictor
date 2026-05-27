# Filter Search & Slider Spacing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace native multi-selects in the sidebar with searchable dropdown components and fix slider help text overlapping the slider thumb.

**Architecture:** A new `SearchableMultiSelect` component handles text filtering, checkbox selection, and click-outside-to-close. `TastingSidebar` swaps the native `<select multiple>` elements for this component. A one-line CSS fix increases slider label gap.

**Tech Stack:** React (useState, useRef, useEffect), CSS custom properties from the existing design system

---

## File Map

- **Create:** `components/SearchableMultiSelect.tsx` — self-contained searchable multi-select dropdown
- **Modify:** `app/globals.css` — add `.sms*` styles, fix `.slider-label` gap, remove unused `.filter-select` styles
- **Modify:** `components/TastingSidebar.tsx` — swap native selects for `SearchableMultiSelect`, simplify handlers

---

### Task 1: Fix slider help text spacing

**Files:**
- Modify: `app/globals.css:443-447`

- [ ] **Step 1: Increase `.slider-label` gap**

In `app/globals.css`, change the `.slider-label` rule's `gap` from `0.1rem` to `0.35rem`:

```css
.slider-label {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
}
```

- [ ] **Step 2: Verify in browser**

Visit `http://localhost:3000` — the help text below each taste slider (e.g., "How sharp / hop-bitter you want it") should no longer overlap with the slider thumb. There should be visible clearance.

- [ ] **Step 3: Commit**

```bash
git add app/globals.css
git commit -m "fix: increase slider label gap to prevent thumb overlap"
```

---

### Task 2: Add SearchableMultiSelect component and CSS

**Files:**
- Create: `components/SearchableMultiSelect.tsx`
- Modify: `app/globals.css`

- [ ] **Step 1: Create the component**

Create `components/SearchableMultiSelect.tsx` with the following content:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";

interface SearchableMultiSelectProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  label: string;
  placeholder?: string;
}

export function SearchableMultiSelect({
  options,
  selected,
  onChange,
  label,
  placeholder = "All",
}: SearchableMultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setFilter("");
      }
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        setOpen(false);
        setFilter("");
      }
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  useEffect(() => {
    if (open && searchRef.current) {
      searchRef.current.focus();
    }
  }, [open]);

  const filtered = filter
    ? options.filter((o) => o.toLowerCase().includes(filter.toLowerCase()))
    : options;

  function toggle(option: string) {
    if (selected.includes(option)) {
      onChange(selected.filter((s) => s !== option));
    } else {
      onChange([...selected, option]);
    }
  }

  const displayText = selected.length > 0 ? selected.join(", ") : placeholder;

  return (
    <div className="sms" ref={containerRef}>
      <button
        type="button"
        className={`sms__trigger${open ? " sms__trigger--open" : ""}`}
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        <span className={`sms__trigger-text${selected.length === 0 ? " sms__trigger-text--placeholder" : ""}`}>
          {displayText}
        </span>
        <span className="sms__arrow">{open ? "▴" : "▾"}</span>
      </button>
      {open && (
        <div className="sms__dropdown">
          <input
            ref={searchRef}
            type="text"
            className="sms__search"
            placeholder={`Search ${label.toLowerCase()}...`}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <div className="sms__list">
            {filtered.length === 0 && (
              <div className="sms__empty">No matches</div>
            )}
            {filtered.map((option) => (
              <label key={option} className="sms__option">
                <input
                  type="checkbox"
                  checked={selected.includes(option)}
                  onChange={() => toggle(option)}
                />
                <span>{option}</span>
              </label>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add `.sms*` CSS styles**

In `app/globals.css`, replace the existing `/* Multi-select dropdown */` section (`.filter-select`, `.filter-select:focus`, `.filter-select option` — lines 511–534) with the following:

```css
/* ───── Searchable multi-select ──────────────────────────────────── */
.sms {
    position: relative;
}
.sms__trigger {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-family: var(--font-serif);
    font-size: 0.95rem;
    color: var(--color-ink);
    background: transparent;
    border: 0;
    border-bottom: 1px solid var(--color-ink-faint);
    padding: 0.3rem 0;
    cursor: pointer;
    text-align: left;
    transition: border-color 0.2s ease;
    min-height: 2.2rem;
}
.sms__trigger--open,
.sms__trigger:focus {
    border-bottom-color: var(--color-copper);
}
.sms__trigger:focus-visible {
    outline: 2px solid var(--color-ink);
    outline-offset: 2px;
}
.sms__trigger-text {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.sms__trigger-text--placeholder {
    color: var(--color-ink-faint);
    font-style: italic;
}
.sms__arrow {
    color: var(--color-ink-faint);
    font-size: 0.7rem;
    margin-left: 0.4rem;
    flex-shrink: 0;
}
.sms__dropdown {
    position: absolute;
    left: 0;
    right: 0;
    top: 100%;
    margin-top: 2px;
    background: var(--color-paper);
    border: 1px solid var(--color-hairline);
    border-top: 2px solid var(--color-copper);
    box-shadow: 0 8px 24px rgba(26,20,16,0.10),
                0 2px 6px rgba(26,20,16,0.06);
    z-index: 20;
}
.sms__search {
    width: 100%;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--color-ink);
    background: transparent;
    border: 0;
    border-bottom: 1px solid var(--color-hairline);
    padding: 0.5rem 0.6rem;
    outline: none;
    transition: border-color 0.2s ease;
}
.sms__search:focus {
    border-bottom-color: var(--color-copper);
}
.sms__search::placeholder {
    color: var(--color-ink-faint);
    text-transform: uppercase;
}
.sms__list {
    max-height: 180px;
    overflow-y: auto;
}
.sms__list::-webkit-scrollbar { width: 6px; }
.sms__list::-webkit-scrollbar-thumb {
    background: var(--color-hairline);
    border-radius: 3px;
}
.sms__option {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.4rem 0.6rem;
    font-family: var(--font-serif);
    font-size: 0.9rem;
    color: var(--color-ink);
    cursor: pointer;
    transition: background 0.1s ease;
}
.sms__option:hover {
    background: var(--color-copper-soft);
}
.sms__option input[type="checkbox"] {
    accent-color: var(--color-copper);
    cursor: pointer;
}
.sms__empty {
    padding: 0.6rem;
    font-family: var(--font-mono);
    font-size: 0.7rem;
    color: var(--color-ink-faint);
    font-style: italic;
    text-transform: none;
}
```

- [ ] **Step 3: Verify CSS loads**

Visit `http://localhost:3000` — page should load without errors. The new styles won't be visible yet since the component isn't wired up.

- [ ] **Step 4: Commit**

```bash
git add components/SearchableMultiSelect.tsx app/globals.css
git commit -m "feat: add SearchableMultiSelect component and styles"
```

---

### Task 3: Integrate SearchableMultiSelect into TastingSidebar

**Files:**
- Modify: `components/TastingSidebar.tsx`

- [ ] **Step 1: Add the import**

At the top of `components/TastingSidebar.tsx`, add:

```typescript
import { SearchableMultiSelect } from "@/components/SearchableMultiSelect";
```

- [ ] **Step 2: Replace handler functions**

Remove the `handleStylesChange` and `handleCountriesChange` functions (the two functions that parse `e.target.selectedOptions`). Replace them with:

```typescript
function handleStylesChange(selected: string[]) {
  onFiltersChange({ ...filters, styles: selected.length ? selected : undefined });
}

function handleCountriesChange(selected: string[]) {
  onFiltersChange({ ...filters, countries: selected.length ? selected : undefined });
}
```

- [ ] **Step 3: Replace Styles select with SearchableMultiSelect**

Replace the Styles filter block:

```tsx
<label className="filter-label">
  <span>Styles</span>
  <select
    multiple
    className="filter-select"
    value={filters.styles ?? []}
    onChange={handleStylesChange}
  >
    {styles.map((s) => (
      <option key={s} value={s}>
        {s}
      </option>
    ))}
  </select>
</label>
```

With:

```tsx
<div className="filter-label">
  <span>Styles</span>
  <SearchableMultiSelect
    options={styles}
    selected={filters.styles ?? []}
    onChange={handleStylesChange}
    label="Styles"
    placeholder="All styles"
  />
</div>
```

- [ ] **Step 4: Replace Countries select with SearchableMultiSelect**

Replace the Countries filter block:

```tsx
<label className="filter-label">
  <span>Countries</span>
  <select
    multiple
    className="filter-select"
    value={filters.countries ?? []}
    onChange={handleCountriesChange}
  >
    {countries.map((c) => (
      <option key={c} value={c}>
        {c}
      </option>
    ))}
  </select>
</label>
```

With:

```tsx
<div className="filter-label">
  <span>Countries</span>
  <SearchableMultiSelect
    options={countries}
    selected={filters.countries ?? []}
    onChange={handleCountriesChange}
    label="Countries"
    placeholder="All countries"
  />
</div>
```

- [ ] **Step 5: Verify in browser**

Visit `http://localhost:3000`:
- Click the Styles trigger — dropdown should open with a search input and checkboxes
- Type to filter the list (e.g., "ipa" should narrow results)
- Check/uncheck items — the Ledger should update accordingly
- Click outside — dropdown should close
- Press Escape — dropdown should close
- Repeat for Countries
- Verify the trigger shows selected items as comma-separated text, or "All styles"/"All countries" when none selected

- [ ] **Step 6: Commit**

```bash
git add components/TastingSidebar.tsx
git commit -m "feat: replace native multi-selects with searchable dropdowns"
```
