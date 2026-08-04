import type { Metadata } from 'next';

import './globals.css';

export const metadata: Metadata = {
  title: 'd-design',
  description: 'AI presentation-experience engine',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
