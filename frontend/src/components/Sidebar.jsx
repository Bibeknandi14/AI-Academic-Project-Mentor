import React from 'react';
import { LayoutDashboard, FolderKanban, GitCommit, Bot, Users, KeyRound, MessageSquare, Trash2 } from 'lucide-react';

const Sidebar = ({ activeTab, setActiveTab, userRole }) => {
  const studentNav = [
    { id: 'kanban', label: 'Kanban Board', icon: FolderKanban },
    { id: 'commits', label: 'GitHub Commits', icon: GitCommit },
    { id: 'mentorship', label: 'AI Mentorship Chat', icon: Bot },
    { id: 'supervision-chat', label: 'Supervision Chat', icon: MessageSquare },
    { id: 'mentor-settings', label: 'Mentor Settings', icon: KeyRound },
  ];

  const mentorNav = [
    { id: 'oversight', label: 'Projects Oversight', icon: LayoutDashboard },
    { id: 'students', label: 'My Students', icon: Users },
    { id: 'pending-deletions', label: 'Deletion Requests', icon: Trash2 },
    { id: 'commits', label: 'Commit Activity Feed', icon: GitCommit },
    { id: 'supervision-chat', label: 'Supervision Chat', icon: MessageSquare },
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
                  onClick={() => {
                    console.log(`[Sidebar] Switching tab to: ${item.id}`);
                    setActiveTab(item.id);
                  }}
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
      </div>

      <div className="text-[11px] text-slate-400 text-center py-2 border-t border-slate-800/60">
        DevPilot AI v1.0.0
      </div>
    </aside>
  );
};

export default Sidebar;
