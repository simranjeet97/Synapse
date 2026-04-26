"use client";

import { useState, useRef, useEffect } from "react";
import { ChatInterface } from "@/components/chat-interface";
import { SourcePanel } from "@/components/source-panel";
import { Message, SearchResult } from "@/lib/types";
import { streamQuery } from "@/lib/api";
import { v4 as uuidv4 } from "uuid";

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [activeSources, setActiveSources] = useState<SearchResult[]>([]);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const sessionId = useRef(uuidv4()).current;

  const handleSendMessage = async (query: string) => {
    const userMsg: Message = {
      id: uuidv4(),
      role: "user",
      content: query,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    const assistantMsgId = uuidv4();
    let currentContent = "";
    
    try {
      const stream = streamQuery({
        query,
        session_id: sessionId,
        stream: true,
      });

      for await (const chunk of stream) {
        if (chunk.token) {
          currentContent += chunk.token;
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.id === assistantMsgId) {
              return [...prev.slice(0, -1), { ...last, content: currentContent }];
            } else {
              return [
                ...prev,
                {
                  id: assistantMsgId,
                  role: "assistant",
                  content: currentContent,
                  timestamp: new Date().toISOString(),
                },
              ];
            }
          });
        }

        if (chunk.sources) {
          setActiveSources(chunk.sources);
          setMessages((prev) => {
            const last = prev[prev.length - 1];
            if (last?.id === assistantMsgId) {
              return [...prev.slice(0, -1), { ...last, sources: chunk.sources, trace: chunk.trace }];
            }
            return prev;
          });
        }
      }
    } catch (error) {
      console.error("Chat error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-background">
      <div className={`flex flex-col flex-1 transition-all duration-300 ${isSidebarOpen ? 'w-3/4' : 'w-full'}`}>
        <ChatInterface 
          messages={messages} 
          onSendMessage={handleSendMessage} 
          isLoading={isLoading}
          onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        />
      </div>
      
      {isSidebarOpen && (
        <div className="w-1/4 border-l border-border bg-muted/30 hidden md:block">
          <SourcePanel sources={activeSources} />
        </div>
      )}
    </div>
  );
}
