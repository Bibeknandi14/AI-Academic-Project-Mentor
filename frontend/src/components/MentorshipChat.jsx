import React, { useState, useEffect, useRef } from 'react';
import { Send, Bot, User, Sparkles, CheckCircle, Code, Info, Terminal, AlertCircle, RefreshCw, X } from 'lucide-react';
import api from '../services/api';

const MentorshipChat = ({ projectId, activeTask }) => {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastFailedQuestion, setLastFailedQuestion] = useState('');
  const [selectedContext, setSelectedContext] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (projectId) {
      fetchHistory();
    } else {
      setMessages([]);
    }
  }, [projectId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, error]);

  const fetchHistory = async () => {
    if (!projectId) return;
    try {
      const res = await api.get(`/mentorship/history/${projectId}`);
      setMessages(res.data);
    } catch (err) {
      console.error("Failed to load chat history", err);
    }
  };

  const sendMessage = async (textToSend) => {
    if (!textToSend.trim() || loading) return;

    if (!projectId) {
      setError("Please select or create an academic project to chat with the AI Mentor.");
      return;
    }

    const userText = textToSend.trim();
    setQuestion('');
    setError(null);
    setLoading(true);
    setLastFailedQuestion('');

    // Immediately add optimistic user message to the UI feed so it never vanishes
    const tempId = `temp-${Date.now()}`;
    const optimisticMessage = {
      id: tempId,
      project_id: projectId,
      sender: 'USER',
      message: userText,
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, optimisticMessage]);

    try {
      const res = await api.post('/mentorship/chat', {
        project_id: projectId,
        active_task_id: activeTask?.id || null,
        question: userText
      });

      // Append AI response
      setMessages((prev) => [...prev, res.data]);
    } catch (err) {
      console.error("Mentorship chat request failed", err);
      const errorDetail =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        "Failed to connect with AI Mentor. Please try again.";
      setError(errorDetail);
      setLastFailedQuestion(userText);
    } finally {
      setLoading(false);
      // Synchronize with database history in the background
      try {
        const res = await api.get(`/mentorship/history/${projectId}`);
        if (res.data && res.data.length > 0) {
          setMessages(res.data);
        }
      } catch (e) {
        // Keep optimistic state if background refresh fails
      }
    }
  };

  const handleSend = (e) => {
    e.preventDefault();
    sendMessage(question);
  };

  const handleRetry = () => {
    if (lastFailedQuestion) {
      sendMessage(lastFailedQuestion);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] bg-slate-900/60 rounded-2xl border border-slate-800/80 overflow-hidden">
      {/* Header with Injected Context Pill */}
      <div className="bg-slate-900/90 border-b border-slate-800 p-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400">
            <Bot className="h-5 w-5" />
          </div>
          <div>
            <h3 className="font-bold text-sm text-slate-100 flex items-center gap-2">
              Context-Aware AI Mentor
              <span className="text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-medium">
                RAG Pipeline Active
              </span>
            </h3>
            <p className="text-xs text-slate-400">Grounding responses in your Kanban task & GitHub commits</p>
          </div>
        </div>

        {activeTask ? (
          <div className="flex items-center gap-2 bg-indigo-950/60 border border-indigo-800/50 px-3 py-1.5 rounded-xl text-xs text-indigo-300">
            <CheckCircle className="h-3.5 w-3.5 text-indigo-400" />
            <span className="font-semibold text-slate-200">Active Task:</span> {activeTask.title}
          </div>
        ) : (
          <div className="flex items-center gap-2 bg-slate-800/60 border border-slate-700/50 px-3 py-1.5 rounded-xl text-xs text-slate-400">
            <Info className="h-3.5 w-3.5" /> No specific task selected (using latest active)
          </div>
        )}
      </div>

      {/* Messages Feed */}
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.length === 0 && !loading && (
          <div className="text-center py-16 space-y-3">
            <div className="h-12 w-12 rounded-2xl bg-indigo-600/20 border border-indigo-500/30 mx-auto flex items-center justify-center text-indigo-400">
              <Sparkles className="h-6 w-6" />
            </div>
            <h4 className="font-semibold text-slate-200 text-sm">Ask your AI Academic Mentor</h4>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Get grounded, task-specific help with bug fixes, code snippets, and architecture guidance based on your repository state.
            </p>
          </div>
        )}

        {messages.map((msg) => {
          const isAI = msg.sender === 'AI';
          return (
            <div
              key={msg.id}
              className={`flex gap-3 ${isAI ? 'justify-start' : 'justify-end'}`}
            >
              {isAI && (
                <div className="h-8 w-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shrink-0 mt-1">
                  <Bot className="h-4 w-4" />
                </div>
              )}

              <div className={`max-w-2xl space-y-2 ${isAI ? 'text-left' : 'text-right'}`}>
                <div
                  className={`p-4 rounded-2xl text-sm leading-relaxed ${
                    isAI
                      ? 'bg-slate-900/90 border border-slate-800 text-slate-200'
                      : 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/20'
                  }`}
                >
                  <div className="whitespace-pre-wrap font-sans">{msg.message}</div>
                </div>

                {isAI && msg.context_used && (
                  <button
                    onClick={() => setSelectedContext(msg.context_used)}
                    className="inline-flex items-center gap-1.5 text-[11px] text-indigo-400 hover:text-indigo-300 font-medium bg-slate-900/40 border border-slate-800 px-2.5 py-1 rounded-lg transition-colors"
                  >
                    <Terminal className="h-3 w-3" /> View Injected Prompt Context
                  </button>
                )}
              </div>

              {!isAI && (
                <div className="h-8 w-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-1">
                  <User className="h-4 w-4" />
                </div>
              )}
            </div>
          );
        })}

        {loading && (
          <div className="flex gap-3 justify-start">
            <div className="h-8 w-8 rounded-lg bg-indigo-600/30 border border-indigo-500/40 flex items-center justify-center text-indigo-400 shrink-0">
              <Bot className="h-4 w-4 animate-spin" />
            </div>
            <div className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 text-slate-400 text-xs flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-indigo-400 animate-pulse" />
              Generating grounded mentorship advice for your active task...
            </div>
          </div>
        )}

        {/* Inline Error Toast / Alert */}
        {error && (
          <div className="flex items-center justify-between gap-3 p-3.5 bg-rose-950/50 border border-rose-800/60 rounded-xl text-rose-300 text-xs animate-in fade-in slide-in-from-bottom-2">
            <div className="flex items-center gap-2.5">
              <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              {lastFailedQuestion && (
                <button
                  type="button"
                  onClick={handleRetry}
                  disabled={loading}
                  className="inline-flex items-center gap-1 px-2.5 py-1 bg-rose-900/60 hover:bg-rose-800/80 border border-rose-700/50 rounded-lg text-[11px] text-rose-200 font-medium transition-colors"
                >
                  <RefreshCw className="h-3 w-3" /> Retry
                </button>
              )}
              <button
                type="button"
                onClick={() => setError(null)}
                className="p-1 text-rose-400 hover:text-rose-200 transition-colors"
                aria-label="Dismiss error"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <form onSubmit={handleSend} className="p-4 bg-slate-900/90 border-t border-slate-800 flex items-center gap-3">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a technical or debug question regarding your active task..."
          className="glass-input flex-1 text-sm"
        />
        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="glass-button-primary flex items-center gap-2 text-sm py-2.5 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Send className="h-4 w-4" />
          Send
        </button>
      </form>

      {/* Context Inspector Modal */}
      {selectedContext && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-xl w-full p-6 space-y-4 max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Code className="h-5 w-5 text-indigo-400" /> Injected RAG Context Payload
              </h3>
              <button
                onClick={() => setSelectedContext(null)}
                className="text-slate-400 hover:text-white text-xs"
              >
                Close
              </button>
            </div>
            <pre className="flex-1 bg-slate-950 p-4 rounded-xl text-xs font-mono text-indigo-300 overflow-y-auto border border-slate-800">
              {JSON.stringify(selectedContext, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};

export default MentorshipChat;
