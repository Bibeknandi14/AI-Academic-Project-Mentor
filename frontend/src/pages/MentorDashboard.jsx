import React, { useState, useEffect } from 'react';
import Navbar from '../components/Navbar';
import Sidebar from '../components/Sidebar';
import GitHubCommitFeed from '../components/GitHubCommitFeed';
import MentorshipChat from '../components/MentorshipChat';
import api from '../services/api';
import { LayoutDashboard, AlertTriangle, CheckCircle2, GitCommit, Users, ArrowRight, Shield } from 'lucide-react';

const MentorDashboard = () => {
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [activeTab, setActiveTab] = useState('oversight');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMentorProjects();
  }, []);

  const fetchMentorProjects = async () => {
    try {
      const res = await api.get('/projects/');
      setProjects(res.data);
    } catch (err) {
      console.error("Failed to fetch mentor projects", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar onOpenPlanner={() => {}} />

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

          {activeTab === 'oversight' && (
            <div className="space-y-6">
              {/* Summary Stats Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div className="glass-card p-5 space-y-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase">Assigned Projects</span>
                  <div className="text-3xl font-extrabold text-white">{projects.length}</div>
                  <p className="text-xs text-slate-500">Active student teams</p>
                </div>

                <div className="glass-card p-5 space-y-2">
                  <span className="text-xs font-semibold text-slate-400 uppercase">Healthy Progress</span>
                  <div className="text-3xl font-extrabold text-emerald-400">
                    {projects.filter((p) => !p.is_at_risk).length}
                  </div>
                  <p className="text-xs text-emerald-500/80">Active commits & on-schedule sprints</p>
                </div>

                <div className="glass-card p-5 space-y-2 border-rose-900/40">
                  <span className="text-xs font-semibold text-rose-400 uppercase">Projects At Risk</span>
                  <div className="text-3xl font-extrabold text-rose-400">
                    {projects.filter((p) => p.is_at_risk).length}
                  </div>
                  <p className="text-xs text-rose-500/80">Inactive commits or delayed tasks</p>
                </div>
              </div>

              {/* Student Project Cards */}
              <div className="space-y-4">
                <h3 className="text-base font-bold text-slate-200">Student Team Projects</h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                  {projects.map((proj) => {
                    const percentComplete = proj.total_tasks > 0 
                      ? Math.round((proj.completed_tasks / proj.total_tasks) * 100)
                      : 0;

                    return (
                      <div
                        key={proj.id}
                        className={`glass-card p-6 space-y-4 transition-all hover:border-slate-700 relative overflow-hidden ${
                          proj.is_at_risk ? 'border-rose-900/40' : ''
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <h4 className="font-bold text-lg text-white">{proj.title}</h4>
                            <p className="text-xs text-slate-400 mt-1 line-clamp-2">{proj.description}</p>
                          </div>
                          {proj.is_at_risk ? (
                            <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-rose-950/80 text-rose-400 border border-rose-800/60 shrink-0">
                              <AlertTriangle className="h-3 w-3" /> AT RISK
                            </span>
                          ) : (
                            <span className="flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 shrink-0">
                              <CheckCircle2 className="h-3 w-3" /> ON TRACK
                            </span>
                          )}
                        </div>

                        {/* Progress Bar */}
                        <div className="space-y-1.5">
                          <div className="flex justify-between text-xs font-semibold">
                            <span className="text-slate-300">Sprint Task Completion</span>
                            <span className="text-indigo-400">{percentComplete}% ({proj.completed_tasks}/{proj.total_tasks})</span>
                          </div>
                          <div className="h-2 w-full bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                            <div
                              className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-500"
                              style={{ width: `${percentComplete}%` }}
                            />
                          </div>
                        </div>

                        <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 text-xs">
                          <div className="flex items-center gap-4 text-slate-400">
                            <span className="flex items-center gap-1">
                              <GitCommit className="h-3.5 w-3.5 text-indigo-400" /> {proj.commit_count} Commits
                            </span>
                            <span className="font-mono text-indigo-300">{proj.github_repo || 'No repo'}</span>
                          </div>

                          <button
                            onClick={() => {
                              setSelectedProject(proj);
                              setActiveTab('commits');
                            }}
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

          {activeTab === 'commits' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <label className="text-xs text-slate-400 font-semibold">Select Team Project:</label>
                <select
                  value={selectedProject?.id || (projects[0]?.id || '')}
                  onChange={(e) => {
                    const p = projects.find((proj) => proj.id === e.target.value);
                    setSelectedProject(p);
                  }}
                  className="bg-slate-900 border border-slate-700 text-white font-semibold text-sm rounded-lg px-3 py-1.5 focus:outline-none"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.title}</option>
                  ))}
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

          {activeTab === 'mentorship' && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                <label className="text-xs text-slate-400 font-semibold">Inspect AI Mentorship Thread For:</label>
                <select
                  value={selectedProject?.id || (projects[0]?.id || '')}
                  onChange={(e) => {
                    const p = projects.find((proj) => proj.id === e.target.value);
                    setSelectedProject(p);
                  }}
                  className="bg-slate-900 border border-slate-700 text-white font-semibold text-sm rounded-lg px-3 py-1.5 focus:outline-none"
                >
                  {projects.map((p) => (
                    <option key={p.id} value={p.id}>{p.title}</option>
                  ))}
                </select>
              </div>

              {(selectedProject || projects[0]) && (
                <MentorshipChat
                  projectId={(selectedProject || projects[0]).id}
                  activeTask={null}
                />
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default MentorDashboard;
