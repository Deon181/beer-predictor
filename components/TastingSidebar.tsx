"use client";

import { useState } from "react";
import type { Filters, TasteProfile } from "@/lib/types";
import { AXES, type AxisKey } from "@/lib/axes";
import { SearchableMultiSelect } from "@/components/SearchableMultiSelect";

interface TastingSidebarProps {
  profile: TasteProfile;
  onProfileChange: (profile: TasteProfile) => void;
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  topK: number;
  onTopKChange: (k: number) => void;
  styles: string[];
  countries: string[];
  onReset: () => void;
  activeAxes: AxisKey[];
}

export function TastingSidebar({
  profile,
  onProfileChange,
  filters,
  onFiltersChange,
  topK,
  onTopKChange,
  styles,
  countries,
  onReset,
  activeAxes,
}: TastingSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  function handleSlider(key: keyof TasteProfile, value: number) {
    onProfileChange({ ...profile, [key]: value });
  }

  function handleStylesChange(selected: string[]) {
    onFiltersChange({ ...filters, styles: selected.length ? selected : undefined });
  }

  function handleCountriesChange(selected: string[]) {
    onFiltersChange({ ...filters, countries: selected.length ? selected : undefined });
  }

  function handleMinAbv(val: number) {
    onFiltersChange({
      ...filters,
      minAbv: val,
      maxAbv: filters.maxAbv != null && filters.maxAbv < val ? val : filters.maxAbv,
    });
  }

  function handleMaxAbv(val: number) {
    onFiltersChange({
      ...filters,
      maxAbv: val,
      minAbv: filters.minAbv != null && filters.minAbv > val ? val : filters.minAbv,
    });
  }

  return (
    <>
      <button
        className="sidebar-toggle"
        onClick={() => setCollapsed((c) => !c)}
        aria-label={collapsed ? "Show taste sliders" : "Hide taste sliders"}
      >
        {collapsed ? "Sliders ▶" : "◀ Sliders"}
      </button>

      <aside className={`tasting-card${collapsed ? " collapsed" : ""}`}>
        <h3 className="tasting-card__title">Your palate</h3>

        <div className="slider-group">
          {AXES.filter((a) => activeAxes.includes(a.key)).map((s) => (
            <label key={s.key} className="slider-label">
              <span className="slider-label__name">
                {s.label}
                <span className="slider-label__value">
                  {profile[s.key].toFixed(1)}
                </span>
              </span>
              <input
                type="range"
                min={0}
                max={10}
                step={0.5}
                value={profile[s.key]}
                onChange={(e) => handleSlider(s.key, parseFloat(e.target.value))}
                className="slider"
                title={s.help}
              />
              <span className="slider-label__help">{s.help}</span>
            </label>
          ))}
        </div>

        <hr className="sidebar-rule" />

        <h3 className="tasting-card__title">Filters</h3>

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

        <div className="filter-label">
          <span>ABV range</span>
          <div className="abv-range">
            <span className="abv-range__value">{(filters.minAbv ?? 0).toFixed(1)}%</span>
            <input
              type="range"
              min={0}
              max={20}
              step={0.5}
              value={filters.minAbv ?? 0}
              onChange={(e) => handleMinAbv(parseFloat(e.target.value))}
              className="slider"
            />
            <span className="abv-range__sep">&ndash;</span>
            <input
              type="range"
              min={0}
              max={20}
              step={0.5}
              value={filters.maxAbv ?? 20}
              onChange={(e) => handleMaxAbv(parseFloat(e.target.value))}
              className="slider"
            />
            <span className="abv-range__value">{(filters.maxAbv ?? 20).toFixed(1)}%</span>
          </div>
        </div>

        <label className="filter-label">
          <span>Results: {topK}</span>
          <input
            type="range"
            min={3}
            max={20}
            step={1}
            value={topK}
            onChange={(e) => onTopKChange(parseInt(e.target.value, 10))}
            className="slider"
          />
        </label>

        <hr className="sidebar-rule" />

        <button className="ink-btn" onClick={onReset}>
          Reset palate
        </button>
      </aside>
    </>
  );
}
