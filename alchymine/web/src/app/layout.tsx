import type { Metadata, Viewport } from "next";
import "./globals.css";
import Navigation from "@/components/shared/Navigation";
import ContentWrapper from "@/components/shared/ContentWrapper";
import { Providers } from "./providers";

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 5,
  viewportFit: "cover",
  themeColor: "#8b5cf6",
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
    <html lang="en">
      <head>
        {/* PWA: Apple touch icon (placeholder — replace with real asset) */}
        <link rel="apple-touch-icon" href="/icon-192.png" />
      </head>
      <body className="font-sans bg-bg text-text min-h-screen antialiased">
        <Providers>
          <Navigation />
          <ContentWrapper>{children}</ContentWrapper>
        </Providers>
      </body>
    </html>
  );
}
