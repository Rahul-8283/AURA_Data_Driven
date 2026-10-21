import React, { useState, useRef, useEffect } from 'react';
import { Send, AlertCircle, Trash2, Loader2, X, FlaskConical } from 'lucide-react';
import axios from 'axios';
import api from '../../lib/api';
import { supabase } from '../../lib/supabase';
import { useAuth } from '../../contexts/useAuth';
import { useDiscoveryTask } from '../../hooks/useDiscoveryTask';
import { useResearchStore } from '../../store/useResearchStore';
import { parseCommand, suggestMode } from '../../lib/chatIntent';
import type { AskResponse, AskSource, ChatMode } from '../../types/chat';

type Message = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  mode?: ChatMode;
  question?: string;
  grounded?: boolean;
  sources?: AskSource[];
  graphRules?: string[];
};

type PendingChoice = { text: string; suggested: ChatMode };

const WELCOME =
  'Welcome to the AURA workspace. Ask a question about the harvested battery literature, or switch to Discover and I will run an evolutionary search for new materials.';

const welcomeMessage = (): Message => ({ id: 'welcome', role: 'assistant', content: WELCOME });

const MODE_HINT: Record<ChatMode, string> = {
  ask: 'Answers from your harvested papers and the knowledge graph, with sources.',
  discover: 'Runs an evolutionary search and opens a ranked report of candidate materials.',
};

const PLACEHOLDER: Record<ChatMode, string> = {
  ask: 'Ask about battery materials (e.g. What do the papers say about LFP cycle life?)...',
  discover: 'Describe a material to discover (e.g. Find a stable cathode without Cobalt)...',
};

function metadataFor(message: Message): Record<string, unknown> {
  return {
    mode: message.mode,
    question: message.question,
    grounded: message.grounded,
    sources: message.sources,
    graph_rules: message.graphRules,
  };
}

function messageFromRow(row: { id: string; role: string; content: string; metadata?: unknown }): Message {
  const meta = (row.metadata && typeof row.metadata === 'object' ? row.metadata : {}) as Record<string, unknown>;
  return {
    id: row.id,
    role: row.role as 'user' | 'assistant',
    content: row.content,
    mode: meta.mode === 'ask' || meta.mode === 'discover' ? meta.mode : undefined,
    question: typeof meta.question === 'string' ? meta.question : undefined,
    grounded: typeof meta.grounded === 'boolean' ? meta.grounded : undefined,
    sources: Array.isArray(meta.sources) ? (meta.sources as AskSource[]) : undefined,
    graphRules: Array.isArray(meta.graph_rules) ? (meta.graph_rules as string[]) : undefined,
  };
}

function errorText(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (err.response?.status === 401 || err.response?.status === 403) return 'Please sign in again to continue.';
    if (err.response?.status === 422) return 'That message could not be processed. Use 3 to 1000 characters.';
  }
  return err instanceof Error ? err.message : 'An error occurred while connecting to the backend.';
}

