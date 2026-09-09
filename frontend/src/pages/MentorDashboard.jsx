import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import GitHubCommitFeed from '../components/GitHubCommitFeed';
import MentorshipChat from '../components/MentorshipChat';
import SupervisorChatPanel from '../components/SupervisorChatPanel';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import {
  LayoutDashboard, AlertTriangle, CheckCircle2, GitCommit,
  ArrowRight, Shield, KeyRound, Copy, Check, Users, Trash2,
  Loader2, MessageSquare, UserX, X, Send, ExternalLink, Clock, PlayCircle, Folder, History
} from 'lucide-react';

const MentorDashboard = () => {
  const { user } = useAuth();
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [activeTab, setActiveTab] = useState('oversight');
  const [loading, setLoading] = useState(true);
  const [codeCopied, setCodeCopied] = useState(false);

  // My Students tab
  const [students, setStudents] = useState([]);
  const [studentsLoading, setStudentsLoading] = useState(false);

  // Pending Deletions tab
  const [tickets, setTickets] = useState([]);
  const [ticketsLoading, setTicketsLoading] = useState(false);
  const [rejectModal, setRejectModal] = useState(null); // ticket id
  const [rejectNote, setRejectNote] = useState('');
  const [actionLoading, setActionLoading] = useState('');

  // Supervision chat tab — project selector
  const [supervisionProject, setSupervisionProject] = useState(null);

  // Activity log
  const [activityLog, setActivityLog] = useState([]);
  const [activityLogLoading, setActivityLogLoading] = useState(false);

  // Student project drill-down detail modal state
  const [selectedStudentDetail, setSelectedStudentDetail] = useState(null); // { student, project }
  const [detailTasks, setDetailTasks] = useState([]);
  const [detailCommits, setDetailCommits] = useState([]);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailSupervisionMsg, setDetailSupervisionMsg] = useState('');
  const [sendingDetailMsg, setSendingDetailMsg] = useState(false);
  const [detailMsgSuccess, setDetailMsgSuccess] = useState('');
  const [detailActiveSubTab, setDetailActiveSubTab] = useState('tasks'); // 'tasks' | 'commits'

  useEffect(() => { fetchMentorProjects(); }, []);

  useEffect(() => {
    if (activeTab === 'students') fetchStudents();
    if (activeTab === 'pending-deletions') fetchTickets();
    if (activeTab === 'activity-log') fetchActivityLog();
  }, [activeTab]);

  const fetchActivityLog = async () => {
    setActivityLogLoading(true);
    try {
      const res = await api.get('/supervision/activity-log');
      setActivityLog(res.data);
    } catch (err) { console.error('Failed to load activity log', err); }
    finally { setActivityLogLoading(false); }
  };

  const fetchMentorProjects = async () => {
    try {
      const res = await api.get('/projects/');
      setProjects(res.data);
      if (res.data.length > 0 && !supervisionProject) setSupervisionProject(res.data[0]);
    } catch (err) { console.error('Failed to fetch mentor projects', err); }
    finally { setLoading(false); }
  };

  const fetchStudents = async () => {
    setStudentsLoading(true);
    try {
      const res = await api.get('/supervision/students');
      setStudents(res.data);
    } catch (err) { console.error('Failed to load students', err); }
    finally { setStudentsLoading(false); }
  };

  const handleOpenStudentDetail = async (student, project) => {
    setSelectedStudentDetail({ student, project });
    setDetailLoading(true);
    setDetailSupervisionMsg('');
    setDetailMsgSuccess('');
    setDetailActiveSubTab('tasks');
    try {
      const [tasksRes, commitsRes] = await Promise.all([
        api.get(`/tasks/project/${project.id}`),
        api.get(`/github/commits/${project.id}`).catch(() => ({ data: [] })),
      ]);
      setDetailTasks(tasksRes.data);
      setDetailCommits(commitsRes.data);
    } catch (err) {
      console.error('Failed to load project details', err);
    } finally {
      setDetailLoading(false);
    }
  };

  const handleSendDetailSupervisionMsg = async (e) => {
    e.preventDefault();
    if (!selectedStudentDetail?.project?.id || !detailSupervisionMsg.trim() || sendingDetailMsg) return;
    setSendingDetailMsg(true);
    setDetailMsgSuccess('');
    try {
      await api.post(`/supervision/messages/${selectedStudentDetail.project.id}`, {
        project_id: selectedStudentDetail.project.id,
        message: detailSupervisionMsg.trim(),
        receiver_id: selectedStudentDetail.student.id,
      });
      setDetailSupervisionMsg('');
      setDetailMsgSuccess('Message sent to student!');
      setTimeout(() => setDetailMsgSuccess(''), 3500);
    } catch (err) {
      console.error('Failed to send supervision message', err);
    } finally {
      setSendingDetailMsg(false);
    }
  };

  const fetchTickets = async () => {
    setTicketsLoading(true);
    try {
      const res = await api.get('/deletion-tickets/');
      setTickets(res.data);
    } catch (err) { console.error('Failed to load tickets', err); }
    finally { setTicketsLoading(false); }
  };

  const handleCopyCode = () => {
    if (user?.mentor_code) {
      navigator.clipboard.writeText(user.mentor_code);
      setCodeCopied(true);
      setTimeout(() => setCodeCopied(false), 2000);
    }
  };

  const handleMarkComplete = async (projectId) => {
    setActionLoading(projectId);
    try {
      await api.patch(`/supervision/projects/${projectId}/complete`);
      await fetchStudents();
    } catch (err) { console.error(err); }
    finally { setActionLoading(''); }
  };

  const handleUnassignStudent = async (studentId) => {
    setActionLoading(studentId);
    try {
      await api.patch(`/supervision/students/${studentId}/unassign`);
      await fetchStudents();
    } catch (err) { console.error(err); }
    finally { setActionLoading(''); }
  };

  const handleApproveTicket = async (ticketId) => {
    setActionLoading(ticketId);
    try {
      await api.post(`/deletion-tickets/${ticketId}/approve`);
      await fetchTickets();
      await fetchMentorProjects(); // project was deleted, refresh list
    } catch (err) { console.error(err); }
    finally { setActionLoading(''); }
  };

  const handleRejectTicket = async () => {
    if (!rejectModal || !rejectNote.trim()) return;
    setActionLoading(rejectModal);
    try {
      await api.post(`/deletion-tickets/${rejectModal}/reject`, { rejection_note: rejectNote });
      setRejectModal(null);
      setRejectNote('');
      await fetchTickets();
    } catch (err) { console.error(err); }
    finally { setActionLoading(''); }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar onOpenPlanner={() => {}} onNavigate={setActiveTab} />

      <div className="flex flex-1">
        <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} userRole="MENTOR" />

        <main className="flex-1 p-6 overflow-y-auto space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                <Shield className="h-5 w-5 text-indigo-400" /> Faculty Mentor Oversight Center
              </h2>
              <p className="text-sm text-slate-400">Real-time daily progress monitoring across all student teams</p>
            </div>
          </div>

          {/* ── Oversight Tab ─────────────────────────────────────────── */}
          {activeTab === 'oversight' && (
            <div className="space-y-6">
              {/* Mentor Code Card */}
              {user?.mentor_code && (
                <div className="glass-card p-5 flex flex-wrap items-center justify-between gap-4 border-indigo-900/50 bg-indigo-950/20">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-indigo-950 border border-indigo-700 flex items-center justify-center text-indigo-400 shrink-0">
                      <KeyRound className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="text-[11px] font-semibold text-indigo-300 uppercase tracking-wider">Your Mentor Code</p>
                      <p className="text-[11px] text-slate-400 mt-0.5">Share this with students so they can link their work to your dashboard</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-2xl font-extrabold tracking-[0.25em] text-white bg-slate-900 border border-indigo-700/60 px-5 py-2 rounded-xl shadow-inner shadow-indigo-950">
                      {user.mentor_code}
                    </span>
                    <button
                      id="copy-mentor-code-btn"
                      onClick={handleCopyCode}
                      className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                        codeCopied
                          ? 'bg-emerald-950/80 border border-emerald-700 text-emerald-300'
                          : 'glass-button-secondary'
                      }`}
                    >
                      {codeCopied ? <><Check className="h-4 w-4" /> Copied!</> : <><Copy className="h-4 w-4" /> Copy Code</>}
                    </button>
                  </div>
                </div>
              )}

              {/* Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="glass-card p-5 space-y-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase">Assigned Projects</span>
                  <div className="text-3xl font-extrabold text-white">{projects.length}</div>
                  <p className="text-xs text-slate-500">Active student teams</p>
                </div>
                <div className="glass-card p-5 space-y-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase">Healthy Progress</span>
                  <div className="text-3xl font-extrabold text-emerald-400">{projects.filter((p) => !p.is_at_risk).length}</div>
                  <p className="text-xs text-emerald-500/80">Active commits & on-schedule sprints</p>
                </div>
                <div className="glass-card p-5 space-y-2 border-rose-900/40">
                  <span className="text-xs font-semibold text-rose-400 uppercase">Projects At Risk</span>
                  <div className="text-3xl font-extrabold text-rose-400">{projects.filter((p) => p.is_at_risk).length}</div>
                  <p className="text-xs text-rose-500/80">Inactive commits or delayed tasks</p>
                </div>
              </div>

              {/* Project cards */}
              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-200">Student Team Projects</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {projects.map((proj) => {
                    const pct = proj.total_tasks > 0
                      ? Math.round((proj.completed_tasks / proj.total_tasks) * 100) : 0;
                    return (
                      <div key={proj.id} className={`glass-card p-6 space-y-4 transition-all hover:border-slate-700 ${proj.is_at_risk ? 'border-rose-900/40' : ''}`}>
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h4 className="font-bold text-lg text-white">{proj.title}</h4>
                            <p className="text-xs text-slate-400 mt-1 line-clamp-2">{proj.description}</p>
                          </div>
                          {proj.is_at_risk
                            ? <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-rose-950/80 text-rose-400 border border-rose-800/60 shrink-0"><AlertTriangle className="h-3 w-3" /> AT RISK</span>
                            : <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 shrink-0"><CheckCircle2 className="h-3 w-3" /> ON TRACK</span>
                          }
                        </div>
                        <div className="space-y-1.5">
                          <div className="flex justify-between text-xs font-semibold">
                            <span className="text-slate-300">Sprint Task Completion</span>
                            <span className="text-indigo-400">{pct}% ({proj.completed_tasks}/{proj.total_tasks})</span>
                          </div>
                          <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                            <div className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-500" style={{ width: `${pct}%` }} />
                          </div>
                        </div>
                        <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs">
                          <div className="flex items-center gap-4 text-slate-400">
                            <span className="flex items-center gap-1"><GitCommit className="h-3.5 w-3.5 text-indigo-400" /> {proj.commit_count} Commits</span>
                            <span className="font-mono text-indigo-300">{proj.github_repo || 'No repo'}</span>
                          </div>
                          <button
                            onClick={() => { setSelectedProject(proj); setActiveTab('commits'); }}
                            className="glass-button-secondary text-xs flex items-center gap-1.5 py-1.5"
                          >
                            Inspect Log <ArrowRight className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ── My Students Tab ───────────────────────────────────────── */}
          {activeTab === 'students' && (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-bold text-slate-200 flex items-center gap-2">
                  <Users className="h-5 w-5 text-indigo-400" /> My Assigned Students
                </h3>
                <span className="text-xs text-slate-400">Click student or project to inspect full sprint tasks & commit stream</span>
              </div>
              {studentsLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="h-6 w-6 text-indigo-400 animate-spin" />
                </div>
              ) : students.length === 0 ? (
                <div className="glass-card p-12 text-center space-y-3">
                  <Users className="h-10 w-10 text-slate-600 mx-auto" />
                  <h4 className="text-base font-bold text-slate-300">No students yet</h4>
                  <p className="text-sm text-slate-500">Share your mentor code with students so they can link to you.</p>
                </div>
              ) : (
                students.map((student) => (
                  <div key={student.id} className="glass-card p-6 space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h4
                          onClick={() => student.projects[0] && handleOpenStudentDetail(student, student.projects[0])}
                          className={`font-bold text-white text-base ${student.projects.length > 0 ? 'hover:text-indigo-300 cursor-pointer' : ''}`}
                        >
                          {student.full_name}
                        </h4>
                        <p className="text-xs text-slate-400">{student.email}
                          {student.github_username && <span className="ml-2 font-mono text-indigo-400">@{student.github_username}</span>}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {student.projects[0] && (
                          <button
                            onClick={() => handleOpenStudentDetail(student, student.projects[0])}
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-950/60 border border-indigo-800/50 text-indigo-300 hover:bg-indigo-900/60 transition-all"
                          >
                            <LayoutDashboard className="h-3.5 w-3.5" /> Inspect Project
                          </button>
                        )}
                        <button
                          onClick={() => handleUnassignStudent(student.id)}
                          disabled={actionLoading === student.id}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-rose-950/60 border border-rose-800/50 text-rose-300 hover:bg-rose-950 transition-all disabled:opacity-50"
                        >
                          {actionLoading === student.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <UserX className="h-3.5 w-3.5" />}
                          Unassign
                        </button>
                      </div>
                    </div>

                    {student.projects.length === 0 ? (
                      <p className="text-xs text-slate-500 italic">No projects linked to this student yet.</p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {student.projects.map((proj) => {
                          const pct = proj.total_tasks > 0
                            ? Math.round((proj.completed_tasks / proj.total_tasks) * 100) : 0;
                          return (
                            <div
                              key={proj.id}
                              onClick={() => handleOpenStudentDetail(student, proj)}
                              className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3 hover:border-indigo-500/50 cursor-pointer transition-all group"
                            >
                              <div className="flex items-center justify-between">
                                <p className="text-sm font-bold text-slate-100 group-hover:text-indigo-300 transition-colors flex items-center gap-2">
                                  {proj.title}
                                  <ArrowRight className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                                </p>
                                <div className="flex items-center gap-2">
                                  {proj.status === 'pending_deletion' && (
                                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-950/80 text-amber-400 border border-amber-800/60">Deletion Pending</span>
                                  )}
                                  {proj.is_at_risk && (
                                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-950/80 text-rose-400 border border-rose-800/60">At Risk</span>
                                  )}
                                </div>
                              </div>
                              <div className="space-y-1">
                                <div className="flex justify-between text-xs text-slate-400">
                                  <span>Progress</span>
                                  <span className="text-indigo-400">{pct}% ({proj.completed_tasks}/{proj.total_tasks} tasks)</span>
                                </div>
                                <div className="h-1.5 w-full bg-slate-950 rounded-full overflow-hidden">
                                  <div className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all" style={{ width: `${pct}%` }} />
                                </div>
                              </div>
                              <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                                <span className="flex items-center gap-1"><GitCommit className="h-3 w-3 text-indigo-400" /> {proj.commit_count} commits</span>
                                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                                  {proj.status === 'active' && (
                                    <button
                                      onClick={() => handleMarkComplete(proj.id)}
                                      disabled={actionLoading === proj.id}
                                      className="flex items-center gap-1 px-2 py-1 rounded-lg bg-emerald-950/60 border border-emerald-800/50 text-emerald-300 hover:bg-emerald-950 transition-all text-[10px] font-bold disabled:opacity-50"
                                    >
                                      {actionLoading === proj.id ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3 w-3" />}
                                      Mark Complete
                                    </button>
                                  )}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* ── Pending Deletions Tab ─────────────────────────────────── */}
          {activeTab === 'pending-deletions' && (
            <div className="space-y-5">
              <h3 className="text-base font-bold text-slate-200 flex items-center gap-2">
                <Trash2 className="h-5 w-5 text-rose-400" /> Pending Deletion Requests
              </h3>
              {ticketsLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="h-6 w-6 text-indigo-400 animate-spin" />
                </div>
              ) : tickets.length === 0 ? (
                <div className="glass-card p-12 text-center space-y-3">
                  <CheckCircle2 className="h-10 w-10 text-emerald-500 mx-auto" />
                  <h4 className="text-base font-bold text-slate-300">No pending requests</h4>
                  <p className="text-sm text-slate-500">All caught up — no students are requesting project deletion.</p>
                </div>
              ) : (
                tickets.map((ticket) => (
                  <div key={ticket.id} className="glass-card p-6 space-y-4 border-amber-900/30">
                    <div className="flex items-start justify-between gap-4">
                      <div className="space-y-1">
                        <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider">Deletion Request</span>
                        <p className="text-xs text-slate-400">Project ID: <span className="font-mono text-slate-300">{ticket.project_id}</span></p>
                        <p className="text-sm text-slate-200 mt-2"><strong>Reason:</strong> {ticket.reason}</p>
                        <p className="text-[11px] text-slate-500 mt-1">
                          Submitted: {new Date(ticket.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3 pt-2 border-t border-slate-800">
                      <button
                        onClick={() => handleApproveTicket(ticket.id)}
                        disabled={!!actionLoading}
                        className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold bg-rose-600 hover:bg-rose-500 text-white transition-all disabled:opacity-50"
                      >
                        {actionLoading === ticket.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trash2 className="h-4 w-4" />}
                        Approve & Delete Project
                      </button>
                      <button
                        onClick={() => setRejectModal(ticket.id)}
                        disabled={!!actionLoading}
                        className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold glass-button-secondary disabled:opacity-50"
                      >
                        <X className="h-4 w-4" /> Reject Request
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}

          {/* ── Commits Tab ──────────────────────────────────────────── */}
          {activeTab === 'commits' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <label className="text-xs text-slate-400 font-semibold">Select Team Project:</label>
                <select
                  value={selectedProject?.id || (projects[0]?.id || '')}
                  onChange={(e) => setSelectedProject(projects.find((p) => p.id === e.target.value))}
                  className="bg-slate-900 border border-slate-700 text-white font-semibold text-sm rounded-lg px-3 py-1.5 focus:outline-none"
                >
                  {projects.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
                </select>
              </div>
              {(selectedProject || projects[0]) && (
                <GitHubCommitFeed
                  projectId={(selectedProject || projects[0]).id}
                  githubRepo={(selectedProject || projects[0]).github_repo}
                />
              )}
            </div>
          )}

          {/* ── Supervision Chat Tab ──────────────────────────────────── */}
          {activeTab === 'supervision-chat' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <label className="text-xs text-slate-400 font-semibold">
                  <MessageSquare className="inline h-3.5 w-3.5 mr-1 text-emerald-400" />
                  Project Thread:
                </label>
                <select
                  value={supervisionProject?.id || ''}
                  onChange={(e) => setSupervisionProject(projects.find((p) => p.id === e.target.value))}
                  className="bg-slate-900 border border-slate-700 text-white font-semibold text-sm rounded-lg px-3 py-1.5 focus:outline-none"
                >
                  {projects.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
                </select>
              </div>
              {supervisionProject ? (
                <SupervisorChatPanel
                  projectId={supervisionProject.id}
                  mentorId={user?.id}
                />
              ) : (
                <div className="glass-card p-10 text-center text-slate-500 text-sm">No projects assigned yet.</div>
              )}
            </div>
          )}

          {/* ── AI Assistance Logs Tab ────────────────────────────────── */}
          {activeTab === 'mentorship' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <label className="text-xs text-slate-400 font-semibold">Inspect AI Mentorship Thread For:</label>
                <select
                  value={selectedProject?.id || (projects[0]?.id || '')}
                  onChange={(e) => setSelectedProject(projects.find((p) => p.id === e.target.value))}
                  className="bg-slate-900 border border-slate-700 text-white font-semibold text-sm rounded-lg px-3 py-1.5 focus:outline-none"
                >
                  {projects.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
                </select>
              </div>
              {(selectedProject || projects[0]) && (
                <MentorshipChat projectId={(selectedProject || projects[0]).id} activeTask={null} />
              )}
            </div>
          )}

          {/* ── Activity Log Tab ──────────────────────────────────────── */}
          {activeTab === 'activity-log' && (
            <div className="space-y-4">
              <h3 className="text-base font-bold text-slate-200 flex items-center gap-2">
                <History className="h-5 w-5 text-indigo-400" /> Activity Log
              </h3>
              <p className="text-xs text-slate-500">Unified history of all your actions across all students, newest first.</p>
              {activityLogLoading ? (
                <div className="flex items-center justify-center py-16">
                  <Loader2 className="h-6 w-6 text-indigo-400 animate-spin" />
                </div>
              ) : activityLog.length === 0 ? (
                <div className="glass-card p-12 text-center space-y-3">
                  <History className="h-10 w-10 text-slate-600 mx-auto" />
                  <h4 className="text-base font-bold text-slate-300">No activity yet</h4>
                  <p className="text-sm text-slate-500">Actions like approving deletions, marking projects complete, or unassigning students will appear here.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {activityLog.map((entry) => {
                    const badges = {
                      approved_deletion: { label: 'Approved Deletion', color: 'text-rose-300 bg-rose-950/60 border-rose-800/50' },
                      rejected_deletion: { label: 'Rejected Deletion', color: 'text-amber-300 bg-amber-950/60 border-amber-800/50' },
                      marked_completed: { label: 'Marked Completed', color: 'text-emerald-300 bg-emerald-950/60 border-emerald-800/50' },
                      unassigned_student: { label: 'Unassigned Student', color: 'text-slate-300 bg-slate-800/60 border-slate-700/50' },
                    };
                    const badge = badges[entry.action_type] || { label: entry.action_type, color: 'text-indigo-300 bg-indigo-950/60 border-indigo-800/50' };
                    return (
                      <div key={entry.id} className="glass-card px-5 py-4 flex items-start gap-4">
                        <div className="h-9 w-9 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                          <History className="h-4 w-4 text-indigo-400" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full border ${badge.color}`}>
                              {badge.label}
                            </span>
                          </div>
                          {entry.detail && (
                            <p className="text-sm text-slate-300 mt-1.5 leading-snug">{entry.detail}</p>
                          )}
                          <p className="text-[11px] text-slate-500 mt-1.5">
                            {new Date(entry.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* Reject confirmation modal */}
      {rejectModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-card max-w-md w-full p-6 space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <X className="h-5 w-5 text-rose-400" /> Reject Deletion Request
            </h3>
            <p className="text-xs text-slate-400">Provide a reason — the student will be able to read this.</p>
            <textarea
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              className="glass-input w-full px-4 h-24 text-sm resize-none"
              placeholder="e.g. Project is still referenced in upcoming assessments..."
            />
            <div className="flex justify-end gap-3">
              <button onClick={() => { setRejectModal(null); setRejectNote(''); }} className="glass-button-secondary text-sm">
                Cancel
              </button>
              <button
                onClick={handleRejectTicket}
                disabled={!rejectNote.trim() || !!actionLoading}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold glass-button-secondary border-rose-800/50 text-rose-300 disabled:opacity-50"
              >
                {actionLoading === rejectModal ? <Loader2 className="h-4 w-4 animate-spin" /> : <X className="h-4 w-4" />}
                Confirm Rejection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Student Project Detail Drill-Down Modal */}
      {selectedStudentDetail && (
        <div className="fixed inset-0 z-50 bg-slate-950/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="glass-card max-w-3xl w-full max-h-[90vh] flex flex-col p-6 space-y-5 overflow-hidden shadow-2xl border-indigo-900/60">
            {/* Header */}
            <div className="flex items-start justify-between gap-4 border-b border-slate-800 pb-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2.5">
                  <div className="h-9 w-9 rounded-xl bg-indigo-950 border border-indigo-700 flex items-center justify-center text-indigo-400">
                    <Folder className="h-5 w-5" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                      {selectedStudentDetail.project.title}
                      {selectedStudentDetail.project.is_at_risk && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-950/80 text-rose-400 border border-rose-800/60">
                          At Risk
                        </span>
                      )}
                      {selectedStudentDetail.project.status === 'completed' && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                          Completed
                        </span>
                      )}
                    </h3>
                    <p className="text-xs text-slate-400">
                      Owner: <strong className="text-slate-200">{selectedStudentDetail.student.full_name}</strong> &bull; {selectedStudentDetail.student.email}
                      {selectedStudentDetail.student.github_username && (
                        <span className="ml-2 font-mono text-indigo-400">@{selectedStudentDetail.student.github_username}</span>
                      )}
                    </p>
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedStudentDetail(null)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800/60 transition-all"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Quick Stats Bar */}
            <div className="grid grid-cols-3 gap-3">
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
                <span className="text-[11px] font-semibold text-slate-400 uppercase">Tasks Completed</span>
                <p className="text-base font-bold text-emerald-400 mt-0.5">
                  {detailTasks.filter(t => t.status === 'DONE').length} / {detailTasks.length}
                </p>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
                <span className="text-[11px] font-semibold text-slate-400 uppercase">Total Commits</span>
                <p className="text-base font-bold text-indigo-300 mt-0.5">{detailCommits.length}</p>
              </div>
              <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800 text-center">
                <span className="text-[11px] font-semibold text-slate-400 uppercase">GitHub Repo</span>
                <p className="text-xs font-mono font-bold text-slate-300 mt-1 truncate">
                  {selectedStudentDetail.project.github_repo || 'None'}
                </p>
              </div>
            </div>

            {/* Sub Tabs: Tasks vs Commits */}
            <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
              <button
                onClick={() => setDetailActiveSubTab('tasks')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  detailActiveSubTab === 'tasks'
                    ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Sprint Tasks ({detailTasks.length})
              </button>
              <button
                onClick={() => setDetailActiveSubTab('commits')}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  detailActiveSubTab === 'commits'
                    ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                GitHub Commits ({detailCommits.length})
              </button>
            </div>

            {/* Tab Body */}
            <div className="flex-1 overflow-y-auto min-h-[180px] max-h-[260px] space-y-3 pr-1">
              {detailLoading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-6 w-6 text-indigo-400 animate-spin" />
                </div>
              ) : detailActiveSubTab === 'tasks' ? (
                detailTasks.length === 0 ? (
                  <div className="text-center py-10 text-slate-500 text-xs">No sprint tasks created in this project yet.</div>
                ) : (
                  <div className="space-y-2">
                    {detailTasks.map((t) => (
                      <div key={t.id} className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between gap-3 text-xs">
                        <div className="space-y-0.5">
                          <p className="font-semibold text-slate-200">{t.title}</p>
                          <p className="text-[11px] text-slate-400">{t.sprint_name || 'Sprint 1'} &bull; {t.epic_name || 'Core'}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            t.priority === 'HIGH' ? 'bg-rose-950/80 text-rose-300 border border-rose-800/40' : 'bg-slate-800 text-slate-400'
                          }`}>
                            {t.priority}
                          </span>
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            t.status === 'DONE' ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/40' :
                            t.status === 'IN_PROGRESS' ? 'bg-amber-950/80 text-amber-400 border border-amber-800/40' :
                            'bg-slate-800 text-slate-300'
                          }`}>
                            {t.status}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )
              ) : (
                detailCommits.length === 0 ? (
                  <div className="text-center py-10 text-slate-500 text-xs">No commits synced for this project yet.</div>
                ) : (
                  <div className="space-y-2">
                    {detailCommits.map((c) => (
                      <div key={c.id} className="p-3 rounded-xl bg-slate-900/60 border border-slate-800 text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-indigo-400 bg-indigo-950/60 px-1.5 py-0.5 rounded text-[10px]">
                            {c.commit_hash}
                          </span>
                          <span className="text-slate-500 text-[10px]">{new Date(c.commit_date).toLocaleString()}</span>
                        </div>
                        <p className="font-semibold text-slate-200">{c.message}</p>
                      </div>
                    ))}
                  </div>
                )
              )}
            </div>

            {/* Direct Supervision Message Composer */}
            <form onSubmit={handleSendDetailSupervisionMsg} className="pt-3 border-t border-slate-800 space-y-2">
              <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <MessageSquare className="h-3.5 w-3.5 text-emerald-400" /> Send Direct Supervision Message:
                </span>
                {detailMsgSuccess && (
                  <span className="text-emerald-400 font-normal text-[11px] flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" /> {detailMsgSuccess}
                  </span>
                )}
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={detailSupervisionMsg}
                  onChange={(e) => setDetailSupervisionMsg(e.target.value)}
                  placeholder={`Write feedback or instruction for ${selectedStudentDetail.student.full_name}...`}
                  className="glass-input flex-1 px-3 text-xs"
                />
                <button
                  type="submit"
                  disabled={sendingDetailMsg || !detailSupervisionMsg.trim()}
                  className="glass-button-primary flex items-center gap-1.5 text-xs py-2 px-3.5 disabled:opacity-50"
                >
                  {sendingDetailMsg ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                  Send
                </button>
              </div>
            </form>

            {/* Modal Bottom Actions */}
            <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
              <button
                type="button"
                onClick={() => {
                  setSupervisionProject(selectedStudentDetail.project);
                  setActiveTab('supervision-chat');
                  setSelectedStudentDetail(null);
                }}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1.5 underline underline-offset-2"
              >
                <MessageSquare className="h-3.5 w-3.5" /> Open Full Supervision Thread
              </button>
              <div className="flex items-center gap-2">
                {selectedStudentDetail.project.status === 'active' && (
                  <button
                    type="button"
                    onClick={async () => {
                      await handleMarkComplete(selectedStudentDetail.project.id);
                      setSelectedStudentDetail(null);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/70 border border-emerald-800/60 text-emerald-300 text-xs font-semibold hover:bg-emerald-900/70 transition-all"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5" /> Mark Completed
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setSelectedStudentDetail(null)}
                  className="glass-button-secondary text-xs"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MentorDashboard;
