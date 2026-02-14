import type { Metadata } from "next";
import "./globals.css";
import { ViewProvider } from "@/contexts/ViewContext";
import { ThemeProvider } from "@/contexts/ThemeContext";

export const metadata: Metadata = {
  title: "MyInvestIA - AI Investment Intelligence Dashboard",
  description: "AI-powered investment intelligence and decision support",
  icons: {
    icon: "/icon.svg",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className="bg-oracle-bg text-oracle-text min-h-screen" suppressHydrationWarning>
<ThemeProvider>
          <ViewProvider>{children}</ViewProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
