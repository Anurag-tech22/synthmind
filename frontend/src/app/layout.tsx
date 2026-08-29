import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SynthMind — Adaptive Research & Decision Intelligence Partner",
  description: "Don't just search. Think together. An AI-powered collaborative partner that transforms chaotic research into structured decisions.",
  keywords: "AI, research, decision making, Gemini, Google ADK, collaborative partner",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
