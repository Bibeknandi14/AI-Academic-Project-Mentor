import React from 'react';
import { LayoutDashboard, FolderKanban, GitCommit, Bot, Award, Users } from 'lucide-react';

const Sidebar = ({ activeTab, setActiveTab, userRole }) => {
  const studentNav = [
    { id: 'kanban', label: 'Kanban Board', icon: FolderKanban },
    { id: 'commits', label: 'GitHub Commits', icon: GitCommit },
    { id: 'mentorship', label: 'AI Mentorship Chat', icon: Bot },
  ];

  const mentorNav = [
    { id: 'oversight', label: 'Projects Oversight', icon: LayoutDashboard },
    { id: 'commits', label: 'Commit Activity Feed', icon: GitCommit },
    { id: 'mentorship', label: 'AI Assistance Logs', icon: Bot },
  ];

  const navItems = userRole === 'MENTOR' ? mentorNav : studentNav;

  return (
    <aside className="w-64 bg-slate-900/60 border-r border-slate-800/80 p-4 flex flex-col justify-between hidden md:flex min-h-[calc(100vh-65px)]">
      <div className="space-y-6">
        <div>
          <p className="px-3 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
            {userRole === 'MENTOR' ? 'Mentor Control Center' : 'Student Workspace'}
          </p>
          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl font-medium text-sm transition-all ${
                    isActive
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-md shadow-indigo-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`}
                >
                  <Icon className={`h-4 w-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        <div className="p-4 rounded-xl bg-gradient-to-b from-indigo-950/40 to-slate-900/40 border border-indigo-800/30 text-xs">
          <div className="flex items-center gap-2 text-indigo-300 font-semibold mb-1">
            <Award className="h-4 w-4" /> Infosys Springboard
          </div>
          <p className="text-slate-400 leading-relaxed">
            Track daily commit velocity & get context-injected AI mentorship assistance.
          </p>
        </div>
      </div>

      <div className="text-[11px] text-slate-400 text-center py-2 border-t border-slate-800/60">
        DevPilot AI v1.0.0 &bull; Infosys Internship
      </div>
    </aside>
  );
};

export default Sidebar;
