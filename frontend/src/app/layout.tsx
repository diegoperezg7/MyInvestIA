import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/contexts/AuthContext";
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
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              // Suppress HMR WebSocket error when behind reverse proxy
              (function(){
                var OrigWS = window.WebSocket;
                window.WebSocket = function(url, protocols) {
                  if (typeof url === 'string' && url.includes('/_next/webpack-hmr')) {
                    var noop = { send: function(){}, close: function(){}, addEventListener: function(){}, removeEventListener: function(){}, readyState: 3, CONNECTING: 0, OPEN: 1, CLOSING: 2, CLOSED: 3, onopen: null, onclose: null, onerror: null, onmessage: null };
                    return noop;
                  }
                  return protocols ? new OrigWS(url, protocols) : new OrigWS(url);
                };
                window.WebSocket.prototype = OrigWS.prototype;
                window.WebSocket.CONNECTING = 0;
                window.WebSocket.OPEN = 1;
                window.WebSocket.CLOSING = 2;
                window.WebSocket.CLOSED = 3;
              })();
            `,
          }}
        />
      </head>
      <body className="bg-oracle-bg text-oracle-text min-h-screen" suppressHydrationWarning>
<AuthProvider>
          <ThemeProvider>
            <ViewProvider>{children}</ViewProvider>
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
