import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Alchymine — Personal Transformation Operating System',
  description:
    'Discover who you truly are through five integrated systems: Identity, Healing, Wealth, Creative, and Perspective. Open-source, AI-powered personal transformation.',
  keywords: [
    'personal transformation',
    'numerology',
    'astrology',
    'personality assessment',
    'self-discovery',
    'archetype',
    'big five',
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="font-sans bg-bg text-text min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
