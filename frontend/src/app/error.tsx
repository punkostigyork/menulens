"use client";
import Link from "next/link";
export default function ErrorPage({reset}: {reset: () => void}) {return <main className="mx-auto max-w-2xl px-6 py-24"><h1 className="font-serif text-4xl">Something didn't load.</h1><p role="alert" className="mt-5 text-[#59645b]">Please try again. Your saved menus are still there.</p><button onClick={reset} className="mt-7 rounded-full bg-[#243e32] px-6 py-3 text-white">Try again</button><Link href="/" className="ml-5 underline">Go home</Link></main>;}
