import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import Sphere from './components/Sphere';

const AGENTS: Record<string, { name: string; glyph: string }> = {
  cardiologist: { name: 'Cardiologist', glyph: '♥' },
  pulmonologist: { name: 'Pulmonologist', glyph: '◐' },
  id: { name: 'Infectious Disease', glyph: '◍' },
  neurologist: { name: 'Neurologist', glyph: '◎' },
  gastroenterologist: { name: 'Gastroenterologist', glyph: '◒' },
  nephrologist: { name: 'Nephrologist', glyph: '◓' },
  endocrinologist: { name: 'Endocrinologist', glyph: '◧' },
  rheumatologist: { name: 'Rheumatologist', glyph: '◨' },
  oncologist: { name: 'Oncologist', glyph: '◈' },
  dermatologist: { name: 'Dermatologist', glyph: '▤' },
  orthopedist: { name: 'Orthopedist', glyph: '🦴' },
  general_surgeon: { name: 'General Surgeon', glyph: '⚕' },
  psychiatrist: { name: 'Psychiatrist', glyph: '🧠' },
  pediatrician: { name: 'Pediatrician', glyph: '👶' },
  skeptic: { name: 'Skeptic', glyph: '✦' },
  chair: { name: 'Chair', glyph: '◇' },
  patient: { name: 'Patient Agent', glyph: '●' },
  user: { name: 'You', glyph: 'Y' },
  system: { name: 'System', glyph: '•' }
};

interface Message { who: string; text: string; }

