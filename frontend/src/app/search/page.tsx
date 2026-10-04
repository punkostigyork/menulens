import type { Metadata } from "next";
import DishSearch from "@/components/DishSearch";
export const metadata: Metadata = { title: "Find a dish — MenuLens" };
export default function SearchPage() { return <DishSearch />; }
