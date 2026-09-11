import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import {
  X,
  User,
  Mail,
  Github,
  Shield,
  KeyRound,
  Copy,
  Check,
  Edit2,
  Save,
  Loader2,
  CheckCircle2,
  AlertCircle,
  GraduationCap
} from 'lucide-react';

const ProfileModal = ({ isOpen, onClose }) => {
  const { user, updateUser } = useAuth();

  const [isEditing, setIsEditing] = useState(false);
  const [fullName, setFullName] = useState('');
  const [githubUsername, setGithubUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [profileData, setProfileData] = useState(null);
  const [fetching, setFetching] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [copiedCode, setCopiedCode] = useState(false);

  // Fetch latest profile from /api/auth/me when modal opens
  useEffect(() => {
    if (isOpen) {
      setError('');
      setSuccess('');
      setIsEditing(false);
      fetchProfile();
    }
  }, [isOpen]);

  const fetchProfile = async () => {
    setFetching(true);
    try {
      const res = await api.get('/auth/me');
      setProfileData(res.data);
      setFullName(res.data.full_name || '');
      setGithubUsername(res.data.github_username || '');
      // Keep AuthContext in sync
      updateUser(res.data);
    } catch (err) {
      console.error('Failed to fetch profile', err);
      // Fallback to cached user
      if (user) {
        setProfileData(user);
        setFullName(user.full_name || '');
        setGithubUsername(user.github_username || '');
      }
    } finally {
      setFetching(false);
    }
  };

  const handleCopyMentorCode = (code) => {
    if (!code) return;
    navigator.clipboard.writeText(code);
    setCopiedCode(true);
    setTimeout(() => setCopiedCode(false), 2000);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (!fullName.trim()) {
      setError('Full name cannot be empty');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const payload = {
        full_name: fullName.trim(),
        github_username: githubUsername.trim() || null,
      };
      const res = await api.patch('/auth/me', payload);
      setProfileData(res.data);
      updateUser(res.data);
      setSuccess('Profile updated successfully!');
      setIsEditing(false);
      setTimeout(() => setSuccess(''), 3000);
    } catch (err) {
      console.error('Failed to update profile', err);
      const msg = err.response?.data?.detail || 'Failed to update profile. Please try again.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleCancelEdit = () => {
    setIsEditing(false);
    setError('');
    if (profileData) {
      setFullName(profileData.full_name || '');
      setGithubUsername(profileData.github_username || '');
    }
  };

  if (!isOpen) return null;

  const current = profileData || user;
  const isStudent = current?.role === 'STUDENT';
  const isMentor = current?.role === 'MENTOR';
  const mentorInfo = current?.assigned_mentor;

  return createPortal(
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 sm:p-8 animate-fadeIn">
      <div
        className="relative w-full max-w-lg bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl shadow-slate-950/80 max-h-[75vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header background glow */}
        <div className="h-28 bg-gradient-to-r from-indigo-900/60 via-purple-900/50 to-indigo-950 border-b border-slate-800/80 relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white bg-slate-900/60 hover:bg-slate-800/80 rounded-xl transition-all"
            title="Close"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Profile Avatar & Info Overlay */}
        <div className="px-6 pb-6 pt-0 relative">
          <div className="flex items-end justify-between -mt-12 mb-4">
            <div className="relative">
              <div className="h-20 w-20 rounded-2xl bg-slate-900 border-4 border-slate-900 flex items-center justify-center text-white text-2xl font-bold bg-gradient-to-tr from-indigo-600 to-purple-600 shadow-xl shadow-indigo-500/20">
                {current?.full_name ? current.full_name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div className="absolute -bottom-1 -right-1 p-1 rounded-full bg-slate-900">
                <span className="flex h-3 w-3 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
              </div>
            </div>

            {!isEditing ? (
              <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition-all shadow-sm"
              >
                <Edit2 className="h-3.5 w-3.5" /> Edit Profile
              </button>
            ) : (
              <button
                type="button"
                onClick={handleCancelEdit}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
              >
                Cancel
              </button>
            )}
          </div>

          <div className="mb-5">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-bold text-white tracking-tight">
                {current?.full_name || 'User Profile'}
              </h2>
              <span className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                <Shield className="h-3 w-3" />
                {current?.role}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{current?.email}</p>
          </div>

          {/* Feedback messages */}
          {error && (
            <div className="mb-4 p-3 rounded-xl bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-xl bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 text-xs flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              <span>{success}</span>
            </div>
          )}

          {/* Edit Form or View Details */}
          {isEditing ? (
            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-1.5">
                  <User className="h-3.5 w-3.5 text-indigo-400" /> Full Name
                </label>
                <input
                  type="text"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="glass-input w-full px-3.5 py-2 text-sm text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                  placeholder="Your full name"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-1.5">
                  <Mail className="h-3.5 w-3.5 text-slate-400" /> Email Address
                </label>
                <input
                  type="email"
                  disabled
                  value={current?.email || ''}
                  className="glass-input w-full px-3.5 py-2 text-sm text-slate-400 bg-slate-800/40 cursor-not-allowed border-slate-800"
                />
                <p className="text-[11px] text-slate-500 mt-1">Email is tied to your login account and cannot be changed.</p>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300 block mb-1.5 flex items-center gap-1.5">
                  <Github className="h-3.5 w-3.5 text-indigo-400" /> GitHub Username
                </label>
                <div className="relative">
                  <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 text-sm">@</span>
                  <input
                    type="text"
                    value={githubUsername}
                    onChange={(e) => setGithubUsername(e.target.value)}
                    className="glass-input w-full pl-8 pr-3.5 py-2 text-sm text-white focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                    placeholder="username"
                  />
                </div>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  disabled={loading}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-750 text-slate-300 transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="glass-button-primary flex items-center gap-1.5 text-xs py-2 px-4 font-semibold disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <Loader2 className="h-3.5 w-3.5 animate-spin" /> Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-3.5 w-3.5" /> Save Changes
                    </>
                  )}
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              {/* Account details list */}
              <div className="grid grid-cols-1 gap-3 p-4 rounded-xl bg-slate-950/40 border border-slate-800/80">
                <div className="flex items-center justify-between text-xs py-1 border-b border-slate-800/60">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <User className="h-3.5 w-3.5 text-slate-500" /> Full Name
                  </span>
                  <span className="text-slate-200 font-medium">{current?.full_name || '—'}</span>
                </div>

                <div className="flex items-center justify-between text-xs py-1 border-b border-slate-800/60">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Mail className="h-3.5 w-3.5 text-slate-500" /> Email Address
                  </span>
                  <span className="text-slate-200 font-mono">{current?.email || '—'}</span>
                </div>

                <div className="flex items-center justify-between text-xs py-1">
                  <span className="text-slate-400 flex items-center gap-1.5">
                    <Github className="h-3.5 w-3.5 text-slate-500" /> GitHub Username
                  </span>
                  {current?.github_username ? (
                    <a
                      href={`https://github.com/${current.github_username}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-400 hover:text-indigo-300 font-mono hover:underline flex items-center gap-1"
                    >
                      @{current.github_username}
                    </a>
                  ) : (
                    <span className="text-slate-500 italic">Not connected</span>
                  )}
                </div>
              </div>

              {/* Student View: Assigned Mentor Card */}
              {isStudent && (
                <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-950/30 to-purple-950/20 border border-indigo-900/40">
                  <div className="flex items-center gap-2 mb-2.5">
                    <GraduationCap className="h-4 w-4 text-indigo-400" />
                    <h4 className="text-xs font-bold text-indigo-300 uppercase tracking-wider">Faculty Mentor</h4>
                  </div>
                  {mentorInfo ? (
                    <div className="space-y-1.5 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Mentor Name:</span>
                        <span className="text-white font-semibold">{mentorInfo.full_name}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-slate-400">Mentor Email:</span>
                        <span className="text-slate-300 font-mono">{mentorInfo.email}</span>
                      </div>
                      <div className="flex items-center justify-between pt-1">
                        <span className="text-slate-400">Mentor Code:</span>
                        <span className="px-2 py-0.5 rounded font-mono text-[11px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                          {mentorInfo.mentor_code || '—'}
                        </span>
                      </div>
                    </div>
                  ) : current?.assigned_mentor_id ? (
                    <p className="text-xs text-slate-400">Mentor linked (details loading...)</p>
                  ) : (
                    <p className="text-xs text-slate-400 italic">
                      No mentor assigned. You can link to a faculty mentor in the "Mentor Settings" tab.
                    </p>
                  )}
                </div>
              )}

              {/* Mentor View: Mentor Code Card with Copy Affordance */}
              {isMentor && (
                <div className="p-4 rounded-xl bg-gradient-to-br from-indigo-950/40 to-slate-900/60 border border-indigo-800/40">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <KeyRound className="h-4 w-4 text-indigo-400" />
                      <h4 className="text-xs font-bold text-indigo-300 uppercase tracking-wider">Your Mentor Code</h4>
                    </div>
                    <span className="text-[11px] text-slate-400">Share with students</span>
                  </div>
                  <div className="flex items-center justify-between gap-3 p-2.5 rounded-xl bg-slate-900/90 border border-slate-700/80">
                    <code className="font-mono text-sm font-bold tracking-widest text-indigo-300">
                      {current?.mentor_code || 'MNT-DEMO-01'}
                    </code>
                    <button
                      type="button"
                      onClick={() => handleCopyMentorCode(current?.mentor_code)}
                      className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition-all"
                    >
                      {copiedCode ? (
                        <>
                          <Check className="h-3.5 w-3.5 text-emerald-400" /> Copied!
                        </>
                      ) : (
                        <>
                          <Copy className="h-3.5 w-3.5" /> Copy
                        </>
                      )}
                    </button>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-end pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>,
    document.body
  );
};

export default ProfileModal;
