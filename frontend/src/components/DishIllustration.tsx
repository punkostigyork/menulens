"use client";
import { useEffect, useRef, useState } from "react";
import type { GeneratedImage } from "@/types/menu";
import { dishImage } from "@/services/api";

export default function DishIllustration({itemId, name, initialImage}: {itemId:string; name:string; initialImage:GeneratedImage | null}) {
  const [image, setImage] = useState(initialImage);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState("");
  const [unavailable, setUnavailable] = useState(false);
  const [reload, setReload] = useState(0);
  const inFlight = useRef(false);
  const mounted = useRef(true);
  const processing = image?.status === "processing";
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!processing) return;
    const abort = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const result = await dishImage(itemId,"GET",abort.signal);
        if (abort.signal.aborted) return;
        setImage(result); setError("");
        if (result.status !== "processing") return;
      } catch {
        if (abort.signal.aborted) return;
        setError("Connection interrupted. Checking your illustration again…");
      }
      timer = setTimeout(poll,2000);
    }
    timer = setTimeout(poll,1000);
    return () => { abort.abort(); clearTimeout(timer); };
  },[itemId,processing]);
  async function generate() {
    if (inFlight.current || processing) return;
    inFlight.current = true; setStarting(true); setError("");
    try {
      const result = await dishImage(itemId,"POST");
      if (mounted.current) {setImage(result); setUnavailable(false);}
    } catch (cause) {
      if (mounted.current) setError(cause instanceof TypeError ? "Connection lost. Please try again." : cause instanceof Error ? cause.message : "We couldn't create the illustration.");
    } finally {inFlight.current = false; if (mounted.current) setStarting(false);}
  }
  return <div className="mt-6">
    {image?.status === "ready" && image.image_url ? <figure>
      {unavailable ? <div role="alert" className="rounded-2xl bg-[#eff1e8] p-6 text-sm"><p>The saved illustration couldn't be loaded.</p><button onClick={() => {setUnavailable(false); setReload(value=>value+1);}} className="mt-3 underline underline-offset-4">Reload illustration</button></div> : <img src={`${image.image_url}${reload ? `?retry=${reload}` : ""}`} alt={`AI-generated illustration of ${name}, not an actual restaurant photo`} width={1024} height={1024} loading="lazy" onError={() => setUnavailable(true)} className="aspect-square w-full rounded-2xl bg-[#eff1e8] object-cover" />}
      <figcaption className="mt-2 text-xs leading-relaxed text-[#69735f]"><span className="font-semibold">AI-generated illustration</span><span className="block">Representative only. Not a photo from the restaurant.</span></figcaption>
    </figure> : processing ? <div role="status" className="rounded-2xl bg-[#eff1e8] p-6"><div aria-hidden="true" className="mb-4 h-20 motion-safe:animate-pulse rounded-xl bg-[#dfe6d1]" /><p className="text-sm font-semibold">Creating your food illustration…</p><p className="mt-2 text-xs text-[#69735f]">This may take a few minutes. Your menu is still available.</p></div> : <>
      {image?.status === "failed" && <p role="alert" className="mb-3 text-sm text-[#8b3521]">{image.error_message || "The illustration couldn't be created."}</p>}
      <button disabled={starting} onClick={generate} className="rounded-full border border-[#b5c2a4] px-4 py-2.5 text-sm font-semibold text-[#40572d] hover:bg-[#edf1e3] disabled:opacity-50">{starting ? "Starting illustration…" : image?.status === "failed" ? "Retry food illustration" : "Create food illustration"}</button>
      <p className="mt-2 text-xs leading-relaxed text-[#69735f]">Optional AI-generated illustration. Sends dish details to the image provider; generation charges may apply.</p>
    </>}
    {error && <p role="alert" className="mt-3 text-sm text-[#8b3521]">{error}</p>}
  </div>;
}
