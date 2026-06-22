import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "本地知识库 RAG 问答",
  description: "基于本地文档的智能问答系统",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
