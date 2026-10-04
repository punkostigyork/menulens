import MenuView from "@/components/MenuView";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "Your menu — MenuLens" };

export default async function MenuPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <MenuView id={id} />;
}
