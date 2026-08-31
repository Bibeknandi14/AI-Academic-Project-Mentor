import React, { useState } from 'react';
import { Sparkles, CheckCircle2, ArrowRight, Layers, Calendar, Users, Rocket, RefreshCw, Plus, X, Cpu } from 'lucide-react';
import api from '../services/api';

const AIPlannerModal = ({ onClose, onProjectCreated }) => {
  const [step, setStep] = useState('input'); // input, generating, review
  const [formData, setFormData] = useState({
    idea_title: '',
    idea_description: '',
    tech_stack: [],
    duration_weeks: 4,
    team_size: 2
  });
  const [techInput, setTechInput] = useState('');
  const [reviewTechInput, setReviewTechInput] = useState('');
  const [roadmap, setRoadmap] = useState(null);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const handleAddTech = () => {
    if (techInput.trim() && !formData.tech_stack.includes(techInput.trim())) {
      setFormData({ ...formData, tech_stack: [...formData.tech_stack, techInput.trim()] });
      setTechInput('');
    }
  };

  const handleRemoveTech = (tech) => {
    setFormData({ ...formData, tech_stack: formData.tech_stack.filter((t) => t !== tech) });
  };

  const handleAddSuggestedTech = () => {
    if (reviewTechInput.trim() && roadmap) {
      const current = roadmap.suggested_tech_stack || [];
      if (!current.includes(reviewTechInput.trim())) {
        setRoadmap({
          ...roadmap,
          suggested_tech_stack: [...current, reviewTechInput.trim()]
        });
      }
      setReviewTechInput('');
    }
  };

  const handleRemoveSuggestedTech = (tech) => {
    if (roadmap) {
      setRoadmap({
        ...roadmap,
        suggested_tech_stack: (roadmap.suggested_tech_stack || []).filter((t) => t !== tech)
      });
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    setError('');
    setStep('generating');
    try {
      const payload = {
        idea_title: formData.idea_title,
        idea_description: formData.idea_description,
        duration_weeks: formData.duration_weeks,
        team_size: formData.team_size,
        tech_stack: formData.tech_stack.length > 0 ? formData.tech_stack : null
      };
      const res = await api.post('/planner/generate', payload);
      setRoadmap(res.data);
      setStep('review');
    } catch (err) {
      console.error("Roadmap generation error", err);
      setError(err.response?.data?.detail || "Failed to generate roadmap. Please try again.");
      setStep('input');
    }
  };

  const handleSaveToProject = async () => {
    setSaving(true);
    try {
      const payload = {
        ...roadmap,
        idea_title: formData.idea_title,
        idea_description: formData.idea_description
      };
      const res = await api.post('/planner/convert-to-project', payload);
      onProjectCreated(res.data);
      onClose();
    } catch (err) {
      console.error("Save to project error", err);
      setError("Failed to convert roadmap into active project tasks.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 overflow-y-auto">
      <div className="glass-card max-w-2xl w-full p-6 space-y-6 my-8">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-bold text-lg text-white">AI Project Roadmap Planner</h3>
              <p className="text-xs text-slate-400">Transform your project idea into architecture and structured sprint tasks</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-sm">Close</button>
        </div>

        {error && (
          <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {step === 'input' && (
          <form onSubmit={handleGenerate} className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-slate-300">Project Idea Title</label>
              <input
                type="text"
                required
                value={formData.idea_title}
                onChange={(e) => setFormData({ ...formData, idea_title: e.target.value })}
                className="glass-input w-full mt-1.5 text-sm"
                placeholder="e.g. JD & Resume Skill Gap Matcher Platform"
              />
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300">Project Description & Goals</label>
                <span className="text-[11px] text-indigo-400 font-medium">Write freely in plain language</span>
              </div>
              <textarea
                required
                value={formData.idea_description}
                onChange={(e) => setFormData({ ...formData, idea_description: e.target.value })}
                className="glass-input w-full mt-1.5 text-sm h-28 leading-relaxed"
                placeholder="Describe what you want to build, the key features, target users, and what problem it solves. The AI software architect will analyze this to design your architecture, suggest optimal tech stacks, and plan your sprint backlog..."
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold text-slate-300">Duration (Weeks)</label>
                <div className="flex items-center gap-2 mt-1.5">
                  <Calendar className="h-4 w-4 text-slate-400" />
                  <input
                    type="number"
                    min="1"
                    max="16"
                    value={formData.duration_weeks}
                    onChange={(e) => setFormData({ ...formData, duration_weeks: parseInt(e.target.value) || 4 })}
                    className="glass-input w-full text-sm"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300">Team Size (Students)</label>
                <div className="flex items-center gap-2 mt-1.5">
                  <Users className="h-4 w-4 text-slate-400" />
                  <input
                    type="number"
                    min="1"
                    max="6"
                    value={formData.team_size}
                    onChange={(e) => setFormData({ ...formData, team_size: parseInt(e.target.value) || 2 })}
                    className="glass-input w-full text-sm"
                  />
                </div>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300">Tech Stack Preferences (Optional)</label>
                <span className="text-[11px] text-slate-400">Leave blank to let AI recommend</span>
              </div>
              <div className="flex items-center gap-2 mt-1.5">
                <input
                  type="text"
                  value={techInput}
                  onChange={(e) => setTechInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddTech();
                    }
                  }}
                  className="glass-input flex-1 text-sm"
                  placeholder="Optional: e.g. Next.js, FastAPI, PyTorch (press Enter or Add)"
                />
                <button
                  type="button"
                  onClick={handleAddTech}
                  className="glass-button-secondary text-xs py-2.5 px-4 flex items-center gap-1"
                >
                  <Plus className="h-3.5 w-3.5" /> Add
                </button>
              </div>
              {formData.tech_stack.length > 0 ? (
                <div className="flex flex-wrap gap-2 mt-2">
                  {formData.tech_stack.map((t) => (
                    <span
                      key={t}
                      className="px-2.5 py-1 rounded-lg bg-indigo-950/60 border border-indigo-800/40 text-indigo-300 text-xs flex items-center gap-1.5"
                    >
                      {t}
                      <button
                        type="button"
                        onClick={() => handleRemoveTech(t)}
                        className="hover:text-rose-400 transition-colors"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-slate-500 mt-1.5 italic">
                  💡 No preferred tech stack added. The AI will automatically select the best frontend, backend, database, and ML libraries for your project idea.
                </p>
              )}
            </div>

            <div className="pt-3 flex justify-end">
              <button type="submit" className="glass-button-primary flex items-center gap-2 text-sm">
                <Sparkles className="h-4 w-4" /> Generate Agile Roadmap
              </button>
            </div>
          </form>
        )}

        {step === 'generating' && (
          <div className="text-center py-16 space-y-4">
            <div className="h-16 w-16 rounded-3xl bg-indigo-600/20 border border-indigo-500/40 mx-auto flex items-center justify-center text-indigo-400">
              <RefreshCw className="h-8 w-8 animate-spin" />
            </div>
            <h4 className="font-bold text-slate-200 text-base">Architecting AI Project Plan...</h4>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Analyzing project objectives, recommending tailored tech stacks, and generating structured Agile sprint backlogs...
            </p>
          </div>
        )}

        {step === 'review' && roadmap && (
          <div className="space-y-5">
            {/* Identified Requirements / AI Analysis */}
            {roadmap.identified_requirements && roadmap.identified_requirements.length > 0 && (
              <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                    <h4 className="font-semibold text-slate-200 text-sm">Identified Technical Requirements</h4>
                  </div>
                  <span className="text-[10px] text-emerald-400 font-medium bg-emerald-950/80 border border-emerald-800/40 px-2 py-0.5 rounded">
                    AI Context Analysis
                  </span>
                </div>
                <div className="grid grid-cols-1 gap-2 pt-1">
                  {roadmap.identified_requirements.map((req, idx) => (
                    <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-300 bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/80">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 mt-1.5 shrink-0" />
                      <span className="leading-relaxed">{req}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Suggested Tech Stack - Editable */}
            <div className="p-4 rounded-xl bg-slate-900 border border-indigo-900/40 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Cpu className="h-4 w-4 text-indigo-400" />
                  <h4 className="font-semibold text-slate-200 text-sm">AI Suggested Tech Stack</h4>
                </div>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/50">
                  Editable
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Recommended for your project architecture. You can modify, remove, or add technologies before proceeding:
              </p>
              
              <div className="flex flex-wrap gap-2 pt-1">
                {(roadmap.suggested_tech_stack || []).map((tech) => (
                  <span
                    key={tech}
                    className="px-2.5 py-1 rounded-lg bg-indigo-950/80 border border-indigo-700/60 text-indigo-200 text-xs flex items-center gap-1.5 font-medium shadow-sm"
                  >
                    {tech}
                    <button
                      type="button"
                      onClick={() => handleRemoveSuggestedTech(tech)}
                      className="text-indigo-400 hover:text-rose-400 transition-colors p-0.5 rounded"
                      title="Remove technology"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </span>
                ))}
              </div>

              {/* Add custom tech input */}
              <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80">
                <input
                  type="text"
                  value={reviewTechInput}
                  onChange={(e) => setReviewTechInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddSuggestedTech();
                    }
                  }}
                  className="glass-input flex-1 text-xs py-1.5"
                  placeholder="Add another technology or library (e.g. TailwindCSS, Celery)..."
                />
                <button
                  type="button"
                  onClick={handleAddSuggestedTech}
                  className="glass-button-secondary text-xs py-1.5 px-3 flex items-center gap-1"
                >
                  <Plus className="h-3 w-3" /> Add
                </button>
              </div>
            </div>

            {/* Architecture Overview */}
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <h4 className="font-semibold text-slate-200 text-sm">Architecture Overview</h4>
              <p className="text-xs text-slate-400 leading-relaxed">{roadmap.recommended_architecture}</p>
            </div>

            {/* Tasks & Epics */}
            <div>
              <h4 className="font-semibold text-slate-200 text-sm mb-3">Planned Epics & Sprint Tasks ({roadmap.tasks.length})</h4>
              <div className="space-y-3 max-h-56 overflow-y-auto pr-1">
                {roadmap.tasks.map((t, idx) => (
                  <div key={idx} className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">{t.title}</span>
                      <span className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 text-[10px] font-bold">
                        {t.sprint_name}
                      </span>
                    </div>
                    <p className="text-slate-400">{t.description}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-between items-center pt-3 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setStep('input')}
                className="glass-button-secondary text-xs"
              >
                Back & Edit
              </button>
              <button
                type="button"
                disabled={saving}
                onClick={handleSaveToProject}
                className="glass-button-primary flex items-center gap-2 text-sm"
              >
                <Rocket className="h-4 w-4" /> Create Project & Tasks
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIPlannerModal;
