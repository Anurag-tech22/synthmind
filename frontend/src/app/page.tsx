"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import DOMPurify from "dompurify";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function sanitizeHtml(html: string): string {
  const rendered = html
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.*?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br/>");
  if (typeof window !== "undefined") {
    return DOMPurify.sanitize(rendered);
  }
  return rendered;
}

interface Message {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  message_type: string;
  timestamp: string;
  active_agent?: string;
  latency_ms?: number;
  confidence_score?: number;
  verification_status?: string;
}

interface SynthesisOutput {
  type: string;
  [key: string]: unknown;
}

const PHASES = [
  { key: "onboarding", label: "Discovery", icon: "◇" },
  { key: "clarification", label: "Deconstruct", icon: "◈" },
  { key: "ingestion", label: "Integrate", icon: "▣" },
  { key: "synthesis", label: "Synthesize", icon: "⬡" },
  { key: "feedback", label: "Refine", icon: "◉" },
];

const SUPPORTED_LANGUAGES = [
  { code: "auto", label: "🌐 Auto Detect", langCode: "auto" },
  { code: "en-US", label: "🇺🇸 English", langCode: "en-US" },
  { code: "zh-CN", label: "🇨🇳 中文 (Chinese)", langCode: "zh-CN" },
  { code: "ja-JP", label: "🇯🇵 日本語 (Japanese)", langCode: "ja-JP" },
  { code: "de-DE", label: "🇩🇪 Deutsch (German)", langCode: "de-DE" },
  { code: "es-ES", label: "🇪🇸 Español (Spanish)", langCode: "es-ES" },
  { code: "fr-FR", label: "🇫🇷 Français (French)", langCode: "fr-FR" },
  { code: "ko-KR", label: "🇰🇷 한국어 (Korean)", langCode: "ko-KR" },
  { code: "hi-IN", label: "🇮🇳 हिन्दी (Hindi)", langCode: "hi-IN" },
  { code: "ar-SA", label: "🇸🇦 العربية (Arabic)", langCode: "ar-SA" },
  { code: "it-IT", label: "🇮🇹 Italiano (Italian)", langCode: "it-IT" },
  { code: "pt-BR", label: "🇧🇷 Português (Portuguese)", langCode: "pt-BR" },
  { code: "ru-RU", label: "🇷🇺 Русский (Russian)", langCode: "ru-RU" },
];

const QUICK_STARTS = [
  { emoji: "⚖️", label: "Compare Options", prompt: "I need to compare multiple complex options and build a decision model" },
  { emoji: "🔬", label: "Deep Investigation", prompt: "I want to conduct a deep research investigation and synthesize key insights" },
  { emoji: "🎯", label: "Decision Matrix", prompt: "I have a high-stakes decision to make and need trade-off analysis" },
  { emoji: "📚", label: "Domain Mastery", prompt: "I want to deconstruct and master a new technical or strategic domain" },
];

const STUCK_RESCUE_ACTIONS = [
  {
    icon: "🎯",
    title: "Clarify my goal",
    desc: "Ask 3 targeted questions to narrow down the core decision",
    prompt: "I'm feeling stuck on how to frame my objective. Can you ask me 3 focused questions in my language to help clarify what I'm deciding and my key constraints?",
  },
  {
    icon: "📊",
    title: "Build decision matrix now",
    desc: "Synthesize discussed options into an interactive matrix",
    prompt: "Please synthesize the information we've discussed so far into a structured decision matrix with weighted criteria and scores.",
  },
  {
    icon: "⚖️",
    title: "Break down trade-offs",
    desc: "Compare pros, cons, and hidden risks for each choice",
    prompt: "Can you provide a clear pros, cons, and trade-off comparison between the options we have discussed?",
  },
  {
    icon: "🔍",
    title: "What are we missing?",
    desc: "Identify missing constraints or blind spots",
    prompt: "What critical constraints, criteria, or data points are missing before we can make a confident recommendation?",
  },
  {
    icon: "💡",
    title: "Give direct recommendation",
    desc: "Get a clear verdict with reasoning",
    prompt: "Based on our conversation so far, what is your top recommendation and what is the primary rationale?",
  },
];

// Helper: Detect language from text content
function detectLanguage(text: string): string {
  // Japanese: Hiragana or Katakana
  if (/[\u3040-\u309F\u30A0-\u30FF]/.test(text)) return "ja-JP";
  // Korean: Hangul
  if (/[\uAC00-\uD7AF\u1100-\u11FF]/.test(text)) return "ko-KR";
  // Chinese: Han characters without Japanese kana
  if (/[\u4E00-\u9FFF]/.test(text)) return "zh-CN";
  // Hindi / Devanagari
  if (/[\u0900-\u097F]/.test(text)) return "hi-IN";
  // Arabic
  if (/[\u0600-\u06FF]/.test(text)) return "ar-SA";
  // Russian / Cyrillic
  if (/[\u0400-\u04FF]/.test(text)) return "ru-RU";
  // German umlauts or common words
  if (/[äöüßÄÖÜ]|\b(und|oder|nicht|für|mit|ist|das|die|der|eine|einer|einem|warum|wie|bitte|danke)\b/i.test(text)) return "de-DE";
  // French accents or common words
  if (/[éèêëàâçîïôùû]|\b(et|ou|pour|avec|dans|sur|est|une|le|la|les|ce|cette|pourquoi|comment|merci)\b/i.test(text)) return "fr-FR";
  // Spanish accents or common words
  if (/[áéíóúñÁÉÍÓÚÑ¿¡]|\b(y|o|para|con|en|sobre|es|una|el|la|los|las|por|que|como|gracias|hola)\b/i.test(text)) return "es-ES";
  // Italian words
  if (/\b(e|o|per|con|in|su|sono|è|il|la|le|un|una|come|perché|grazie|ciao)\b/i.test(text)) return "it-IT";
  // Portuguese words
  if (/[ãõçÃÕÇ]|\b(e|ou|para|com|em|sobre|é|uma|o|a|os|as|por|que|como|obrigado|olá)\b/i.test(text)) return "pt-BR";
  return "en-US";
}

/* ─── Interactive Synthesis Components ────────────────────────────── */

