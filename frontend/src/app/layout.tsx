import type { Metadata } from "next";
import "./globals.css";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "LabSafe Mom — Laboratory Safety for Expecting Researchers",
  description:
    "AI-powered risk assessment of laboratory protocols for pregnant, trying-to-conceive, and breastfeeding researchers. Protecting scientists through intelligent protocol analysis.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="antialiased">
      <body className="min-h-screen bg-cream-50">
        <Navbar />
        <main>{children}</main>
      </body>
    </html>
  );
}
