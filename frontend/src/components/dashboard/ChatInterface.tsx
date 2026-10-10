import React, { useState, useRef, useEffect } from 'react';
import { Send, AlertCircle, Trash2, Loader2 } from 'lucide-react';
import axios from 'axios';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/useAuth';
import { useDiscoveryTask } from '../../hooks/useDiscoveryTask';
import { useResearchStore } from '../../store/useResearchStore';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
};

export default function ChatInterface() {
  const { user } = useAuth();
  const { startDiscovery } = useDiscoveryTask();
  const { taskStatus, progress, bestScore } = useResearchStore();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Welcome to the AURA discovery space. Describe the battery material you want to discover (e.g. "Find a cobalt-free cathode with >280 mAh/g capacity and <50 $/kg cost") and I will run a 20-generation evolutionary search for you.',
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

      // Kick off the full GA discovery pipeline; useDiscoveryTask polls status
      // and redirects to /results/:taskId once the backend reports completion.
      await startDiscovery(userMessage.content);

      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: 'Discovery task launched. Running the genetic algorithm across 20 generations — this page will redirect to your results automatically once it finishes.',
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

        {taskStatus === 'processing' && (
          <div className="flex items-center gap-2 text-[#bdc58e] text-xs px-3 py-2 bg-[#8f9b68]/10 border border-[#8f9b68]/20 rounded-lg max-w-[85%] self-center">
            <Loader2 size={14} className="animate-spin" />
            <span>Evolving candidates — generation {progress}/20 · best score {bestScore.toFixed(2)}</span>
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
