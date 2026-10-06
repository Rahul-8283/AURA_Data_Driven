import React, { useState, useRef, useEffect } from 'react';
import { Send, AlertCircle, Trash2 } from 'lucide-react';
import axios from 'axios';
import api from '../../lib/api';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/useAuth';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

export default function ChatInterface() {
  const { user } = useAuth();
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

  // Fetch history on load
  useEffect(() => {
    if (!user || !supabase) return;
    const client = supabase;
    const fetchHistory = async () => {
      const { data, error } = await client
        .from('chat_messages')
        .select('*')
        .eq('user_id', user.id)
        .order('created_at', { ascending: true });
        
      if (!error && data && data.length > 0) {
        const formattedHistory: Message[] = data.map((msg) => ({
          id: msg.id,
          role: msg.role as 'user' | 'assistant',
          content: msg.content
        }));
        setMessages([
          {
            id: 'welcome',
            role: 'assistant',
            content: 'Welcome to the AURA discovery space. How can I assist you with your battery-material research today?',
          },
          ...formattedHistory
        ]);
      }
    };
    fetchHistory();
  }, [user]);

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
      // Save user message to Supabase
      if (user && supabase) {
        await supabase.from('chat_messages').insert([{
          user_id: user.id,
          role: 'user',
          content: userMessage.content
        }]);
      }

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

      // Save assistant message to Supabase
      if (user && supabase) {
        await supabase.from('chat_messages').insert([{
          user_id: user.id,
          role: 'assistant',
          content: assistantMessage.content
        }]);
      }
    } catch (err: unknown) {
      console.error(err);
      const detail = axios.isAxiosError(err) ? err.response?.data?.detail : undefined;
      setError(detail || (err instanceof Error ? err.message : 'An error occurred while connecting to the backend.'));
    } finally {
      setLoading(false);
    }
  };

  const handleClearChat = async () => {
    if (!user || !supabase || !window.confirm("Are you sure you want to clear your chat history?")) return;
    
    // Delete from Supabase
    await supabase.from('chat_messages').delete().eq('user_id', user.id);
    
    // Reset local state
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: 'Welcome to the AURA discovery space. How can I assist you with your battery-material research today?',
      },
    ]);
  };

  return (
    <div className="chat-container relative">
      {messages.length > 1 && (
        <button 
          onClick={handleClearChat}
          className="absolute top-4 right-4 p-2 text-gray-400 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-colors z-10"
          title="Clear Chat History"
        >
          <Trash2 size={18} />
        </button>
      )}
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
