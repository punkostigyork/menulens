"use client";
import Link from "next/link";
import {useCallback, useEffect, useRef, useState} from "react";
import Map from "@/components/Map";
import RestaurantCard, {PlaceFacts, PlaceAttributions} from "@/components/RestaurantCard";
import {nearbyPlaces} from "@/services/api";
import type {Coordinates, Place, PlaceType} from "@/types/places";

const BUDAPEST = {latitude:47.4979, longitude:19.0402};
const categories: {value: PlaceType; label: string}[] = [{value:"restaurant",label:"Restaurants"},{value:"cafe",label:"Cafes"},{value:"bar",label:"Bars"}];
export default function ExplorePlaces() {
  const [center, setCenter] = useState<Coordinates | null>(null);
  const [locationName, setLocationName] = useState("");
  const [type, setType] = useState<PlaceType>("restaurant");
  const [radius, setRadius] = useState(1500);
  const [places, setPlaces] = useState<Place[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [locating, setLocating] = useState(false);
  const [error, setError] = useState("");
  const [locationError, setLocationError] = useState("");
  const [searched, setSearched] = useState(false);
  const [summary, setSummary] = useState("");
  const [view, setView] = useState<"both" | "list">("both");
  const request = useRef<AbortController | null>(null);
  const locationSequence = useRef(0);
  useEffect(() => () => { request.current?.abort(); locationSequence.current += 1; }, []);
  const reset = () => {request.current?.abort(); setPlaces([]); setSelectedId(null); setBusy(false); setError(""); setSearched(false);};
  const chooseLocation = (point: Coordinates, label: string) => {reset(); setCenter(point); setLocationName(label); setLocationError("");};
  function locate() {
    if (!navigator.geolocation) {setLocationError("Your browser doesn't support location access. You can explore central Budapest instead."); return;}
    const sequence = ++locationSequence.current;
    setLocating(true); setLocationError("");
    navigator.geolocation.getCurrentPosition(position => {
      if (sequence !== locationSequence.current) return;
      setLocating(false); chooseLocation({latitude:position.coords.latitude, longitude:position.coords.longitude}, "Your current location");
    }, error => {
      if (sequence !== locationSequence.current) return;
      setLocating(false);
      setLocationError(error.code === 1 ? "Location permission was declined. Allow location in your browser or explore central Budapest." : "We couldn't find your location. Try again or explore central Budapest.");
    }, {enableHighAccuracy:false, timeout:10000, maximumAge:60000});
  }
  async function search() {
    if (!center) return;
    request.current?.abort();
    const controller = new AbortController(); request.current = controller;
    setBusy(true); setError(""); setPlaces([]); setSelectedId(null); setSearched(false);
    try {
      const result = await nearbyPlaces(center, type, radius, controller.signal);
      if (controller.signal.aborted) return;
      setPlaces(result.places); setSearched(true);
      setSummary(`${categories.find(c => c.value === type)?.label} within ${radius / 1000} km · ${locationName}`);
    } catch (e) {if (!controller.signal.aborted) setError(e instanceof Error ? e.message : "We couldn't find nearby places.");}
    finally {if (!controller.signal.aborted) setBusy(false);}
  }
  const select = useCallback((id: string) => setSelectedId(id), []);
  const selected = places.find(p => p.id === selectedId);
  return <div className="mx-auto min-h-svh max-w-7xl px-5 pb-12 sm:px-10">
    <header className="flex flex-wrap items-center justify-between gap-4 border-b border-[#243e32]/15 py-6">
      <Link href="/" className="text-xl font-semibold tracking-tight">MenuLens<span className="text-[#738348]">.</span></Link>
      <nav aria-label="Main navigation" className="flex gap-5 text-sm"><Link href="/upload">Upload a menu</Link><Link href="/search">Find a dish</Link></nav>
    </header>
    <main>
      <div className="pb-8 pt-12 sm:pt-16"><p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#68754c]">Around the corner</p><h1 className="mt-4 font-serif text-5xl tracking-tight sm:text-6xl">Find your next favorite.</h1><p className="mt-5 max-w-xl text-lg leading-7 text-[#59645b]">A quiet coffee, a long lunch, or one more drink. Discover the places around you.</p></div>
      <section aria-label="Choose a location" className="rounded-3xl bg-[#e8eddf] p-6">
        <div className="flex flex-wrap items-center gap-3"><button type="button" onClick={locate} disabled={locating} className="rounded-full bg-[#243e32] px-6 py-3 font-semibold text-white disabled:opacity-60">{locating ? "Finding your location…" : "Use my location"}</button>
        <button type="button" onClick={() => {locationSequence.current += 1; setLocating(false); chooseLocation(BUDAPEST,"Central Budapest");}} className="rounded-full border border-[#243e32]/30 px-6 py-3 font-semibold">Explore central Budapest</button></div>
        <p className="mt-3 text-sm text-[#59645b]">{center ? `Search location: ${locationName}.` : "Choose where to explore."} Location is used for this search and isn't stored by MenuLens.</p>
        <p className="mt-1 text-xs text-[#59645b]">Maps and nearby searches share the chosen area with Google. Your browser asks before sharing your location.</p>
        {locationError && <p role="alert" className="mt-3 text-sm text-[#943c2e]">{locationError}</p>}
      </section>
      <form onSubmit={e => {e.preventDefault(); void search();}} className="my-7 flex flex-wrap items-end gap-5">
        <fieldset><legend className="mb-2 text-sm font-semibold">What are you in the mood for?</legend><div className="flex flex-wrap gap-2">{categories.map(c => <label key={c.value} className={`cursor-pointer rounded-full border px-4 py-2.5 text-sm ${type === c.value ? "border-[#243e32] bg-[#243e32] text-white" : "border-[#243e32]/20 bg-white"}`}><input type="radio" name="category" value={c.value} checked={type === c.value} onChange={() => {reset(); setType(c.value);}} className="mr-2 accent-[#738348]" />{c.label}</label>)}</div></fieldset>
        <label className="text-sm font-semibold">Distance<select value={radius} onChange={e => {reset(); setRadius(Number(e.target.value));}} className="mt-2 block rounded-xl border border-[#243e32]/20 bg-white px-4 py-3 font-normal"><option value={500}>500 m</option><option value={1500}>1.5 km</option><option value={5000}>5 km</option><option value={10000}>10 km</option></select></label>
        <button disabled={!center || busy || locating} className="rounded-full bg-[#243e32] px-6 py-3 font-semibold text-white disabled:opacity-40">{busy ? "Finding places…" : "Find nearby places"}</button>
      </form>
      {error && <div role="alert" className="mb-6 rounded-2xl border border-[#943c2e]/20 bg-[#fff1eb] p-5 text-[#943c2e]">{error} <button onClick={() => void search()} className="ml-2 font-semibold underline">Try again</button></div>}
      {center && <div className="mb-5 flex items-center justify-between gap-3"><h2 className="font-serif text-2xl">{searched ? `${places.length} places to explore` : "Your neighborhood, waiting"}</h2><button onClick={() => setView(v => v === "both" ? "list" : "both")} className="shrink-0 rounded-full border border-[#243e32]/20 px-4 py-2 text-sm">{view === "both" ? "List only" : "Show map"}</button></div>}
      {searched && <p className="mb-5 text-sm text-[#59645b]">{summary}. Up to 20 nearest matches; this isn't a complete directory.</p>}
      <div className={view === "both" && center ? "grid items-start gap-6 lg:grid-cols-[1fr_1.2fr]" : ""}>
        <section aria-label="Nearby places" aria-busy={busy}>
          {busy && <div role="status" className="space-y-4"><p className="text-sm text-[#59645b]">Finding a few good places…</p>{[0,1,2].map(i => <div key={i} className="h-40 animate-pulse rounded-2xl bg-[#e8eddf]" />)}</div>}
          {!busy && searched && places.length === 0 && <div role="status" className="rounded-2xl border border-[#243e32]/15 p-8"><h3 className="font-serif text-2xl">A little further afield?</h3><p className="mt-3 text-[#59645b]">No places matched this search. Try a wider distance or another category.</p></div>}
          {!busy && !searched && !error && center && <p className="rounded-2xl border border-dashed border-[#243e32]/20 p-8 text-[#59645b]">Choose a category and find nearby places to start exploring.</p>}
          <ul className={`grid gap-4 ${view === "list" ? "sm:grid-cols-2 lg:grid-cols-3" : ""}`}>{places.map((place,index) => <RestaurantCard key={place.id} place={place} index={index} selected={selectedId === place.id} onSelect={() => select(place.id)} />)}</ul>
          {searched && <div className="px-3 pb-2 pt-4"><img src="/google-maps-logo.svg" alt="Google Maps" className="h-[18px] w-auto" /></div>}
        </section>
        {center && view === "both" && <div className="lg:sticky lg:top-6"><Map center={center} places={places} selectedId={selectedId} onSelect={select} />
          {selected && <section aria-label="Selected place" aria-live="polite" className="mt-4 rounded-2xl border border-[#243e32]/15 bg-white p-6"><h2 className="break-words font-serif text-3xl">{selected.name}</h2><p className="mt-2 text-[#59645b]">{selected.address || "Address unavailable"}</p><PlaceFacts place={selected} /><PlaceAttributions place={selected} /><a className="mt-4 inline-block text-sm font-semibold underline" href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(selected.name)}&query_place_id=${encodeURIComponent(selected.id)}`} target="_blank" rel="noopener noreferrer">Open in Google Maps ↗</a></section>}
        </div>}
      </div>
    </main>
    <footer className="mt-14 border-t border-[#243e32]/15 pt-6 text-xs leading-6 text-[#59645b]">Place information provided by Google Maps. <a className="underline" href="https://policies.google.com/privacy" target="_blank" rel="noopener noreferrer">Google Privacy Policy</a> · <a className="underline" href="https://www.google.com/help/terms_maps/" target="_blank" rel="noopener noreferrer">Google Maps terms</a></footer>
  </div>;
}
