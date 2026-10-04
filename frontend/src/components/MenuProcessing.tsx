"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { Menu } from "@/types/menu";
import { getMenu, processMenu } from "@/services/api";

export default function MenuProcessing({ initialMenu, onReset, onReady }: { initialMenu: Menu; onReset: () => void; onReady?: (menu: Menu) => void }) {
  const [menu, setMenu] = useState(initialMenu);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState("");
  const processing = menu.status === "processing";
  const processed = menu.status === "processed";

  useEffect(() => { if (processed && onReady) onReady(menu); }, [processed, menu, onReady]);

  useEffect(() => {
    if (!processing) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const latest = await getMenu(menu.id, controller.signal);
        if (controller.signal.aborted) return;
        setMenu(latest); setError("");
        if (latest.status !== "processing") return;
      } catch {
        if (controller.signal.aborted) return;
        setError("Connection interrupted. Reconnecting to check your menu…");
      }
      timer = setTimeout(poll, 2000);
    }
    timer = setTimeout(poll, 1000);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [menu.id, processing]);

  async function start() {
    if (requesting || processing) return;
    setRequesting(true); setError("");
    try { setMenu(await processMenu(menu.id)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Please try again."); }
    finally { setRequesting(false); }
  }

  const sectionCount = menu.sections?.length || 0;
  const items = menu.sections?.reduce((total, section) => total + section.items.length, 0) || 0;
  return <section aria-live="polite" className="mt-10 rounded-3xl border border-[#c9d6b9] bg-[#edf1e3] p-8">
    <span aria-hidden="true" className={`mb-5 flex size-10 items-center justify-center rounded-full bg-[#243e32] text-white ${processing ? "animate-pulse" : ""}`}>{processing ? "…" : processed ? "✓" : "↑"}</span>
    <h2 className="font-serif text-3xl">{processing ? "Understanding your menu…" : processed ? "Your menu is ready." : menu.status === "failed" ? "Let’s try that again." : "Menu saved."}</h2>
    <p className="mt-3 break-all font-semibold">{menu.original_filename}</p>
    <p className="mt-2 text-[#59645b]">{processing ? "Reading the dishes, sections, and prices. This may take a minute." : processed ? `${items} menu ${items === 1 ? "item" : "items"} saved across ${sectionCount} ${sectionCount === 1 ? "section" : "sections"}. Explore the dishes and their details.` : "Your file is safely stored. Next, let MenuLens read the dishes and prices."}</p>
    {processed && <Link href={`/menu/${menu.id}`} className="mt-6 inline-flex rounded-full bg-[#243e32] px-6 py-3 font-semibold text-white">View your menu <span aria-hidden="true" className="ml-4">↗</span></Link>}
    {menu.processing_error && <p role="alert" className="mt-4 text-[#8b3521]">{menu.processing_error}</p>}
    {error && <p role="alert" className="mt-4 text-[#8b3521]">{error}</p>}
    {!processed && !processing && <>
      <button disabled={requesting} onClick={start} className="mt-7 rounded-full bg-[#243e32] px-7 py-3.5 font-semibold text-white disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-4">{requesting ? "Starting…" : menu.status === "failed" ? "Try understanding again" : "Understand this menu"}</button>
      <p className="mt-3 text-sm text-[#66705f]">This sends your menu to the configured AI service for extraction.</p>
    </>}
    <button disabled={processing || requesting} className="mt-6 block text-sm underline underline-offset-4 disabled:opacity-50" onClick={onReset}>Upload another menu</button>
  </section>;
}
