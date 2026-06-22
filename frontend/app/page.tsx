"use client";

import { useState, useEffect, useRef } from "react";
import ChatMessage from "@/components/ChatMessage";
import ChatInput from "@/components/ChatInput";
import { ChatMessage as ChatMessageType, Source, chat, getDocuments, indexDocuments, DocumentsResponse } from "@/lib/api";

interface MessageWithSources extends ChatMessageType {
  sources?: Source[];
}

export default function Home() {
  const [messages, setMessages] = useState<MessageWithSources[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [docsInfo, setDocsInfo] = useState<DocumentsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadDocuments();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadDocuments = async () => {
    try {
      const info = await getDocuments();
      setDocsInfo(info);
    } catch (err) {
      setError("无法连接到后端服务，请确保后端已启动");
    }
  };

  const handleIndex = async () => {
    setIsIndexing(true);
    setError(null);
    try {
      await indexDocuments();
      await loadDocuments();
    } catch (err) {
      setError(err instanceof Error ? err.message : "索引失败");
    } finally {
      setIsIndexing(false);
    }
  };

  const handleSend = async (question: string) => {
    if (!docsInfo || docsInfo.indexed_chunks === 0) {
      setError("请先索引文档，然后再提问");
      return;
    }

    setError(null);
    const userMessage: MessageWithSources = { role: "user", content: question };
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await chat(question, messages);
      const assistantMessage: MessageWithSources = {
        role: "assistant",
        content: response.answer,
        sources: response.sources,
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "发送失败");
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-800">本地知识库 RAG 问答</h1>
            <p className="text-sm text-gray-500">
              基于本地文档的智能问答系统
            </p>
          </div>
          <div className="flex items-center gap-3">
            {docsInfo && (
              <div className="text-sm text-gray-600">
                已索引：{docsInfo.indexed_chunks} 个片段 | 文件：{docsInfo.files.length} 个
              </div>
            )}
            <button
              onClick={handleIndex}
              disabled={isIndexing}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm"
            >
              {isIndexing ? "索引中..." : "重新索引文档"}
            </button>
            <button
              onClick={handleClearChat}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors text-sm"
            >
              清空对话
            </button>
          </div>
        </div>
      </header>

      {error && (
        <div className="bg-red-50 border-b border-red-200 px-6 py-3">
          <div className="max-w-4xl mx-auto text-red-600 text-sm">{error}</div>
        </div>
      )}

      {docsInfo && docsInfo.files.length > 0 && (
        <div className="bg-blue-50 border-b border-blue-200 px-6 py-2">
          <div className="max-w-4xl mx-auto text-blue-600 text-xs">
            文档列表：{docsInfo.files.join("、")}
          </div>
        </div>
      )}

      <main className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 mt-20">
              <div className="text-6xl mb-4">💬</div>
              <h2 className="text-xl font-medium mb-2">开始你的问答</h2>
              <p className="text-sm">
                {docsInfo && docsInfo.indexed_chunks > 0
                  ? "请在下方输入你的问题，系统会基于本地文档为你解答"
                  : "请先点击上方「重新索引文档」按钮，将本地文档加载到系统中"}
              </p>
            </div>
          ) : (
            <>
              {messages.map((msg, index) => (
                <ChatMessage
                  key={index}
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                />
              ))}
              {isLoading && (
                <div className="flex w-full mb-4 justify-start">
                  <div className="flex">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold bg-green-500 mr-3">
                      A
                    </div>
                    <div className="p-4 rounded-lg bg-gray-100 text-gray-800 rounded-tl-none">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
                      </div>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      </main>

      <ChatInput onSend={handleSend} disabled={isLoading || isIndexing} />
    </div>
  );
}
