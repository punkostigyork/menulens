"use client";
import Link from "next/link";
import {useEffect, useState} from "react";
import MenuView from "@/components/MenuView";
export default function DemoPage() {
  const [id, setId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setError("");
    fetch("/api/demo", {signal:controller.signal, cache:"no-store"}).then(async response => {
      if (!response.ok) throw new Error("We couldn't load the sample menu. Please try again.");
      const data = await response.json();
      if (!data.menu_id) throw new Error("The sample menu isn't available on this installation yet. You can still download it or upload your own.");
      if (!controller.signal.aborted) setId(data.menu_id);
    }).catch(cause => {if (!controller.signal.aborted) setError(cause instanceof TypeError ? "Check your connection and try again." : cause.message);});
    return () => controller.abort();
  }, [attempt]);
  if (id) return <MenuView id={id} />;
  return <main className="mx-auto max-w-2xl px-6 py-24"><Link href="/" className="font-semibold">MenuLens</Link><h1 className="mt-8 font-serif text-4xl">A taste of Hungary.</h1>{error ? <><p role="alert" className="mt-5 leading-7">{error}</p><button className="mt-6 rounded-full bg-[#243e32] px-6 py-3 text-white" onClick={() => setAttempt(a => a + 1)}>Try again</button><p className="mt-5"><a href="/api/demo/source" className="underline">Download the sample PDF</a> · <Link href="/upload" className="underline">Upload a menu</Link></p></> : <p role="status" className="mt-5">Opening the sample menu…</p>}</main>;
}
