import React, { useState, useRef, useEffect } from 'react';
import { Send, AlertCircle} from 'lucide-react';
import api from '../../lib/api';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Welcome to the AURA discovery space. How can I assist you with your battery-material research today?',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: input.trim(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setError('');

    try {
      // Direct call to live backend RAG query endpoint
      const response = await api.post('/api/v1/rag/query', {
        prompt: userMessage.content,
      });

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.data.context || 'Empty context returned.',
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      console.error(err);
      setError(err?.response?.data?.detail || err.message || 'An error occurred while connecting to the backend.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`chat-message chat-message--${msg.role}`}
          >
            <div className="chat-message__sender">
              {msg.role === 'user' ? 'Researcher' : 'AURA Assistant'}
            </div>
            <div className="chat-message__bubble">
              {msg.role === 'assistant' ? (
                <AssistantBubbleContent content={msg.content} />
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="chat-message chat-message--assistant">
            <div className="chat-message__sender">AURA Assistant</div>
            <div className="chat-message__bubble">
              <div className="chat-thinking" aria-label="Thinking">
                <span className="chat-thinking__dot" />
                <span className="chat-thinking__dot" />
                <span className="chat-thinking__dot" />
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-[#d59a72] text-xs px-3 py-2 bg-[#d59a72]/10 border border-[#d59a72]/20 rounded-lg max-w-[85%] self-center">
            <AlertCircle size={14} />
            <span>{error}</span>
          </div>
        )}
        <div ref={scrollRef} />
      </div>

      <div className="chat-composer-container">
        <form onSubmit={handleSend} className="chat-form">
          <input
            type="text"
            className="chat-composer-input"
            placeholder="Type your battery query (e.g. Find a stable cathode without Cobalt)..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={loading || !input.trim()}
            aria-label="Send message"
          >
            <Send size={16} />
          </button>
        </form>
      </div>
    </div>
  );
}

// Special subcomponent to render the RAG assistant response
function AssistantBubbleContent({ content }: { content: string }) {
  return <div className="whitespace-pre-wrap">{content}</div>;
}
