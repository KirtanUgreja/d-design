import type { Metadata } from "next";
import { Brygada_1918, Instrument_Sans } from "next/font/google";
import "./globals.css";

import { AppBar } from "@/components/app-bar";
import { TooltipProvider } from "@/components/ui/tooltip";

// Self-hosted at build time: the page never asks Google for a font.
const display = Brygada_1918({ subsets: ["latin"], variable: "--font-brygada", display: "swap" });
const sans = Instrument_Sans({ subsets: ["latin"], variable: "--font-instrument", display: "swap" });

export const metadata: Metadata = {
  title: "d-design",
  description: "A deck that looks designed and says one thing.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable}`}>
      <body className="min-h-dvh">
        <TooltipProvider>
          <AppBar />
          {children}
        </TooltipProvider>
      </body>
    </html>
  );
}
