"use client";

import { useEffect, useRef, useState } from "react";
import { getUploadLimit, uploadMenu, getMenu } from "@/services/api";
import MenuProcessing from "@/components/MenuProcessing";
import type { Menu } from "@/types/menu";

const buttonStyle = "rounded-full bg-[#243e32] px-7 py-3.5 font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#243e32]";

export default function MenuUpload() {
  const [restoring, setRestoring] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [limit, setLimit] = useState<number | null>(null);
  const [configError, setConfigError] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [menu, setMenu] = useState<Menu | null>(null);
  const [dragging, setDragging] = useState(false);
  const picker = useRef<HTMLInputElement>(null);
  const inFlight = useRef(false);

  async function loadConfig() {
    setConfigError(false);
    try { setLimit(await getUploadLimit()); }
    catch { setConfigError(true); }
  }
  useEffect(() => { void loadConfig(); }, []);
  useEffect(() => {
    const controller = new AbortController();
    const id = new URLSearchParams(window.location.search).get("menu");
    if (!id) { setRestoring(false); return; }
    getMenu(id, controller.signal).then(setMenu).catch(() => {
      if (!controller.signal.aborted) setError("We couldn't reopen your menu. Refresh to try again, or upload a new file.");
    }).finally(() => { if (!controller.signal.aborted) setRestoring(false); });
    return () => controller.abort();
  }, []);

  function selectFiles(files: FileList | null) {
    setDragging(false);
    if (inFlight.current || !limit || !files?.length) return;
    setError(""); setMenu(null); setFile(null);
    const selected = files[0];
    if (files.length !== 1) { setError("Please choose one menu at a time."); return; }
    if (!/\.(pdf|jpe?g|png)$/i.test(selected.name)) { setError("Choose a PDF, JPG, JPEG, or PNG file."); return; }
    if (selected.size === 0) { setError("This file is empty. Please choose another menu."); return; }
    if (selected.size > limit) { setError(`Choose a file smaller than ${Math.round(limit / 1024 / 1024)} MB.`); return; }
    setFile(selected);
  }

  async function submit() {
    if (!file || inFlight.current) return;
    inFlight.current = true; setUploading(true); setProgress(0); setError("");
    try {
      const saved = await uploadMenu(file, setProgress);
      setMenu(saved); setFile(null);
      window.history.replaceState(null, "", `/upload?menu=${encodeURIComponent(saved.id)}`);
    }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Upload failed. Please try again."); }
    finally { inFlight.current = false; setUploading(false); }
  }

  if (restoring) return <p role="status" className="mt-10">Loading menu…</p>;
  if (menu) return <MenuProcessing key={menu.id} initialMenu={menu} onReset={() => { setMenu(null); setError(""); window.history.replaceState(null, "", "/upload"); }} />;

  return <section className="mt-10" aria-label="Menu upload">
    {configError ? <div role="alert" className="rounded-2xl bg-[#f7e6df] p-6">Uploads are unavailable right now. <button className="underline" onClick={loadConfig}>Try again</button></div> : !limit ? <p role="status">Getting upload options…</p> : <>
      <div onDragOver={(event) => { event.preventDefault(); if (!uploading) setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={(event) => { event.preventDefault(); selectFiles(event.dataTransfer.files); }} className={`rounded-3xl border-2 border-dashed p-8 text-center transition-colors sm:p-12 ${dragging ? "border-[#738348] bg-[#edf1e3]" : "border-[#b5bfa8] bg-white/40"}`}>
        <span aria-hidden="true" className="mb-5 inline-flex size-12 items-center justify-center rounded-full bg-[#e9eddf] text-2xl">↑</span>
        <h2 className="text-xl font-semibold">Drop your menu here</h2>
        <p id="file-help" className="mt-2 text-sm text-[#66705f]">PDF, JPG, JPEG or PNG · Up to {Math.round(limit / 1024 / 1024)} MB</p>
        <input ref={picker} type="file" accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png" aria-label="Choose a menu file" aria-describedby="file-help" className="sr-only" tabIndex={-1} disabled={uploading} onChange={(event) => { selectFiles(event.target.files); event.target.value = ""; }} />
        <button type="button" disabled={uploading} className={`${buttonStyle} mt-6`} onClick={() => picker.current?.click()}>Choose a file</button>
      </div>
      {file && <div className="mt-5 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-[#243e32]/15 p-5">
        <div className="min-w-0 flex-1"><p className="break-all font-semibold">{file.name}</p><p className="mt-1 text-sm text-[#66705f]">{(file.size / 1024 / 1024).toFixed(2)} MB</p></div>
        <button disabled={uploading} onClick={submit} className={buttonStyle}>{uploading ? "Uploading…" : error ? "Retry upload" : "Upload menu"}</button>
      </div>}
      {uploading && <div className="mt-5" role="status" aria-live="polite"><p className="mb-2 text-sm">{progress === 100 ? "Saving your menu…" : `Uploading menu… ${progress}%`}</p><progress className="h-2 w-full accent-[#738348]" value={progress} max={100} aria-label="Upload progress" /></div>}
      {error && <p role="alert" className="mt-5 rounded-xl bg-[#f7e6df] p-4 text-[#8b3521]">{error}</p>}
    </>}
  </section>;
}
