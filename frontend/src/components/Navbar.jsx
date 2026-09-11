import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { Sparkles, LogOut, Shield, Bell, X, CheckCheck, User } from 'lucide-react';
import api from '../services/api';
import ProfileModal from './ProfileModal';

const TYPE_LABEL = {
  deletion_request: '🗑️ Deletion Request',
  deletion_approved: '✅ Deletion Approved',
  deletion_rejected: '❌ Deletion Rejected',
  supervision_message: '💬 Supervision Message',
};

const Navbar = ({ onOpenPlanner, onNavigate }) => {
  const { user, logout } = useAuth();
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [open, setOpen] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const dropdownRef = useRef(null);

  // Poll unread count every 30 s
  useEffect(() => {
    if (!user) return;
    const fetchCount = async () => {
      try {
        const res = await api.get('/notifications/unread-count');
        setUnreadCount(res.data.count);
      } catch (_) {}
    };
    fetchCount();
    const id = setInterval(fetchCount, 30000);
    return () => clearInterval(id);
  }, [user]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleOpenBell = async () => {
    setOpen((prev) => !prev);
    if (!open) {
      try {
        const res = await api.get('/notifications/');
        setNotifications(res.data);
      } catch (_) {}
    }
  };

  const handleMarkRead = async (notif) => {
    if (!notif.is_read) {
      try {
        await api.patch(`/notifications/${notif.id}/read`);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
        );
        setUnreadCount((c) => Math.max(0, c - 1));
      } catch (_) {}
    }
    // Navigate to the relevant tab if possible
    if (onNavigate && notif.type === 'deletion_request') onNavigate('pending-deletions');
    if (onNavigate && notif.type === 'deletion_approved') onNavigate('kanban');
    if (onNavigate && notif.type === 'deletion_rejected') onNavigate('kanban');
    if (onNavigate && notif.type === 'supervision_message') onNavigate('supervision-chat');
    setOpen(false);
  };

  const handleMarkAllRead = async () => {
    try {
      await api.patch('/notifications/read-all');
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch (_) {}
  };

  const formatTime = (ts) => {
    const d = new Date(ts);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHrs = Math.floor(diffMins / 60);
    if (diffHrs < 24) return `${diffHrs}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <header className="sticky top-0 z-30 bg-slate-900/90 backdrop-blur-xl border-b border-slate-800/80 px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
          <Sparkles className="h-5 w-5 text-white animate-pulse" />
        </div>
        <div>
          <h1 className="font-extrabold text-lg text-white tracking-tight flex items-center gap-2">
            DevPilot AI <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 font-medium">Sprint Tracker</span>
          </h1>
          <p className="text-xs text-slate-400">AI-Guided Academic Project &amp; Mentorship Platform</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {user?.role === 'STUDENT' && (
          <button
            onClick={onOpenPlanner}
            className="glass-button-primary flex items-center gap-2 text-sm py-2"
          >
            <Sparkles className="h-4 w-4" />
            AI Project Planner
          </button>
        )}

        {/* ── Notification Bell ── */}
        <div className="relative" ref={dropdownRef}>
          <button
            onClick={handleOpenBell}
            className="relative p-2 text-slate-400 hover:text-slate-200 hover:bg-slate-800/80 rounded-xl transition-all"
            title="Notifications"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 h-4.5 min-w-[1.1rem] px-1 text-[10px] font-bold bg-rose-500 text-white rounded-full flex items-center justify-center leading-none border border-slate-900">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {open && (
            <div className="absolute right-0 top-12 w-80 bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl shadow-slate-950/60 overflow-hidden z-50">
              {/* Header */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800">
                <span className="text-sm font-bold text-white">Notifications</span>
                <div className="flex items-center gap-2">
                  {unreadCount > 0 && (
                    <button
                      onClick={handleMarkAllRead}
                      className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                    >
                      <CheckCheck className="h-3.5 w-3.5" /> Mark all read
                    </button>
                  )}
                  <button onClick={() => setOpen(false)} className="text-slate-500 hover:text-slate-300 transition-colors">
                    <X className="h-4 w-4" />
                  </button>
                </div>
              </div>

              {/* List */}
              <div className="max-h-80 overflow-y-auto divide-y divide-slate-800/60">
                {notifications.length === 0 ? (
                  <div className="px-4 py-8 text-center text-sm text-slate-500">
                    <Bell className="h-6 w-6 mx-auto mb-2 text-slate-600" />
                    No notifications yet
                  </div>
                ) : (
                  notifications.map((n) => (
                    <button
                      key={n.id}
                      onClick={() => handleMarkRead(n)}
                      className={`w-full text-left px-4 py-3 hover:bg-slate-800/60 transition-colors ${
                        !n.is_read ? 'bg-indigo-950/20' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <p className="text-[11px] font-semibold text-indigo-300 mb-0.5">
                            {TYPE_LABEL[n.type] || n.type}
                          </p>
                          <p className="text-xs text-slate-300 leading-snug line-clamp-2">{n.message}</p>
                          <p className="text-[11px] text-slate-500 mt-1">{formatTime(n.created_at)}</p>
                        </div>
                        {!n.is_read && (
                          <span className="h-2 w-2 rounded-full bg-indigo-400 shrink-0 mt-1" />
                        )}
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 pl-4 border-l border-slate-800">
          <button
            id="user-profile-button"
            type="button"
            onClick={() => setShowProfile(true)}
            className="flex items-center gap-2.5 px-2 py-1.5 rounded-xl hover:bg-slate-800/80 transition-all text-left group cursor-pointer"
            title="View & Edit Profile"
          >
            <div className="h-9 w-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-indigo-400 font-semibold text-sm group-hover:border-indigo-500/50 group-hover:scale-105 transition-all shadow-sm">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="hidden md:block text-left">
              <p className="text-sm font-medium text-slate-200 leading-none group-hover:text-indigo-300 transition-colors">
                {user?.full_name}
              </p>
              <span className="inline-flex items-center gap-1 text-[11px] text-slate-400 mt-1">
                <Shield className="h-3 w-3 text-indigo-400" />
                {user?.role}
              </span>
            </div>
          </button>

          <button
            onClick={logout}
            className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 rounded-xl transition-all"
            title="Log Out"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Profile Modal */}
      <ProfileModal isOpen={showProfile} onClose={() => setShowProfile(false)} />
    </header>
  );
};

export default Navbar;
