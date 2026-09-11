import React, { useState, useRef, useEffect, useMemo } from 'react';
import { createPortal } from 'react-dom';
import { 
  Sparkles, 
  CheckCircle2, 
  Layers, 
  Calendar, 
  Users, 
  Rocket, 
  RefreshCw, 
  Plus, 
  X, 
  Cpu, 
  ChevronDown, 
  ChevronUp, 
  GitBranch, 
  Download, 
  FileText, 
  ListTodo,
  Check,
  AlertTriangle
} from 'lucide-react';
import api from '../services/api';

const TECH_CATEGORIES = [
  {
    id: 'client_gui',
    name: 'Client / GUI',
    badgeClass: 'bg-emerald-950/80 border-emerald-700/50 text-emerald-300',
    tagClass: 'bg-emerald-950/60 border-emerald-600/50 text-emerald-200 hover:border-emerald-400',
    removeBtnClass: 'text-emerald-400 hover:text-rose-400',
    keywords: ['react', 'vite', 'next', 'vue', 'svelte', 'angular', 'tailwind', 'css', 'html', 'bootstrap', 'ui', 'gui', 'electron', 'flutter', 'react native', 'pyqt', 'tkinter', 'wxpython', 'kivy', 'styled', 'material-ui', 'chakra', 'shadcn', 'web', 'frontend', 'client']
  },
  {
    id: 'core_backend',
    name: 'Core / Backend',
    badgeClass: 'bg-blue-950/80 border-blue-700/50 text-blue-300',
    tagClass: 'bg-blue-950/60 border-blue-600/50 text-blue-200 hover:border-blue-400',
    removeBtnClass: 'text-blue-400 hover:text-rose-400',
    keywords: ['fastapi', 'flask', 'django', 'express', 'node', 'nodejs', 'python', 'java', 'spring', 'go', 'golang', 'rust', 'c++', 'c#', '.net', 'ruby', 'rails', 'php', 'laravel', 'celery', 'rest', 'graphql', 'websocket', 'websockets', 'jwt', 'auth', 'api', 'backend', 'server', 'runtime']
  },
  {
    id: 'ai_ml',
    name: 'AI / ML',
    badgeClass: 'bg-purple-950/80 border-purple-700/50 text-purple-300',
    tagClass: 'bg-purple-950/60 border-purple-600/50 text-purple-200 hover:border-purple-400',
    removeBtnClass: 'text-purple-400 hover:text-rose-400',
    keywords: ['pytorch', 'tensorflow', 'keras', 'scikit', 'sklearn', 'opencv', 'cv', 'sentence-transformers', 'transformer', 'bert', 'huggingface', 'llm', 'openai', 'gemini', 'anthropic', 'langchain', 'llamaindex', 'nltk', 'spacy', 'yolo', 'mediapipe', 'whisper', 'diffusion', 'nlp', 'machine learning', 'deep learning', 'cnn', 'rnn', 'lstm', 'torchvision', 'surprise', 'vision', 'model', 'embeddings']
  },
  {
    id: 'persistence',
    name: 'Persistence',
    badgeClass: 'bg-amber-950/80 border-amber-700/50 text-amber-300',
    tagClass: 'bg-amber-950/60 border-amber-600/50 text-amber-200 hover:border-amber-400',
    removeBtnClass: 'text-amber-400 hover:text-rose-400',
    keywords: ['sqlite', 'postgres', 'postgresql', 'mysql', 'mongodb', 'mongo', 'redis', 'chroma', 'chromadb', 'faiss', 'pinecone', 'weaviate', 'qdrant', 'supabase', 'firebase', 'dynamodb', 'mariadb', 'neo4j', 'cassandra', 'sql', 'sqlalchemy', 'prisma', 'vector', 'nosql', 'storage', 'database', 'db']
  },
  {
    id: 'visualization',
    name: 'Visualization & Tools',
    badgeClass: 'bg-cyan-950/80 border-cyan-700/50 text-cyan-300',
    tagClass: 'bg-cyan-950/60 border-cyan-600/50 text-cyan-200 hover:border-cyan-400',
    removeBtnClass: 'text-cyan-400 hover:text-rose-400',
    keywords: ['chart', 'chart.js', 'd3', 'd3.js', 'recharts', 'matplotlib', 'seaborn', 'plotly', 'pandas', 'numpy', 'scipy', 'pdfplumber', 'pypdf2', 'pypdf', 'pillow', 'pil', 'beautifulsoup', 'bs4', 'selenium', 'playwright', 'requests', 'axios', 'streamlit', 'docker', 'git']
  },
  {
    id: 'other',
    name: 'Other Packages',
    badgeClass: 'bg-slate-800/80 border-slate-700/50 text-slate-300',
    tagClass: 'bg-slate-900/80 border-slate-700/60 text-slate-200 hover:border-slate-500',
    removeBtnClass: 'text-slate-400 hover:text-rose-400',
    keywords: []
  }
];

