import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Sparkles, LogOut, User as UserIcon, Shield, Layers } from 'lucide-react';

const Navbar = ({ onOpenPlanner }) => {
  const { user, logout } = useAuth();

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
          <p className="text-xs text-slate-400">AI-Guided Academic Project & Mentorship Platform</p>
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

        <div className="flex items-center gap-3 pl-4 border-l border-slate-800">
          <div className="flex items-center gap-2">
            <div className="h-9 w-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-indigo-400 font-semibold text-sm">
              {user?.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="hidden md:block text-left">
              <p className="text-sm font-medium text-slate-200 leading-none">{user?.full_name}</p>
              <span className="inline-flex items-center gap-1 text-[11px] text-slate-400 mt-1">
                <Shield className="h-3 w-3 text-indigo-400" />
                {user?.role}
              </span>
            </div>
          </div>

          <button
            onClick={logout}
            className="p-2 text-slate-400 hover:text-rose-400 hover:bg-slate-800/80 rounded-xl transition-all"
            title="Log Out"
          >
            <LogOut className="h-5 w-5" />
          </button>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
