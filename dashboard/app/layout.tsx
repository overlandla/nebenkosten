import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Utility Meter Dashboard",
  description: "Real-time monitoring and analysis of utility consumption",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