export default function ChatInterface() {
  const { user } = useAuth();
  const { startDiscovery } = useDiscoveryTask();
  const { taskStatus } = useResearchStore();
  const [messages, setMessages] = useState<Message[]>([welcomeMessage()]);
  const [input, setInput] = useState('');
  const [mode, setMode] = useState<ChatMode>('ask');
  const [pending, setPending] = useState<PendingChoice | null>(null);
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
        setMessages([welcomeMessage(), ...data.map(messageFromRow)]);
      }
    };
    fetchHistory();
  }, [user]);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, pending]);

  const persist = async (message: Message) => {
    if (!user || !supabase) return;
    const { error: insertError } = await supabase.from('chat_messages').insert([{
      user_id: user.id,
      role: message.role,
      content: message.content,
      metadata: metadataFor(message),
    }]);
    if (insertError) console.error('Could not save chat message', insertError.message);
  };

  const dispatch = async (text: string, chosen: ChatMode) => {
    const userMessage: Message = { id: `user-${Date.now()}`, role: 'user', content: text, mode: chosen };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setPending(null);
    setLoading(true);
    setError('');

    try {
      await persist(userMessage);

      let assistantMessage: Message;
      if (chosen === 'discover') {
        // Kick off the full GA discovery pipeline; useDiscoveryTask polls status
        // and redirects to /results/:taskId once the backend reports completion.
        await startDiscovery(text);
        assistantMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          mode: 'discover',
          content: 'Discovery task launched. Running the evolutionary search. This page will redirect to your results automatically once it finishes.',
        };
      } else {
        const { data } = await api.post<AskResponse>('/api/v1/chat/ask', { question: text });
        assistantMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          mode: 'ask',
          question: text,
          grounded: data.grounded,
          sources: data.sources,
          graphRules: data.graph_rules,
          content: data.answer,
        };
      }

      setMessages((prev) => [...prev, assistantMessage]);
      await persist(assistantMessage);
    } catch (err: unknown) {
      console.error(err);
      setError(errorText(err));
    } finally {
      setLoading(false);
    }
  };

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;

    const command = parseCommand(input);
    if (command.mode && !command.text) {
      setError('Add your request after the command, for example: /discover find a cobalt-free cathode');
      return;
    }
    if (!command.text) return;
    setError('');

    if (command.mode) {
      void dispatch(command.text, command.mode);
      return;
    }

    // A hint, never a silent switch: when the text fits the other mode, ask first.
    const suggestion = suggestMode(command.text);
    if (suggestion && suggestion !== mode) {
      setPending({ text: command.text, suggested: suggestion });
      return;
    }
    void dispatch(command.text, mode);
  };

  const changeMode = (next: ChatMode) => {
    setMode(next);
    setPending(null);
  };

  const handleClearChat = async () => {
    if (!user || !supabase || !window.confirm("Are you sure you want to clear your chat history?")) return;

    // Delete from Supabase
    await supabase.from('chat_messages').delete().eq('user_id', user.id);

    // Reset local state
    setMessages([welcomeMessage()]);
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
              {msg.mode && <span className={`chat-mode-tag chat-mode-tag--${msg.mode}`}>{msg.mode}</span>}
            </div>
            <div className={`chat-message__bubble ${msg.grounded === false ? 'chat-message__bubble--muted' : ''}`}>
              {msg.role === 'assistant' ? (
                <AssistantBubbleContent
                  message={msg}
                  busy={loading}
                  onFollowUp={(question) => void dispatch(question, 'discover')}
                />
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
            <span>Discovering candidates…</span>
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
        {pending && (
          <div className="chat-suggest" role="status">
            <span className="chat-suggest__text">
              {pending.suggested === 'discover'
                ? 'This looks like a design request. Run a discovery instead?'
                : 'This looks like a question. Ask the literature instead?'}
            </span>
            <div className="chat-suggest__actions">
              <button type="button" className="chat-suggest__primary" onClick={() => void dispatch(pending.text, pending.suggested)}>
                {pending.suggested === 'discover' ? 'Run discovery' : 'Ask'}
              </button>
              <button type="button" className="chat-suggest__secondary" onClick={() => void dispatch(pending.text, mode)}>
                Keep {mode === 'discover' ? 'Discover' : 'Ask'}
              </button>
              <button type="button" className="chat-suggest__dismiss" onClick={() => setPending(null)} aria-label="Dismiss and edit the message">
                <X size={14} />
              </button>
            </div>
          </div>
        )}

        <div className="chat-mode-row">
          <div className="chat-mode" role="group" aria-label="Chat mode">
            {(['ask', 'discover'] as ChatMode[]).map((option) => (
              <button
                key={option}
                type="button"
                className={`chat-mode__option ${mode === option ? 'chat-mode__option--active' : ''}`}
                aria-pressed={mode === option}
                onClick={() => changeMode(option)}
                disabled={loading}
              >
                {option === 'ask' ? 'Ask' : 'Discover'}
              </button>
            ))}
          </div>
          <span className="chat-mode__hint">{MODE_HINT[mode]}</span>
        </div>

        <form onSubmit={handleSend} className="chat-form">
          <input
            type="text"
            className="chat-composer-input"
            placeholder={PLACEHOLDER[mode]}
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

// Only http(s) links are rendered, since source URLs come from third-party APIs.
function sourceHref(source: AskSource): string | null {
  const candidate = source.url || (source.doi?.startsWith('doi:') ? `https://doi.org/${source.doi.slice(4)}` : null);
  return candidate && /^https?:\/\//i.test(candidate) ? candidate : null;
}

function AssistantBubbleContent({
  message,
  busy,
  onFollowUp,
}: {
  message: Message;
  busy: boolean;
  onFollowUp: (question: string) => void;
}) {
  const sources = message.sources ?? [];
  const rules = message.graphRules ?? [];
  return (
    <>
      <div className="whitespace-pre-wrap">{message.content}</div>

      {sources.length > 0 && (
        <div className="chat-sources">
          <div className="chat-sources__title">Sources</div>
          <ol className="chat-sources__list">
            {sources.map((source) => {
              const href = sourceHref(source);
              return (
                <li key={source.id}>
                  <span className="chat-sources__id">{source.id}</span>
                  {href ? (
                    <a href={href} target="_blank" rel="noopener noreferrer">{source.title}</a>
                  ) : (
                    <span>{source.title}</span>
                  )}
                  {source.source && <span className="chat-sources__meta">{source.source}</span>}
                </li>
              );
            })}
          </ol>
        </div>
      )}

      {rules.length > 0 && (
        <details className="chat-rules">
          <summary>Knowledge-graph rules ({rules.length})</summary>
          <ul>
            {rules.map((rule, index) => (
              <li key={`${index}-${rule}`}><span className="chat-sources__id">R{index + 1}</span>{rule}</li>
            ))}
          </ul>
        </details>
      )}

      {message.mode === 'ask' && message.question && (
        <button type="button" className="chat-followup" disabled={busy} onClick={() => onFollowUp(message.question as string)}>
          <FlaskConical size={14} /> Search for candidates based on this
        </button>
      )}
    </>
  );
}
