import React, { useState, useEffect } from 'react';
import { GitCommit, RefreshCw, ExternalLink, CheckCircle2, AlertCircle, Clock, Edit2, Save, X } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

const GitHubCommitFeed = ({ projectId, githubRepo, onProjectUpdated }) => {
  const { user } = useAuth();
  const [commits, setCommits] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState(null);
  const [isEditingRepo, setIsEditingRepo] = useState(false);
  const [repoInput, setRepoInput] = useState('');
  const [savingRepo, setSavingRepo] = useState(false);
  const [repoError, setRepoError] = useState('');

  useEffect(() => {
    if (projectId) {
      fetchCommits();
      setRepoInput(githubRepo || '');
      setIsEditingRepo(false);
      setRepoError('');
    } else {
      setCommits([]);
    }
  }, [projectId, githubRepo]);

  const fetchCommits = async () => {
    if (!projectId) return;
    try {
      const res = await api.get(`/github/commits/${projectId}`);
      setCommits(res.data);
    } catch (err) {
      console.error("Failed to fetch commit log", err);
    }
  };

  const handleSync = async () => {
    if (!projectId) return;
    setSyncing(true);
    setSyncResult(null);
    try {
      const res = await api.post(`/github/sync/${projectId}`);
      setSyncResult(res.data);
      fetchCommits();
    } catch (err) {
      console.error("GitHub sync failed", err);
    } finally {
      setSyncing(false);
    }
  };

  const handleSaveRepo = async () => {
    if (!projectId) return;
    setSavingRepo(true);
    setRepoError('');
    try {
      const res = await api.patch(`/projects/${projectId}`, {
        github_repo: repoInput.trim() || null
      });
      setIsEditingRepo(false);
      if (onProjectUpdated) {
        onProjectUpdated(res.data);
      }
      // If we linked a new repo, try to fetch commits
      if (repoInput.trim()) {
        fetchCommits();
      }
    } catch (err) {
      console.error("Failed to update repo", err);
      setRepoError("Failed to update repository link. Make sure you own this project.");
    } finally {
      setSavingRepo(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/60 p-5 rounded-2xl border border-slate-800/80">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <GitCommit className="h-5 w-5 text-indigo-400" />
            GitHub Commit Progress Tracker
          </h3>
          <div className="mt-1 flex items-center gap-2">
            <span className="text-xs text-slate-400">Repo Link:</span>
            {!isEditingRepo ? (
              <div className="flex items-center gap-2">
                <span className="font-mono text-indigo-300 text-sm">{githubRepo || 'Not configured'}</span>
                {user?.role === 'STUDENT' && projectId && (
                  <button 
                    onClick={() => { setIsEditingRepo(true); setRepoInput(githubRepo || ''); }}
                    className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 ml-2"
                  >
                    <Edit2 className="h-3 w-3" /> {githubRepo ? 'Change' : 'Link Repository'}
                  </button>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={repoInput}
                  onChange={(e) => setRepoInput(e.target.value)}
                  placeholder="owner/repo (e.g. facebook/react)"
                  className="glass-input px-2 py-1 text-xs font-mono text-white w-48 focus:ring-1 focus:ring-indigo-500"
                  disabled={savingRepo}
                />
                <button 
                  onClick={handleSaveRepo} 
                  disabled={savingRepo}
                  className="p-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
                  title="Save"
                >
                  <Save className="h-3.5 w-3.5" />
                </button>
                <button 
                  onClick={() => setIsEditingRepo(false)} 
                  disabled={savingRepo}
                  className="p-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300"
                  title="Cancel"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            )}
          </div>
          {repoError && <p className="text-[10px] text-rose-400 mt-1">{repoError}</p>}
        </div>

        <button
          onClick={handleSync}
          disabled={syncing || !projectId}
          className="glass-button-primary flex items-center gap-2 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
          {syncing ? 'Syncing GitHub...' : 'Sync Commits'}
        </button>
      </div>

      {syncResult && (
        <div className="p-4 rounded-xl bg-indigo-950/60 border border-indigo-800/50 text-indigo-300 text-xs flex items-center justify-between">
          <span>
            Synced <strong>{syncResult.synced_commits || 0}</strong> new commits & auto-updated <strong>{syncResult.updated_tasks || 0}</strong> Kanban tasks.
          </span>
        </div>
      )}

      <div className="glass-card p-6 space-y-4">
        <h4 className="font-bold text-sm text-slate-200 uppercase tracking-wider">Commit Log Timeline</h4>

        {commits.length === 0 ? (
          <div className="text-center py-12 text-slate-400 text-sm">
            {!projectId
              ? "No active project selected. Select or create an academic project to view GitHub commit activity."
              : 'No commits recorded yet. Click "Sync Commits" above to ingest repository activity.'}
          </div>
        ) : (
          <div className="relative border-l border-slate-800 ml-4 space-y-6 pl-6 py-2">
            {commits.map((c) => (
              <div key={c.id} className="relative group">
                <div className="absolute -left-[31px] top-1.5 h-3.5 w-3.5 rounded-full bg-indigo-600 border-2 border-slate-950 group-hover:scale-125 transition-transform" />

                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-slate-700 transition-all space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold text-indigo-400 bg-indigo-950/60 px-2 py-0.5 rounded border border-indigo-900/40">
                        {c.commit_hash}
                      </span>
                      <span className="text-slate-300 font-medium">{c.author_name}</span>
                    </div>
                    <span className="text-slate-400 text-[11px]">
                      {new Date(c.commit_date).toLocaleString()}
                    </span>
                  </div>

                  <p className="text-sm font-semibold text-slate-200">{c.message}</p>

                  <div className="flex items-center justify-between pt-2 text-xs">
                    {c.task_id ? (
                      <span className="text-emerald-400 flex items-center gap-1 font-medium text-[11px] bg-emerald-950/60 px-2.5 py-0.5 rounded-full border border-emerald-900/40">
                        <CheckCircle2 className="h-3 w-3" /> Auto-Linked to Kanban Task
                      </span>
                    ) : (
                      <span className="text-slate-400 text-[11px]">General Commit</span>
                    )}

                    {c.url && (
                      <a
                        href={c.url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium"
                      >
                        View Diff <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default GitHubCommitFeed;
