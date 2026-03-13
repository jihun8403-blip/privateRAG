import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/layout/Sidebar";
import QueryProvider from "@/components/layout/QueryProvider";
import { Toaster } from "sonner";

export const metadata: Metadata = {
  title: "PrivateRAG",
  description: "주제 중심 자동 수집·검증·검색 RAG 시스템",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="flex h-screen overflow-hidden bg-background">
        <QueryProvider>
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            {children}
          </main>
          <Toaster richColors position="top-right" />
        </QueryProvider>
      </body>
    </html>
  );
}
