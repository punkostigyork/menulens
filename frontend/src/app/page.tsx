import Link from "next/link";

export default function Home() {
  return (
    <div className="mx-auto flex min-h-svh max-w-7xl flex-col px-6 sm:px-12">
      <header className="flex items-center gap-3 border-b border-[#243e32]/15 py-7">
        <span aria-hidden="true" className="flex size-9 items-center justify-center rounded-full bg-[#243e32] text-lg text-[#f7f5ee]">m.</span>
        <span className="text-xl font-semibold tracking-tight">MenuLens</span>
      </header>
      <main className="flex flex-1 items-center py-20 sm:py-28">
        <div className="max-w-3xl">
          <p className="mb-7 text-xs font-semibold uppercase tracking-[0.22em] text-[#68754c]">A little clarity. A great meal.</p>
          <h1 className="font-serif text-6xl leading-[1.06] tracking-tight sm:text-8xl">Less guessing.<br /><span className="text-[#738348]">More savoring.</span></h1>
          <p className="mt-8 max-w-xl text-lg leading-relaxed text-[#59645b] sm:text-xl">Meet MenuLens. Turn unfamiliar menus into dishes you understand, and discover your next favorite place to eat.</p>
          <div className="mt-10">
            <Link href="/upload" aria-describedby="upload-note" className="inline-flex items-center gap-8 rounded-full bg-[#243e32] px-7 py-4 text-base font-semibold text-white">Upload a menu <span aria-hidden="true">↗</span></Link>
            <Link href="/search" className="ml-0 mt-3 inline-flex rounded-full border border-[#aebd9d] px-7 py-4 font-semibold sm:ml-4 sm:mt-0">Find a dish ↗</Link>
            <Link href="/explore" className="ml-0 mt-3 inline-flex rounded-full border border-[#aebd9d] px-7 py-4 font-semibold sm:ml-4 sm:mt-0">Explore nearby ↗</Link>
            <p className="mt-6"><Link href="/demo" className="font-semibold underline underline-offset-4">Try a Hungarian sample menu</Link><span className="mt-2 block text-sm text-[#66705f]">Four dishes to explore. No upload or API key needed.</span></p>
            <p id="upload-note" className="mt-4 text-sm text-[#66705f]">Bring a menu. PDF, JPG or PNG.</p>
          </div>
        </div>
      </main>
      <footer className="border-t border-[#243e32]/15 py-6 text-sm text-[#66705f]">A world of food. A little easier to explore.</footer>
    </div>
  );
}
