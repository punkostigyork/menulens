"use client";
import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { searchDishes } from "@/services/api";
import type { SearchIntent, SearchRequest, SearchResponse } from "@/types/search";
import SearchBar from "./SearchBar";
import DishCard from "./DishCard";

const examples = ["Something spicy under 5000 HUF", "Chicken under 6000 HUF", "Dessert under 3000 HUF"];
const fieldClass = "mt-2 w-full rounded-xl border border-[#cbd3bd] bg-[#fffefa] px-3 py-3 text-base";
function filtersLabel(intent: SearchIntent): string[] {
  const labels = [...intent.ingredients.map(value => `Ingredient: ${value}`), ...intent.tags.map(value => `Tag: ${value}`)];
  if (intent.name) labels.push(`Dish: ${intent.name}`);
  if (intent.min_price !== null) labels.push(`${intent.min_price_inclusive ? "At least" : "Over"} ${intent.min_price} ${intent.currency || ""}`);
  if (intent.max_price !== null) labels.push(`${intent.max_price_inclusive ? "Up to" : "Under"} ${intent.max_price} ${intent.currency || ""}`);
  if (intent.currency && intent.min_price === null && intent.max_price === null) labels.push(intent.currency);
  return labels.length ? labels : ["All saved dishes"];
}
export default function DishSearch() {
  const [mode, setMode] = useState<"query" | "filters">("query");
  const [query, setQuery] = useState("");
  const [name, setName] = useState("");
  const [ingredient, setIngredient] = useState("");
  const [tag, setTag] = useState("");
  const [budget, setBudget] = useState("");
  const [currency, setCurrency] = useState("HUF");
  const [data, setData] = useState<SearchResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [lastRequest, setLastRequest] = useState<SearchRequest | null>(null);
  const controller = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  useEffect(() => () => { controller.current?.abort(); }, []);

  async function run(request: SearchRequest) {
    controller.current?.abort();
    const abort = new AbortController(); controller.current = abort;
    const number = ++sequence.current;
    setBusy(true); setError(""); setData(null); setLastRequest(request);
    try {
      const result = await searchDishes(request, abort.signal);
      if (!abort.signal.aborted && number === sequence.current) setData(result);
    } catch (cause) {
      if (!abort.signal.aborted && number === sequence.current) setError(cause instanceof TypeError ? "Connection lost. Check your connection and try again." : cause instanceof Error ? cause.message : "Search is unavailable. Please try again.");
    } finally { if (!abort.signal.aborted && number === sequence.current) setBusy(false); }
  }
  function chooseMode(next: "query" | "filters") { setMode(next); }
  function submitFilters(event: FormEvent) {
    event.preventDefault();
    run({filters:{name:name.trim() || null, ingredients:ingredient.trim() ? [ingredient.trim()] : [], tags:tag ? [tag] : [], max_price:budget || null, currency:budget ? currency : null}});
  }
  return <div className="min-h-svh">
    <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 border-b border-[#243e32]/15 px-6 py-6 sm:px-10">
      <Link href="/" className="flex items-center gap-2.5 text-xl font-semibold tracking-tight"><span aria-hidden="true" className="flex size-8 items-center justify-center rounded-full bg-[#243e32] font-serif text-lg text-[#f7f5ee]">m.</span>MenuLens</Link>
      <nav aria-label="Main navigation" className="flex flex-wrap justify-end gap-3"><Link href="/explore" className="px-2 py-2 text-sm font-semibold">Explore nearby</Link><Link href="/upload" className="rounded-full border border-[#b8c2aa] px-4 py-2 text-sm font-semibold">Upload a menu ↗</Link></nav>
    </header>
    <main className="mx-auto max-w-6xl px-6 pb-16 sm:px-10">
      <section className="max-w-3xl py-10 sm:py-14">
        <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#738348]">Follow your appetite</p>
        <h1 className="mt-5 font-serif text-5xl leading-[1.08] tracking-tight sm:text-6xl">A craving. A few good options.</h1>
        <p className="mt-5 max-w-xl leading-relaxed text-[#66705f]">Find a dish in the menus you’ve saved. Tell us what you’re in the mood for, with a budget if you like.</p>
        <div role="group" aria-label="Search method" className="mt-7 inline-flex max-w-full rounded-full border border-[#cbd3bd] p-1">
          <button onClick={() => chooseMode("query")} aria-pressed={mode === "query"} className={`rounded-full px-4 py-2.5 text-sm ${mode === "query" ? "bg-[#243e32] text-white" : "text-[#59664e]"}`}>Describe a craving</button>
          <button onClick={() => chooseMode("filters")} aria-pressed={mode === "filters"} className={`rounded-full px-4 py-2.5 text-sm ${mode === "filters" ? "bg-[#243e32] text-white" : "text-[#59664e]"}`}>Choose filters</button>
        </div>
        {mode === "query" ? <>
          <SearchBar value={query} onChange={setQuery} busy={busy} onSearch={() => run({query:query.trim()})} />
          <div className="mt-5 flex flex-wrap gap-2" aria-label="Example searches">{examples.map(example => <button key={example} disabled={busy} onClick={() => setQuery(example)} className="rounded-full border border-[#d9dfce] px-3.5 py-2 text-xs text-[#59664e] hover:bg-[#edf1e3] disabled:opacity-50">{example}</button>)}</div>
        </> : <form onSubmit={submitFilters} className="mt-7 rounded-3xl border border-[#dce0d2] bg-[#eff1e8] p-5 sm:p-6">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold">Dish name<input value={name} onChange={event => setName(event.target.value)} maxLength={100} placeholder="e.g. Gulyásleves" className={fieldClass} /></label>
            <label className="text-sm font-semibold">Listed ingredient<input value={ingredient} onChange={event => setIngredient(event.target.value)} maxLength={100} placeholder="e.g. chicken or csirke" className={fieldClass} /></label>
            <label className="text-sm font-semibold">Tag<select value={tag} onChange={event => setTag(event.target.value)} className={fieldClass}><option value="">Any tag</option>{["Hungarian","Italian","meat","poultry","seafood","pasta","soup","dessert","coffee","cocktail","sweet","savory","spicy","breakfast","brunch"].map(value => <option key={value} value={value}>{value}</option>)}</select></label>
            <div className="grid grid-cols-[1fr_5.5rem] gap-2"><label className="min-w-0 text-sm font-semibold">Maximum price<input value={budget} onChange={event => setBudget(event.target.value)} type="number" min="0" max="9999999999.99" step="0.01" placeholder="No limit" className={fieldClass} /></label><label className="text-sm font-semibold">Currency<select value={currency} onChange={event => setCurrency(event.target.value)} className={fieldClass}><option>HUF</option><option>EUR</option><option>USD</option></select></label></div>
          </div>
          <button disabled={busy} className="mt-5 rounded-full bg-[#243e32] px-6 py-3 font-semibold text-white disabled:opacity-50">{busy ? "Searching…" : "Find matching dishes"}</button>
          <p className="mt-3 text-xs leading-relaxed text-[#69735f]">All chosen filters must match. No new AI request is made. Tags can include previously generated suggestions.</p>
        </form>}
      </section>
      {busy ? <section role="status" aria-label="Searching dishes" className="border-t border-[#dce0d2] pt-8"><p className="font-serif text-2xl">Finding dishes for you…</p><div aria-hidden="true" className="mt-6 grid gap-5 md:grid-cols-2">{[0,1].map(value => <div key={value} className="h-52 motion-safe:animate-pulse rounded-3xl bg-[#e9ecdf]" />)}</div></section> : error ? <section role="alert" className="rounded-3xl border border-[#dcc9bb] bg-[#fffefa] p-7"><h2 className="font-serif text-2xl">Let’s try that again.</h2><p className="mt-3 leading-relaxed text-[#754b3a]">{error}</p><div className="mt-5 flex flex-wrap gap-5">{lastRequest && <button onClick={() => run(lastRequest)} className="font-semibold underline underline-offset-4">Retry search</button>}<button onClick={() => {setMode("filters"); setError("");}} className="font-semibold underline underline-offset-4">Use filters</button></div></section> : data ? <section aria-label="Search results" className="border-t border-[#dce0d2] pt-8">
        {data.clarification ? <div role="status" className="rounded-3xl border border-[#dce0d2] bg-[#fffefa] p-7"><h2 className="font-serif text-3xl">A little more detail, please.</h2><p className="mt-3 max-w-2xl leading-relaxed text-[#66705f]">{data.clarification}</p></div> : <>
          <div className="flex flex-wrap items-center justify-between gap-3"><h2 aria-live="polite" className="font-serif text-3xl">{data.total === 0 ? "No matches this time." : `${data.total} ${data.total === 1 ? "dish" : "dishes"} to consider`}</h2><p className="text-sm text-[#66705f]">Saved menus · all filters match</p></div>
          <ul aria-label="Applied filters" className="mt-4 flex flex-wrap gap-2">{filtersLabel(data.intent).map(label => <li key={label} className="rounded-full bg-[#e9eddd] px-3 py-1.5 text-xs text-[#526536]">{label}</li>)}</ul>
          {data.total === 0 ? <div className="mt-6 rounded-3xl border border-[#dce0d2] bg-[#fffefa] p-8"><p className="max-w-xl leading-relaxed text-[#66705f]">Try fewer filters or a different budget. Only processed menus are searched; some dishes may not have listed ingredients or tags yet.</p><button onClick={() => run({filters:{}})} className="mt-5 font-semibold underline underline-offset-4">Browse all saved dishes</button><Link href="/upload" className="ml-6 inline-block font-semibold underline underline-offset-4">Upload a menu</Link></div> : <>
            <div className="mt-7 grid items-start gap-6 md:grid-cols-2">{data.results.map(match => <div key={match.item.id} className="min-w-0"><Link href={`/menu/${match.menu_id}#dish-${match.item.id}`} className="mb-3 block break-words text-sm text-[#59664e] underline decoration-[#bcc7aa] underline-offset-4">{match.menu_title} · {match.section_name} ↗</Link><DishCard item={match.item} language="en" />{match.matched_inferred_tags.length > 0 && <p className="mt-2 text-xs text-[#69735f]">Matched AI-suggested tags: {match.matched_inferred_tags.join(", ")}</p>}</div>)}</div>
            <nav aria-label="Search result pages" className="mt-8 flex flex-wrap items-center gap-5"><button disabled={data.offset === 0} onClick={() => run({filters:data.intent,offset:Math.max(0,data.offset-data.limit),limit:data.limit})} className="rounded-full border border-[#b8c2aa] px-5 py-2.5 text-sm font-semibold disabled:opacity-40">Previous</button><span className="text-sm text-[#66705f]">{data.offset+1}–{data.offset+data.results.length} of {data.total}</span><button disabled={!data.has_more} onClick={() => run({filters:data.intent,offset:data.offset+data.limit,limit:data.limit})} className="rounded-full border border-[#b8c2aa] px-5 py-2.5 text-sm font-semibold disabled:opacity-40">Next</button></nav>
          </>}
        </>}
      </section> : <section className="rounded-3xl border border-[#dce0d2] bg-[#fffefa] p-7 sm:p-9"><h2 className="font-serif text-3xl">Start with what you love.</h2><p className="mt-3 max-w-xl leading-relaxed text-[#66705f]">A favorite ingredient, something sweet, or a comforting bowl of soup. Explore what’s already on the menu.</p><button onClick={() => run({filters:{}})} className="mt-5 font-semibold underline underline-offset-4">Browse all saved dishes ↗</button></section>}
      <p className="mt-9 text-xs leading-relaxed text-[#737b68]">Search matches saved menu information and optional AI-suggested tags. It does not verify allergens or dietary safety. Ask the restaurant about your needs.</p>
    </main>
  </div>;
}