const getCategoryForTech = (tech) => {
  const lower = tech.toLowerCase();
  for (const cat of TECH_CATEGORIES) {
    if (cat.id === 'other') continue;
    if (cat.keywords.some((kw) => lower.includes(kw))) {
      return cat;
    }
  }
  return TECH_CATEGORIES.find((c) => c.id === 'other');
};

const AIPlannerModal = ({ onClose, onProjectCreated }) => {
  const [step, setStep] = useState('input'); // input, generating, review
  const [activeTab, setActiveTab] = useState('architecture'); // 'architecture' | 'roadmap'
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
  const [expandedSprints, setExpandedSprints] = useState({});
  const [exported, setExported] = useState(false);

  // Group tasks by sprint
  const sprintGroups = useMemo(() => {
    if (!roadmap?.tasks) return {};
    const groups = {};
    roadmap.tasks.forEach((task) => {
      const sprintKey = task.sprint_name || 'Sprint 1';
      if (!groups[sprintKey]) {
        groups[sprintKey] = [];
      }
      groups[sprintKey].push(task);
    });
    return groups;
  }, [roadmap?.tasks]);

  // Default ONLY Sprint 1 to open
  useEffect(() => {
    if (roadmap?.tasks) {
      const initial = {};
      const sprintKeys = Object.keys(sprintGroups);
      sprintKeys.forEach((key, index) => {
        if (index === 0 || key.toLowerCase().includes('1') || key.toLowerCase().includes('sprint 1')) {
          initial[key] = true;
        } else {
          initial[key] = false;
        }
      });
      setExpandedSprints(initial);
    }
  }, [roadmap, sprintGroups]);

  const toggleSprint = (sprintKey) => {
    setExpandedSprints((prev) => ({
      ...prev,
      [sprintKey]: !prev[sprintKey]
    }));
  };

  const expandAllSprints = () => {
    const updated = {};
    Object.keys(sprintGroups).forEach((k) => (updated[k] = true));
    setExpandedSprints(updated);
  };

  const collapseAllSprints = () => {
    const updated = {};
    Object.keys(sprintGroups).forEach((k) => (updated[k] = false));
    setExpandedSprints(updated);
  };

  // Group suggested tech stack by category
  const groupedSuggestedTech = useMemo(() => {
    if (!roadmap?.suggested_tech_stack) return [];
    return TECH_CATEGORIES.map((cat) => {
      const items = (roadmap.suggested_tech_stack || []).filter(
        (tech) => getCategoryForTech(tech).id === cat.id
      );
      return { ...cat, items };
    }).filter((cat) => cat.items.length > 0);
  }, [roadmap?.suggested_tech_stack]);

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
      setActiveTab('architecture');
      setStep('review');
    } catch (err) {
      console.error("Roadmap generation error", err);
      setError(err.response?.data?.detail || "Failed to generate roadmap. Please try again.");
      setStep('input');
    }
  };

  const handleExportMarkdown = () => {
    if (!roadmap) return;
    
    let md = `# ${formData.idea_title || 'Project Roadmap'} - AI Architecture & Sprint Plan\n\n`;
    md += `> **Generated by AI Academic Project Mentor**\n`;
    md += `> **Duration:** ${formData.duration_weeks} Weeks | **Team Size:** ${formData.team_size} Student(s)\n\n`;
    
    if (roadmap.project_summary) {
      md += `## Project Summary\n${roadmap.project_summary}\n\n`;
    }
    
    md += `## Architecture Overview\n${roadmap.recommended_architecture}\n\n`;
    
    if (roadmap.identified_requirements && roadmap.identified_requirements.length > 0) {
      md += `## Identified Technical Requirements\n`;
      roadmap.identified_requirements.forEach((req) => {
        md += `- ${req}\n`;
      });
      md += `\n`;
    }
    
    md += `## Technology Stack Specification\n`;
    if (roadmap.stack_rationale) {
      md += `> **Stack Architecture Rationale:** ${roadmap.stack_rationale}\n\n`;
    }
    groupedSuggestedTech.forEach((group) => {
      md += `### ${group.name}\n`;
      group.items.forEach((tech) => {
        md += `- ${tech}\n`;
      });
      md += `\n`;
    });
    
    if (roadmap.epics && roadmap.epics.length > 0) {
      md += `## High-Level Epics\n`;
      roadmap.epics.forEach((epic) => {
        md += `- **${epic.name}**: ${epic.description}\n`;
      });
      md += `\n`;
    }
    
    md += `## Sprint Backlog & Tasks\n`;
    Object.entries(sprintGroups).forEach(([sprintName, tasks]) => {
      md += `### ${sprintName}\n\n`;
      tasks.forEach((t) => {
        md += `#### ${t.title} [Priority: ${t.priority || 'MEDIUM'}]\n`;
        if (t.epic_name) md += `- **Epic**: ${t.epic_name}\n`;
        if (t.git_branch_suggestion) md += `- **Suggested Branch**: \`${t.git_branch_suggestion}\`\n`;
        md += `- **Description**: ${t.description}\n\n`;
      });
    });

    try {
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const sanitizedTitle = (formData.idea_title || 'Project_Roadmap').replace(/[^a-zA-Z0-9_-]/g, '_');
      link.setAttribute('download', `${sanitizedTitle}_Plan.md`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      setExported(true);
      setTimeout(() => setExported(false), 3000);
    } catch (err) {
      console.error("Markdown export error", err);
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

  return createPortal(
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-start justify-center p-3 sm:p-6 overflow-y-auto">
      <div className="glass-card max-w-3xl w-full my-4 sm:my-8 flex flex-col max-h-[90vh] overflow-hidden border border-slate-800 shadow-2xl">
        
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 p-5 bg-slate-900/90 shrink-0">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-white shrink-0 shadow-md shadow-indigo-600/20">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h3 className="font-bold text-lg text-white">AI Project Roadmap Planner</h3>
              <p className="text-xs text-slate-400">Architect systems, curate tech stacks, and plan Agile sprint backlogs</p>
            </div>
          </div>
          <button 
            onClick={onClose} 
            className="text-slate-400 hover:text-white text-sm p-1.5 rounded-lg hover:bg-slate-800/80 transition-colors cursor-pointer"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mx-5 mt-4 p-3 rounded-xl bg-rose-950/60 border border-rose-800/60 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {/* Scrollable Body Content */}
        <div className="p-5 overflow-y-auto flex-1 space-y-5">
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
                  <span className="text-[11px] text-indigo-400 font-medium">Plain language description</span>
                </div>
                <textarea
                  required
                  value={formData.idea_description}
                  onChange={(e) => setFormData({ ...formData, idea_description: e.target.value })}
                  className="glass-input w-full mt-1.5 text-sm h-32 leading-relaxed"
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
                  <span className="text-[11px] text-slate-400">Leave blank to let AI recommend or enter partial stack</span>
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
                    placeholder="e.g. Python, or React, or PyTorch (press Enter or Add)"
                  />
                  <button
                    type="button"
                    onClick={handleAddTech}
                    className="glass-button-secondary text-xs py-2.5 px-4 flex items-center gap-1 cursor-pointer"
                  >
                    <Plus className="h-3.5 w-3.5" /> Add
                  </button>
                </div>
                {formData.tech_stack.length > 0 ? (
                  <div className="flex flex-wrap gap-2 mt-2">
                    {formData.tech_stack.map((t) => {
                      const cat = getCategoryForTech(t);
                      return (
                        <span
                          key={t}
                          className={`px-2.5 py-1 rounded-lg border text-xs flex items-center gap-1.5 shadow-sm ${cat.tagClass}`}
                        >
                          {t}
                          <button
                            type="button"
                            onClick={() => handleRemoveTech(t)}
                            className={cat.removeBtnClass}
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </span>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-[11px] text-slate-500 mt-1.5 italic">
                    💡 No preferred tech stack added. The AI will automatically infer the full client, backend, database, and domain libraries.
                  </p>
                )}
              </div>

              <div className="pt-3 flex justify-end">
                <button type="submit" className="glass-button-primary flex items-center gap-2 text-sm cursor-pointer">
                  <Sparkles className="h-4 w-4" /> Generate Agile Roadmap
                </button>
              </div>
            </form>
          )}

          {step === 'generating' && (
            <div className="text-center py-20 space-y-4">
              <div className="h-16 w-16 rounded-3xl bg-indigo-600/20 border border-indigo-500/40 mx-auto flex items-center justify-center text-indigo-400">
                <RefreshCw className="h-8 w-8 animate-spin" />
              </div>
              <h4 className="font-bold text-slate-200 text-base">Architecting AI Project Plan...</h4>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Analyzing project objectives, completing multi-layer architectures, and organizing structured Agile sprint backlogs...
              </p>
            </div>
          )}

          {step === 'review' && roadmap && (
            <div className="space-y-4">
              {/* Tab Navigation Header */}
              <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
                <button
                  type="button"
                  onClick={() => setActiveTab('architecture')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                    activeTab === 'architecture'
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/50 shadow-sm shadow-indigo-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
                  }`}
                >
                  <Cpu className="h-4 w-4" />
                  <span>Architecture & Stack</span>
                  <span className="px-1.5 py-0.5 rounded-full bg-slate-800 text-[10px] text-slate-300 font-mono">
                    {roadmap.suggested_tech_stack?.length || 0}
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveTab('roadmap')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                    activeTab === 'roadmap'
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/50 shadow-sm shadow-indigo-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
                  }`}
                >
                  <Calendar className="h-4 w-4" />
                  <span>Sprint Roadmap</span>
                  <span className="px-1.5 py-0.5 rounded-full bg-slate-800 text-[10px] text-slate-300 font-mono">
                    {roadmap.tasks?.length || 0} tasks
                  </span>
                </button>
              </div>

              {/* TAB 1: Architecture & Stack */}
              {activeTab === 'architecture' && (
                <div className="space-y-4">
                  {/* Top Advisory Banner if Mismatch/Warning is Flagged */}
                  {roadmap.stack_rationale && (() => {
                    const isWarning = roadmap.stack_rationale.includes('⚠️') || 
                                      roadmap.stack_rationale.toLowerCase().includes('warning') || 
                                      roadmap.stack_rationale.toLowerCase().includes('mismatch') || 
                                      roadmap.stack_rationale.toLowerCase().includes('advisory') || 
                                      roadmap.stack_rationale.toLowerCase().includes('bottleneck');
                    if (!isWarning) return null;
                    return (
                      <div className="p-4 rounded-xl bg-gradient-to-r from-amber-950/80 via-slate-900 to-amber-950/40 border border-amber-600/60 text-xs text-amber-200 flex items-start gap-3 shadow-lg shadow-amber-950/30">
                        <div className="h-7 w-7 rounded-xl bg-amber-900/80 border border-amber-500/60 flex items-center justify-center text-amber-300 shrink-0 mt-0.5">
                          <AlertTriangle className="h-4 w-4" />
                        </div>
                        <div className="space-y-1 flex-1">
                          <div className="flex items-center justify-between">
                            <span className="font-bold text-xs uppercase tracking-wider text-amber-300 flex items-center gap-1.5">
                              Architectural Advisory & Friction Guidance
                            </span>
                            <span className="text-[10px] bg-amber-900/70 border border-amber-600/50 text-amber-300 font-bold px-2 py-0.5 rounded">
                              Mentor Notice
                            </span>
                          </div>
                          <p className="text-slate-200 leading-relaxed text-xs pt-0.5 whitespace-pre-line">
                            {roadmap.stack_rationale}
                          </p>
                        </div>
                      </div>
                    );
                  })()}

                  {/* Module 1: Architecture Overview */}
                  <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <FileText className="h-4 w-4 text-indigo-400" />
                        <h4 className="font-semibold text-slate-200 text-sm">Architecture Blueprint & Design</h4>
                      </div>
                      <span className="text-[10px] text-indigo-400 font-medium bg-indigo-950/80 border border-indigo-800/40 px-2 py-0.5 rounded">
                        System Specification
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 leading-relaxed pt-1">
                      {roadmap.recommended_architecture}
                    </p>
                    {roadmap.project_summary && (
                      <p className="text-xs text-slate-400 leading-relaxed border-t border-slate-800/60 pt-2 italic">
                        {roadmap.project_summary}
                      </p>
                    )}
                  </div>

                  {/* Module 2: Identified Technical Requirements */}
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

                  {/* Module 3: Layered Tech Stack Specification */}
                  <div className="p-4 rounded-xl bg-slate-900 border border-indigo-900/40 space-y-3.5">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Layers className="h-4 w-4 text-indigo-400" />
                        <h4 className="font-semibold text-slate-200 text-sm">Layered Tech Stack Specification</h4>
                      </div>
                      <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/50">
                        Categorized by Layer
                      </span>
                    </div>

                    {/* Standard Stack Rationale Box (if not already shown in top warning) */}
                    {roadmap.stack_rationale && !roadmap.stack_rationale.includes('⚠️') && !roadmap.stack_rationale.toLowerCase().includes('warning') && !roadmap.stack_rationale.toLowerCase().includes('advisory') && (
                      <div className="p-3.5 rounded-xl bg-gradient-to-r from-indigo-950/70 to-slate-900 border border-indigo-800/50 text-xs text-indigo-200 flex items-start gap-3 shadow-sm">
                        <div className="h-6 w-6 rounded-lg bg-indigo-900/60 border border-indigo-700/50 flex items-center justify-center text-indigo-300 shrink-0 mt-0.5">
                          <Sparkles className="h-3.5 w-3.5" />
                        </div>
                        <div className="space-y-0.5">
                          <span className="font-bold text-[11px] uppercase tracking-wider text-indigo-300 flex items-center gap-1.5">
                            Architectural Stack Rationale
                          </span>
                          <p className="text-slate-300 leading-relaxed text-xs">
                            {roadmap.stack_rationale}
                          </p>
                        </div>
                      </div>
                    )}
                    
                    {/* Layered Chips */}
                    <div className="space-y-3 pt-1">
                      {groupedSuggestedTech.map((category) => (
                        <div key={category.id} className="space-y-1.5 bg-slate-950/60 p-3 rounded-lg border border-slate-800/70">
                          <div className="flex items-center gap-2">
                            <span className={`text-[10px] font-bold tracking-wide uppercase px-2 py-0.5 rounded border ${category.badgeClass}`}>
                              {category.name}
                            </span>
                            <span className="text-[11px] text-slate-500 font-mono">({category.items.length})</span>
                          </div>
                          <div className="flex flex-wrap gap-2 pt-1">
                            {category.items.map((tech) => (
                              <span
                                key={tech}
                                className={`px-2.5 py-1 rounded-lg border text-xs flex items-center gap-1.5 font-medium shadow-sm transition-all ${category.tagClass}`}
                              >
                                <span>{tech}</span>
                                <button
                                  type="button"
                                  onClick={() => handleRemoveSuggestedTech(tech)}
                                  className={`p-0.5 rounded transition-colors ${category.removeBtnClass}`}
                                  title={`Remove ${tech}`}
                                >
                                  <X className="h-3 w-3" />
                                </button>
                              </span>
                            ))}
                          </div>
                        </div>
                      ))}

                      {groupedSuggestedTech.length === 0 && (
                        <p className="text-xs text-slate-500 italic py-1">No technologies selected. Add one below.</p>
                      )}
                    </div>

                    {/* Add Custom Tech */}
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
                        className="glass-input flex-1 text-xs py-2"
                        placeholder="Add another technology or library (e.g. Tailwind CSS, Celery, FAISS)..."
                      />
                      <button
                        type="button"
                        onClick={handleAddSuggestedTech}
                        className="glass-button-secondary text-xs py-2 px-3.5 flex items-center gap-1 cursor-pointer"
                      >
                        <Plus className="h-3.5 w-3.5" /> Add
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: Sprint Roadmap */}
              {activeTab === 'roadmap' && (
                <div className="space-y-4">
                  {/* High-Level Epics Pill Summary (if present) */}
                  {roadmap.epics && roadmap.epics.length > 0 && (
                    <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
                      <div className="flex items-center gap-2">
                        <ListTodo className="h-4 w-4 text-indigo-400" />
                        <h4 className="font-semibold text-slate-200 text-xs">High-Level Epics ({roadmap.epics.length})</h4>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {roadmap.epics.map((epic, idx) => (
                          <div 
                            key={idx} 
                            className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 text-[11px] text-slate-300 flex items-center gap-1.5"
                            title={epic.description}
                          >
                            <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                            <span className="font-semibold text-slate-200">{epic.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Sprints & Tasks Accordion */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Layers className="h-4 w-4 text-indigo-400" />
                        <h4 className="font-semibold text-slate-200 text-sm">
                          Planned Epics & Sprint Tasks ({roadmap.tasks.length})
                        </h4>
                      </div>
                      <div className="flex items-center gap-2 text-xs">
                        <button
                          type="button"
                          onClick={expandAllSprints}
                          className="text-[11px] text-indigo-400 hover:text-indigo-300 font-medium transition-colors cursor-pointer"
                        >
                          Expand All
                        </button>
                        <span className="text-slate-600">•</span>
                        <button
                          type="button"
                          onClick={collapseAllSprints}
                          className="text-[11px] text-slate-400 hover:text-slate-300 font-medium transition-colors cursor-pointer"
                        >
                          Collapse All
                        </button>
                      </div>
                    </div>

                    <div className="space-y-2.5">
                      {Object.entries(sprintGroups).map(([sprintName, tasks]) => {
                        const isExpanded = expandedSprints[sprintName] ?? false;
                        const highPriCount = tasks.filter((t) => t.priority === 'HIGH').length;

                        return (
                          <div
                            key={sprintName}
                            className="rounded-xl border border-slate-800 bg-slate-900/90 overflow-hidden transition-all shadow-sm"
                          >
                            {/* Sprint Accordion Header */}
                            <button
                              type="button"
                              onClick={() => toggleSprint(sprintName)}
                              className="w-full p-3.5 flex items-center justify-between text-left hover:bg-slate-800/50 transition-colors cursor-pointer"
                            >
                              <div className="flex items-center gap-2.5">
                                <div className="h-6 w-6 rounded-lg bg-indigo-950/80 border border-indigo-700/50 flex items-center justify-center text-indigo-300">
                                  <Calendar className="h-3.5 w-3.5" />
                                </div>
                                <div>
                                  <span className="font-bold text-xs text-slate-100">{sprintName}</span>
                                  <span className="ml-2 text-[11px] text-slate-400">
                                    ({tasks.length} task{tasks.length !== 1 ? 's' : ''})
                                  </span>
                                </div>
                              </div>
                              <div className="flex items-center gap-2">
                                {highPriCount > 0 && (
                                  <span className="text-[10px] text-rose-300 bg-rose-950/70 border border-rose-800/50 px-2 py-0.5 rounded font-mono font-medium">
                                    {highPriCount} High Priority
                                  </span>
                                )}
                                {isExpanded ? (
                                  <ChevronUp className="h-4 w-4 text-slate-400" />
                                ) : (
                                  <ChevronDown className="h-4 w-4 text-slate-400" />
                                )}
                              </div>
                            </button>

                            {/* Sprint Tasks (Collapsible Content) */}
                            {isExpanded && (
                              <div className="p-3 pt-1 space-y-2 border-t border-slate-800/80 bg-slate-950/60">
                                {tasks.map((t, idx) => {
                                  const priorityBadge =
                                    t.priority === 'HIGH'
                                      ? 'bg-rose-950/70 border-rose-800/50 text-rose-300'
                                      : t.priority === 'LOW'
                                      ? 'bg-slate-800/60 border-slate-700/50 text-slate-400'
                                      : 'bg-amber-950/70 border-amber-800/50 text-amber-300';

                                  return (
                                    <div
                                      key={idx}
                                      className="p-3 rounded-lg bg-slate-900 border border-slate-800 text-xs space-y-1.5 hover:border-slate-700 transition-colors"
                                    >
                                      <div className="flex items-start justify-between gap-2">
                                        <span className="font-semibold text-slate-200 leading-snug">{t.title}</span>
                                        <div className="flex items-center gap-1.5 shrink-0">
                                          {t.epic_name && (
                                            <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] text-slate-300 font-medium">
                                              {t.epic_name}
                                            </span>
                                          )}
                                          <span className={`px-1.5 py-0.5 rounded border text-[10px] font-bold ${priorityBadge}`}>
                                            {t.priority || 'MEDIUM'}
                                          </span>
                                        </div>
                                      </div>
                                      <p className="text-slate-400 text-[11px] leading-relaxed">{t.description}</p>
                                      {t.git_branch_suggestion && (
                                        <div className="flex items-center gap-1.5 text-[10px] text-slate-500 font-mono pt-0.5">
                                          <GitBranch className="h-3 w-3 text-indigo-400" />
                                          <span className="text-slate-400">{t.git_branch_suggestion}</span>
                                        </div>
                                      )}
                                    </div>
                                  );
                                })}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Fixed Footer */}
        {step === 'review' && roadmap && (
          <div className="border-t border-slate-800 p-4 bg-slate-900/95 flex items-center justify-between gap-3 shrink-0">
            <button
              type="button"
              onClick={() => setStep('input')}
              className="glass-button-secondary text-xs py-2 px-3.5 cursor-pointer"
            >
              Back & Edit
            </button>
            <div className="flex items-center gap-2.5">
              <button
                type="button"
                onClick={handleExportMarkdown}
                className="glass-button-secondary text-xs py-2 px-3.5 flex items-center gap-1.5 hover:text-indigo-300 transition-colors cursor-pointer"
                title="Download roadmap and sprint tasks as Markdown file"
              >
                {exported ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-emerald-400">Exported!</span>
                  </>
                ) : (
                  <>
                    <Download className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Export Markdown</span>
                  </>
                )}
              </button>
              <button
                type="button"
                disabled={saving}
                onClick={handleSaveToProject}
                className="glass-button-primary flex items-center gap-2 text-xs sm:text-sm py-2 px-4 cursor-pointer"
              >
                <Rocket className="h-4 w-4" /> Confirm & Create Board
              </button>
            </div>
          </div>
        )}

      </div>
    </div>,
    document.body
  );
};

export default AIPlannerModal;
