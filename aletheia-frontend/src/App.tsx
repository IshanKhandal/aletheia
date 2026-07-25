import React, { useState, useEffect, useRef } from 'react';
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
  const [mode, setMode] = useState<'doctor'|'student'|null>(null);
  
  const [caseText, setCaseText] = useState('');
  const [sealedDx, setSealedDx] = useState('');
  const [patientFeed, setPatientFeed] = useState<Message[]>([]);
  const [patientInput, setPatientInput] = useState('');
  
  const [selectedAgents, setSelectedAgents] = useState<string[]>([]);
  const [triage, setTriage] = useState<{level: string, reason: string} | null>(null);
  
  const [debateFeed, setDebateFeed] = useState<Message[]>([]);
  const [debateQueue, setDebateQueue] = useState<Message[]>([]);
  const [round1Queue, setRound1Queue] = useState<Message[]>([]);
  const [round2Queue, setRound2Queue] = useState<Message[]>([]);
  const [currentRound, setCurrentRound] = useState(1);
  const [verdictText, setVerdictText] = useState('');
  const [isDebateDone, setIsDebateDone] = useState(false);
  const [interjectInput, setInterjectInput] = useState('');
  const [showReveal, setShowReveal] = useState(false);
  const [debateLog, setDebateLog] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const [comparisonText, setComparisonText] = useState('');

  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const feedEndRef = useRef<HTMLDivElement>(null);
  const debateFeedRef = useRef<HTMLDivElement>(null);

 useEffect(() => { feedEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [debateFeed, patientFeed]);
  const generateDebateData = (agents: string[]) => {
    const a1 = agents[0] || 'cardiologist'; const a2 = agents[1] || 'pulmonologist';
    const a3 = agents[2] || 'id'; const a4 = agents[3] || 'neurologist';
    return {
      round1: [
        { who: a1, text: `Based on the initial presentation, my primary concern highlights acute risks in my domain. I'd strongly advocate for immediate baseline diagnostics here before we start prematurely anchoring.` },
        { who: a2, text: `I see your point, ${AGENTS[a1].name}. However, looking at the vitals, we have to consider overlapping pathologies. My primary differential focuses on ruling out a life-threatening systemic issue.` },
        { who: a3, text: `Let's not narrow down too quickly. From my specialty's perspective, there are several "can't-miss" diagnoses that could present exactly like this.` },
        { who: a4, text: `We need to be cautious about attributing these symptoms purely to one system. Transient or atypical presentations often masquerade behind vague signs.` },
        { who: 'skeptic', text: `Hold on. You are all throwing a lot of high-end diagnostics at this immediately. Are we ignoring a simpler, benign explanation? Let's verify the exact timeline of symptoms.` }
      ],
      round2: [
        { who: a1, text: `Okay, if we want to avoid shotgun testing based on the Skeptic's challenge, I propose a tiered diagnostic approach. We secure the fast, cheap, non-invasive tests first.` },
        { who: a4, text: `I support that. We can gate the more complex imaging or invasive procedures behind the results of that first tier.` },
        { who: 'skeptic', text: `This is a much more reasoned approach. Tiered diagnostics based on risk stratification rather than shotgun testing. I am satisfied.` }
      ],
      verdict: `After two rounds of multi-specialist deliberation, the panel has reached a consensus on a tiered diagnostic approach. Initial non-invasive screens will lead; further advanced imaging or empiric treatments will be gated behind those initial results.`
    };
  };

  const handleCaseSubmit = () => {
  if (!caseText) return;
  if (mode === 'student') {
    setPatientFeed([{ who: 'patient', text: "I'm ready when you are — what would you like to know?" }]);
    setStage('interview');
    return;
   }
   startDebateStream();
  };

  const processTriageAndSelection = async () => {
  try {
    const res = await fetch('http://localhost:8000/debate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        case_text: caseText,
        user_diagnosis: sealedDx,
        mode: mode,
      })
    });
    const data = await res.json();
    console.log("BACKEND RESPONSE:", data); // keep this for now, check the shape

    setTriage({ level: data.triage?.level || 'routine', reason: data.triage?.reason || '' });
    setSelectedAgents(data.selected_specialists || []);
    setDebateLog(data.debate_log || []);
    setVerdictText(data.final_verdict || '');
    setStage('triage');
   } catch (err) {
    console.error("Debate Fetch Error:", err);
     }
  };

  useEffect(() => {
    if (stage === 'debate' && debateQueue.length > 0) {
      timerRef.current = setTimeout(() => {
        setDebateFeed(prev => [...prev, debateQueue[0]]);
        setDebateQueue(prev => prev.slice(1));
      }, 1500);
    }
    return () => { if(timerRef.current) clearTimeout(timerRef.current); };
  }, [debateQueue, stage]);

  const startDebateStream = () => {
  setStage('triage');
  setDebateFeed([]);
  setTriage(null);
  setSelectedAgents([]);

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
        if (msg.round === 1) {
          setDebateFeed(prev => [...prev, { who: 'system', text: `— ROUND 1 BEGINS —` }]);
          // stay on triage stage — user clicks the button below to proceed
        } else {
          setDebateFeed(prev => [...prev, { who: 'system', text: `— ROUND ${msg.round} BEGINS —` }]);
          setStage('debate');
        }
        break;

      case 'agent_response':
        setDebateFeed(prev => [...prev, { who: msg.agent, text: msg.response }]);
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
        break; // status/agent_thinking messages, ignore or use for a "typing..." indicator later
    }
  };

  ws.onerror = (err) => {
    console.error("WebSocket error:", err);
  };

  ws.onclose = () => {
    console.log("WebSocket closed");
  };
};

  const handleInterject = () => {
    if (!interjectInput || isDebateDone) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    const input = interjectInput; setInterjectInput('');
    setDebateFeed(prev => [...prev, { who: 'user', text: input }]);
    setTimeout(() => {
      setDebateFeed(prev => [...prev, { who: 'chair', text: "Noted — factoring that mid-debate interjection into the discussion." }]);
      setDebateQueue(prev => [...prev]); 
    }, 1000);
  };

  return (
    <>
      <Sphere />
      <nav>
        <div className="logo">alétheia</div>
        <div className="navlinks">
          <a href="#console">Console</a>
          <a href="#problem">Problem</a>
          <a href="#panel">Panel</a>
          <a href="#flow">Flow</a>
        </div>
      </nav>

      <section className="hero">
        <div className="hero-content">
          <div className="eyebrow">ἀλήθεια — the uncovering of truth</div>
          <h1><em>Aletheia</em></h1>
          <p className="sub">Four specialists, a Skeptic, and a Chair debate your case live. Your own diagnosis stays sealed until they reach a verdict — so the comparison means something.</p>
          <div className="hero-cta">
            <a className="btn primary" href="#console">Run a case</a>
            <a className="btn ghost" href="#panel">Meet the panel</a>
          </div>
        </div>
      </section>

      <section id="console">
        <div className="section-inner">
          <div className="console-shell">
            <div className="console-top"><div className="live-dot">Aletheia console</div></div>
            <div className="console-body">
              
              {stage === 'mode' && (
                <div>
                  <div className="field-label">Choose a mode</div>
                  <div className="mode-select">
                    <div className={`mode-opt ${mode === 'doctor' ? 'active' : ''}`} onClick={() => setMode('doctor')}>
                      <div className="tag">Doctor mode</div>
                      <h3>Full case, straight in</h3>
                      <p>Submit the complete case directly. Triage and the panel see everything at once.</p>
                    </div>
                    <div className={`mode-opt ${mode === 'student' ? 'active' : ''}`} onClick={() => setMode('student')}>
                      <div className="tag">Student mode</div>
                      <h3>History-taking first</h3>
                      <p>Interview the Patient Agent yourself to build the history before the panel sees the case.</p>
                    </div>
                  </div>
                  <div className="console-actions"><button className="btn primary" disabled={!mode} onClick={() => setStage('case')}>Continue</button></div>
                </div>
              )}

              {stage === 'case' && (
                <div>
                  <div className="field-label">Case file</div>
                  <textarea className="console-input" value={caseText} onChange={e => setCaseText(e.target.value)} placeholder="Describe the case details..." />
                  <div className="field-label">Your diagnosis — sealed on submit</div>
                  <input type="text" className="console-input" value={sealedDx} onChange={e => setSealedDx(e.target.value)} placeholder="What do you think this is?" />
                  <div className="console-actions"><button className="btn primary" onClick={handleCaseSubmit}>Submit case</button></div>
                </div>
              )}

              {stage === 'interview' && (
                <div>
                  <div className="field-label">Chief complaint</div>
                  <p style={{marginBottom:'18px'}}>{caseText.split('.')[0]}...</p>
                  <div className="patient-panel">
                    <div className="patient-feed">
                      {patientFeed.map((m, i) => (
                        <div key={i} className={`p-msg ${m.who === 'You' ? 'q' : 'a'}`}>
                          <span className="who">{m.who}</span>{m.text}
                        </div>
                      ))}
                      <div ref={feedEndRef} />
                    </div>
                    <div className="patient-ask">
                      <input type="text" className="console-input" value={patientInput} onChange={e => setPatientInput(e.target.value)} 
                             onKeyDown={e => e.key === 'Enter' && setPatientInput('')} placeholder="Ask the patient..." />
                      <button className="btn primary" onClick={() => setPatientInput('')}>Ask</button>
                    </div>
                  </div>
                  <div className="console-actions"><button className="btn primary" onClick={processTriageAndSelection}>Proceed to Triage</button></div>
                </div>
              )}

              {stage === 'triage' && (
                <div>
                  <div className="field-label">Panel Assembled</div>
                  <div className="case-bank" style={{marginBottom: '20px'}}>{selectedAgents.map(a => <div key={a} className="case-chip active">{AGENTS[a]?.name || a}</div>)}</div>
                  <div className="field-label">Independent Triage Assessment</div>
                  <div className={`triage-banner ${triage?.level}`}><div className="lvl">{triage?.level.toUpperCase()}</div><p>{triage?.reason}</p></div>
                  <div className="console-actions">
                    <button className="btn primary" disabled={selectedAgents.length === 0} onClick={() => setStage('debate')}>
                      Begin panel debate
                    </button>
                  </div>
                </div>
              )}

              {stage === 'debate' && (
                <div>
                  <div className="debate-feed" ref={debateFeedRef}>
                    {debateFeed.map((msg, i) => (
                      <div key={i} className={`msg ${msg.who}`}>
                        <div className="avatar">{AGENTS[msg.who]?.glyph || '•'}</div>
                        <div><div className="name">{AGENTS[msg.who]?.name || 'System'}</div><div className="bubble">{msg.text}</div></div>
                      </div>
                    ))}
                    <div ref={feedEndRef} />
                  </div>
                  {debateQueue.length === 0 && (
                    <div className="console-actions" style={{ borderTop: '1px solid var(--line)', paddingTop: '20px' }}>
                      {currentRound === 1 ? (
                        <button className="btn primary" onClick={() => { setCurrentRound(2); setDebateQueue(round2Queue); }}>Proceed to Round 2</button>
                      ) : (
                        <button className="btn primary" onClick={() => { setIsDebateDone(true); setStage('verdict'); }}>Proceed to Verdict</button>
                      )}
                    </div>
                  )}
                  <div className="interject-bar">
                    <input type="text" className="console-input" value={interjectInput} onChange={e => setInterjectInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && handleInterject()} disabled={isDebateDone} placeholder="Notice something missing? Interject..."/>
                    <button className="btn ghost" disabled={isDebateDone} onClick={handleInterject}>Interject</button>
                  </div>
                </div>
              )}

              {stage === 'verdict' && (
                <div>
                  <div className="verdict-box"><p>{verdictText}</p></div>
                  <div className="console-actions">
                    <button className="btn ghost" onClick={() => { setStage('mode'); setMode(null); setCaseText(''); setDebateFeed([]); setShowReveal(false); }}>Start Over</button>
                    {!showReveal && <button className="btn primary" onClick={() => setShowReveal(true)}>Break Seal</button>}
                  </div>
                  {showReveal && (
                    <div className="reveal-box">
                      <div className="reveal-row"><div className="k">Your Seal</div><div className="v">{sealedDx || 'None'}</div></div>
                    </div>
                  )}
                </div>
              )}

            </div>
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

      <section id="flow" style={{borderTop: '1px solid var(--line)', marginTop: '60px', paddingBottom: '120px'}}>
        <div className="section-inner">
          <div className="eyebrow" style={{marginBottom: '14px'}}>How a case moves</div>
          <h2 style={{fontSize: '32px', marginBottom: '40px'}}>Sealed first. Debated blind. Compared last.</h2>
          <div style={{display: 'flex', flexDirection: 'column', gap: '16px'}}>
            <div style={{display: 'grid', gridTemplateColumns: '60px 1fr', padding: '20px 0', borderBottom: '1px solid var(--line)'}}>
              <div style={{fontFamily: 'monospace', color: 'var(--ink-faint)'}}>01</div>
              <div><h3>Submit the case</h3><p style={{color: 'var(--ink-dim)', marginTop: '4px'}}>Your attached diagnosis is sealed immediately — invisible to the panel until a verdict is earned.</p></div>
            </div>
            <div style={{display: 'grid', gridTemplateColumns: '60px 1fr', padding: '20px 0', borderBottom: '1px solid var(--line)'}}>
              <div style={{fontFamily: 'monospace', color: 'var(--ink-faint)'}}>02</div>
              <div><h3>The panel debates, live</h3><p style={{color: 'var(--ink-dim)', marginTop: '4px'}}>Specialists and the Skeptic argue round by round, streaming live directly to your console monitor.</p></div>
            </div>
          </div>
        </div>
      </section>

      <footer style={{padding: '40px 5vw', borderTop: '1px solid var(--line)', display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: 'var(--ink-faint)'}}>
        <div>alétheia</div>
        <div>A multi-agent clinical reasoning panel concept.</div>
      </footer>
    </>
  );
};

export default App;