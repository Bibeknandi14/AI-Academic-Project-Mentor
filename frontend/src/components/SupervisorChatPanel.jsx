import React, { useState, useEffect, useRef } from 'react';
import { Send, MessageSquare, User, Shield, Loader2, AlertCircle } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

/**
 * Two-way human mentor ↔ student supervision chat for a project.
 * Backed by SupervisorMessage model — entirely separate from AI MentorshipChat.
 */
const SupervisorChatPanel = ({ projectId, mentorId }) => {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const bottomRef = useRef(null);

  useEffect(() => {
    if (projectId) {
      fetchMessages();
    } else {
      setMessages([]);
    }
  }, [projectId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const fetchMessages = async () => {
    if (!projectId) return;
    setLoading(true);
    setError('');
    try {
      const res = await api.get(`/supervision/messages/${projectId}`);
      setMessages(res.data);
    } catch (err) {
      setError('Failed to load supervision messages.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending || !projectId) return;

    setSending(true);
    setInput('');

    // Optimistic append
    const optimistic = {
      id: `opt-${Date.now()}`,
      project_id: projectId,
      sender_id: user.id,
      receiver_id: mentorId || '',
      message: text,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimistic]);

    try {
      await api.post(`/supervision/messages/${projectId}`, {
        project_id: projectId,
        message: text,
        receiver_id: mentorId || '',   // server auto-resolves the real receiver
      });
      // Sync with server to get proper IDs
      const res = await api.get(`/supervision/messages/${projectId}`);
      setMessages(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send message.');
      // Remove optimistic message on failure
      setMessages((prev) => prev.filter((m) => m.id !== optimistic.id));
    } finally {
      setSending(false);
    }
  };

  const isMine = (msg) => msg.sender_id === user?.id;

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] bg-slate-900/60 rounded-2xl border border-slate-800/80 overflow-hidden">
      {/* Header */}
      <div className="bg-slate-900/90 border-b border-slate-800 p-4 flex items-center gap-3">
        <div className="h-9 w-9 rounded-xl bg-emerald-600/20 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
          <MessageSquare className="h-5 w-5" />
        </div>
        <div>
          <h3 className="font-bold text-sm text-slate-100">Supervision Thread</h3>
          <p className="text-xs text-slate-400">
            Direct mentor ↔ student communication — separate from AI chat
          </p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 p-4 overflow-y-auto space-y-3">
        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-5 w-5 text-indigo-400 animate-spin" />
          </div>
        )}

        {!loading && messages.length === 0 && (
          <div className="text-center py-16 space-y-2">
            <div className="h-12 w-12 rounded-2xl bg-emerald-600/10 border border-emerald-500/20 mx-auto flex items-center justify-center">
              <MessageSquare className="h-6 w-6 text-emerald-400" />
            </div>
            <h4 className="font-semibold text-slate-200 text-sm">No messages yet</h4>
            <p className="text-xs text-slate-500 max-w-xs mx-auto">
              Start a supervision conversation with your{' '}
              {user?.role === 'MENTOR' ? 'student' : 'faculty mentor'}.
            </p>
          </div>
        )}

        {messages.map((msg) => {
          const mine = isMine(msg);
          return (
            <div key={msg.id} className={`flex gap-2.5 ${mine ? 'justify-end' : 'justify-start'}`}>
              {!mine && (
                <div className="h-8 w-8 rounded-lg bg-emerald-900/50 border border-emerald-700/40 flex items-center justify-center text-emerald-400 shrink-0 mt-1">
                  {user?.role === 'STUDENT' ? (
                    <Shield className="h-4 w-4" />
                  ) : (
                    <User className="h-4 w-4" />
                  )}
                </div>
              )}

              <div className={`max-w-lg space-y-1 ${mine ? 'text-right' : 'text-left'}`}>
                <div
                  className={`px-4 py-3 rounded-2xl text-sm leading-relaxed ${
                    mine
                      ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/20'
                      : 'bg-slate-900/90 border border-slate-800 text-slate-200'
                  }`}
                >
                  {msg.message}
                </div>
                <p className="text-[10px] text-slate-500 px-1">
                  {new Date(msg.created_at).toLocaleTimeString([], {
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
              </div>

              {mine && (
                <div className="h-8 w-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-1">
                  {user?.role === 'MENTOR' ? (
                    <Shield className="h-4 w-4" />
                  ) : (
                    <User className="h-4 w-4" />
                  )}
                </div>
              )}
            </div>
          );
        })}

        {error && (
          <div className="flex items-center gap-2 p-3 bg-rose-950/50 border border-rose-800/50 rounded-xl text-rose-300 text-xs">
            <AlertCircle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSend}
        className="p-4 bg-slate-900/90 border-t border-slate-800 flex items-center gap-3"
      >
        <input
          id="supervision-chat-input"
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={`Message your ${user?.role === 'MENTOR' ? 'student' : 'faculty mentor'}...`}
          className="glass-input flex-1 text-sm"
          disabled={sending}
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="glass-button-primary flex items-center gap-2 text-sm py-2.5 disabled:opacity-50"
        >
          {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          Send
        </button>
      </form>
    </div>
  );
};

export default SupervisorChatPanel;
