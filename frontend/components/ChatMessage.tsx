"use client";

import { useState } from "react";
import { Source } from "@/lib/api";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export default function ChatMessage({ role, content, sources }: ChatMessageProps) {
  const isUser = role === "user";
  const [expanded, setExpanded] = useState(false);

  const formatScore = (score: number) => {
    return `${(score * 100).toFixed(1)}%`;
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "text-green-600";
    if (score >= 0.5) return "text-yellow-600";
    return "text-red-500";
  };

  return (
    <div className={`flex w-full mb-4 ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`flex max-w-[80%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
        <div
          className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${
            isUser ? "bg-blue-500 ml-3" : "bg-green-500 mr-3"
          }`}
        >
          {isUser ? "U" : "A"}
        </div>
        <div className="min-w-0 flex-1">
          <div
            className={`p-4 rounded-lg ${
              isUser
                ? "bg-blue-500 text-white rounded-tr-none"
                : "bg-gray-100 text-gray-800 rounded-tl-none"
            }`}
          >
            <p className="whitespace-pre-wrap">{content}</p>
          </div>
          {!isUser && sources && sources.length > 0 && (
            <div className="mt-1.5">
              <button
                onClick={() => setExpanded(!expanded)}
                className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 transition-colors group"
              >
                <svg
                  className={`w-3 h-3 transition-transform duration-200 ${expanded ? "rotate-90" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                </svg>
                <span>查看参考源</span>
                <span className="text-gray-300 group-hover:text-gray-400">({sources.length})</span>
              </button>
              <div
                className={`overflow-hidden transition-all duration-200 ease-in-out ${
                  expanded ? "max-h-[600px] opacity-100 mt-2" : "max-h-0 opacity-0"
                }`}
              >
                <div className="space-y-1.5">
                  {sources.map((source, index) => (
                    <div
                      key={index}
                      className="flex items-start gap-2 text-xs bg-gray-50 px-3 py-2 rounded border border-gray-200"
                    >
                      <div className="flex-shrink-0 mt-0.5">
                        <svg className="w-3.5 h-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-700 truncate">
                            {source.source}
                          </span>
                          <span className={`flex-shrink-0 font-mono ${getScoreColor(source.score)}`}>
                            {formatScore(source.score)}
                          </span>
                        </div>
                        <p className="text-gray-500 mt-1 line-clamp-2 leading-relaxed">
                          {source.content}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
