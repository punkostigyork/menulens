"use client";
export default function MenuError({ reset }: { reset: () => void }) {
  return <main className="mx-auto max-w-xl px-6 py-24 text-center"><h1 className="font-serif text-4xl">We couldn’t open this menu.</h1><p className="mt-4 text-[#66705f]">Please try again in a moment.</p><button className="mt-6 rounded-full bg-[#243e32] px-6 py-3 font-semibold text-white" onClick={reset}>Try again</button></main>;
}
