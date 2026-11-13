import type { Metadata } from "next";
import { Inter, Noto_Sans_Bengali } from "next/font/google";
import "./globals.css";
import { I18nProvider } from "@/i18n/I18nContext";
import { AuthProvider } from "@/lib/auth";

const notoSansBengali = Noto_Sans_Bengali({
  subsets: ["bengali", "latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-bengali",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-latin",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Smart Question Bank | স্মার্ট কোয়েশ্চন ব্যাংক",
  description: "Source-grounded BCS exam preparation platform for Bangladesh.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="bn" className={`${notoSansBengali.variable} ${inter.variable}`}>
      <body className="font-sans antialiased">
        <I18nProvider>
          <AuthProvider>{children}</AuthProvider>
        </I18nProvider>
      </body>
    </html>
  );
}
