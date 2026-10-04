"use client";
import { useEffect, useRef, useState } from "react";
import DishIllustration from "./DishIllustration";
import type { Explanation, ExplanationLanguage, MenuItem } from "@/types/menu";
import { getExplanation, requestExplanation } from "@/services/api";

function priceLabel(item: MenuItem, language: ExplanationLanguage) {
  if (item.price === null) return "Price not listed";
  const amount = Number(item.price);
  if (!Number.isFinite(amount)) return "Price unavailable";
  const price = new Intl.NumberFormat(language === "hu" ? "hu-HU" : "en-GB", { maximumFractionDigits: 2 }).format(amount);
  return item.currency ? `${price} ${item.currency}` : `${price} · currency not listed`;
}

export default function DishCard({ item, language }: { item: MenuItem; language: ExplanationLanguage }) {
  const [explanations, setExplanations] = useState<Explanation[]>(item.explanations || []);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  const mounted = useRef(true);
  const activeLanguage = useRef(language);
  activeLanguage.current = language;
  const explanation = explanations.find(entry => entry.language === language);
  const processing = explanation?.status === "processing";
  const titleId = `dish-${item.id}`;

  function remember(result: Explanation) {
    setExplanations(current => [...current.filter(entry => entry.language !== result.language), result]);
  }
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => { setError(""); }, [language]);
  useEffect(() => {
    if (!processing) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const result = await getExplanation(item.id, language, controller.signal);
        if (controller.signal.aborted) return;
        remember(result); setError("");
        if (result.status !== "processing") return;
      } catch {
        if (controller.signal.aborted) return;
        setError("Connection interrupted. Checking again…");
      }
      timer = setTimeout(poll, 2000);
    }
    timer = setTimeout(poll, 1000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [item.id, language, processing]);

  async function explain() {
    if (inFlight.current || processing) return;
    inFlight.current = true; setRequesting(true); setError("");
    try {
      const result = await requestExplanation(item.id, language);
      if (mounted.current) remember(result);
    } catch (cause) {
      if (mounted.current && activeLanguage.current === language) setError(cause instanceof TypeError ? "Connection lost. Check your connection and try again." : cause instanceof Error ? cause.message : "Please try again.");
    } finally {
      inFlight.current = false;
      if (mounted.current) setRequesting(false);
    }
  }

  return <article aria-labelledby={titleId} className="flex flex-col rounded-3xl border border-[#dde1d5] bg-[#fffefa] p-6 sm:p-8">
    <div className="flex flex-wrap items-start justify-between gap-3">
      <h3 id={titleId} className="scroll-mt-24 min-w-0 flex-1 basis-48 break-words font-serif text-[1.75rem] leading-tight">{item.name}</h3>
      <p className="rounded-full bg-[#eff1e8] px-3.5 py-2 text-sm font-semibold tabular-nums">{priceLabel(item, language)}</p>
    </div>
    {item.original_description && <div className="mt-6"><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#6b745e]">On the menu</p><p className="mt-2 whitespace-pre-line break-words text-[15px] leading-relaxed text-[#52604e]">{item.original_description}</p></div>}
    {item.ingredients.length > 0 && <div className="mt-5"><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#6b745e]">Listed ingredients</p><p className="mt-2 break-words text-sm leading-relaxed text-[#52604e]">{item.ingredients.join(" · ")}</p></div>}
    {!item.original_description && item.ingredients.length === 0 && <p className="mt-5 text-sm leading-relaxed text-[#66705f]">No description or ingredients were listed for this dish.</p>}
    {item.tags.length > 0 && <div className="mt-5"><p className="mb-2 text-xs text-[#69735f]">Menu tags</p><ul aria-label="Menu tags" className="flex flex-wrap gap-2">{item.tags.map(tag => <li key={tag} className="rounded-full bg-[#eff1e8] px-3 py-1 text-xs">{tag}</li>)}</ul></div>}
    <DishIllustration itemId={item.id} name={item.name} initialImage={item.generated_image || null} />
    <div className="mt-auto pt-6">
      <div className="border-t border-[#e4e7dd] pt-5" aria-live="polite">
        {explanation?.status === "ready" ? <>
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-[#68783f]">✧ AI explanation · {language === "en" ? "English" : "Magyar"}</p>
          <p lang={language} className="mt-2.5 break-words text-[15px] leading-relaxed">{explanation.description}</p>
          {explanation.tags.length > 0 && <div className="mt-4"><p className="mb-2 text-xs text-[#69735f]">AI-suggested tags</p><ul aria-label="AI-suggested tags" className="flex flex-wrap gap-2">{explanation.tags.map(tag => <li key={tag} className="rounded-full border border-[#d9e0c7] bg-[#f0f3e7] px-2.5 py-1 text-xs text-[#526536]">{tag}</li>)}</ul></div>}
        </> : processing ? <p role="status" className="text-sm text-[#68783f]">Generating description…</p> : <>
          {explanation?.status === "failed" && <p className="mb-3 text-sm text-[#8b3521]">{explanation.error_message || "The explanation couldn't be created."}</p>}
          <button type="button" disabled={requesting} onClick={explain} className="rounded-full border border-[#b5c2a4] px-4 py-2.5 text-sm font-semibold text-[#40572d] transition-colors hover:bg-[#edf1e3] disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-4">{requesting ? "Starting…" : explanation?.status === "failed" ? "Try explanation again" : language === "en" ? "✧ Explain this dish" : "✧ Magyarázd el az ételt"}</button>
        </>}
        {error && <p role="alert" className="mt-3 text-sm text-[#8b3521]">{error}</p>}
      </div>
    </div>
  </article>;
}
