import type { Place } from "@/types/places";
export function PlaceFacts({place}: {place: Place}) {
  const prices = ["Free", "Inexpensive", "Moderate", "Expensive", "Very expensive"];
  return <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-sm text-[#59645b]">
    <span className="capitalize">{place.category}</span>
    {place.rating !== null && <span aria-label={`${place.rating} out of 5 stars`}>★ {place.rating.toFixed(1)}</span>}
    {place.price_level !== null && <span>{prices[place.price_level]}</span>}
  </p>;
}
export function PlaceAttributions({place}: {place: Place}) {
  return place.attributions.length > 0 && <p className="mt-3 text-xs text-[#59645b]">Data: {place.attributions.map((a,i) => <span key={i}>{i > 0 && ", "}{a.url ? <a href={a.url} target="_blank" rel="noopener noreferrer" className="underline">{a.name}</a> : a.name}</span>)}</p>;
}
export default function RestaurantCard({place, index, selected, onSelect}: {place: Place; index: number; selected: boolean; onSelect: () => void}) {
  return <li className={`rounded-2xl border bg-white p-5 transition ${selected ? "border-[#243e32] ring-1 ring-[#243e32]" : "border-[#243e32]/15"}`}>
    <button type="button" aria-pressed={selected} onClick={onSelect} className="w-full text-left focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-[#243e32]">
      <span className="text-xs font-semibold uppercase tracking-widest text-[#68754c]">{String(index + 1).padStart(2, "0")}</span>
      <h3 className="mt-2 break-words font-serif text-2xl">{place.name}</h3>
      <p className="mt-2 text-sm text-[#59645b]">{place.address || "Address unavailable"}</p>
      <PlaceFacts place={place} />
      <span className="mt-4 inline-block text-sm font-semibold">{selected ? "Selected place" : "View place"} ↗</span>
    </button>
    <PlaceAttributions place={place} />
  </li>;
}
