import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import KanbanBoard from '../components/KanbanBoard';
import GitHubCommitFeed from '../components/GitHubCommitFeed';
import MentorshipChat from '../components/MentorshipChat';
import AIPlannerModal from '../components/AIPlannerModal';
import api from '../services/api';
import { Sparkles, Folder, GitBranch, Plus, CheckCircle2, Clock } from 'lucide-react';

const StudentDashboard = () => {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [activeTab, setActiveTab] = useState('kanban');
  const [showPlanner, setShowPlanner] = useState(false);
  const [activeTaskForChat, setActiveTaskForChat] = useState(null);

  useEffect(() => {
    fetchProjects();
  }, []);

  useEffect(() => {
    if (selectedProject) {
      fetchTasks(selectedProject.id);
    }
  }, [selectedProject]);

  const fetchProjects = async () => {
    try {
      const res = await api.get('/projects/');
      setProjects(res.data);
      if (res.data.length > 0 && !selectedProject) {
        setSelectedProject(res.data[0]);
      }
    } catch (err) {
      console.error("Failed to load projects", err);
    }
  };

  const fetchTasks = async (projectId) => {
    try {
      const res = await api.get(`/tasks/project/${projectId}`);
      setTasks(res.data);
    } catch (err) {
      console.error("Failed to load project tasks", err);
    }
  };

  const handleTaskUpdate = (updatedTask) => {
    setTasks((prev) => {
      const idx = prev.findIndex((t) => t.id === updatedTask.id);
      if (idx !== -1) {
        const next = [...prev];
        next[idx] = updatedTask;
        return next;
      }
      return [...prev, updatedTask];
    });
  };

  const handleOpenChatForTask = (task) => {
    setActiveTaskForChat(task);
    setActiveTab('mentorship');
  };

  const handleProjectCreated = (newProj) => {
    fetchProjects();
    setSelectedProject(newProj);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar onOpenPlanner={() => setShowPlanner(true)} />

      <div className="flex flex-1">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} userRole="STUDENT" />

        <main className="flex-1 p-6 overflow-y-auto space-y-6">
          {/* Project Header Bar */}
          <div className="glass-card p-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400">
                <Folder className="h-5 w-5" />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Active Academic Project</label>
                <div className="flex items-center gap-3 mt-0.5">
                  <select
                    value={selectedProject?.id || ''}
                    onChange={(e) => {
                      const p = projects.find((proj) => proj.id === e.target.value);
                      setSelectedProject(p);
                    }}
                    className="bg-slate-900 border border-slate-700 text-white font-bold text-base rounded-xl px-3 py-1 focus:outline-none focus:border-indigo-500 cursor-pointer"
                  >
                    {projects.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.title}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {selectedProject && (
              <div className="flex items-center gap-6 text-xs border-l border-slate-800 pl-6">
                <div>
                  <span className="text-slate-400">Total Tasks:</span>
                  <p className="text-sm font-bold text-slate-200">{tasks.length}</p>
                </div>
                <div>
                  <span className="text-slate-400">Completed:</span>
                  <p className="text-sm font-bold text-emerald-400">
                    {tasks.filter((t) => t.status === 'DONE').length}
                  </p>
                </div>
                <div>
                  <span className="text-slate-400">GitHub Repo:</span>
                  <p className="text-sm font-bold font-mono text-indigo-300">
                    {selectedProject.github_repo || 'None'}
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Main Tab Content */}
          {selectedProject ? (
            <>
              {activeTab === 'kanban' && (
                <KanbanBoard
                  tasks={tasks}
                  projectId={selectedProject.id}
                  onTaskUpdate={handleTaskUpdate}
                  onOpenChatForTask={handleOpenChatForTask}
                />
              )}

              {activeTab === 'commits' && (
                <GitHubCommitFeed
                  projectId={selectedProject.id}
                  githubRepo={selectedProject.github_repo}
                />
              )}

              {activeTab === 'mentorship' && (
                <MentorshipChat
                  projectId={selectedProject.id}
                  activeTask={activeTaskForChat}
                />
              )}
            </>
          ) : (
            <div className="glass-card p-12 text-center space-y-4">
              <Sparkles className="h-10 w-10 text-indigo-400 mx-auto animate-pulse" />
              <h3 className="text-lg font-bold text-white">No Academic Projects Found</h3>
              <p className="text-sm text-slate-400 max-w-md mx-auto">
                Use the AI Project Planner to automatically convert your project idea into structured sprint tasks.
              </p>
              <button
                onClick={() => setShowPlanner(true)}
                className="glass-button-primary inline-flex items-center gap-2 text-sm"
              >
                <Sparkles className="h-4 w-4" /> Start AI Project Planner
              </button>
            </div>
          )}
        </main>
      </div>

      {showPlanner && (
        <AIPlannerModal
          onClose={() => setShowPlanner(false)}
          onProjectCreated={handleProjectCreated}
        />
      )}
    </div>
  );
};

export default StudentDashboard;
