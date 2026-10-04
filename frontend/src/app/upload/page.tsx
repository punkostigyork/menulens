import Link from "next/link";
import MenuUpload from "@/components/MenuUpload";

export default function UploadPage() {
  return <div className="mx-auto min-h-svh max-w-7xl px-6 sm:px-12">
    <header className="border-b border-[#243e32]/15 py-7"><Link href="/" className="text-xl font-semibold tracking-tight focus-visible:outline-2 focus-visible:outline-offset-4">MenuLens</Link></header>
    <main className="mx-auto max-w-2xl py-14 sm:py-20">
      <Link href="/" className="text-sm text-[#59645b] underline underline-offset-4">← Back to home</Link>
      <h1 className="mt-8 font-serif text-5xl leading-tight sm:text-6xl">Start with a menu.</h1>
      <p className="mt-5 text-lg leading-relaxed text-[#59645b]">A photo from your table. A PDF from your favorite spot. Keep your menu here for what comes next.</p>
      <MenuUpload />
      <p className="mt-6 text-sm"><Link href="/demo" className="font-semibold underline underline-offset-4">Just looking? Try the sample menu.</Link></p>
      <p className="mt-7 text-sm leading-relaxed text-[#66705f]">Upload a menu, understand its dishes and prices, then explore the menu with optional English or Hungarian explanations.</p>
    </main>
  </div>;
}