function InteractiveDecisionMatrix({ data }: { data: SynthesisOutput }) {
  const initialCriteria = (data.criteria as Array<{ name: string; weight: number }>) || [];
  const [weights, setWeights] = useState<Record<string, number>>(() => {
    const map: Record<string, number> = {};
    initialCriteria.forEach((c) => { map[c.name] = c.weight; });
    return map;
  });

  const rawOptions = (data.options as Array<{ name: string; scores: Record<string, number>; total_weighted?: number }>) || [];

  const scoredOptions = rawOptions.map((opt) => {
    let total = 0;
    let totalWeight = 0;
    Object.keys(weights).forEach((critName) => {
      const w = weights[critName] || 0;
      const score = opt.scores?.[critName] || 0;
      total += score * (w / 100);
      totalWeight += w;
    });
    const normalizedTotal = totalWeight > 0 ? (total / (totalWeight / 100)) : 0;
    return { ...opt, liveTotal: normalizedTotal };
  }).sort((a, b) => b.liveTotal - a.liveTotal);

  const handleWeightChange = (critName: string, val: number) => {
    setWeights((prev) => ({ ...prev, [critName]: val }));
  };

  const scoreClass = (s: number) => s >= 8 ? "score-high" : s >= 5 ? "score-mid" : "score-low";

  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: "1.1rem" }}>◈</span>
          <span>{String(data.title || "Decision Matrix")}</span>
        </div>
        <span className="synthesis-badge" style={{ background: "rgba(99, 102, 241, 0.15)", color: "#a5b4fc" }}>
          LIVE
        </span>
      </div>

      <div style={{ background: "rgba(0,0,0,0.2)", padding: "12px", borderRadius: "10px", marginBottom: "14px", border: "1px solid var(--border-subtle)" }}>
        <div style={{ fontSize: "0.7rem", fontWeight: 700, color: "var(--text-accent)", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.8px" }}>
          Adjust Weights
        </div>
        {initialCriteria.map((crit) => (
          <div key={crit.name} className="weight-slider-row">
            <span style={{ width: "100px", fontSize: "0.72rem", color: "var(--text-secondary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {crit.name}
            </span>
            <input
              type="range"
              min="0"
              max="100"
              value={weights[crit.name] ?? crit.weight}
              onChange={(e) => handleWeightChange(crit.name, Number(e.target.value))}
              className="weight-slider"
            />
            <span style={{ width: "32px", textAlign: "right", fontFamily: "monospace", color: "var(--text-accent)", fontSize: "0.7rem" }}>
              {weights[crit.name] ?? crit.weight}%
            </span>
          </div>
        ))}
      </div>

      <table className="matrix-table">
        <thead>
          <tr>
            <th>Option</th>
            {initialCriteria.map((c) => (
              <th key={c.name}>{c.name}</th>
            ))}
            <th style={{ color: "var(--text-cyan)" }}>Score</th>
          </tr>
        </thead>
        <tbody>
          {scoredOptions.map((opt, idx) => (
            <tr key={opt.name} style={{ background: idx === 0 ? "rgba(99, 102, 241, 0.08)" : "rgba(255,255,255,0.01)" }}>
              <td style={{ fontWeight: 600, display: "flex", alignItems: "center", gap: 6 }}>
                {idx === 0 ? "◆ " : `${idx + 1}. `}
                <span>{opt.name}</span>
              </td>
              {initialCriteria.map((c) => {
                const score = opt.scores?.[c.name] ?? 0;
                return (
                  <td key={c.name} className={`score-cell ${scoreClass(score)}`}>
                    {score}/10
                  </td>
                );
              })}
              <td className="score-cell score-high" style={{ fontSize: "0.9rem" }}>
                {opt.liveTotal.toFixed(1)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.recommendation ? (
        <div style={{ marginTop: 14, padding: "10px 12px", background: "rgba(99, 102, 241, 0.06)", borderRadius: "8px", borderLeft: "3px solid rgba(99,102,241,0.5)", fontSize: "0.825rem", color: "var(--text-secondary)" }}>
          <strong style={{ color: "var(--text-primary)" }}>Recommendation:</strong> {String(data.recommendation)}
        </div>
      ) : null}
    </div>
  );
}

function ComparisonView({ data }: { data: SynthesisOutput }) {
  const items = (data.items as string[]) || [];
  const features = (data.features as Array<{ name: string; values: Record<string, string>; winner?: string }>) || [];

  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: "1.1rem" }}>◇</span>
          <span>{String(data.title || "Comparison Matrix")}</span>
        </div>
        <span className="synthesis-badge" style={{ background: "rgba(6, 182, 212, 0.15)", color: "#67e8f9" }}>
          DIFF
        </span>
      </div>
      <table className="matrix-table">
        <thead>
          <tr>
            <th>Dimension</th>
            {items.map((i) => <th key={i}>{i}</th>)}
            <th style={{ color: "var(--text-emerald)" }}>Leader</th>
          </tr>
        </thead>
        <tbody>
          {features.map((f) => (
            <tr key={f.name}>
              <td style={{ fontWeight: 600 }}>{f.name}</td>
              {items.map((i) => (
                <td key={i} style={{ color: f.winner === i ? "var(--text-emerald)" : "var(--text-secondary)" }}>
                  {f.values?.[i] ?? "—"} {f.winner === i && "✓"}
                </td>
              ))}
              <td style={{ fontWeight: 700, color: "var(--text-emerald)" }}>{f.winner || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.summary ? (
        <p style={{ marginTop: 12, fontSize: "0.825rem", color: "var(--text-secondary)" }}>{String(data.summary)}</p>
      ) : null}
    </div>
  );
}

function ProsConsView({ data }: { data: SynthesisOutput }) {
  const pros = (data.pros as Array<{ text: string; confidence: number }>) || [];
  const cons = (data.cons as Array<{ text: string; confidence: number }>) || [];

  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: "1.1rem" }}>⚖</span>
          <span>{String(data.title || "Trade-Off Analysis")}</span>
        </div>
        <span className="synthesis-badge" style={{ background: "rgba(16, 185, 129, 0.15)", color: "#6ee7b7" }}>
          WEIGHTED
        </span>
      </div>
      <div className="proscons-grid">
        <div>
          <h4 style={{ color: "#6ee7b7", fontSize: "0.75rem", marginBottom: 10, display: "flex", alignItems: "center", gap: 4, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Strengths
          </h4>
          {pros.map((p, i) => (
            <div key={i} className="pro-item" style={{ marginBottom: 8 }}>
              <div>{p.text}</div>
              <div className="confidence-bar">
                <div className="confidence-fill" style={{ width: `${p.confidence || 85}%`, background: "var(--gradient-emerald)" }} />
              </div>
            </div>
          ))}
        </div>
        <div>
          <h4 style={{ color: "#fca5a5", fontSize: "0.75rem", marginBottom: 10, display: "flex", alignItems: "center", gap: 4, textTransform: "uppercase", letterSpacing: "0.5px" }}>
            Risks
          </h4>
          {cons.map((c, i) => (
            <div key={i} className="con-item" style={{ marginBottom: 8 }}>
              <div>{c.text}</div>
              <div className="confidence-bar">
                <div className="confidence-fill" style={{ width: `${c.confidence || 75}%`, background: "var(--gradient-amber)" }} />
              </div>
            </div>
          ))}
        </div>
      </div>
      {data.verdict ? (
        <div style={{ marginTop: 14, padding: "10px 12px", background: "rgba(255,255,255,0.02)", borderRadius: "8px", borderTop: "1px solid var(--border-subtle)", fontSize: "0.825rem", color: "var(--text-secondary)" }}>
          <strong style={{ color: "var(--text-primary)" }}>Verdict:</strong> {String(data.verdict)}
        </div>
      ) : null}
    </div>
  );
}

function SwotView({ data }: { data: SynthesisOutput }) {
  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: "1.1rem" }}>◉</span>
          <span>{String(data.title || "SWOT Analysis")}</span>
        </div>
        <span className="synthesis-badge" style={{ background: "rgba(244, 114, 182, 0.15)", color: "#f9a8d4" }}>
          MATRIX
        </span>
      </div>
      <div className="swot-grid">
        <div className="swot-quadrant swot-strengths">
          <h4 style={{ color: "#6ee7b7" }}>Strengths</h4>
          <ul>{((data.strengths as string[]) || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
        <div className="swot-quadrant swot-weaknesses">
          <h4 style={{ color: "#fca5a5" }}>Weaknesses</h4>
          <ul>{((data.weaknesses as string[]) || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
        <div className="swot-quadrant swot-opportunities">
          <h4 style={{ color: "#67e8f9" }}>Opportunities</h4>
          <ul>{((data.opportunities as string[]) || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
        <div className="swot-quadrant swot-threats">
          <h4 style={{ color: "#f9a8d4" }}>Threats</h4>
          <ul>{((data.threats as string[]) || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      </div>
      {data.strategic_summary ? (
        <p style={{ marginTop: 12, fontSize: "0.825rem", color: "var(--text-secondary)" }}>{String(data.strategic_summary)}</p>
      ) : null}
    </div>
  );
}

function InteractiveKnowledgeGraph({ data }: { data: SynthesisOutput }) {
  const nodes = (data.nodes as Array<{ id: string; label: string; group?: string }>) || [
    { id: "1", label: "Core Objective", group: "core" },
    { id: "2", label: "Key Criteria", group: "crit" },
    { id: "3", label: "Candidate A", group: "opt" },
    { id: "4", label: "Candidate B", group: "opt" },
    { id: "5", label: "Trade-offs", group: "risk" },
  ];

  const [activeNode, setActiveNode] = useState<string | null>(null);

  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: "1.1rem" }}>✦</span>
          <span>{String(data.title || "Knowledge Graph")}</span>
        </div>
        <span className="synthesis-badge" style={{ background: "rgba(56, 189, 248, 0.15)", color: "#67e8f9" }}>
          LIVE
        </span>
      </div>

      <div className="knowledge-graph-container">
        <svg width="100%" height="220" viewBox="0 0 400 220">
          <line x1="200" y1="40" x2="100" y2="110" stroke="rgba(99, 102, 241, 0.3)" strokeWidth="1.5" strokeDasharray="4" />
          <line x1="200" y1="40" x2="300" y2="110" stroke="rgba(99, 102, 241, 0.3)" strokeWidth="1.5" strokeDasharray="4" />
          <line x1="100" y1="110" x2="130" y2="180" stroke="rgba(56, 189, 248, 0.3)" strokeWidth="1.5" />
          <line x1="300" y1="110" x2="270" y2="180" stroke="rgba(56, 189, 248, 0.3)" strokeWidth="1.5" />
          <line x1="130" y1="180" x2="270" y2="180" stroke="rgba(244, 114, 182, 0.3)" strokeWidth="1.5" />

          <g className="graph-node" onClick={() => setActiveNode(nodes[0]?.label || "Core")}>
            <circle cx="200" cy="40" r="24" fill="url(#gradHero)" stroke="rgba(129,140,248,0.5)" strokeWidth="1.5" />
            <text x="200" y="44" textAnchor="middle" fill="#fff" fontSize="9" fontWeight="600">Root</text>
          </g>

          <g className="graph-node" onClick={() => setActiveNode(nodes[1]?.label || "Criteria")}>
            <circle cx="100" cy="110" r="20" fill="rgba(12,12,26,0.9)" stroke="rgba(103,232,249,0.4)" strokeWidth="1.5" />
            <text x="100" y="114" textAnchor="middle" fill="#67e8f9" fontSize="8.5" fontWeight="600">Criteria</text>
          </g>

          <g className="graph-node" onClick={() => setActiveNode(nodes[2]?.label || "Options")}>
            <circle cx="300" cy="110" r="20" fill="rgba(12,12,26,0.9)" stroke="rgba(168,85,247,0.4)" strokeWidth="1.5" />
            <text x="300" y="114" textAnchor="middle" fill="#c4b5fd" fontSize="8.5" fontWeight="600">Options</text>
          </g>

          <g className="graph-node" onClick={() => setActiveNode("Synthesis")}>
            <circle cx="130" cy="180" r="16" fill="rgba(12,12,26,0.9)" stroke="rgba(110,231,183,0.4)" strokeWidth="1.5" />
            <text x="130" y="184" textAnchor="middle" fill="#6ee7b7" fontSize="8">Pros</text>
          </g>

          <g className="graph-node" onClick={() => setActiveNode("Risk Factors")}>
            <circle cx="270" cy="180" r="16" fill="rgba(12,12,26,0.9)" stroke="rgba(249,168,212,0.4)" strokeWidth="1.5" />
            <text x="270" y="184" textAnchor="middle" fill="#f9a8d4" fontSize="8">Risks</text>
          </g>

          <defs>
            <linearGradient id="gradHero" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#ec4899" />
            </linearGradient>
          </defs>
        </svg>
      </div>

      {activeNode ? (
        <div style={{ marginTop: 10, fontSize: "0.78rem", color: "var(--text-cyan)", textAlign: "center" }}>
          Selected: <strong>{activeNode}</strong>
        </div>
      ) : (
        <div style={{ marginTop: 10, fontSize: "0.72rem", color: "var(--text-muted)", textAlign: "center" }}>
          Click a node to inspect
        </div>
      )}
    </div>
  );
}

function SynthesisRenderer({ output }: { output: SynthesisOutput }) {
  switch (output.type) {
    case "decision_matrix":
      return <InteractiveDecisionMatrix data={output} />;
    case "comparison_table":
      return <ComparisonView data={output} />;
    case "pros_cons":
      return <ProsConsView data={output} />;
    case "swot_analysis":
      return <SwotView data={output} />;
    case "knowledge_map":
    case "concept_map":
      return <InteractiveKnowledgeGraph data={output} />;
    default:
      return <InteractiveDecisionMatrix data={output} />;
  }
}

/* ─── Cognitive Profile ─────────────────────────────────────────── */

function ThinkingStyleRadar({ style }: { style: Record<string, number> | null }) {
  if (!style) return null;
  const dims = [
    { key: "analytical", label: "Analytical" },
    { key: "detail_oriented", label: "Precision" },
    { key: "visual", label: "Visual" },
    { key: "structured", label: "Structure" },
    { key: "risk_aware", label: "Risk Aware" },
    { key: "speed", label: "Velocity" },
  ];
  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span>◉</span>
          <span>Cognitive Profile</span>
        </div>
        <span className="synthesis-badge" style={{ background: "rgba(16, 185, 129, 0.12)", color: "#6ee7b7" }}>
          ADAPTIVE
        </span>
      </div>
      <div className="style-radar">
        {dims.map((d) => (
          <div key={d.key} className="style-dimension">
            <span className="style-label">{d.label}</span>
            <div className="style-bar">
              <div className="style-fill" style={{ width: `${style[d.key] ?? 60}%` }} />
            </div>
            <span className="style-value">{style[d.key] ?? 60}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}



/* ═══════════════════════════════════════════════════════════════════
   MAIN APPLICATION
   ═══════════════════════════════════════════════════════════════════ */

export default function Home() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [phase, setPhase] = useState("onboarding");
  const [synthesis, setSynthesis] = useState<SynthesisOutput[]>([]);
  const [thinkingStyle, setThinkingStyle] = useState<Record<string, number> | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [thinkingMode, setThinkingMode] = useState("deliberation");
  const [selectedLanguage, setSelectedLanguage] = useState("auto");
  const [copyToast, setCopyToast] = useState(false);
  const [deliberationTrace, setDeliberationTrace] = useState<Array<{agent: string; action: string; ts: number}>>([]);
  const [lastConfidence, setLastConfidence] = useState(0);
  const [lastVerification, setLastVerification] = useState("");
  const [veoModalOpen, setVeoModalOpen] = useState(false);
  const [veoData, setVeoData] = useState<any>(null);
  const [isGeneratingVeo, setIsGeneratingVeo] = useState(false);
  const [gemmaModalOpen, setGemmaModalOpen] = useState(false);
  const [gemmaData, setGemmaData] = useState<any>(null);
  const [isGeneratingGemma, setIsGeneratingGemma] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopyToast(true);
      setTimeout(() => setCopyToast(false), 2000);
    });
  };

  const speakText = (text: string) => {
    if (!("speechSynthesis" in window)) return;
    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }
    // Remove markdown code fences and JSON blocks for clean speech
    const cleanText = text
      .replace(/```json[\s\S]*?```/g, "")
      .replace(/```[\s\S]*?```/g, "")
      .replace(/[*#_`~>]/g, "")
      .trim();

    if (!cleanText) return;

    const utterance = new SpeechSynthesisUtterance(cleanText);
    const langCode = selectedLanguage !== "auto" ? selectedLanguage : detectLanguage(text);
    utterance.lang = langCode;
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    // Pick best matching voice for detected language
    const voices = window.speechSynthesis.getVoices();
    const exactVoice = voices.find((v) => v.lang.toLowerCase() === langCode.toLowerCase());
    const prefixVoice = voices.find((v) => v.lang.toLowerCase().startsWith(langCode.slice(0, 2).toLowerCase()));
    if (exactVoice) {
      utterance.voice = exactVoice;
    } else if (prefixVoice) {
      utterance.voice = prefixVoice;
    }

    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;
    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: text,
      message_type: "text",
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    const agentMsgId = (Date.now() + 1).toString();
    let streamedContent = "";

    try {
      const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          user_id: "user-1",
          thinking_mode: thinkingMode,
        }),
      });

      if (response.ok && response.body) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        // Add initial streaming message placeholder
        setMessages((prev) => [
          ...prev,
          {
            id: agentMsgId,
            role: "agent",
            content: "",
            message_type: "text",
            timestamp: new Date().toISOString(),
            active_agent: "Synthesizer",
          },
        ]);

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const eventData = JSON.parse(line.slice(6));
                if (eventData.type === "init") {
                  setSessionId(eventData.session_id);
                } else if (eventData.type === "token") {
                  streamedContent += eventData.token;
                  setMessages((prev) =>
                    prev.map((m) => (m.id === agentMsgId ? { ...m, content: streamedContent } : m))
                  );
                } else if (eventData.type === "trace" && eventData.step) {
                  setDeliberationTrace((prev) => [...prev, eventData.step]);
                } else if (eventData.type === "done") {
                  if (eventData.phase) setPhase(eventData.phase);
                  if (eventData.synthesis?.length) {
                    setSynthesis((prev) => [...prev, ...eventData.synthesis]);
                  }
                  if (eventData.confidence_score) {
                    setLastConfidence(eventData.confidence_score);
                  }
                  if (eventData.verification_status) {
                    setLastVerification(eventData.verification_status);
                  }
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === agentMsgId
                        ? {
                            ...m,
                            latency_ms: eventData.latency_ms,
                            confidence_score: eventData.confidence_score,
                            verification_status: eventData.verification_status,
                          }
                        : m
                    )
                  );
                }
              } catch {
                // Ignore parse errors on partial chunks
              }
            }
          }
        }
      } else {
        // Fallback to standard chat endpoint if streaming unsupported
        const res = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            session_id: sessionId,
            message: text,
            user_id: "user-1",
            thinking_mode: thinkingMode,
          }),
        });
        const data = await res.json();
        setSessionId(data.session_id);
        setPhase(data.phase);

        const agentMsg: Message = {
          id: agentMsgId,
          role: "agent",
          content: data.message,
          message_type: data.message_type || "text",
          timestamp: new Date().toISOString(),
          active_agent: data.active_agent,
          latency_ms: data.latency_ms,
          confidence_score: data.confidence_score,
          verification_status: data.verification_status,
        };
        setMessages((prev) => [...prev, agentMsg]);

        if (data.synthesis?.length) setSynthesis((prev) => [...prev, ...data.synthesis]);
        if (data.thinking_style) setThinkingStyle(data.thinking_style);
        if (data.deliberation_trace?.length) setDeliberationTrace(data.deliberation_trace);
        if (data.confidence_score) setLastConfidence(data.confidence_score);
        if (data.verification_status) setLastVerification(data.verification_status);
      }
    } catch {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "agent",
        content: "Connection interrupted. Please verify the service is running.",
        message_type: "alert",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    }
    setIsLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setIsLoading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("session_id", sessionId || "");
    formData.append("user_id", "user-1");

    try {
      const res = await fetch(`${API_URL}/api/upload`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      setSessionId(data.session_id);

      const agentMsg: Message = {
        id: Date.now().toString(),
        role: "agent",
        content: data.message || `Processed: ${file.name}`,
        message_type: "text",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, agentMsg]);
    } catch {
      const errorMsg: Message = {
        id: Date.now().toString(),
        role: "agent",
        content: "File upload failed. Please try again.",
        message_type: "alert",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    }
    setIsLoading(false);
    setShowUpload(false);
  };

  const startVoiceInput = () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const W = window as any;
    const SpeechRecognitionCtor = W.SpeechRecognition || W.webkitSpeechRecognition;
    if (!SpeechRecognitionCtor) return;
    const recognition = new SpeechRecognitionCtor();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = selectedLanguage !== "auto" ? selectedLanguage : (navigator.language || "en-US");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
      setIsRecording(false);
    };
    recognition.onerror = () => setIsRecording(false);
    recognition.onend = () => setIsRecording(false);
    setIsRecording(true);
    recognition.start();
  };

  const getPhaseStatus = (key: string) => {
    const order = PHASES.map((p) => p.key);
    const currentIdx = order.indexOf(phase);
    const phaseIdx = order.indexOf(key);
    if (phaseIdx < currentIdx) return "completed";
    if (phaseIdx === currentIdx) return "active";
    return "";
  };

  const msgClass = (msg: Message) => {
    if (msg.role === "user") return "message message-user";
    if (msg.message_type === "question") return "message message-question";
    if (msg.message_type === "insight") return "message message-insight";
    return "message message-agent";
  };

  /* ═══════════════════════════════════════════════════════════════════
     HERO LANDING — CLEAN & FOCUSED (NO TOP-BAR CLUTTER)
     ═══════════════════════════════════════════════════════════════════ */
  if (!sessionId && messages.length === 0) {
    return (
      <div className="landing">
        <div className="ambient-bg" />
        <div className="ambient-grid" />

        {/* Hero Body */}
        <main className="landing-hero">
          <div
            className="landing-logo-icon"
            style={{ width: 44, height: 44, fontSize: "1.3rem", borderRadius: "12px", margin: "0 auto 20px" }}
          >
            S
          </div>

          <h1 className="landing-title">SynthMind</h1>
          <p className="landing-subtitle">
            Don&apos;t just search. <strong>Think together.</strong><br />
            Transform chaotic research into crystal-clear decisions through adaptive co-intelligence.
          </p>

          {/* Command Bar Input Box */}
          <div className="landing-search-container">
            <div className="landing-search-bar">
              <span className="landing-search-icon">✦</span>
              <input
                className="landing-input"
                placeholder="What complex decision are you navigating?"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") sendMessage(input);
                }}
                autoFocus
              />
              <div className="landing-search-actions">
                <button
                  className={`landing-mic-btn ${isRecording ? "voice-pulse" : ""}`}
                  style={{ color: isRecording ? "#fca5a5" : "inherit" }}
                  onClick={startVoiceInput}
                  title="Voice input"
                >
                  🎤
                </button>
                <button
                  className="landing-send-btn"
                  onClick={() => sendMessage(input)}
                  disabled={!input.trim() || isLoading}
                >
                  <span>Ask</span>
                  <span>→</span>
                </button>
              </div>
            </div>
          </div>

          {/* Quick Starts */}
          <div className="quick-starts">
            {QUICK_STARTS.map((qs) => (
              <button key={qs.label} className="quick-start-chip" onClick={() => sendMessage(qs.prompt)}>
                <span>{qs.emoji}</span>
                <span>{qs.label}</span>
              </button>
            ))}
          </div>
        </main>

        {/* Footer Status */}
        <footer className="landing-footer">
          <div className="landing-status-bar">
            <span className="status-dot" />
            <span>Ready</span>
            <span style={{ color: "rgba(255,255,255,0.15)" }}>•</span>
            <span>Multilingual Intelligence</span>
            <span style={{ color: "rgba(255,255,255,0.15)" }}>•</span>
            <span>Sub-Second Response</span>
          </div>
        </footer>
      </div>
    );
  }

  /* ═══════════════════════════════════════════════════════════════════
     WORKSPACE DASHBOARD (CLEAN SIDEBAR, UNCLUTTERED)
     ═══════════════════════════════════════════════════════════════════ */
  return (
    <div className="app-layout">
      <div className="ambient-bg" />

      {/* Left Sidebar — Clean Minimal */}
      <aside className="sidebar">
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 24 }}>
          <div style={{
            width: 36, height: 36, borderRadius: "10px",
            background: "var(--gradient-primary)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: "1rem", fontWeight: 800, color: "white",
            boxShadow: "0 4px 16px rgba(99,102,241,0.3)"
          }}>
            S
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: "1.05rem", background: "var(--gradient-hero)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              SynthMind
            </div>
            <div style={{ fontSize: "0.62rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "1.2px" }}>
              Research Partner
            </div>
          </div>
        </div>

        <button
          className="btn-gradient"
          style={{ width: "100%", marginBottom: 20 }}
          onClick={() => {
            setSessionId(null);
            setMessages([]);
            setSynthesis([]);
            setPhase("onboarding");
          }}
        >
          <span>+</span> New Session
        </button>

        <div style={{ flex: 1 }} />



        {/* Status */}
        <div style={{ padding: "10px 12px", background: "rgba(0,0,0,0.2)", borderRadius: "10px", border: "1px solid var(--border-subtle)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
            <span className="status-dot" />
            <span style={{ fontSize: "0.72rem", color: "var(--text-emerald)", fontWeight: 600 }}>Active</span>
          </div>
          <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", lineHeight: 1.5 }}>
            Multilingual intelligence running.
          </div>
        </div>
      </aside>

      {/* Center Chat Area */}
      <div className="main-content">
        {/* Phase Pipeline & Language Selector */}
        <div className="phase-bar">
          <div className="phase-steps-container">
            {PHASES.map((p, i) => (
              <div key={p.key} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <div className={`phase-step ${getPhaseStatus(p.key)}`}>
                  <div className={`phase-dot ${getPhaseStatus(p.key)}`} />
                  <span>{p.icon} {p.label}</span>
                </div>
                {i < PHASES.length - 1 && <div className="phase-connector" />}
              </div>
            ))}
          </div>

          <div className="lang-selector-wrapper">
            <select
              className="lang-select-dropdown"
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              title="Select conversation language"
            >
              {SUPPORTED_LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Messages */}
        <div className="chat-container">
          <div className="chat-messages">
            {messages.map((msg) => (
              <div key={msg.id} className={msgClass(msg)}>
                {msg.role === "agent" && (
                  <div className="agent-msg-header">
                    <div className="agent-identity">
                      <div className="agent-avatar">S</div>
                      <span className="agent-name">SynthMind</span>
                      {msg.active_agent && (
                        <span className="agent-badge">{msg.active_agent}</span>
                      )}
                    </div>
                    <div className="msg-actions">
                      <button
                        className="msg-action-btn"
                        onClick={() => copyToClipboard(msg.content)}
                        title="Copy text"
                      >
                        ◫ Copy
                      </button>
                      <button
                        className={`msg-action-btn ${isSpeaking ? "active" : ""}`}
                        onClick={() => speakText(msg.content)}
                        title="Listen (Multilingual Voice)"
                      >
                        {isSpeaking ? "◉ Stop" : "◎ Listen"}
                      </button>
                    </div>
                  </div>
                )}

                <div
                  dangerouslySetInnerHTML={{
                    __html: sanitizeHtml(msg.content),
                  }}
                />

                {msg.role === "agent" && msg.latency_ms && (
                  <div style={{ marginTop: 8, display: "flex", alignItems: "center", gap: 10, fontSize: "0.62rem", color: "var(--text-muted)", fontFamily: "'JetBrains Mono', monospace" }}>
                    <span>{msg.latency_ms}ms</span>
                    {msg.confidence_score ? (
                      <span className={`confidence-pill confidence-${msg.verification_status || 'none'}`}>
                        {msg.confidence_score}% Confidence
                        {msg.verification_status === 'verified' && ' • ✓ Verified'}
                        {msg.verification_status === 'partially_verified' && ' • ◐ Reviewed'}
                        {msg.verification_status === 'needs_review' && ' • ⚠ Needs Review'}
                      </span>
                    ) : null}
                  </div>
                )}

              </div>
            ))}

            {isLoading && (
              <div className="thinking-indicator">
                <div className="thinking-avatar">S</div>
                <div className="thinking-content">
                  <div className="thinking-shimmer" />
                  <div className="thinking-shimmer" />
                  <div className="deliberation-trace">
                    {deliberationTrace.length > 0 ? (
                      deliberationTrace.map((step, i) => (
                        <div key={i} className={`trace-step ${i === deliberationTrace.length - 1 ? 'trace-active' : 'trace-done'}`}>
                          <span className="trace-agent">{step.agent}</span>
                          <span className="trace-action">{step.action}</span>
                          <span className="trace-ts">{step.ts}ms</span>
                        </div>
                      ))
                    ) : (
                      <div className="thinking-label">Thinking...</div>
                    )}
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Upload */}
          {showUpload && (
            <div style={{ padding: "0 32px 14px" }}>
              <div className="upload-zone" onClick={() => fileInputRef.current?.click()}>
                <div className="upload-zone-icon">📁</div>
                <div className="upload-zone-text">
                  Drop files here — PDF, CSV, TXT, images<br />
                  <small>Up to 10MB</small>
                </div>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.png,.jpg,.jpeg,.csv,.txt"
                style={{ display: "none" }}
                onChange={handleFileUpload}
              />
            </div>
          )}

          {/* Input Bar */}
          <div className="chat-input-area">

            <div className="chat-input-wrapper">
              <div className="input-actions">
                <button
                  className="input-btn"
                  onClick={() => setShowUpload(!showUpload)}
                  title="Upload"
                >
                  📎
                </button>
                <button
                  className={`input-btn ${isRecording ? "voice-pulse" : ""}`}
                  style={{ color: isRecording ? "#fca5a5" : "inherit" }}
                  onClick={startVoiceInput}
                  title="Voice input (Any language)"
                >
                  🎤
                </button>
              </div>

              <textarea
                ref={inputRef}
                className="chat-input"
                placeholder={phase === "ingestion" ? "Paste data, links, or requirements..." : "Ask in any language (English, 中文, 日本語, Deutsch, Español...)..."}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
              />

              <div className="chat-input-right-actions">
                {/* Gemini & Claude style Co-Thinking Mode Selector */}
                <select
                  className="cothink-mode-dropdown"
                  value={thinkingMode}
                  onChange={(e) => setThinkingMode(e.target.value)}
                  title="Co-Thinking / Reasoning Mode"
                >
                  <option value="deliberation">🧠 Deliberate</option>
                  <option value="fast">⚡ Fast</option>
                  <option value="socratic">🔬 Socratic</option>
                </select>

                <button className="send-btn" onClick={() => sendMessage(input)} disabled={!input.trim() || isLoading}>
                  <span>Send</span>
                  <span>→</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel — Synthesis */}
      <aside className="synthesis-panel">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: 700, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: 8 }}>
            <span>✦</span> Intelligence
          </h3>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {sessionId && messages.length > 0 && (
              <button
                className="export-header-btn"
                onClick={async () => {
                  try {
                    const res = await fetch(`${API_URL}/api/export`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ session_id: sessionId }),
                    });
                    const data = await res.json();
                    if (data.markdown) {
                      const blob = new Blob([data.markdown], { type: 'text/markdown' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `SynthMind-Brief-${sessionId?.slice(0,8) || 'export'}.md`;
                      a.click();
                      URL.revokeObjectURL(url);
                    }
                  } catch (err) {
                    console.error('Export failed:', err);
                  }
                }}
                title="Export Executive Brief Markdown"
              >
                <span>📑</span> Export Brief
              </button>
            )}
            <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>
              {synthesis.length} Output{synthesis.length !== 1 ? "s" : ""}
            </span>
          </div>
        </div>

        {synthesis.length === 0 ? (
          <div style={{ textAlign: "center", padding: "60px 20px", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            <div style={{ fontSize: "2.2rem", marginBottom: 12, opacity: 0.5 }}>◈</div>
            <div style={{ fontWeight: 600, color: "var(--text-secondary)", marginBottom: 6, fontSize: "0.9rem" }}>
              Awaiting Data
            </div>
            <div style={{ lineHeight: 1.6 }}>
              Decision matrices, trade-off models, and strategic grids will appear here as your research progresses.
            </div>
          </div>
        ) : (
          synthesis.map((s, i) => <SynthesisRenderer key={i} output={s} />)
        )}

        <ThinkingStyleRadar style={thinkingStyle} />

        {/* Confidence Indicator */}
        {lastConfidence > 0 && (
          <div className={`confidence-card confidence-${lastVerification}`}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
              <span style={{ fontSize: "0.7rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.8px", color: "var(--text-muted)" }}>Confidence</span>
              <span style={{ fontSize: "0.7rem", fontWeight: 700, color: lastConfidence >= 80 ? "#6ee7b7" : lastConfidence >= 60 ? "#fcd34d" : "#fca5a5" }}>
                {lastConfidence}%
              </span>
            </div>
            <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden" }}>
              <div style={{ height: "100%", width: `${lastConfidence}%`, background: lastConfidence >= 80 ? "var(--gradient-emerald)" : lastConfidence >= 60 ? "linear-gradient(90deg, #f59e0b, #fbbf24)" : "linear-gradient(90deg, #ef4444, #f87171)", borderRadius: 2, transition: "width 1s cubic-bezier(0.16, 1, 0.3, 1)" }} />
            </div>
            <div style={{ fontSize: "0.62rem", color: "var(--text-muted)", marginTop: 6 }}>
              {lastVerification === 'verified' && '✓ Audited for bias — verified'}
              {lastVerification === 'partially_verified' && '◐ Partially verified — minor gaps'}
              {lastVerification === 'needs_review' && '⚠ Needs review — evidence gaps'}
              {!lastVerification && 'Pending audit'}
            </div>
          </div>
        )}

        {/* Contextual Google Multimodal Studio Toolbar (Only appears when synthesis data exists) */}
        {synthesis.length > 0 && (
          <div className="multimodal-studio-toolbar">
            <div style={{ fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "1px", color: "var(--text-accent)", marginBottom: 8, display: "flex", alignItems: "center", gap: 6 }}>
              <span>✨</span> Google Multimodal Studio
            </div>
            
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <button
                className="studio-action-btn veo-action"
                onClick={async () => {
                  setIsGeneratingVeo(true);
                  setVeoModalOpen(true);
                  try {
                    const res = await fetch(`${API_URL}/api/veo/storyboard`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ session_id: sessionId }),
                    });
                    const data = await res.json();
                    setVeoData(data);
                  } catch (err) {
                    console.error('Veo generation failed:', err);
                  } finally {
                    setIsGeneratingVeo(false);
                  }
                }}
                title="Google Veo Cinematic Video Brief"
              >
                <span>🎬</span> Veo Video Brief
              </button>

              <button
                className="studio-action-btn gemma-action"
                onClick={async () => {
                  setIsGeneratingGemma(true);
                  setGemmaModalOpen(true);
                  try {
                    const recentContent = messages.slice(-4).map(m => m.content).join("\n\n");
                    const res = await fetch(`${API_URL}/api/gemma/distill`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ content: recentContent || "Synthesized decision trade-offs." }),
                    });
                    const data = await res.json();
                    setGemmaData(data);
                  } catch (err) {
                    console.error('Gemma distillation failed:', err);
                  } finally {
                    setIsGeneratingGemma(false);
                  }
                }}
                title="Google Gemma 2 Open Model Distillation"
              >
                <span>💎</span> Gemma 2 Distill
              </button>
            </div>
          </div>
        )}
      </aside>



      {/* Google Veo Video Storyboard Modal */}
      {veoModalOpen && (
        <div className="assistant-modal-backdrop" onClick={() => setVeoModalOpen(false)}>
          <div className="assistant-modal-card" style={{ maxWidth: 780 }} onClick={(e) => e.stopPropagation()}>
            <div className="assistant-modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: "1.3rem" }}>🎬</span>
                <div>
                  <div style={{ fontWeight: 800, fontSize: "1.05rem", color: "var(--text-primary)" }}>
                    Google Veo 3.1 &amp; Lyria Studio
                  </div>
                  <div style={{ fontSize: "0.68rem", color: "var(--text-secondary)" }}>
                    Cinematic Multi-Shot Visual Brief &amp; DeepMind Lyria Soundscape
                  </div>
                </div>
              </div>
              <button className="assistant-modal-close" onClick={() => setVeoModalOpen(false)}>✕</button>
            </div>

            <div className="assistant-modal-body" style={{ maxHeight: "70vh", overflowY: "auto" }}>
              {isGeneratingVeo ? (
                <div style={{ textAlign: "center", padding: "40px 20px" }}>
                  <div className="status-dot" style={{ margin: "0 auto 16px", transform: "scale(1.5)" }} />
                  <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                    Directing Google Veo Video Storyboard...
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    Synthesizing camera paths, scene lighting, and Lyria audio prompts
                  </div>
                </div>
              ) : veoData ? (
                <div>
                  <div style={{ padding: "12px 16px", background: "rgba(236,72,153,0.08)", borderRadius: "10px", border: "1px solid rgba(236,72,153,0.2)", marginBottom: 16 }}>
                    <div style={{ fontWeight: 700, fontSize: "0.9rem", color: "#f472b6", marginBottom: 4 }}>
                      {veoData.video_title}
                    </div>
                    <div style={{ display: "flex", gap: 12, fontSize: "0.68rem", color: "var(--text-secondary)" }}>
                      <span>Model: <strong>{veoData.veo_model}</strong></span>
                      <span>Ratio: <strong>{veoData.aspect_ratio || "16:9"}</strong></span>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 16 }}>
                    {veoData.scenes?.map((scene: any, idx: number) => (
                      <div key={idx} style={{ padding: "14px", background: "rgba(255,255,255,0.02)", borderRadius: "10px", border: "1px solid var(--border-subtle)" }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
                          <span style={{ fontWeight: 700, fontSize: "0.8rem", color: "var(--text-cyan)" }}>
                            Scene {scene.scene_number}: {scene.title}
                          </span>
                          <span style={{ fontSize: "0.62rem", padding: "2px 8px", borderRadius: "999px", background: "rgba(99,102,241,0.15)", color: "#a5b4fc" }}>
                            {scene.camera_motion}
                          </span>
                        </div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-primary)", lineHeight: 1.5, marginBottom: 8 }}>
                          🎥 <em>&quot;{scene.visual_prompt}&quot;</em>
                        </div>
                        <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", background: "rgba(0,0,0,0.2)", padding: "8px 10px", borderRadius: "6px" }}>
                          🎙️ <strong>VO:</strong> {scene.voiceover_script}
                        </div>
                      </div>
                    ))}
                  </div>

                  {veoData.lyria_audio_cue && (
                    <div style={{ padding: "12px", background: "rgba(6,182,212,0.08)", borderRadius: "10px", border: "1px solid rgba(6,182,212,0.2)", marginBottom: 16 }}>
                      <div style={{ fontSize: "0.65rem", fontWeight: 700, color: "var(--text-cyan)", textTransform: "uppercase", marginBottom: 4 }}>
                        🎵 Google DeepMind Lyria Sonic Cue
                      </div>
                      <div style={{ fontSize: "0.75rem", color: "var(--text-primary)" }}>
                        {veoData.lyria_audio_cue}
                      </div>
                    </div>
                  )}

                  {veoData.veo_master_prompt && (
                    <button
                      className="btn-gradient"
                      style={{ width: "100%", justifyContent: "center" }}
                      onClick={() => copyToClipboard(veoData.veo_master_prompt)}
                    >
                      <span>◫</span> Copy Google Veo Master Prompt
                    </button>
                  )}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Google Gemma 2 Distillation Modal */}
      {gemmaModalOpen && (
        <div className="assistant-modal-backdrop" onClick={() => setGemmaModalOpen(false)}>
          <div className="assistant-modal-card" style={{ maxWidth: 700 }} onClick={(e) => e.stopPropagation()}>
            <div className="assistant-modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                <span style={{ fontSize: "1.3rem" }}>💎</span>
                <div>
                  <div style={{ fontWeight: 800, fontSize: "1.05rem", color: "var(--text-primary)" }}>
                    Google Gemma 2 Distillation
                  </div>
                  <div style={{ fontSize: "0.68rem", color: "var(--text-secondary)" }}>
                    High-Efficiency Open Foundation Model Engine
                  </div>
                </div>
              </div>
              <button className="assistant-modal-close" onClick={() => setGemmaModalOpen(false)}>✕</button>
            </div>

            <div className="assistant-modal-body" style={{ maxHeight: "70vh", overflowY: "auto" }}>
              {isGeneratingGemma ? (
                <div style={{ textAlign: "center", padding: "40px 20px" }}>
                  <div className="status-dot" style={{ margin: "0 auto 16px", transform: "scale(1.5)" }} />
                  <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 6 }}>
                    Running Google Gemma Distillation...
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    Fast factual distillation using Google open weights
                  </div>
                </div>
              ) : gemmaData ? (
                <div>
                  <div style={{ padding: "10px 14px", background: "rgba(56,189,248,0.08)", borderRadius: "8px", border: "1px solid rgba(56,189,248,0.2)", marginBottom: 14, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.72rem", color: "var(--text-cyan)", fontWeight: 600 }}>
                      Model: {gemmaData.model_used}
                    </span>
                    <span style={{ fontSize: "0.62rem", color: "var(--text-muted)" }}>
                      {gemmaData.provider}
                    </span>
                  </div>

                  <div
                    style={{ fontSize: "0.82rem", lineHeight: 1.6, color: "var(--text-primary)" }}
                    dangerouslySetInnerHTML={{
                      __html: sanitizeHtml(gemmaData.summary || ""),
                    }}
                  />
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}

      {/* Copy Toast */}
      {copyToast && (
        <div className="copy-toast">✓ Copied to clipboard</div>
      )}
    </div>
  );
}


