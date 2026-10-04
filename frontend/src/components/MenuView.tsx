"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { ExplanationLanguage, Menu } from "@/types/menu";
import { ApiError, getMenu } from "@/services/api";
import MenuSection from "./MenuSection";
import MenuProcessing from "./MenuProcessing";
import MenuSkeleton from "./MenuSkeleton";

export default function MenuView({ id }: { id: string }) {
  const [menu, setMenu] = useState<Menu | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [language, setLanguage] = useState<ExplanationLanguage>("en");
  useEffect(() => {
    const controller = new AbortController();
    setMenu(null); setError(null); setMissing(false);
    getMenu(id, controller.signal).then(value => { if (!controller.signal.aborted) setMenu(value); }).catch(cause => {
      if (controller.signal.aborted) return;
      if (cause instanceof ApiError && [404, 422].includes(cause.status)) { setMissing(true); setError("This menu link may be incorrect or the menu is no longer available."); }
      else setError("We couldn't load your menu. Check your connection and try again.");
    });
    return () => controller.abort();
  }, [id, attempt]);

  const sections = menu?.sections || [];
  const itemCount = sections.reduce((count, section) => count + section.items.length, 0);
  const title = menu?.restaurant_name || menu?.original_filename.replace(/\.[^.]+$/, "") || "Your menu";
  return <div className="min-h-svh">
    <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 border-b border-[#243e32]/15 px-6 py-6 sm:px-10">
      <Link href="/" className="flex items-center gap-2.5 text-xl font-semibold tracking-tight"><span aria-hidden="true" className="flex size-8 items-center justify-center rounded-full bg-[#243e32] font-serif text-lg text-[#f7f5ee]">m.</span>MenuLens</Link>
      <nav aria-label="Main navigation" className="flex flex-wrap justify-end gap-3"><Link href="/explore" className="px-2 py-2 text-sm font-semibold">Explore nearby</Link><Link href="/search" className="px-2 py-2 text-sm font-semibold">Find a dish</Link><Link href="/upload" className="rounded-full border border-[#b8c2aa] px-4 py-2 text-sm font-semibold hover:bg-[#edf1e3]">Upload a menu <span aria-hidden="true">↗</span></Link></nav>
    </header>
    {!menu && !error ? <MenuSkeleton /> : error ? <main className="mx-auto max-w-2xl px-6 py-24 text-center"><h1 className="font-serif text-4xl">{missing ? "Menu not found." : "Let’s try that again."}</h1><p role="alert" className="mt-5 leading-relaxed text-[#66705f]">{error}</p>{!missing && <button onClick={() => setAttempt(value => value + 1)} className="mt-7 rounded-full bg-[#243e32] px-6 py-3 font-semibold text-white">Try again</button>}<p className="mt-6"><Link href="/upload" className="text-sm underline underline-offset-4">Upload a different menu</Link></p></main> : menu && menu.status !== "processed" ? <main className="mx-auto max-w-2xl px-6 py-14"><h1 className="font-serif text-4xl">Your menu</h1><MenuProcessing key={menu.id} initialMenu={menu} onReset={() => window.location.assign("/upload")} onReady={setMenu} /></main> : menu && <>
      <main className="mx-auto max-w-6xl px-6 pb-16 sm:px-10">
        <div className="py-8 sm:py-10">
          {menu.is_demo && <aside className="mb-7 rounded-2xl border border-[#cbd3bd] bg-[#edf1e3] p-5 text-sm leading-6"><strong>A fictional Hungarian menu.</strong> These dishes, descriptions, prices and tags are hand-authored sample data. No AI extraction was used. <a href="/api/demo/source" className="font-semibold underline">Download the source PDF</a>.</aside>}
          <p className="mb-5 text-[11px] font-semibold uppercase tracking-[0.2em] text-[#738348]">A little clarity. A great meal.</p>
          <h1 className="max-w-4xl break-words font-serif text-5xl leading-[1.08] tracking-tight sm:text-6xl">{title}</h1>
          <p className="mt-5 text-[#69735f]">{itemCount} {itemCount === 1 ? "dish" : "dishes"} · {sections.length} {sections.length === 1 ? "section" : "sections"}{menu.currency ? ` · ${menu.currency}` : ""}</p>
          <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-[#66705f]">The menu, made a little clearer. Browse what’s on offer and ask for an explanation of anything unfamiliar.</p>
          <div className="mt-7 flex flex-wrap items-center gap-3"><span id="explanation-language" className="text-sm text-[#59664e]">Explanation language</span><div role="group" aria-labelledby="explanation-language" className="inline-flex rounded-full border border-[#cbd3bd] p-1">{([['en','English'],['hu','Magyar']] as const).map(([code,label]) => <button key={code} type="button" aria-pressed={language === code} onClick={() => setLanguage(code)} className={`rounded-full px-4 py-2 text-sm transition-colors ${language === code ? "bg-[#243e32] text-white" : "text-[#59664e] hover:bg-[#e7eddb]"}`}>{label}</button>)}</div></div>
        </div>
        {sections.length > 0 && <nav aria-label="Menu sections" className="sticky top-0 z-10 -mx-1 flex gap-2 overflow-x-auto border-y border-[#dce0d2] bg-[#f7f5ee]/95 px-1 py-3 backdrop-blur-sm">{sections.map(section => <a key={section.id} href={`#section-${section.id}`} className="shrink-0 rounded-full px-4 py-2 text-sm font-medium text-[#566444] hover:bg-[#e8eddc] focus-visible:outline-2 focus-visible:outline-offset-[-2px]">{section.name}<span className="ml-2 text-[#879075]">{section.items.length}</span></a>)}</nav>}
        {itemCount === 0 ? <section className="rounded-3xl border border-[#dce0d2] bg-[#fffefa] px-6 py-16 text-center"><h2 className="font-serif text-3xl">No dishes to show yet.</h2><p className="mt-3 text-[#66705f]">Try uploading a clearer menu with visible dish names and prices.</p><Link href="/upload" className="mt-6 inline-block underline underline-offset-4">Upload another menu</Link></section> : sections.map(section => <MenuSection key={section.id} section={section} language={language} />)}
        <aside className="mt-8 border-t border-[#dce0d2] pt-6 text-xs leading-relaxed text-[#737b68]"><p>Original text and listed ingredients come from the uploaded menu. AI explanations and suggested tags are separate and may be inaccurate. Ask the restaurant about allergens.</p><p className="mt-2">Requesting an explanation sends that dish’s details to the configured AI service.</p></aside>
      </main>
    </>}
  </div>;
}
