import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "d-design",
  description: "A deck that looks designed and says one thing.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
