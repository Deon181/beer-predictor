# Filter Search & Slider Spacing — Design Spec

**Date:** 2026-05-27
**Status:** Approved

## Summary

Two sidebar improvements: (1) replace native `<select multiple>` elements for Styles and Countries filters with a custom searchable multi-select dropdown, and (2) fix slider help text overlapping with the slider thumb by increasing spacing.

## 1. SearchableMultiSelect Component

### Behavior

- **Trigger:** A clickable element displaying the current selection as comma-separated text (e.g., "IPA, Stout") or a placeholder (e.g., "All styles") when nothing is selected. Styled as a bottom-bordered text field matching existing filter inputs.
- **Dropdown panel:** Opens on trigger click. Contains a text input at the top for filtering, and a scrollable list of checkboxes below.
- **Filtering:** Case-insensitive substring match on the option text. All options visible when the filter input is empty.
- **Selection:** Checking/unchecking a checkbox toggles that option. The parent receives the updated array via `onChange`.
- **Closing:** Clicking outside the dropdown or pressing Escape closes it. The filter text resets on close.
- **No selection limit:** Users can select any number of options.

### Props

```typescript
interface SearchableMultiSelectProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  label: string;
  placeholder?: string;
}
```

### Styling

- Trigger: `var(--font-serif)`, 0.95rem, bottom-border only (`var(--color-ink-faint)`), copper on focus/open
- Dropdown panel: `var(--color-paper)` background, `var(--color-hairline)` border, top border `var(--color-copper)` (2px), subtle shadow
- Search input inside dropdown: `var(--font-mono)`, 0.72rem, uppercase, bottom-border, copper focus
- Checkbox labels: `var(--font-serif)`, 0.9rem, copper highlight on hover
- Scrollable list: max-height ~180px with overflow-y auto
- Class name prefix: `.sms` (searchable-multi-select)

## 2. Slider Help Text Spacing

Increase `.slider-label` gap from `0.1rem` to `0.35rem` in `globals.css`. This gives the 20px slider thumb sufficient clearance from the help text below it.

## 3. Integration

### `components/TastingSidebar.tsx`

Replace both `<select multiple>` elements (Styles and Countries) with `<SearchableMultiSelect>`. The `onChange` handler converts the selected array to the same format currently used (`filters.styles` / `filters.countries`).

Remove the `handleStylesChange` and `handleCountriesChange` functions that parse `e.target.selectedOptions`, since the new component passes a plain `string[]` directly.

### Files

- **Create:** `components/SearchableMultiSelect.tsx`
- **Modify:** `components/TastingSidebar.tsx` — swap native selects for new component, simplify handlers
- **Modify:** `app/globals.css` — add `.sms*` styles, fix `.slider-label` gap
