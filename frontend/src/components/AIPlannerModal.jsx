import React, { useState } from 'react';
import { Sparkles, CheckCircle2, ArrowRight, Layers, Calendar, Users, Rocket, RefreshCw } from 'lucide-react';
import api from '../services/api';

const AIPlannerModal = ({ onClose, onProjectCreated }) => {
  const [step, setStep] = useState('input'); // input, generating, review
  const [formData, setFormData] = useState({
    idea_title: '',
    idea_description: '',
    tech_stack: ['React', 'FastAPI', 'PostgreSQL'],
    duration_weeks: 4,
    team_size: 2
  });
  const [techInput, setTechInput] = useState('');
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

  const handleGenerate = async (e) => {
    e.preventDefault();
    setError('');
    setStep('generating');
    try {
      const res = await api.post('/planner/generate', formData);
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
              <p className="text-xs text-slate-400">Convert raw student project ideas into strict Agile sprint tasks</p>
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
                placeholder="e.g. AI-Powered Academic Progress Tracking Platform"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-300">Raw Project Description / Objectives</label>
              <textarea
                required
                value={formData.idea_description}
                onChange={(e) => setFormData({ ...formData, idea_description: e.target.value })}
                className="glass-input w-full mt-1.5 text-sm h-24"
                placeholder="Describe what problem your project solves and key student features..."
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
              <label className="text-xs font-semibold text-slate-300">Technology Stack</label>
              <div className="flex items-center gap-2 mt-1.5">
                <input
                  type="text"
                  value={techInput}
                  onChange={(e) => setTechInput(e.target.value)}
                  className="glass-input flex-1 text-sm"
                  placeholder="Add technology (e.g. PyTorch, Docker)"
                />
                <button
                  type="button"
                  onClick={handleAddTech}
                  className="glass-button-secondary text-xs py-2.5"
                >
                  Add
                </button>
              </div>
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
                      className="hover:text-rose-400"
                    >
                      &times;
                    </button>
                  </span>
                ))}
              </div>
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
            <h4 className="font-bold text-slate-200 text-base">Orchestrating AI Agile Roadmap...</h4>
            <p className="text-xs text-slate-400 max-w-sm mx-auto">
              Querying Gemini LLM with Pydantic JSON Schema enforcement & automatic validation retries...
            </p>
          </div>
        )}

        {step === 'review' && roadmap && (
          <div className="space-y-5">
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <h4 className="font-semibold text-slate-200 text-sm">Architecture Overview</h4>
              <p className="text-xs text-slate-400">{roadmap.recommended_architecture}</p>
            </div>

            <div>
              <h4 className="font-semibold text-slate-200 text-sm mb-3">Planned Epics & Tasks ({roadmap.tasks.length})</h4>
              <div className="space-y-3 max-h-60 overflow-y-auto pr-1">
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
