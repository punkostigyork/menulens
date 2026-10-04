import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { icons: { icon: "/icon.svg" }, title: "MenuLens — A little clarity. A great meal.", description: "Understand unfamiliar dishes and discover your next favorite meal with MenuLens." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
