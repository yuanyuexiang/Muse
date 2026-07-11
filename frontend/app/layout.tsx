import "./globals.css";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata = { title: "MUSE 后台" };

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh">
      <body>
        <header className="topbar">
          <Link href="/" className="brand">
            MUSE
          </Link>
          <nav>
            <Link href="/inbox">待整理收件箱</Link>
          </nav>
        </header>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
