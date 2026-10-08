import type { Metadata } from "next";
import "./globals.css";

import { TooltipProvider } from "@/components/ui/tooltip";
import { UserMenu } from "@/components/user-menu";

export const metadata: Metadata = {
  title: "d-design",
  description: "A deck that looks designed and says one thing.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-dvh">
        <TooltipProvider>
          <UserMenu />
          {children}
        </TooltipProvider>
      </body>
    </html>
  );
}
