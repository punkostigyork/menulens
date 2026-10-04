import type { ExplanationLanguage, MenuSectionData } from "@/types/menu";
import DishCard from "./DishCard";

export default function MenuSection({ section, language }: { section: MenuSectionData; language: ExplanationLanguage }) {
  return <section id={`section-${section.id}`} aria-labelledby={`heading-${section.id}`} className="scroll-mt-28 py-8 sm:py-10">
    <div className="mb-6 flex items-baseline gap-3"><h2 id={`heading-${section.id}`} className="break-words font-serif text-4xl">{section.name}</h2><span className="text-sm text-[#76806b]">{section.items.length}</span></div>
    {section.items.length ? <div className="grid items-start gap-5 md:grid-cols-2">{section.items.map(item => <DishCard key={item.id} item={item} language={language} />)}</div> : <p className="text-[#66705f]">No dishes were found in this section.</p>}
  </section>;
}
