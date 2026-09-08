import React, { useState } from 'react';
import { Plus, GitBranch, Bot, CheckCircle2, Clock, AlertCircle, PlayCircle, AlertTriangle } from 'lucide-react';
import api from '../services/api';

const columns = [
  { id: 'TODO', title: 'To Do', icon: Clock, color: 'border-slate-700 bg-slate-900/50 text-slate-300' },
  { id: 'IN_PROGRESS', title: 'In Progress', icon: PlayCircle, color: 'border-amber-500/40 bg-amber-950/20 text-amber-300' },
  { id: 'IN_REVIEW', title: 'In Review', icon: AlertCircle, color: 'border-indigo-500/40 bg-indigo-950/20 text-indigo-300' },
  { id: 'DONE', title: 'Completed', icon: CheckCircle2, color: 'border-emerald-500/40 bg-emerald-950/20 text-emerald-300' },
];

const KanbanBoard = ({ tasks, projectId, onTaskUpdate, onOpenChatForTask, projectStatus }) => {
  const isPendingDeletion = projectStatus === 'pending_deletion';
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newTask, setNewTask] = useState({
    title: '',
    description: '',
    epic_name: 'Core Features',
    sprint_name: 'Sprint 1',
    priority: 'MEDIUM',
    git_branch: ''
  });

  const handleStatusChange = async (taskId, newStatus) => {
    try {
      const res = await api.patch(`/tasks/${taskId}`, { status: newStatus });
      onTaskUpdate(res.data);
    } catch (err) {
      console.error("Failed to update task status", err);
    }
  };

  const handleCreateTask = async (e) => {
    e.preventDefault();
    try {
      const res = await api.post('/tasks/', { ...newTask, project_id: projectId });
      onTaskUpdate(res.data);
      setShowCreateModal(false);
      setNewTask({
        title: '',
        description: '',
        epic_name: 'Core Features',
        sprint_name: 'Sprint 1',
        priority: 'MEDIUM',
        git_branch: ''
      });
    } catch (err) {
      console.error("Failed to create task", err);
    }
  };

  return (
    <div className="space-y-6">

      {/* Pending deletion warning banner */}
      {isPendingDeletion && (
        <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-950/40 border border-amber-700/50 text-amber-300">
          <AlertTriangle className="h-5 w-5 shrink-0 mt-0.5 text-amber-400" />
          <div>
            <p className="text-sm font-bold">Deletion Pending Mentor Approval</p>
            <p className="text-xs text-amber-400/80 mt-0.5">
              Your deletion request is awaiting your mentor's review. The project is read-only until a decision is made.
            </p>
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Interactive Agile Kanban</h2>
          <p className="text-sm text-slate-400">Track task status and auto-updates from GitHub commits</p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          disabled={isPendingDeletion}
          className="glass-button-primary flex items-center gap-2 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Plus className="h-4 w-4" /> Add Task
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {columns.map((col) => {
          const colTasks = tasks.filter((t) => t.status === col.id);
          const ColIcon = col.icon;

          return (
            <div key={col.id} className="flex flex-col rounded-2xl bg-slate-900/60 border border-slate-800/80 p-4 min-h-[500px]">
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800/80">
                <div className="flex items-center gap-2">
                  <ColIcon className="h-4 w-4 text-indigo-400" />
                  <span className="font-semibold text-sm text-slate-200">{col.title}</span>
                </div>
                <span className="px-2.5 py-0.5 text-xs font-bold rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                  {colTasks.length}
                </span>
              </div>

              <div className="space-y-3 flex-1 overflow-y-auto">
                {colTasks.map((t) => (
                  <div
                    key={t.id}
                    className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-slate-700 transition-all shadow-lg group relative"
                  >
                    <div className="flex items-start justify-between gap-2 mb-2">
                      <span className="text-[10px] font-semibold uppercase px-2 py-0.5 rounded-md bg-indigo-950/60 text-indigo-300 border border-indigo-800/40">
                        {t.sprint_name || 'Sprint 1'}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                          t.priority === 'HIGH'
                            ? 'bg-rose-950/60 text-rose-300 border border-rose-800/40'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {t.priority}
                      </span>
                    </div>

                    <h4 className="font-semibold text-sm text-slate-100 group-hover:text-indigo-300 transition-colors mb-1">
                      {t.title}
                    </h4>

                    {t.description && (
                      <p className="text-xs text-slate-400 line-clamp-2 mb-3">
                        {t.description}
                      </p>
                    )}

                    {t.git_branch && (
                      <div className="flex items-center gap-1.5 text-[11px] text-indigo-400/80 font-mono mb-3 bg-indigo-950/30 px-2 py-1 rounded-md border border-indigo-900/40">
                        <GitBranch className="h-3 w-3" /> {t.git_branch}
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-3 border-t border-slate-800/60 text-xs">
                      <button
                        onClick={() => onOpenChatForTask(t)}
                        className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors font-medium text-xs"
                      >
                        <Bot className="h-3.5 w-3.5" /> AI Mentor
                      </button>

                      <select
                        value={t.status}
                        onChange={(e) => handleStatusChange(t.id, e.target.value)}
                        className="bg-slate-900 border border-slate-700 text-slate-300 text-xs rounded-lg px-2 py-1 focus:outline-none focus:border-indigo-500 cursor-pointer"
                      >
                        <option value="TODO">To Do</option>
                        <option value="IN_PROGRESS">In Progress</option>
                        <option value="IN_REVIEW">In Review</option>
                        <option value="DONE">Done</option>
                      </select>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {/* Modal to Create Task */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-4">
            <h3 className="text-lg font-bold text-white">Create New Task</h3>
            <form onSubmit={handleCreateTask} className="space-y-3">
              <div>
                <label className="text-xs text-slate-400">Task Title</label>
                <input
                  type="text"
                  required
                  value={newTask.title}
                  onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                  className="glass-input w-full mt-1 text-sm"
                  placeholder="e.g. Set up JWT authentication API"
                />
              </div>

              <div>
                <label className="text-xs text-slate-400">Description</label>
                <textarea
                  value={newTask.description}
                  onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                  className="glass-input w-full mt-1 text-sm h-20"
                  placeholder="Technical details of work required..."
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-400">Sprint</label>
                  <input
                    type="text"
                    value={newTask.sprint_name}
                    onChange={(e) => setNewTask({ ...newTask, sprint_name: e.target.value })}
                    className="glass-input w-full mt-1 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-slate-400">Priority</label>
                  <select
                    value={newTask.priority}
                    onChange={(e) => setNewTask({ ...newTask, priority: e.target.value })}
                    className="glass-input w-full mt-1 text-sm"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-400">Git Branch Suggestion</label>
                <input
                  type="text"
                  value={newTask.git_branch}
                  onChange={(e) => setNewTask({ ...newTask, git_branch: e.target.value })}
                  className="glass-input w-full mt-1 text-sm font-mono"
                  placeholder="e.g. feature/jwt-auth"
                />
              </div>

              <div className="flex justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="glass-button-secondary text-sm"
                >
                  Cancel
                </button>
                <button type="submit" className="glass-button-primary text-sm">
                  Create Task
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default KanbanBoard;