const App: React.FC = () => {
  const [stage, setStage] = useState<'mode'|'case'|'interview'|'triage'|'debate'|'verdict'>('mode');
  const [mode, setMode] = useState<'doctor'|'student'|null>('doctor');
  
  const [caseText, setCaseText] = useState('');
  const [sealedDx, setSealedDx] = useState('');
  const [patientFeed, setPatientFeed] = useState<Message[]>([]);
  const [patientInput, setPatientInput] = useState('');
  
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [triage, setTriage] = useState<{level: string, reason: string} | null>(null);
  
  const [debateFeed, setDebateFeed] = useState<Message[]>([]);
  const [verdictText, setVerdictText] = useState('');
  const [comparisonText, setComparisonText] = useState('');
  const [interjectInput, setInterjectInput] = useState('');
  const [showReveal, setShowReveal] = useState(false);
  const [view, setView] = useState<'landing' | 'console'>('landing');
  const [showModeMenu, setShowModeMenu] = useState(false);
  const [caseSubmitted, setCaseSubmitted] = useState(false);

  // Toggle transcript view after verdict
  const [showTranscript, setShowTranscript] = useState(true);

  const wsRef = useRef<WebSocket | null>(null);
  const feedEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { 
    feedEndRef.current?.scrollIntoView({ behavior: 'smooth' }); 
  }, [debateFeed, patientFeed]);

  const handleCaseSubmit = () => {
    if (!caseText) return;
    setCaseSubmitted(true);
    if (mode === 'student') {
      setPatientFeed([{ who: 'patient', text: "I'm ready when you are — what would you like to know?" }]);
      setStage('interview');
      return;
    }
    startDebateStream();
  };

  const handlePatientAsk = async () => {
    if (!patientInput.trim()) return;
    const question = patientInput;
    setPatientInput('');

    setPatientFeed(prev => [...prev, { who: 'user', text: question }]);

    try {
      const res = await fetch('http://localhost:8000/patient/respond', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_text: caseText,
          question: question,
          history: patientFeed
        })
      });
      const data = await res.json();
      setPatientFeed(prev => [...prev, { who: 'patient', text: data.response }]);
    } catch (err) {
      console.error("Patient chat error:", err);
      setPatientFeed(prev => [...prev, { who: 'patient', text: "I'm having trouble responding right now." }]);
    }
  };

  const startDebateStream = () => {
    setStage('triage');
    setDebateFeed([]);
    setTriage(null);
    setSelectedAgents([]);
    setVerdictText('');
    setComparisonText('');
    setShowTranscript(true);

    const ws = new WebSocket('ws://localhost:8000/debate/stream');
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({
        case_text: caseText,
        user_diagnosis: sealedDx,
        mode: mode,
      }));
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      console.log("WS MESSAGE:", msg);

      switch (msg.type) {
        case 'triage':
          setTriage({ level: msg.severity, reason: msg.reason });
          break;

        case 'specialists_selected':
          setSelectedAgents(msg.specialists);
          break;

        case 'round_start':
          setStage('debate');
          setDebateFeed(prev => [...prev, { who: 'system', text: `— ROUND ${msg.round} BEGINS —` }]);
          break;

        case 'agent_response':
          setDebateFeed(prev => [...prev, { who: msg.agent, text: msg.response }]);
          break;

        case 'interjection_acknowledged':
          setDebateFeed(prev => [...prev, { who: 'chair', text: msg.response }]);
          break;

        case 'verdict':
          setVerdictText(msg.response);
          break;

        case 'comparison':
          setComparisonText(msg.response);
          break;

        case 'debate_complete':
          setStage('verdict');
          break;

        case 'error':
          console.error("Backend error:", msg.message);
          break;

        default:
          break;
      }
    };

    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
    };

    ws.onclose = () => {
      console.log("WebSocket closed — debate history retained.");
    };
  };

  const handleInterject = () => {
    if (!interjectInput) return;
    const input = interjectInput; 
    setInterjectInput('');
    setDebateFeed(prev => [...prev, { who: 'user', text: input }]);

    fetch('http://localhost:8000/debate/interject', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: 'active',
        interjection: input
      })
    }).catch(err => console.error("Interject error:", err));
  };

  const handleOpenAnalyticsWindow = () => {
    const payload = {
      caseText,
      sealedDx,
      verdictText,
      comparisonText,
      selectedAgents
    };
    localStorage.setItem('aletheia_analytics_data', JSON.stringify(payload));
    window.open('/analytics.html', '_blank', 'width=1200,height=800');
  };

  return (
    <>
      <Sphere />
      <nav>
        <div className="logo">alétheia</div>
        <div className="navlinks">
          <a href="#console" onClick={() => setView('console')}>Console</a>
          <a href="#problem" onClick={() => setView('landing')}>Problem</a>
          <a href="#panel" onClick={() => setView('landing')}>Panel</a>
          <a href="#flow" onClick={() => setView('landing')}>Flow</a>
        </div>
      </nav>

      {view === 'landing' && (
        <>
          <section className="hero">
            <div className="hero-content">
              <div className="eyebrow">ἀλήθεια — the uncovering of truth</div>
              <h1><em>Aletheia</em></h1>
              <p className="sub">Four specialists, a Skeptic, and a Chair debate your case live. Your own diagnosis stays sealed until they reach a verdict — so the comparison means something.</p>
              <div className="hero-cta">
                <button className="btn primary" onClick={() => setView('console')}>Get Started</button>
                <a className="btn ghost" href="#panel">Meet the panel</a>
              </div>
            </div>
          </section>

          <section id="problem" style={{borderTop: '1px solid var(--line)', marginTop: '60px'}}>
            <div className="section-inner" style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '60px'}}>
              <div>
                <div className="eyebrow" style={{marginBottom: '14px'}}>Problem</div>
                <h2 style={{fontSize: '32px', marginBottom: '20px'}}>One doctor, no matter how good, still has blind spots.</h2>
                <p style={{color: 'var(--ink-dim)', lineHeight: '1.7'}}>Doctors often need multiple specialist opinions for complex cases, but multidisciplinary discussions are time-consuming and not always accessible.</p>
              </div>
              <div style={{display: 'flex', flexDirection: 'column', gap: '24px', justifyContent: 'center'}}>
                <div style={{borderLeft: '1px solid var(--line)', paddingLeft: '20px'}}>
                  <div style={{fontFamily: "'Fraunces', serif", fontSize: '40px', color: 'var(--accent)'}}>$100B+</div>
                  <div style={{fontSize: '13px', color: 'var(--ink-faint)', marginTop: '4px'}}>annual cost of diagnostic error, U.S. healthcare system</div>
                </div>
              </div>
            </div>
          </section>

          <section id="panel" style={{borderTop: '1px solid var(--line)', marginTop: '60px'}}>
            <div className="section-inner">
              <div className="eyebrow" style={{marginBottom: '14px'}}>The Panel</div>
              <h2 style={{fontSize: '32px', marginBottom: '40px'}}>Six agents, one debate.</h2>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px'}}>
                <div style={{background: 'var(--panel)', padding: '24px', border: '1px solid var(--line)'}}>
                  <div style={{fontSize: '24px'}}>♥</div><h3 style={{marginTop: '12px'}}>Cardiologist</h3>
                  <p style={{fontSize: '13px', color: 'var(--ink-dim)', marginTop: '8px'}}>Reads the case for cardiac origin first — rhythm, perfusion, structural cause.</p>
                </div>
                <div style={{background: 'var(--panel)', padding: '24px', border: '1px solid var(--line)'}}>
                  <div style={{fontSize: '24px'}}>◐</div><h3 style={{marginTop: '12px'}}>Pulmonologist</h3>
                  <p style={{fontSize: '13px', color: 'var(--ink-dim)', marginTop: '8px'}}>Weighs respiratory explanations against what the cardiologist proposed.</p>
                </div>
                <div style={{background: 'var(--panel)', padding: '24px', border: '1px solid var(--line)'}}>
                  <div style={{fontSize: '24px'}}>✦</div><h3 style={{marginTop: '12px', color: 'var(--accent)'}}>Skeptic</h3>
                  <p style={{fontSize: '13px', color: 'var(--ink-dim)', marginTop: '8px'}}>Challenges every conclusion on the floor. Exists to prevent premature agreement.</p>
                </div>
              </div>
            </div>
          </section>

          <footer style={{padding: '40px 5vw', borderTop: '1px solid var(--line)', display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--ink-faint)'}}>
            <div>alétheia</div>
            <div>A multi-agent clinical reasoning panel concept.</div>
          </footer>
        </>
      )}

      {view === 'console' && (
        <section id="console">
          <div className="chat-shell">
            <div className="chat-top">
              <div className="live-dot">Aletheia console</div>
              <button className="btn ghost" onClick={() => setView('landing')}>← Home</button>
            </div>

            <div className="chat-messages">
              {!caseSubmitted && (
                <div className="chat-placeholder">
                  <div className="pulse-dot"></div>
                  <p>The debate will begin soon.<br/>Describe the case below to assemble the panel.</p>
                </div>
              )}

              {/* STUDENT MODE: PATIENT INTERVIEW STAGE */}
              {stage === 'interview' && (
                <div className="interview-container" style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '30px' }}>
                  <div style={{ padding: '12px 16px', background: 'rgba(59, 130, 246, 0.1)', borderLeft: '3px solid #3b82f6', borderRadius: '4px' }}>
                    <strong style={{ color: '#60a5fa', fontSize: '13px' }}>🎓 Student Interview Mode:</strong>
                    <p style={{ margin: '4px 0 0 0', fontSize: '13px', color: '#d1d5db' }}>
                      Ask the patient targeted clinical questions to gather history. When you are ready to assemble the panel, click <strong>"Submit Case to Panel →"</strong> below.
                    </p>
                  </div>

                  {patientFeed.map((msg, i) => (
                    <div key={i} className={`msg ${msg.who}`} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                      <div className="avatar" style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'var(--panel)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px' }}>
                        {AGENTS[msg.who]?.glyph || '●'}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div className="name" style={{ fontSize: '11px', color: 'var(--ink-faint)', marginBottom: '2px' }}>
                          {AGENTS[msg.who]?.name || 'Patient'}
                        </div>
                        <div className="bubble" style={{ background: 'rgba(255,255,255,0.03)', padding: '10px 14px', borderRadius: '8px', fontSize: '14px', lineHeight: '1.5' }}>
                          <div className="markdown-content">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.text}</ReactMarkdown>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                  <div ref={feedEndRef} />
                </div>
              )}

              {/* 1. TRIAGE & SPECIALIST PANEL HEADER */}
              {(stage === 'triage' || stage === 'debate' || stage === 'verdict') && (
                <>
                  <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
                    <span style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#888', marginRight: '4px' }}>
                      Panel Assembled:
                    </span>
                    {selectedAgents.map(a => (
                      <div 
                        key={a} 
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '6px 14px',
                          backgroundColor: '#1e2025',
                          border: '1px solid #3b82f6',
                          color: '#ffffff',
                          borderRadius: '20px',
                          fontSize: '13px',
                          fontWeight: 600,
                          boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
                        }}
                      >
                        <span style={{ color: '#60a5fa', fontSize: '14px' }}>
                          {AGENTS[a]?.glyph || '•'}
                        </span>
                        <span style={{ color: '#f3f4f6' }}>
                          {AGENTS[a]?.name || a}
                        </span>
                      </div>
                    ))}
                  </div>

                  {triage && (
                    <div className={`triage-banner ${triage.level}`} style={{padding: '12px', background: 'rgba(255,255,255,0.05)', borderLeft: '3px solid var(--accent)', marginBottom: '20px'}}>
                      <div className="lvl" style={{fontWeight: 'bold', fontSize: '12px'}}>{triage.level.toUpperCase()} SEVERITY</div>
                      <p style={{fontSize: '13px', margin: '4px 0 0 0'}}>{triage.reason}</p>
                    </div>
                  )}
                </>
              )}

              {/* 2. FULL DEBATE TRANSCRIPT */}
              {debateFeed.length > 0 && (
                <div 
                  className="debate-feed" 
                  style={{
                    display: (stage === 'verdict' && !showTranscript) ? 'none' : 'flex',
                    flexDirection: 'column', 
                    gap: '16px', 
                    marginBottom: '30px'
                  }}
                >
                  {debateFeed.map((msg, i) => (
                    <div key={i} className={`msg ${msg.who}`} style={{display: 'flex', gap: '12px', alignItems: 'flex-start'}}>
                      <div className="avatar" style={{width: '28px', height: '28px', borderRadius: '50%', background: 'var(--panel)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px'}}>
                        {AGENTS[msg.who]?.glyph || '•'}
                      </div>
                      <div style={{flex: 1}}>
                        <div className="name" style={{fontSize: '11px', color: 'var(--ink-faint)', marginBottom: '2px'}}>
                          {AGENTS[msg.who]?.name || 'System'}
                        </div>
                        <div className="bubble" style={{background: 'rgba(255,255,255,0.03)', padding: '10px 14px', borderRadius: '8px', fontSize: '14px', lineHeight: '1.5'}}>
                          <div className="markdown-content">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                              {msg.text}
                            </ReactMarkdown>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                  <div ref={feedEndRef} />
                </div>
              )}

              {/* 3. FINAL VERDICT & COMPARISON */}
              {stage === 'verdict' && (
                <div className="verdict-container" style={{ marginTop: '24px', display: 'flex', flexDirection: 'column', gap: '20px', borderTop: '1px solid var(--line)', paddingTop: '20px' }}>
                  {verdictText && (
                    <div className="verdict-box" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid var(--accent)', padding: '24px', borderRadius: '8px' }}>
                      <h3 style={{ margin: '0 0 16px 0', color: 'var(--accent)' }}>🏆 Chair Final Verdict</h3>
                      <div className="markdown-content" style={{ fontSize: '14px', lineHeight: '1.6' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {verdictText}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}

                  {showReveal && comparisonText && (
                    <div className="comparison-box" style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--line)', padding: '24px', borderRadius: '8px' }}>
                      <h3 style={{ margin: '0 0 16px 0' }}>📊 Unsealed Comparison</h3>
                      <div className="markdown-content" style={{ fontSize: '14px', lineHeight: '1.6' }}>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {comparisonText}
                        </ReactMarkdown>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* FLOATING CORNER BUTTON TO TOGGLE DEBATE HISTORY AFTER CONCLUSION */}
            {stage === 'verdict' && (
              <button 
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowTranscript(prev => !prev);
                }}
                style={{
                  position: 'fixed',
                  bottom: '80px',
                  right: '30px',
                  backgroundColor: '#1e2025',
                  color: '#ffffff',
                  border: '1px solid var(--accent)',
                  borderRadius: '30px',
                  padding: '10px 18px',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  boxShadow: '0 4px 14px rgba(0,0,0,0.5)',
                  zIndex: 9999,
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  userSelect: 'none'
                }}
              >
                <span style={{ color: 'var(--accent)', fontSize: '14px' }}>💬</span>
                {showTranscript ? 'Hide Debate History' : 'Show Debate History'}
              </button>
            )}

            {/* INPUT FOOTERS FOR EACH STAGE */}
            {!caseSubmitted && (
              <div className="chat-input-bar" style={{ position: 'relative', display: 'flex', gap: '10px', marginTop: '20px' }}>
                <button className="plus-btn" onClick={() => setShowModeMenu(v => !v)} style={{padding: '0 12px'}}>+</button>
                {showModeMenu && (
                  <div className="mode-menu" style={{position: 'absolute', top: '-70px', left: 0, background: 'var(--panel)', border: '1px solid var(--line)', padding: '8px', borderRadius: '6px', zIndex: 10}}>
                    <div style={{cursor: 'pointer', padding: '4px 8px'}} onClick={() => { setMode('doctor'); setShowModeMenu(false); }}>Doctor mode {mode === 'doctor' ? '✓' : ''}</div>
                    <div style={{cursor: 'pointer', padding: '4px 8px'}} onClick={() => { setMode('student'); setShowModeMenu(false); }}>Student mode {mode === 'student' ? '✓' : ''}</div>
                  </div>
                )}
                <div className="chat-input-fields" style={{flex: 1, display: 'flex', flexDirection: 'column', gap: '8px'}}>
                  <textarea className="console-input" value={caseText} onChange={e => setCaseText(e.target.value)} placeholder="Describe the case details..." style={{width: '100%', height: '60px', padding: '8px', background: 'var(--panel)', border: '1px solid var(--line)', color: 'inherit'}} />
                  <input type="text" className="console-input" value={sealedDx} onChange={e => setSealedDx(e.target.value)} placeholder="Your diagnosis — sealed on submit" style={{width: '100%', padding: '8px', background: 'var(--panel)', border: '1px solid var(--line)', color: 'inherit'}} />
                </div>
                <button className="btn primary" onClick={handleCaseSubmit}>Submit</button>
              </div>
            )}

            {stage === 'interview' && (
              <div className="chat-input-bar" style={{ display: 'flex', gap: '10px', marginTop: '20px' }}>
                <input 
                  type="text" 
                  className="console-input" 
                  value={patientInput} 
                  onChange={e => setPatientInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handlePatientAsk()} 
                  placeholder="Ask the patient a question..." 
                  style={{ flex: 1, padding: '10px', background: 'var(--panel)', border: '1px solid var(--line)', color: 'inherit', borderRadius: '6px' }} 
                />
                <button className="btn ghost" onClick={handlePatientAsk}>Ask Patient</button>
                <button className="btn primary" onClick={startDebateStream}>Submit Case to Panel →</button>
              </div>
            )}

            {stage === 'debate' && (
              <div className="chat-input-bar" style={{display: 'flex', gap: '10px', marginTop: '20px'}}>
                <input type="text" className="console-input" value={interjectInput} onChange={e => setInterjectInput(e.target.value)}
                       onKeyDown={e => e.key === 'Enter' && handleInterject()} placeholder="Notice something missing? Interject..." style={{flex: 1, padding: '8px', background: 'var(--panel)', border: '1px solid var(--line)', color: 'inherit'}} />
                <button className="btn ghost" onClick={handleInterject}>Interject</button>
              </div>
            )}

            {stage === 'verdict' && (
              <div className="chat-input-bar" style={{display: 'flex', gap: '10px', marginTop: '20px', flexWrap: 'wrap'}}>
                <button className="btn ghost" onClick={() => { setStage('mode'); setMode('doctor'); setCaseText(''); setSealedDx(''); setDebateFeed([]); setCaseSubmitted(false); setShowReveal(false); }}>
                  Start Over
                </button>
                {!showReveal && (
                  <button className="btn primary" onClick={() => setShowReveal(true)}>
                    Break Seal & Compare
                  </button>
                )}
                {showReveal && (
                  <>
                    <div style={{color: 'var(--ink-dim)', fontSize: '13px', alignSelf: 'center'}}>
                      Sealed Diagnosis: <strong>{sealedDx || 'None'}</strong>
                    </div>
                    <button 
                      className="btn primary" 
                      onClick={handleOpenAnalyticsWindow}
                      style={{
                        marginLeft: 'auto',
                        background: 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)',
                        border: 'none',
                        color: '#fff',
                        fontWeight: 600,
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        cursor: 'pointer'
                      }}
                    >
                      <span>📊</span> Launch Visual Analytics Dashboard
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </section>
      )}
    </>
  );
};

export default App;