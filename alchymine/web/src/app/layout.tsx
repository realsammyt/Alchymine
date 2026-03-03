import type { Metadata, Viewport } from "next";
import { Cormorant_Garamond, Outfit } from "next/font/google";
import "./globals.css";
import Navigation from "@/components/shared/Navigation";
import ContentWrapper from "@/components/shared/ContentWrapper";
import { Providers } from "./providers";

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  style: ["normal", "italic"],
  variable: "--font-display",
  display: "swap",
});

const outfit = Outfit({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
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
      </head>
      <body className="font-body bg-bg text-text min-h-screen antialiased">
        <Providers>
          <Navigation />
          <ContentWrapper>{children}</ContentWrapper>
        </Providers>
      </body>
    </html>
  );
}
