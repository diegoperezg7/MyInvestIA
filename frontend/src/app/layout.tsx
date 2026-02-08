import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ORACLE - AI Investment Intelligence Dashboard",
  description: "AI-powered investment intelligence and decision support",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-oracle-bg text-oracle-text min-h-screen">
        {children}
      </body>
    </html>
  );
}
