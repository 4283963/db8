import { Source } from "@/lib/api";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
}

export default function ChatMessage({ role, content, sources }: ChatMessageProps) {
  const isUser = role === "user";

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
        <div>
          <div
            className={`p-4 rounded-lg ${
              isUser
                ? "bg-blue-500 text-white rounded-tr-none"
                : "bg-gray-100 text-gray-800 rounded-tl-none"
            }`}
          >
            <p className="whitespace-pre-wrap">{content}</p>
          </div>
          {sources && sources.length > 0 && (
            <div className="mt-2 ml-1">
              <p className="text-xs text-gray-500 mb-1">参考来源：</p>
              <div className="space-y-1">
                {sources.map((source, index) => (
                  <div
                    key={index}
                    className="text-xs bg-gray-50 p-2 rounded border border-gray-200"
                  >
                    <span className="font-medium text-gray-600">
                      {source.source}
                    </span>
                    <p className="text-gray-500 mt-1 line-clamp-2">
                      {source.content}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
