"use client";
import {useEffect, useRef, useState} from "react";
import {getMapsConfig} from "@/services/api";
import {loadMaps, type GoogleMap, type MapsSdk, type Marker} from "@/services/googleMaps";
import type {Coordinates, Place} from "@/types/places";

export default function Map({center, places, selectedId, onSelect}: {center: Coordinates; places: Place[]; selectedId: string | null; onSelect: (id: string) => void}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<GoogleMap | null>(null);
  const sdk = useRef<MapsSdk | null>(null);
  const select = useRef(onSelect); select.current = onSelect;
  const initialCenter = useRef(center);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let disposed = false;
    setError(""); setReady(false);
    const authFailure = () => {setError("The map is unavailable. You can still browse the list."); setReady(false);};
    window.addEventListener("menulens-map-error", authFailure);
    (async () => {
      try {
        const config = await getMapsConfig(controller.signal);
        if (!config.maps_api_key) throw new Error("The map isn't available yet. Nearby places can still appear in the list.");
        const maps = await loadMaps(config.maps_api_key);
        if (disposed || !container.current) return;
        sdk.current = maps;
        map.current = new maps.Map(container.current, {center:{lat:initialCenter.current.latitude, lng:initialCenter.current.longitude}, zoom:14, mapId:config.maps_map_id, mapTypeControl:false, streetViewControl:false, fullscreenControl:true, gestureHandling:"cooperative"});
        setReady(true);
      } catch (e) { if (!disposed) setError(e instanceof Error ? e.message : "The map couldn't load."); }
    })();
    return () => {disposed = true; controller.abort(); window.removeEventListener("menulens-map-error", authFailure); map.current = null;};
  }, [attempt]);
  useEffect(() => {
    if (!ready || !map.current || !sdk.current) return;
    const currentMap = map.current, maps = sdk.current;
    const markers: Marker[] = [];
    const listeners: {remove(): void}[] = [];
    const origin = {lat:center.latitude, lng:center.longitude};
    const centerDot = document.createElement("div");
    centerDot.textContent = "◎"; centerDot.style.cssText = "background:white;color:#243e32;border:2px solid #243e32;border-radius:50%;padding:4px 8px;font-size:22px";
    markers.push(new maps.marker.AdvancedMarkerElement({map:currentMap, position:origin, title:"Search center", content:centerDot}));
    const bounds = new maps.LatLngBounds(); bounds.extend(origin);
    places.forEach((place, index) => {
      const point = {lat:place.latitude, lng:place.longitude}; bounds.extend(point);
      const pin = document.createElement("div"); pin.textContent = String(index + 1);
      pin.style.cssText = "background:#243e32;color:white;border:2px solid white;border-radius:50%;min-width:32px;height:32px;display:grid;place-items:center;font-weight:700;box-shadow:0 2px 8px #0004";
      const marker = new maps.marker.AdvancedMarkerElement({map:currentMap, position:point, title:place.name, content:pin});
      listeners.push(marker.addListener("click", () => select.current(place.id))); markers.push(marker);
    });
    if (places.length) currentMap.fitBounds(bounds, 55); else {currentMap.panTo(origin); currentMap.setZoom(14);}
    return () => {listeners.forEach(l => l.remove()); markers.forEach(m => {m.map = null;});};
  }, [ready, center, places]);
  useEffect(() => {
    const selected = places.find(p => p.id === selectedId);
    if (ready && selected) map.current?.panTo({lat:selected.latitude, lng:selected.longitude});
  }, [selectedId, places, ready]);
  return <div className="relative overflow-hidden rounded-3xl border border-[#243e32]/15 bg-[#e8eddf]">
    <div ref={container} aria-label="Map of nearby places" className="h-[360px] sm:h-[480px]" />
    {!ready && <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center">
      <span aria-hidden="true" className="mb-4 text-5xl text-[#738348]">◎</span>
      <p role="status" className="max-w-xs text-sm leading-6">{error || "Loading the map…"}</p>
      {error && <button className="mt-4 rounded-full border border-[#243e32]/30 px-5 py-2 text-sm" onClick={() => setAttempt(a => a + 1)}>Retry map</button>}
    </div>}
  </div>;
}
