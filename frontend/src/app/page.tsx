"use client";

import { useState, useRef, useEffect, useCallback } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Message {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  message_type: string;
  timestamp: string;
}

interface SynthesisOutput {
  type: string;
  [key: string]: unknown;
}

const PHASES = [
  { key: "onboarding", label: "Welcome", icon: "🚀" },
  { key: "clarification", label: "Understanding", icon: "🔍" },
  { key: "ingestion", label: "Data Input", icon: "📄" },
  { key: "synthesis", label: "Synthesis", icon: "⚡" },
  { key: "feedback", label: "Feedback", icon: "💬" },
];

const QUICK_STARTS = [
  { emoji: "⚖️", label: "Compare options", prompt: "I need to compare several options and make a decision" },
  { emoji: "🔬", label: "Research a topic", prompt: "I want to deeply research and understand a topic" },
  { emoji: "🎯", label: "Make a decision", prompt: "I have a big decision to make and need help thinking through it" },
  { emoji: "📚", label: "Learn something", prompt: "I want to learn about something new and complex" },
];

/* ─── Synthesis Renderers ────────────────────────────────────────── */

function DecisionMatrixView({ data }: { data: SynthesisOutput }) {
  const criteria = (data.criteria as Array<{ name: string; weight: number }>) || [];
  const options = (data.options as Array<{ name: string; scores: Record<string, number>; total_weighted?: number }>) || [];
  const scoreClass = (s: number) => s >= 8 ? "score-high" : s >= 5 ? "score-mid" : "score-low";

  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <span>📊</span>
        <span>{(data.title as string) || "Decision Matrix"}</span>
        <span className="synthesis-badge" style={{ background: "rgba(102,126,234,0.2)", color: "#667eea" }}>MATRIX</span>
      </div>
      <table className="matrix-table">
        <thead>
          <tr>
            <th>Option</th>
            {criteria.map((c) => <th key={c.name}>{c.name} ({c.weight}%)</th>)}
            <th>Total</th>
          </tr>
        </thead>
        <tbody>
          {options.map((opt) => (
            <tr key={opt.name}>
              <td style={{ fontWeight: 600 }}>{opt.name}</td>
              {criteria.map((c) => {
                const score = opt.scores?.[c.name] ?? 0;
                return <td key={c.name} className={`score-cell ${scoreClass(score)}`}>{score}/10</td>;
              })}
              <td className="score-cell score-high" style={{ fontWeight: 700 }}>{opt.total_weighted?.toFixed(1) ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.recommendation ? <p style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--text-secondary)" }}>💡 {String(data.recommendation)}</p> : null}
    </div>
  );
}

function ComparisonView({ data }: { data: SynthesisOutput }) {
  const items = (data.items as string[]) || [];
  const features = (data.features as Array<{ name: string; values: Record<string, string>; winner?: string }>) || [];

  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <span>📋</span>
        <span>{(data.title as string) || "Comparison"}</span>
        <span className="synthesis-badge" style={{ background: "rgba(79,172,254,0.2)", color: "#4facfe" }}>COMPARE</span>
      </div>
      <table className="matrix-table">
        <thead><tr><th>Feature</th>{items.map((i) => <th key={i}>{i}</th>)}<th>Best</th></tr></thead>
        <tbody>
          {features.map((f) => (
            <tr key={f.name}>
              <td style={{ fontWeight: 500 }}>{f.name}</td>
              {items.map((i) => (
                <td key={i} style={{ color: f.winner === i ? "#43e97b" : "var(--text-secondary)" }}>
                  {f.values?.[i] ?? "—"} {f.winner === i && "✓"}
                </td>
              ))}
              <td className="score-high" style={{ fontWeight: 600 }}>{f.winner || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {data.summary ? <p style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--text-secondary)" }}>{String(data.summary)}</p> : null}
    </div>
  );
}

function ProsConsView({ data }: { data: SynthesisOutput }) {
  const pros = (data.pros as Array<{ text: string; confidence: number }>) || [];
  const cons = (data.cons as Array<{ text: string; confidence: number }>) || [];

  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <span>⚖️</span>
        <span>{(data.title as string) || "Pros & Cons"}</span>
        <span className="synthesis-badge" style={{ background: "rgba(67,233,123,0.2)", color: "#43e97b" }}>ANALYSIS</span>
      </div>
      <div className="proscons-grid">
        <div>
          <h4 style={{ color: "#43e97b", fontSize: "0.8rem", marginBottom: 8 }}>✅ Pros</h4>
          {pros.map((p, i) => (
            <div key={i} className="pro-item">
              {p.text}
              <div className="confidence-bar"><div className="confidence-fill" style={{ width: `${p.confidence}%`, background: "var(--gradient-success)" }} /></div>
            </div>
          ))}
        </div>
        <div>
          <h4 style={{ color: "#f5576c", fontSize: "0.8rem", marginBottom: 8 }}>❌ Cons</h4>
          {cons.map((c, i) => (
            <div key={i} className="con-item">
              {c.text}
              <div className="confidence-bar"><div className="confidence-fill" style={{ width: `${c.confidence}%`, background: "var(--gradient-secondary)" }} /></div>
            </div>
          ))}
        </div>
      </div>
      {data.verdict ? <p style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--text-secondary)", borderTop: "1px solid var(--border-subtle)", paddingTop: 12 }}>⚖️ {String(data.verdict)}</p> : null}
    </div>
  );
}

function SwotView({ data }: { data: SynthesisOutput }) {
  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <span>🔄</span>
        <span>{(data.title as string) || "SWOT Analysis"}</span>
        <span className="synthesis-badge" style={{ background: "rgba(240,147,251,0.2)", color: "#f093fb" }}>SWOT</span>
      </div>
      <div className="swot-grid">
        <div className="swot-quadrant swot-strengths"><h4 style={{ color: "#43e97b" }}>💪 Strengths</h4><ul>{((data.strengths as string[]) || []).map((s, i) => <li key={i}>{s}</li>)}</ul></div>
        <div className="swot-quadrant swot-weaknesses"><h4 style={{ color: "#f5576c" }}>⚠️ Weaknesses</h4><ul>{((data.weaknesses as string[]) || []).map((s, i) => <li key={i}>{s}</li>)}</ul></div>
        <div className="swot-quadrant swot-opportunities"><h4 style={{ color: "#4facfe" }}>🚀 Opportunities</h4><ul>{((data.opportunities as string[]) || []).map((s, i) => <li key={i}>{s}</li>)}</ul></div>
        <div className="swot-quadrant swot-threats"><h4 style={{ color: "#fa709a" }}>🛡️ Threats</h4><ul>{((data.threats as string[]) || []).map((s, i) => <li key={i}>{s}</li>)}</ul></div>
      </div>
      {data.strategic_summary ? <p style={{ marginTop: 12, fontSize: "0.85rem", color: "var(--text-secondary)" }}>📌 {String(data.strategic_summary)}</p> : null}
    </div>
  );
}

function InsightsView({ data }: { data: SynthesisOutput }) {
  const insights = (data.insights as Array<{ text: string; importance: number; category: string; confidence: number }>) || [];
  if (!insights.length && data.text) {
    insights.push({ text: data.text as string, importance: (data.importance as number) || 7, category: (data.category as string) || "finding", confidence: (data.confidence as number) || 80 });
  }
  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header">
        <span>💡</span>
        <span>Key Insights</span>
        <span className="synthesis-badge" style={{ background: "rgba(254,225,64,0.2)", color: "#fee140" }}>INSIGHTS</span>
      </div>
      {insights.map((ins, i) => (
        <div key={i} className="insight-card">
          <div className="insight-importance">{ins.importance}</div>
          <div>
            <div style={{ fontSize: "0.85rem", marginBottom: 4 }}>{ins.text}</div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>{ins.category} • {ins.confidence}% confidence</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function SynthesisRenderer({ output }: { output: SynthesisOutput }) {
  switch (output.type) {
    case "decision_matrix": return <DecisionMatrixView data={output} />;
    case "comparison_table": return <ComparisonView data={output} />;
    case "pros_cons": return <ProsConsView data={output} />;
    case "swot_analysis": return <SwotView data={output} />;
    case "key_insights":
    case "key_insight": return <InsightsView data={output} />;
    default: return (
      <div className="synthesis-card">
        <div className="synthesis-card-header"><span>📊</span><span>{output.type || "Analysis"}</span></div>
        <pre style={{ fontSize: "0.75rem", color: "var(--text-secondary)", whiteSpace: "pre-wrap" }}>{JSON.stringify(output, null, 2)}</pre>
      </div>
    );
  }
}

/* ─── Thinking Style Radar ───────────────────────────────────────── */

function ThinkingStyleRadar({ style }: { style: Record<string, number> | null }) {
  if (!style) return null;
  const dims = [
    { key: "analytical", label: "Analytical" },
    { key: "detail_oriented", label: "Detail" },
    { key: "visual", label: "Visual" },
    { key: "structured", label: "Structured" },
    { key: "risk_aware", label: "Risk Aware" },
    { key: "speed", label: "Speed" },
  ];
  return (
    <div className="synthesis-card">
      <div className="synthesis-card-header"><span>🧬</span><span>Your Thinking Style</span></div>
      <div className="style-radar">
        {dims.map((d) => (
          <div key={d.key} className="style-dimension">
            <span className="style-label">{d.label}</span>
            <div className="style-bar"><div className="style-fill" style={{ width: `${style[d.key] ?? 50}%` }} /></div>
            <span className="style-value">{style[d.key] ?? 50}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ─── Main App ───────────────────────────────────────────────────── */

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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isLoading) return;
    const userMsg: Message = { id: Date.now().toString(), role: "user", content: text, message_type: "text", timestamp: new Date().toISOString() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: text, user_id: "user-1" }),
      });
      const data = await res.json();
      setSessionId(data.session_id);
      setPhase(data.phase);
      const agentMsg: Message = { id: (Date.now() + 1).toString(), role: "agent", content: data.message, message_type: data.message_type || "text", timestamp: new Date().toISOString() };
      setMessages((prev) => [...prev, agentMsg]);
      if (data.synthesis?.length) setSynthesis((prev) => [...prev, ...data.synthesis]);
      if (data.thinking_style) setThinkingStyle(data.thinking_style);
    } catch (err) {
      const errorMsg: Message = { id: (Date.now() + 1).toString(), role: "agent", content: "Connection issue — make sure the backend is running on localhost:8000", message_type: "alert", timestamp: new Date().toISOString() };
      setMessages((prev) => [...prev, errorMsg]);
    }
    setIsLoading(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
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
      const res = await fetch(`${API_URL}/api/upload`, { method: "POST", body: formData });
      const data = await res.json();
      setSessionId(data.session_id);
      const sysMsg: Message = { id: Date.now().toString(), role: "agent", content: `📄 Processed **${file.name}**: ${data.extracted?.summary || "File analyzed successfully"}`, message_type: "insight", timestamp: new Date().toISOString() };
      setMessages((prev) => [...prev, sysMsg]);
      setPhase("ingestion");
    } catch {
      const errMsg: Message = { id: Date.now().toString(), role: "agent", content: "Failed to upload file. Please try again.", message_type: "alert", timestamp: new Date().toISOString() };
      setMessages((prev) => [...prev, errMsg]);
    }
    setIsLoading(false);
    setShowUpload(false);
  };

  const startVoiceInput = () => {
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      alert("Voice input not supported in this browser");
      return;
    }
    const SpeechRecognition = (window as unknown as Record<string, unknown>).webkitSpeechRecognition || (window as unknown as Record<string, unknown>).SpeechRecognition;
    const recognition = new (SpeechRecognition as new () => { lang: string; onresult: (e: { results: { transcript: string }[][] }) => void; onend: () => void; start: () => void })();
    recognition.lang = "en-US";
    recognition.onresult = (e: { results: { transcript: string }[][] }) => {
      const transcript = e.results[0][0].transcript;
      setInput(transcript);
      setIsRecording(false);
    };
    recognition.onend = () => setIsRecording(false);
    recognition.start();
    setIsRecording(true);
  };

  const sendFeedback = async (rating: "positive" | "negative") => {
    if (!sessionId) return;
    try {
      await fetch(`${API_URL}/api/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, rating }),
      });
    } catch { /* silent */ }
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
    if (msg.message_type === "synthesis") return "message message-synthesis";
    return "message message-agent";
  };

  /* Landing page */
  if (!sessionId && messages.length === 0) {
    return (
      <div className="landing">
        <div style={{ fontSize: "4rem", marginBottom: 16 }}>🧠</div>
        <h1 className="landing-title">SynthMind</h1>
        <p className="landing-subtitle">
          Don&apos;t just search. <strong>Think together.</strong><br />
          Your adaptive research partner that transforms chaos into clarity.
        </p>
        <input
          className="landing-input"
          placeholder="What are you trying to figure out today?"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") sendMessage(input); }}
          autoFocus
        />
        <div className="quick-starts">
          {QUICK_STARTS.map((qs) => (
            <button key={qs.label} className="quick-start-chip" onClick={() => sendMessage(qs.prompt)}>
              {qs.emoji} {qs.label}
            </button>
          ))}
        </div>
        <p style={{ marginTop: 40, fontSize: "0.75rem", color: "var(--text-muted)" }}>
          Powered by Gemini 3.7 Flash · Google ADK · Firebase
        </p>
      </div>
    );
  }

  /* Main workspace */
  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 24 }}>
          <span style={{ fontSize: "1.5rem" }}>🧠</span>
          <span style={{ fontWeight: 700, fontSize: "1.1rem", background: "var(--gradient-hero)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>SynthMind</span>
        </div>
        <button className="btn-gradient" style={{ width: "100%", marginBottom: 16 }} onClick={() => { setSessionId(null); setMessages([]); setSynthesis([]); setPhase("onboarding"); }}>
          + New Research
        </button>
        <div style={{ flex: 1 }} />
        <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textAlign: "center", padding: "12px 0" }}>
          Built for All Things Agentic Hackathon 2026
        </div>
      </aside>

      {/* Main Chat Area */}
      <div className="main-content">
        {/* Phase Bar */}
        <div className="phase-bar">
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

        {/* Chat Messages */}
        <div className="chat-container">
          <div className="chat-messages">
            {messages.map((msg) => (
              <div key={msg.id} className={msgClass(msg)}>
                <div dangerouslySetInnerHTML={{ __html: msg.content.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>").replace(/\n/g, "<br/>") }} />
                {msg.role === "agent" && (
                  <div className="feedback-bar">
                    <button className="feedback-btn" onClick={() => sendFeedback("positive")}>👍</button>
                    <button className="feedback-btn" onClick={() => sendFeedback("negative")}>👎</button>
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="typing-indicator">
                <div className="typing-dot" />
                <div className="typing-dot" />
                <div className="typing-dot" />
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Upload Zone */}
          {showUpload && (
            <div style={{ padding: "0 24px 16px" }}>
              <div className="upload-zone" onClick={() => fileInputRef.current?.click()}>
                <div className="upload-zone-icon">📁</div>
                <div className="upload-zone-text">Drop files here or click to upload<br /><small>PDF, Images, CSV — up to 10MB</small></div>
              </div>
              <input ref={fileInputRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.csv,.txt,.xlsx" style={{ display: "none" }} onChange={handleFileUpload} />
            </div>
          )}

          {/* Chat Input */}
          <div className="chat-input-area">
            <div className="chat-input-wrapper">
              <div className="input-actions">
                <button className="input-btn" onClick={() => setShowUpload(!showUpload)} title="Upload file">📎</button>
                <button className={`input-btn voice-btn ${isRecording ? "recording" : ""}`} onClick={startVoiceInput} title="Voice input">🎤</button>
              </div>
              <textarea
                ref={inputRef}
                className="chat-input"
                placeholder={phase === "ingestion" ? "Paste data, share a URL, or type your thoughts..." : "Type your message..."}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                rows={1}
              />
              <button className="send-btn" onClick={() => sendMessage(input)} disabled={!input.trim() || isLoading}>
                Send →
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Synthesis Panel */}
      <aside className="synthesis-panel">
        <h3 style={{ fontSize: "0.9rem", fontWeight: 600, marginBottom: 16, color: "var(--text-secondary)" }}>
          ⚡ Synthesis Outputs
        </h3>
        {synthesis.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px 0", color: "var(--text-muted)", fontSize: "0.85rem" }}>
            <div style={{ fontSize: "2rem", marginBottom: 8 }}>📊</div>
            Synthesis results will appear here as the agent processes your research data.
          </div>
        ) : (
          synthesis.map((s, i) => <SynthesisRenderer key={i} output={s} />)
        )}
        <ThinkingStyleRadar style={thinkingStyle} />
      </aside>
    </div>
  );
}
