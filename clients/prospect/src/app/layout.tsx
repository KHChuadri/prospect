import type { Metadata } from "next";
import { Geist_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// The Prospect wordmark is Space Grotesk 600 (see prospect-logo/README.md).
// The kit's lockup SVGs carry live text, but an SVG loaded via <img> is an
// isolated document and never sees the page's webfonts — it would silently
// fall back to Helvetica. So the header pairs the mark SVG with real text in
// this font instead, which also keeps the brand name selectable.
const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["600"],
});

export const metadata: Metadata = {
  title: "Job Application Tracker",
  description: "Track your job applications, statuses, and notes",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`dark ${geistMono.variable} ${spaceGrotesk.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
