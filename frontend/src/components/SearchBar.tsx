"use client";
import type { FormEvent } from "react";

export default function SearchBar({ value, onChange, onSearch, busy }: {
  value: string; onChange: (value: string) => void; onSearch: () => void; busy: boolean;
}) {
  function submit(event: FormEvent) { event.preventDefault(); if (value.trim() && !busy) onSearch(); }
  return <form onSubmit={submit} className="mt-8">
    <label htmlFor="dish-query" className="mb-3 block text-sm font-semibold">What sounds good?</label>
    <div className="flex flex-col gap-3 rounded-3xl border border-[#cbd3bd] bg-[#fffefa] p-3 sm:flex-row sm:items-center">
      <input id="dish-query" value={value} onChange={event => onChange(event.target.value)} maxLength={500} required placeholder="Something spicy under 5000 HUF" autoComplete="off" className="min-w-0 flex-1 rounded-xl bg-transparent px-3 py-3 text-base outline-offset-2 placeholder:text-[#838b79]" aria-describedby="search-privacy" />
      <button disabled={busy || !value.trim()} className="shrink-0 rounded-full bg-[#243e32] px-7 py-3.5 font-semibold text-white disabled:opacity-50">{busy ? "Searching…" : "Find dishes ↗"}</button>
    </div>
    <p id="search-privacy" className="mt-3 text-xs leading-relaxed text-[#69735f]">Your request is sent to the configured AI service to understand your preferences. Results come from saved menus.</p>
  </form>;
}
