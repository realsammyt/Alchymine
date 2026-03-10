import type { Metadata, Viewport } from "next";
import localFont from "next/font/local";
import "./globals.css";
import Navigation from "@/components/shared/Navigation";
import ContentWrapper from "@/components/shared/ContentWrapper";
import FeedbackButton from "@/components/shared/FeedbackButton";
import { Providers } from "./providers";

const cormorant = localFont({
  src: [
    { path: "../fonts/CormorantGaramond-Latin.woff2", style: "normal" },
    { path: "../fonts/CormorantGaramond-LatinItalic.woff2", style: "italic" },
  ],
  variable: "--font-display",
  display: "swap",
});

const outfit = localFont({
  src: [{ path: "../fonts/Outfit-Variable.woff2", style: "normal" }],
  variable: "--font-body",
  display: "swap",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
  themeColor: "#0A0A0F",
};

export const metadata: Metadata = {
  title: "Alchymine — Personal Transformation Operating System",
  description:
    "Discover who you truly are through five integrated systems: Intelligence, Healing, Wealth, Creative, and Perspective. Open-source, AI-powered personal transformation.",
  keywords: [
    "personal transformation",
    "numerology",
    "astrology",
    "personality assessment",
    "self-discovery",
    "archetype",
    "big five",
  ],
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Alchymine",
  },
  other: {
    "mobile-web-app-capable": "yes",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${cormorant.variable} ${outfit.variable}`}>
      <head>
        {/* PWA: Apple touch icon (placeholder — replace with real asset) */}
        <link rel="apple-touch-icon" href="/icon-192.png" />
        {/* Preconnect to API origin for faster first requests */}
        {process.env.NEXT_PUBLIC_API_URL && (
          <link
            rel="preconnect"
            href={new URL(process.env.NEXT_PUBLIC_API_URL).origin}
          />
        )}
      </head>
      <body className="font-body bg-bg text-text min-h-screen antialiased">
        <Providers>
          {/* Skip navigation — first focusable element, visible on keyboard focus */}
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-[9999] focus:bg-primary focus:text-bg focus:px-4 focus:py-2 focus:rounded-lg focus:text-sm focus:font-body focus:outline-none"
          >
            Skip to main content
          </a>
          <Navigation />
          <ContentWrapper>{children}</ContentWrapper>
          <FeedbackButton />
        </Providers>
      </body>
    </html>
  );
}
