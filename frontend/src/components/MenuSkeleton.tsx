export default function MenuSkeleton() {
  return <div role="status" aria-label="Loading menu" className="mx-auto max-w-6xl px-6 py-14 sm:px-10">
    <span className="sr-only">Loading your menu…</span>
    <div aria-hidden="true" className="motion-safe:animate-pulse">
      <div className="h-3 w-28 rounded bg-[#dfe4d7]" />
      <div className="mt-6 h-14 w-3/4 rounded-lg bg-[#dfe4d7]" />
      <div className="mt-6 h-4 w-1/2 rounded bg-[#e7e9df]" />
      <div className="mt-12 grid gap-6 md:grid-cols-2">{[0,1,2,3].map(i => <div key={i} className="h-64 rounded-3xl bg-[#e7e9df]" />)}</div>
    </div>
  </div>;
}
