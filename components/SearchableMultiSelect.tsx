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
