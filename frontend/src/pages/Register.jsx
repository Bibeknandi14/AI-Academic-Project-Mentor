import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Sparkles, Lock, Mail, User, Github, Shield, ArrowRight,
  KeyRound, CheckCircle2, Info
} from 'lucide-react';

const Register = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    role: 'STUDENT',
    github_username: '',
    mentor_code: '',   // optional — students only
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const isStudent = formData.role === 'STUDENT';

  const handleChange = (field) => (e) =>
    setFormData((prev) => ({ ...prev, [field]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // Strip empty optional fields so the backend ignores them
      const payload = {
        ...formData,
        email: formData.email.trim(),
        full_name: formData.full_name.trim(),
      };
      if (!payload.mentor_code) delete payload.mentor_code;
      else payload.mentor_code = payload.mentor_code.trim();

      if (!payload.github_username) delete payload.github_username;
      else payload.github_username = payload.github_username.trim();

      await register(payload);
      navigate('/login', { state: { registered: true } });
    } catch (err) {
      console.error('Registration error', err);
      setError(err.response?.data?.detail || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-indigo-950 via-slate-950 to-slate-950">
      <div className="glass-card max-w-md w-full p-8 space-y-6 relative overflow-hidden">

        {/* Header */}
        <div className="text-center space-y-2">
          <div className="h-12 w-12 rounded-2xl bg-gradient-to-tr from-indigo-600 to-purple-600 mx-auto flex items-center justify-center shadow-lg shadow-indigo-500/30">
            <Sparkles className="h-6 w-6 text-white" />
          </div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight">Create Account</h2>
          <p className="text-xs text-slate-400">Join the AI Academic Project Progress Tracking Platform</p>
        </div>

        {/* Error banner */}
        {error && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Full Name */}
          <div>
            <label className="text-xs font-semibold text-slate-300">Full Name</label>
            <div className="relative mt-1">
              <User className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                id="reg-full-name"
                type="text"
                required
                value={formData.full_name}
                onChange={handleChange('full_name')}
                className="glass-input w-full pl-11 pr-4 text-sm"
                placeholder="Alex Student"
              />
            </div>
          </div>

          {/* Email */}
          <div>
            <label className="text-xs font-semibold text-slate-300">University Email</label>
            <div className="relative mt-1">
              <Mail className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                id="reg-email"
                type="email"
                required
                value={formData.email}
                onChange={handleChange('email')}
                className="glass-input w-full pl-11 pr-4 text-sm"
                placeholder="alex@univ.edu"
              />
            </div>
          </div>

          {/* Password */}
          <div>
            <label className="text-xs font-semibold text-slate-300">Password</label>
            <div className="relative mt-1">
              <Lock className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
              <input
                id="reg-password"
                type="password"
                required
                value={formData.password}
                onChange={handleChange('password')}
                className="glass-input w-full pl-11 pr-4 text-sm"
                placeholder="••••••••"
              />
            </div>
          </div>

          {/* Role + GitHub */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-slate-300">Account Role</label>
              <select
                id="reg-role"
                value={formData.role}
                onChange={handleChange('role')}
                className="glass-input w-full px-4 mt-1 text-sm"
              >
                <option value="STUDENT">Student Team</option>
                <option value="MENTOR">Faculty Mentor</option>
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300">GitHub Username</label>
              <div className="relative mt-1">
                <Github className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <input
                  id="reg-github"
                  type="text"
                  value={formData.github_username}
                  onChange={handleChange('github_username')}
                  className="glass-input w-full pl-11 pr-4 text-sm font-mono"
                  placeholder="alex-dev"
                />
              </div>
            </div>
          </div>

          {/* Mentor Code — shown only for students */}
          {isStudent && (
            <div>
              <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <KeyRound className="h-3.5 w-3.5 text-indigo-400" />
                Mentor Code
                <span className="text-slate-500 font-normal">(optional)</span>
              </label>
              <div className="relative mt-1">
                <input
                  id="reg-mentor-code"
                  type="text"
                  value={formData.mentor_code}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      mentor_code: e.target.value.toUpperCase(),
                    }))
                  }
                  className="glass-input w-full px-4 text-sm font-mono tracking-widest uppercase"
                  placeholder="MNT-XXXXX"
                  maxLength={9}
                />
              </div>
              <p className="mt-1.5 text-[11px] text-slate-500 flex items-start gap-1">
                <Info className="h-3 w-3 mt-0.5 shrink-0 text-slate-600" />
                Ask your faculty mentor for their 9-character code. You can also add it later from your dashboard.
              </p>
            </div>
          )}

          {/* Mentor role info banner */}
          {!isStudent && (
            <div className="flex items-start gap-2.5 p-3 rounded-xl bg-indigo-950/60 border border-indigo-800/40 text-indigo-300 text-xs">
              <Shield className="h-4 w-4 shrink-0 mt-0.5 text-indigo-400" />
              <span>
                A unique <strong>Mentor Code</strong> will be automatically generated for your account.
                Share it with your students so they can link their work to your oversight dashboard.
              </span>
            </div>
          )}

          <button
            id="reg-submit"
            type="submit"
            disabled={loading}
            className="glass-button-primary w-full flex items-center justify-center gap-2 py-3 text-sm font-semibold mt-2"
          >
            {loading ? 'Creating Account...' : 'Register Account'}
            {!loading && <ArrowRight className="h-4 w-4" />}
          </button>
        </form>

        <div className="text-center text-xs text-slate-400">
          Already registered?{' '}
          <Link to="/login" className="text-indigo-400 font-semibold hover:underline">
            Sign In Here
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Register;
