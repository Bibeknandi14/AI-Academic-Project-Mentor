import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import KanbanBoard from '../components/KanbanBoard';
import GitHubCommitFeed from '../components/GitHubCommitFeed';
import MentorshipChat from '../components/MentorshipChat';
import SupervisorChatPanel from '../components/SupervisorChatPanel';
import AIPlannerModal from '../components/AIPlannerModal';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import {
  Sparkles, Folder, AlertTriangle, CheckCircle2,
  Trash2, KeyRound, UserCheck, UserX, Loader2, MessageSquare, X
} from 'lucide-react';

const StudentDashboard = () => {
  const { user, linkMentor, unlinkMentor } = useAuth();
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [activeTab, setActiveTab] = useState('kanban');
  const [showPlanner, setShowPlanner] = useState(false);
  const [activeTaskForChat, setActiveTaskForChat] = useState(null);

  // Mentor link state
  const [mentorCodeInput, setMentorCodeInput] = useState('');
  const [mentorLinkLoading, setMentorLinkLoading] = useState(false);
  const [mentorLinkError, setMentorLinkError] = useState('');
  const [mentorLinkSuccess, setMentorLinkSuccess] = useState('');

  // Deletion request state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteReason, setDeleteReason] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState('');
  const [deleteSuccess, setDeleteSuccess] = useState('');
  const [rejectedTickets, setRejectedTickets] = useState([]);
  const [pendingTicketId, setPendingTicketId] = useState(null);
  const [cancelLoading, setCancelLoading] = useState(false);

  useEffect(() => { fetchProjects(); }, []);

  useEffect(() => {
    if (selectedProject) {
      fetchTasks(selectedProject.id);
      if (selectedProject.status === 'pending_deletion') {
        fetchPendingTicket(selectedProject.id);
      } else {
        setPendingTicketId(null);
      }
    }
  }, [selectedProject]);

  const fetchProjects = async () => {
    try {
      const res = await api.get('/projects/');
      setProjects(res.data);
      if (res.data.length > 0 && !selectedProject) setSelectedProject(res.data[0]);
    } catch (err) { console.error('Failed to load projects', err); }
  };

  const fetchTasks = async (projectId) => {
    try {
      const res = await api.get(`/tasks/project/${projectId}`);
      setTasks(res.data);
    } catch (err) { console.error('Failed to load tasks', err); }
  };

  // Fetch the pending ticket id for this project (for cancel button)
  const fetchPendingTicket = async (projectId) => {
    try {
      const res = await api.get(`/deletion-tickets/mine/${projectId}`);
      setPendingTicketId(res.data?.id || null);
    } catch (_) {
      setPendingTicketId(null);
    }
  };

  const handleTaskUpdate = (updatedTask) => {
    setTasks((prev) => {
      const idx = prev.findIndex((t) => t.id === updatedTask.id);
      if (idx !== -1) { const next = [...prev]; next[idx] = updatedTask; return next; }
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

  // ── Mentor link handlers ──────────────────────────────────────────────────
  const handleLinkMentor = async (e) => {
    e.preventDefault();
    setMentorLinkError(''); setMentorLinkSuccess(''); setMentorLinkLoading(true);
    try {
      await linkMentor(mentorCodeInput.trim().toUpperCase());
      setMentorCodeInput('');
      setMentorLinkSuccess('Mentor linked successfully!');
      await fetchProjects();
    } catch (err) {
      setMentorLinkError(err.response?.data?.detail || 'Invalid mentor code.');
    } finally { setMentorLinkLoading(false); }
  };

  const handleUnlinkMentor = async () => {
    setMentorLinkError(''); setMentorLinkSuccess(''); setMentorLinkLoading(true);
    try {
      await unlinkMentor();
      setMentorLinkSuccess('Mentor unlinked.');
      await fetchProjects();
    } catch (err) {
      setMentorLinkError(err.response?.data?.detail || 'Failed to unlink mentor.');
    } finally { setMentorLinkLoading(false); }
  };

  // ── Deletion request handler ──────────────────────────────────────────────
  const handleRequestDeletion = async (e) => {
    e.preventDefault();
    setDeleteError(''); setDeleteLoading(true);
    try {
      const res = await api.post(`/projects/${selectedProject.id}/request-deletion`, {
        project_id: selectedProject.id,
        reason: deleteReason,
      });
      setPendingTicketId(res.data?.id || null);
      setShowDeleteModal(false);
      setDeleteReason('');
      setDeleteSuccess('Deletion request sent to your mentor for approval.');
      setTimeout(() => setDeleteSuccess(''), 5000);
      await fetchProjects();
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Failed to submit deletion request.');
    } finally { setDeleteLoading(false); }
  };

  // ── Cancel deletion ticket handler ────────────────────────────────────────
  const handleCancelDeletion = async () => {
    if (!pendingTicketId) return;
    if (!window.confirm('Cancel your deletion request? The project will return to active status.')) return;
    setCancelLoading(true);
    try {
      await api.delete(`/deletion-tickets/${pendingTicketId}/cancel`);
      setPendingTicketId(null);
      setDeleteSuccess('Deletion request cancelled. Project is active again.');
      setTimeout(() => setDeleteSuccess(''), 5000);
      await fetchProjects();
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to cancel deletion request.');
    } finally { setCancelLoading(false); }
  };

  const handleTabChange = (tabId) => {
    console.log(`[StudentDashboard] Tab changed to: ${tabId}`);
    setActiveTab(tabId);
  };

  const isPendingDeletion = selectedProject?.status === 'pending_deletion';
  const hasMentor = !!selectedProject?.mentor_id || !!user?.assigned_mentor_id;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar onOpenPlanner={() => setShowPlanner(true)} onNavigate={handleTabChange} />

      <div className="flex flex-1">
        <Sidebar activeTab={activeTab} setActiveTab={handleTabChange} userRole="STUDENT" />

        <main className="flex-1 p-6 overflow-y-auto space-y-6">

          {/* Project header bar */}
          <div className="glass-card p-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400">
                <Folder className="h-5 w-5" />
              </div>
              <div>
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                  Active Academic Project
                </label>
                <div className="flex items-center gap-3 mt-0.5">
                  {projects.length > 0 ? (
                    <select
                      value={selectedProject?.id || ''}
                      onChange={(e) => {
                        const p = projects.find((proj) => proj.id === e.target.value);
                        setSelectedProject(p);
                      }}
                      className="bg-slate-900 border border-slate-700 text-white font-bold text-base rounded-xl px-3 py-1 focus:outline-none focus:border-indigo-500 cursor-pointer"
                    >
                      {projects.map((p) => (
                        <option key={p.id} value={p.id}>{p.title}</option>
                      ))}
                    </select>
                  ) : (
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-400 italic">No projects created yet</span>
                      <button
                        onClick={() => setShowPlanner(true)}
                        className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold underline underline-offset-2 ml-1"
                      >
                        + Create with AI Planner
                      </button>
                    </div>
                  )}

                  {/* Status badge */}
                  {selectedProject?.status === 'pending_deletion' && (
                    <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-amber-950/80 text-amber-400 border border-amber-800/60 shrink-0">
                      <AlertTriangle className="h-3 w-3" /> Pending Deletion
                    </span>
                  )}
                  {selectedProject?.status === 'completed' && (
                    <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 shrink-0">
                      <CheckCircle2 className="h-3 w-3" /> Completed
                    </span>
                  )}
                </div>
              </div>
            </div>

            {selectedProject && (
              <div className="flex items-center gap-4 text-xs border-l border-slate-800 pl-6">
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

                {/* Request Deletion button — only when mentor assigned and not already pending */}
                {hasMentor && !isPendingDeletion && selectedProject?.status !== 'completed' && (
                  <button
                    onClick={() => setShowDeleteModal(true)}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-950/60 border border-rose-800/50 text-rose-300 hover:bg-rose-950 transition-all"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Request Deletion
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Success/cancel toast */}
          {deleteSuccess && (
            <div className="glass-card flex items-center justify-between gap-3 px-4 py-3 border-emerald-800/50 bg-emerald-950/30 text-emerald-300 text-sm">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                {deleteSuccess}
              </div>
              <button onClick={() => setDeleteSuccess('')} className="text-emerald-500 hover:text-emerald-300 transition-colors">
                <X className="h-4 w-4" />
              </button>
            </div>
          )}

          {/* Pending deletion cancel banner */}
          {isPendingDeletion && (
            <div className="glass-card flex items-center justify-between gap-3 px-4 py-3 border-amber-800/40 bg-amber-950/20">
              <div className="flex items-center gap-2 text-amber-300 text-sm">
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-400" />
                Deletion request is pending mentor approval.
              </div>
              {pendingTicketId && (
                <button
                  onClick={handleCancelDeletion}
                  disabled={cancelLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 transition-all disabled:opacity-50"
                >
                  {cancelLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <X className="h-3.5 w-3.5" />}
                  Cancel Request
                </button>
              )}
            </div>
          )}

          {/* Tab content — conditionally rendered by activeTab */}
          {activeTab === 'kanban' && (
            selectedProject ? (
              <KanbanBoard
                tasks={tasks}
                projectId={selectedProject.id}
                projectStatus={selectedProject.status}
                onTaskUpdate={handleTaskUpdate}
                onOpenChatForTask={handleOpenChatForTask}
              />
            ) : (
              <div className="glass-card p-12 text-center space-y-4">
                <Sparkles className="h-10 w-10 text-indigo-400 mx-auto animate-pulse" />
                <h3 className="text-lg font-bold text-white">No Academic Projects Found</h3>
                <p className="text-sm text-slate-400 max-w-md mx-auto">
                  Use the AI Project Planner to automatically convert your project idea into structured sprint tasks on your Kanban board.
                </p>
                <button
                  onClick={() => setShowPlanner(true)}
                  className="glass-button-primary inline-flex items-center gap-2 text-sm"
                >
                  <Sparkles className="h-4 w-4" /> Start AI Project Planner
                </button>
              </div>
            )
          )}

          {activeTab === 'commits' && (
            <GitHubCommitFeed
              projectId={selectedProject?.id}
              githubRepo={selectedProject?.github_repo}
            />
          )}

          {activeTab === 'mentorship' && (
            <MentorshipChat
              projectId={selectedProject?.id}
              activeTask={activeTaskForChat}
            />
          )}

          {activeTab === 'supervision-chat' && (
            !selectedProject ? (
              <div className="glass-card p-10 text-center space-y-3">
                <MessageSquare className="h-10 w-10 text-slate-600 mx-auto" />
                <h3 className="text-base font-bold text-slate-300">No Active Project Selected</h3>
                <p className="text-sm text-slate-500">
                  Select or create an academic project to start a supervision chat with your faculty mentor.
                </p>
              </div>
            ) : (selectedProject.mentor_id || user?.assigned_mentor_id) ? (
              <SupervisorChatPanel
                projectId={selectedProject.id}
                mentorId={selectedProject.mentor_id || user?.assigned_mentor_id}
              />
            ) : (
              <div className="glass-card p-10 text-center space-y-3">
                <MessageSquare className="h-10 w-10 text-slate-600 mx-auto" />
                <h3 className="text-base font-bold text-slate-300">No Mentor Assigned</h3>
                <p className="text-sm text-slate-500">
                  Link a mentor in <strong>Mentor Settings</strong> to unlock supervision chat.
                </p>
              </div>
            )
          )}

          {activeTab === 'mentor-settings' && (
            <div className="glass-card p-8 space-y-6 max-w-lg mx-auto">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-indigo-950 border border-indigo-700 flex items-center justify-center text-indigo-400">
                  <KeyRound className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Faculty Mentor Assignment</h3>
                  <p className="text-xs text-slate-400">Link your account to a mentor so they can supervise your projects</p>
                </div>
              </div>

              {mentorLinkError && (
                <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs">{mentorLinkError}</div>
              )}
              {mentorLinkSuccess && (
                <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 shrink-0" /> {mentorLinkSuccess}
                </div>
              )}

              {user?.assigned_mentor_id ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-950/30 border border-emerald-800/40">
                    <UserCheck className="h-5 w-5 text-emerald-400 shrink-0" />
                    <div>
                      <p className="text-sm font-semibold text-emerald-300">Mentor Linked</p>
                      <p className="text-xs text-slate-400 mt-0.5">Your account is supervised by a faculty mentor.</p>
                    </div>
                  </div>
                  <button
                    id="unlink-mentor-btn"
                    onClick={handleUnlinkMentor}
                    disabled={mentorLinkLoading}
                    className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-rose-950/60 border border-rose-800/50 text-rose-300 hover:bg-rose-950 transition-all disabled:opacity-50"
                  >
                    {mentorLinkLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserX className="h-4 w-4" />}
                    Unlink Mentor
                  </button>
                </div>
              ) : (
                <form onSubmit={handleLinkMentor} className="space-y-4">
                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1.5">Enter Mentor Code</label>
                    <input
                      id="student-mentor-code-input"
                      type="text"
                      required
                      value={mentorCodeInput}
                      onChange={(e) => setMentorCodeInput(e.target.value.toUpperCase())}
                      className="glass-input w-full px-4 font-mono tracking-widest uppercase text-sm"
                      placeholder="MNT-XXXXX"
                      maxLength={9}
                    />
                    <p className="text-[11px] text-slate-500 mt-1.5">Format: MNT-XXXXX (9 characters)</p>
                  </div>
                  <button
                    id="link-mentor-btn"
                    type="submit"
                    disabled={mentorLinkLoading || mentorCodeInput.length < 9}
                    className="glass-button-primary flex items-center gap-2 px-5 py-2.5 text-sm font-semibold disabled:opacity-50"
                  >
                    {mentorLinkLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserCheck className="h-4 w-4" />}
                    Link Mentor
                  </button>
                </form>
              )}
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

      {/* Deletion request modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-5">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-rose-950 border border-rose-800 flex items-center justify-center text-rose-400">
                <Trash2 className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Request Project Deletion</h3>
                <p className="text-xs text-slate-400">Your mentor must approve this request</p>
              </div>
            </div>

            {deleteError && (
              <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs">{deleteError}</div>
            )}

            <form onSubmit={handleRequestDeletion} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5">
                  Reason for deletion
                </label>
                <textarea
                  required
                  value={deleteReason}
                  onChange={(e) => setDeleteReason(e.target.value)}
                  className="glass-input w-full px-4 h-24 text-sm resize-none"
                  placeholder="Explain why this project should be deleted..."
                />
              </div>
              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => { setShowDeleteModal(false); setDeleteError(''); setDeleteReason(''); }}
                  className="glass-button-secondary text-sm"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={deleteLoading || !deleteReason.trim()}
                  className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold bg-rose-600 hover:bg-rose-500 text-white disabled:opacity-50 transition-all"
                >
                  {deleteLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                  Submit Request
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentDashboard;
