"use client";

import React, { useState, useEffect, useRef } from "react";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      sender: "agent",
      content: "## Welcome to the Mall Operations Brain\nOpen the chat cockpit to diagnose tenant performance, draft contextual marketing campaigns, triage structural maintenance issues, or run automated scans for operational anomalies across Elasticsearch indexes.",
      reasoningSteps: [],
      isStreaming: false
    }
  ]);
  const [activeFlow, setActiveFlow] = useState("all");
  const [isGenerating, setIsGenerating] = useState(false);
  const [status, setStatus] = useState("connected");
  const [isReasoningOpen, setIsReasoningOpen] = useState(true);
  
  const feedEndRef = useRef(null);

  // Auto-scroll messages feed to bottom on new updates
  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Suggested Quick Chips
  const quickActions = [
    {
      label: "📈 Performance Diagnosis",
      prompt: "Which stores are underperforming this month vs last month?",
      flow: "performance"
    },
    {
      label: "📣 Draft Weekend Campaign",
      prompt: "Draft a weekend push for the underperforming east wing.",
      flow: "campaign"
    },
    {
      label: "🔧 Maintenance Triage",
      prompt: "Any facility issues that might be hurting the food court sales?",
      flow: "triage"
    }
  ];

  // Helper to format/parse ESQL results cleanly for display
  const formatOutput = (outputStr) => {
    try {
      const parsed = JSON.parse(outputStr);
      if (Array.isArray(parsed) && parsed.length > 0) {
        const headers = Object.keys(parsed[0]);
        return (
          <div className="esql-output-container">
            <div style={{ fontSize: "0.78rem", color: "#53627a", marginBottom: "4px", fontWeight: "600" }}>ESQL Result Table:</div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem", fontFamily: "monospace", color: "#a7f3d0" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.15)" }}>
                  {headers.map(h => <th key={h} style={{ padding: "4px 8px", textAlign: "left" }}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {parsed.slice(0, 5).map((row, idx) => (
                  <tr key={idx} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                    {headers.map(h => <td key={h} style={{ padding: "4px 8px" }}>{String(row[h])}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
            {parsed.length > 5 && <div style={{ fontSize: "0.7rem", color: "#53627a", marginTop: "4px" }}>+ {parsed.length - 5} more records</div>}
          </div>
        );
      }
      return <div className="esql-output-grid">{outputStr}</div>;
    } catch (e) {
      return <div className="esql-output-grid">{outputStr}</div>;
    }
  };

  // Custom regex markdown parser to avoid external node_modules compile issues
  const renderMarkdown = (text) => {
    if (!text) return "";
    
    let html = text;
    
    // Protect checkboxes
    html = html.replace(/- \[\ \]/g, "<li><input type='checkbox' disabled /> ");
    html = html.replace(/- \[x\]/g, "<li><input type='checkbox' checked disabled /> ");
    
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
    
    // Headers
    html = html.replace(/^### (.*?)$/gm, "<h3>$1</h3>");
    html = html.replace(/^## (.*?)$/gm, "<h2>$1</h2>");
    html = html.replace(/^# (.*?)$/gm, "<h1>$1</h1>");
    
    // Tables
    const tableRegex = /\|([\s\S]*?)\|\r?\n\|[ :-|]*?\|\r?\n([\s\S]*?)(?=\r?\n\r?\n|\r?\n[^|]|$)/g;
    html = html.replace(tableRegex, (match) => {
      const lines = match.trim().split("\n");
      const headers = lines[0].split("|").slice(1, -1).map(h => h.trim());
      const rows = lines.slice(2).map(line => line.split("|").slice(1, -1).map(c => c.trim()));
      
      return `<table>
        <thead>
          <tr>${headers.map(h => `<th>${h}</th>`).join("")}</tr>
        </thead>
        <tbody>
          ${rows.map(r => `<tr>${r.map(c => `<td>${c}</td>`).join("")}</tr>`).join("")}
        </tbody>
      </table>`;
    });
    
    // Paragraphs
    html = html.replace(/^(?!<(h1|h2|h3|h4|ul|ol|li|table|thead|tbody|tr|td|th|div|pre|input)).+$/gm, "<p>$&</p>");
    
    return <div className="message-content" dangerouslySetInnerHTML={{ __html: html }} />;
  };

  // Chat Execution Stream Router
  const executeChatStream = async (messageText, flowType = "all") => {
    if (isGenerating) return;
    
    setIsGenerating(true);
    setActiveFlow(flowType);
    
    const userMsgId = "msg-" + Date.now();
    const agentMsgId = "agent-" + Date.now();
    
    // 1. Append User Message
    const newUserMessage = {
      id: userMsgId,
      sender: "user",
      content: messageText,
      reasoningSteps: [],
      isStreaming: false
    };
    
    // 2. Prepare Agent Empty Message Placeholder
    const newAgentMessage = {
      id: agentMsgId,
      sender: "agent",
      content: "",
      reasoningSteps: [],
      isStreaming: true
    };
    
    setMessages((prev) => [...prev, newUserMessage, newAgentMessage]);
    setPrompt("");
    setIsReasoningOpen(true);
    
    try {
      // Establish Connection to FastAPI Server
      const backendUrl = "http://localhost:8000/api/chat";
      const response = await fetch(backendUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: messageText })
      });
      
      if (!response.ok) {
        throw new Error("Failed to load stream from agent server.");
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        // Parse Server-Sent Events (data: ...)
        const lines = buffer.split("\n");
        buffer = lines.pop(); // Keep partial line in buffer
        
        for (const line of lines) {
          const cleanLine = line.trim();
          if (cleanLine.startsWith("data: ")) {
            const dataStr = cleanLine.slice(6);
            try {
              const event = JSON.parse(dataStr);
              
              setMessages((prev) => {
                return prev.map((msg) => {
                  if (msg.id !== agentMsgId) return msg;
                  
                  let updatedReasoning = [...msg.reasoningSteps];
                  let updatedContent = msg.content;
                  
                  if (event.type === "reasoning") {
                    updatedReasoning.push({
                      id: "step-" + Date.now() + "-" + Math.random().toString(36).substring(2, 9),
                      type: "reasoning",
                      description: event.content
                    });
                  } else if (event.type === "tool_call") {
                    updatedReasoning.push({
                      id: "tool-" + Date.now() + "-" + Math.random().toString(36).substring(2, 9),
                      type: "tool_call",
                      tool: event.tool,
                      arguments: event.arguments
                    });
                  } else if (event.type === "tool_result") {
                    // Update the last matching tool call with its output
                    updatedReasoning = updatedReasoning.map((step) => {
                      if (step.type === "tool_call" && step.tool === event.tool && !step.output) {
                        return { ...step, output: event.output };
                      }
                      return step;
                    });
                  } else if (event.type === "final_answer") {
                    updatedContent = event.content;
                  } else if (event.type === "error") {
                    updatedContent += `\n\n*[System Error: ${event.content}]*`;
                  }
                  
                  return {
                    ...msg,
                    content: updatedContent,
                    reasoningSteps: updatedReasoning
                  };
                });
              });
            } catch (err) {
              console.error("Error parsing event stream data", err);
            }
          }
        }
      }
      
    } catch (error) {
      console.error("Streaming error", error);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === agentMsgId 
            ? { ...msg, content: `## ⚠️ Connection Failure\n\nCould not connect to the backend agent server at \`http://localhost:8000\`. Please ensure the FastAPI server is running (\`make start-backend\`).\n\n*(Error detail: ${error.message})*`, isStreaming: false }
            : msg
        )
      );
    } finally {
      setIsGenerating(false);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === agentMsgId ? { ...msg, isStreaming: false } : msg
        )
      );
    }
  };

  // Triggers proactive scan (Flow 4)
  const triggerProactiveScan = async () => {
    await executeChatStream("Run the proactive weekly operational foot traffic anomaly check.", "anomaly");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (prompt.trim()) {
        executeChatStream(prompt);
      }
    }
  };

  return (
    <div className="cockpit-layout">
      {/* Sidebar Navigation */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <span style={{ fontSize: "1.8rem" }}>🧠</span>
          <div className="sidebar-logo">Mall Ops Brain</div>
        </div>

        <nav style={{ flex: 1 }}>
          <div className="nav-section-title">Capabilities</div>
          <button 
            className={`nav-button ${activeFlow === "all" ? "active" : ""}`}
            onClick={() => setActiveFlow("all")}
          >
            <span>💬</span> Operations Terminal
          </button>
          <button 
            className={`nav-button ${activeFlow === "performance" ? "active" : ""}`}
            onClick={() => {
              setPrompt(quickActions[0].prompt);
              setActiveFlow("performance");
            }}
          >
            <span>📊</span> Sales Diagnosis MoM
          </button>
          <button 
            className={`nav-button ${activeFlow === "campaign" ? "active" : ""}`}
            onClick={() => {
              setPrompt(quickActions[1].prompt);
              setActiveFlow("campaign");
            }}
          >
            <span>📣</span> Campaign Composer
          </button>
          <button 
            className={`nav-button ${activeFlow === "triage" ? "active" : ""}`}
            onClick={() => {
              setPrompt(quickActions[2].prompt);
              setActiveFlow("triage");
            }}
          >
            <span>🔧</span> Facility Triage
          </button>

          <div className="nav-section-title" style={{ marginTop: "24px" }}>Customer Portal</div>
          <a 
            href="/customer" 
            className="nav-button"
            style={{ textDecoration: "none", display: "flex", alignItems: "center" }}
          >
            <span>🛍️</span> Shopper Co-Pilot View
          </a>
        </nav>

        {/* Operational Status Display */}
        <div className="status-indicator">
          <div className="status-row" style={{ marginBottom: "8px" }}>
            <span className="status-dot"></span>
            <span style={{ fontWeight: 600, color: "#f1f3f9" }}>Elastic Cloud</span>
          </div>
          <div style={{ fontSize: "0.78rem", color: "var(--text-muted)", marginLeft: "16px" }}>
            Serverless active
          </div>
        </div>
      </aside>

      {/* Main Chat Cockpit */}
      <main className="main-chat-container">
        <header className="chat-header">
          <div>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 700 }}>Real-time Operations Feed</h1>
            <p style={{ fontSize: "0.82rem", color: "var(--text-secondary)" }}>Reasoning across Foot-Traffic, Sales, Maintenance, & Marketing</p>
          </div>
          <button className="scan-trigger-btn" onClick={triggerProactiveScan} disabled={isGenerating}>
            <span>⚡</span> Scheduled Audit Scan
          </button>
        </header>

        {/* Message Logs Feed */}
        <div className="messages-feed">
          {messages.map((msg, index) => (
            <div key={msg.id} className={`message-bubble glass-panel ${msg.sender}`}>
              <span className="sender-tag">{msg.sender === "user" ? "Mall Manager" : "Ops Brain Agent"}</span>
              
              {/* Reasoning Drawer if there are thinking steps */}
              {msg.sender === "agent" && msg.reasoningSteps.length > 0 && (
                <div className="reasoning-drawer">
                  <div 
                    className="reasoning-toggle"
                    onClick={() => setIsReasoningOpen(!isReasoningOpen)}
                  >
                    <div className="reasoning-header-text">
                      <span>🧠</span> {msg.isStreaming ? "Thinking Process..." : "Reasoning Sequence Traced"}
                      {msg.isStreaming && (
                        <span className="pulse-loader">
                          <span className="pulse-dot"></span>
                          <span className="pulse-dot"></span>
                          <span className="pulse-dot"></span>
                        </span>
                      )}
                    </div>
                    <span className={`reasoning-chevron ${isReasoningOpen ? "open" : ""}`}>▼</span>
                  </div>

                  {isReasoningOpen && (
                    <div className="reasoning-steps-list">
                      {msg.reasoningSteps.map((step, idx) => (
                        <div key={step.id || idx} className="reasoning-step-item">
                          <div className={`step-bullet ${step.output ? "success" : ""}`}>
                            {step.type === "tool_call" ? "⚒️" : "✓"}
                          </div>
                          <div className="step-details">
                            {step.type === "reasoning" && (
                              <div className="step-desc">{step.description}</div>
                            )}
                            {step.type === "tool_call" && (
                              <>
                                <div className="step-desc" style={{ color: "#93c5fd", fontWeight: 600 }}>
                                  Called Tool: <span style={{ fontFamily: "monospace" }}>{step.tool}</span>
                                </div>
                                {step.arguments?.query && (
                                  <pre className="esql-code-block">{step.arguments.query}</pre>
                                )}
                                {step.arguments?.query_text && (
                                  <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                                    Semantic Term: <strong style={{ color: "#f1f3f9" }}>"{step.arguments.query_text}"</strong>
                                    {step.arguments.zone && ` in ${step.arguments.zone}`}
                                  </div>
                                )}
                              </>
                            )}
                            {step.type === "tool_call" && step.output && (
                              <div style={{ marginTop: "6px" }}>
                                {formatOutput(step.output)}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Message Markdown Content */}
              {msg.content ? (
                renderMarkdown(msg.content)
              ) : (
                msg.isStreaming && (
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--text-secondary)", fontSize: "0.9rem" }}>
                    Formatting Actionable Report
                    <span className="pulse-loader">
                      <span className="pulse-dot"></span>
                      <span className="pulse-dot"></span>
                      <span className="pulse-dot"></span>
                    </span>
                  </div>
                )
              )}
            </div>
          ))}
          <div ref={feedEndRef} />
        </div>

        {/* Input & Suggested Chips Panel */}
        <div className="chat-input-area">
          <div className="suggested-chips">
            {quickActions.map((act, idx) => (
              <button 
                key={idx} 
                className="chip"
                onClick={() => {
                  setPrompt(act.prompt);
                  executeChatStream(act.prompt, act.flow);
                }}
                disabled={isGenerating}
              >
                {act.label}
              </button>
            ))}
          </div>

          <div className="input-row">
            <textarea
              className="chat-textarea"
              placeholder="Ask operations question (e.g. 'MoM performance report' or 'draft weekend push')..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isGenerating}
            />
            <button 
              className="send-btn"
              onClick={() => {
                if (prompt.trim()) {
                  executeChatStream(prompt);
                }
              }}
              disabled={isGenerating || !prompt.trim()}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" />
              </svg>
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
