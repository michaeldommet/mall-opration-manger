"use client";

import React, { useState, useEffect, useRef } from "react";

export default function CustomerCockpit() {
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState([
    {
      id: "welcome",
      sender: "agent",
      content: "## Welcome, Shopper! 🛍️\n\nI am your **Shopper Personal Co-Pilot**.\n\nTell me what you'd like to do today (e.g., *'buy shoes, eat sushi, and get coffee'*) and how much time you have (e.g., *'3 hours'*), and I will calculate a backtrack-free, time-optimized physical walking itinerary including floor transits and active mall promotions!",
      reasoningSteps: [],
      isStreaming: false
    }
  ]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isReasoningOpen, setIsReasoningOpen] = useState(false);
  const [activePromotionPrompt, setActivePromotionPrompt] = useState(null);

  // Widescreen Entrance Kiosk Mode state
  const [isMobilePreview, setIsMobilePreview] = useState(false);
  const [selectedFloorFilter, setSelectedFloorFilter] = useState("all");
  const [storeSearchQuery, setStoreSearchQuery] = useState("");
  const [selectedKioskStore, setSelectedKioskStore] = useState(null);
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);

  const mallStores = [
    { name: "SneakerVault", floor: "Floor 1", zone: "EAST-WING", category: "Apparel", desc: "Premium sneaker boutique featuring retro releases." },
    { name: "Sushi Express", floor: "Floor 1", zone: "FOOD-COURT", category: "Dining", desc: "Fresh sushi rolls, sashimi, and classic Japanese dishes." },
    { name: "Café Bloom", floor: "Floor 1", zone: "FOOD-COURT", category: "Dining", desc: "Specialty coffee, organic teas, and freshly baked pastries." },
    { name: "TechZone", floor: "Floor 2", zone: "ELECTRONICS-WING", category: "Electronics", desc: "Latest smartphones, laptops, smart home tech, and accessories." },
    { name: "ByteShop", floor: "Floor 2", zone: "ELECTRONICS-WING", category: "Electronics", desc: "Expert computer components and high-performance gaming rigs." },
    { name: "StyleCraft", floor: "Floor 1", zone: "FASHION-DISTRICT", category: "Apparel", desc: "Custom tailored menswear and premium accessories." },
    { name: "FashionHub", floor: "Floor 1", zone: "FASHION-DISTRICT", category: "Apparel", desc: "Trendy streetwear and modern wardrobe essentials." },
    { name: "Urban Threads", floor: "Floor 1", zone: "EAST-WING", category: "Apparel", desc: "Eco-friendly fabrics and contemporary casualwear." },
    { name: "Pizza Palace", floor: "Floor 1", zone: "FOOD-COURT", category: "Dining", desc: "Gourmet wood-fired pizzas and fresh Italian pasta." },
    { name: "Burger Barn", floor: "Floor 1", zone: "FOOD-COURT", category: "Dining", desc: "Flame-grilled artisan burgers and hand-cut fries." },
    { name: "HomeStyle", floor: "Floor 1", zone: "WEST-WING", category: "Apparel", desc: "Modern home decor, textile accents, and furniture." },
    { name: "BookNook", floor: "Floor 1", zone: "WEST-WING", category: "Apparel", desc: "Curated novels, local literature, and cozy reading corners." },
    { name: "GlamCuts Salon", floor: "Floor 3", zone: "SERVICES-HUB", category: "Services", desc: "Full-service luxury hair styling and aesthetic treatments." },
    { name: "QuickFix Phones", floor: "Floor 3", zone: "SERVICES-HUB", category: "Services", desc: "Immediate screen repairs and battery diagnostics." },
    { name: "Entrance A", floor: "Floor 0", zone: "ENTRANCE-A", category: "Transit", desc: "East entrance portal situated on the ground level." },
    { name: "Entrance B", floor: "Floor 0", zone: "ENTRANCE-B", category: "Transit", desc: "West entrance portal situated on the ground level." },
    { name: "Entrance C", floor: "Floor 0", zone: "ENTRANCE-C", category: "Transit", desc: "North entrance portal situated on the ground level." },
    { name: "Parking A", floor: "Floor -1", zone: "PARKING-A", category: "Transit", desc: "Underground parking hub with EV charging stalls." }
  ];

  const [storesList, setStoresList] = useState(mallStores);

  const storeCoordinates = {
    "SneakerVault": { top: "30%", left: "70%" },
    "Sushi Express": { top: "55%", left: "45%" },
    "Café Bloom": { top: "50%", left: "40%" },
    "TechZone": { top: "25%", left: "60%" },
    "ByteShop": { top: "22%", left: "55%" },
    "StyleCraft": { top: "60%", left: "65%" },
    "FashionHub": { top: "58%", left: "68%" },
    "Urban Threads": { top: "32%", left: "73%" },
    "Pizza Palace": { top: "52%", left: "48%" },
    "Burger Barn": { top: "56%", left: "50%" },
    "HomeStyle": { top: "40%", left: "30%" },
    "BookNook": { top: "42%", left: "28%" },
    "GlamCuts Salon": { top: "15%", left: "50%" },
    "QuickFix Phones": { top: "18%", left: "48%" },
    "Entrance A": { top: "70%", left: "50%" },
    "Entrance B": { top: "72%", left: "35%" },
    "Entrance C": { top: "68%", left: "65%" },
    "Parking A": { top: "85%", left: "45%" }
  };

  const mallHappenings = [
    {
      id: "happening-1",
      type: "event",
      badge: "🎨 Art & Craft",
      title: "Spring Artisan Market",
      desc: "Local crafts, handmade jewelry, and organic food stalls in the Central Atrium.",
      time: "Today, 10:00 AM - 8:00 PM",
      location: "📍 Central Atrium (Floor 1)",
      store: "Café Bloom",
      actionLabel: "🧭 Route to Atrium",
      prompt: "Plan a walking itinerary starting from Entrance A to Café Bloom to visit the Spring Artisan Market in the Central Atrium"
    },
    {
      id: "happening-2",
      type: "promo",
      badge: "⚡ Flash Promo",
      title: "Café Bloom: Pastry Happy Hour",
      desc: "Get an exclusive free organic pastry with any Large Latte purchase.",
      time: "1:00 PM - 4:00 PM Daily",
      location: "📍 Food Court (Floor 1)",
      store: "Café Bloom",
      actionLabel: "🎟️ Claim BOGO Pastry",
      prompt: "Activate customer coupon for Store: **Café Bloom** and Discount: **Free Pastry w/ Large Latte**"
    },
    {
      id: "happening-3",
      type: "music",
      badge: "🎷 Live Music",
      title: "Sunset Jazz Concert",
      desc: "Enjoy smooth contemporary jazz tunes while dining at the Food Court.",
      time: "Tonight, 6:00 PM - 9:00 PM",
      location: "📍 Food Court (Floor 1)",
      store: "Sushi Express",
      actionLabel: "🧭 Plan Dinner Route",
      prompt: "Plan a 90-minute dining stop at Sushi Express including the BOGO Roll deal while enjoying the Sunset Jazz Concert"
    },
    {
      id: "happening-4",
      type: "promo",
      badge: "🎁 Seasonal Sale",
      title: "SneakerVault Retro Weekend",
      desc: "Get an exclusive 20% off all vintage and retro sneakers releases.",
      time: "This Friday - Sunday",
      location: "📍 East-Wing (Floor 1)",
      store: "SneakerVault",
      actionLabel: "👟 View Retro Deals",
      prompt: "Check SneakerVault deals, activate coupon, and plan a shopping stop"
    }
  ];

  useEffect(() => {
    const fetchStores = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/stores");
        if (response.ok) {
          const data = await response.json();
          if (data && data.stores && data.stores.length > 0) {
            setStoresList(data.stores);
          }
        }
      } catch (err) {
        console.error("Failed to fetch dynamic stores from backend api", err);
      }
    };
    fetchStores();
  }, []);

  // Live debounced search API integration with local fallback
  useEffect(() => {
    const q = storeSearchQuery.trim();
    if (!q) {
      setSearchResults(null);
      return;
    }

    const delayDebounceFn = setTimeout(async () => {
      setIsSearching(true);
      try {
        const floorParam = selectedFloorFilter !== "all" ? selectedFloorFilter : "";
        const url = `http://localhost:8000/api/search?q=${encodeURIComponent(q)}&floor=${floorParam}`;
        const response = await fetch(url);
        if (response.ok) {
          const data = await response.json();
          if (data && data.stores) {
            setSearchResults(data.stores);
          }
        }
      } catch (err) {
        console.error("Failed to fetch hybrid search results from backend", err);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [storeSearchQuery, selectedFloorFilter]);

  // If live search results are active, display them; otherwise, compute locally from static or dynamically fetched storesList
  const filteredStores = searchResults !== null ? searchResults : storesList.filter((store) => {
    const matchesFloor = selectedFloorFilter === "all" || 
                         store.floor === `Floor ${selectedFloorFilter}` || 
                         (selectedFloorFilter === "-1" && store.floor.toLowerCase().includes("parking"));
    
    const q = storeSearchQuery.toLowerCase().trim();
    const matchesSearch = q === "" ||
                          store.name.toLowerCase().includes(q) ||
                          store.category.toLowerCase().includes(q) ||
                          store.desc.toLowerCase().includes(q) ||
                          store.zone.toLowerCase().includes(q);
                          
    return matchesFloor && matchesSearch;
  });

  const feedEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Premium Custom Promotions
  const featuredPromotions = [
    {
      id: "promo-1",
      store: "SneakerVault",
      badge: "👟 Shoe Deal",
      discount: "20% OFF Retro Styles",
      copy: "Redeem on Floor 1, East-Wing. Walk-in only.",
      prompt: "Tell me more about the SneakerVault 20% off promotion and draft a route there from Entrance A"
    },
    {
      id: "promo-2",
      store: "Sushi Express",
      badge: "🍣 Dining Deal",
      discount: "Buy 1 Get 1 Roll Active",
      copy: "Redeem on Floor 1, Food Court. Valid 11AM-3PM.",
      prompt: "Show me the Sushi Express BOGO deal details and add it to a dining stop"
    },
    {
      id: "promo-3",
      store: "Café Bloom",
      badge: "☕ Beverage Deal",
      discount: "Free Pastry w/ Large Latte",
      copy: "Redeem on Floor 1, Food Court. Great for breaks!",
      prompt: "Plan a coffee break at Cafe Bloom utilizing the free pastry discount"
    },
    {
      id: "promo-4",
      store: "TechZone",
      badge: "💻 Electronics Special",
      discount: "Up to $100 Trade-In Credit",
      copy: "Redeem on Floor 2, Electronics-Wing. Phone diagnostic free.",
      prompt: "Check TechZone promotions and coordinate a visit to get my phone screen repaired nearby"
    }
  ];

  // Quick Action Chips
  const quickActions = [
    {
      label: "🧭 Plan 3hr Shopping Trip",
      prompt: "Plan a 3-hour shopping trip: buy shoes at SneakerVault, eat sushi, get coffee. I'm starting at Entrance A."
    },
    {
      label: "🏷️ Active Promotions today",
      prompt: "What are the most attractive active customer promotions and coupons running today across the stores?"
    },
    {
      label: "🗺️ Path from Entrance A to Floor 2",
      prompt: "How do I get to TechZone on Floor 2 starting from Entrance A? Please show me the walking distance and floor transit time."
    },
    {
      label: "💇 Haircut & Coffee Break (1.5hr)",
      prompt: "I have 90 minutes. I need a quick haircut at GlamCuts Salon and a fast coffee break. Plan my schedule."
    }
  ];

  // Helper to parse markdown itinerary table into a structured JSON array
  const parseItineraryTable = (text) => {
    if (!text) return null;
    const lines = text.split("\n");
    // Find lines that represent table rows starting and ending with |
    const tableRows = lines.filter(line => line.trim().startsWith("|") && line.trim().endsWith("|"));
    if (tableRows.length < 3) return null; // Needs header, divider line, and at least one data row
    
    // Check if the headers look like our itinerary columns
    const headerLine = tableRows[0].toLowerCase();
    if (!headerLine.includes("time slot") && !headerLine.includes("floor") && !headerLine.includes("activity")) {
      return null;
    }
    
    const steps = [];
    // Index 0 is Header, Index 1 is Divider |---|---|
    for (let i = 2; i < tableRows.length; i++) {
      const cells = tableRows[i]
        .split("|")
        .map(c => c.trim())
        .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1);
      
      if (cells.length >= 4) {
        steps.push({
          time: cells[0] || "",
          floor: cells[1] || "",
          zone: cells[2] || "",
          activity: cells[3] || "",
          duration: cells[4] || "",
          transit: cells[5] || "",
          notes: cells[6] || ""
        });
      }
    }
    
    return steps.length > 0 ? steps : null;
  };

  // Helper to extract coupon details from text
  const extractCouponDetails = (text) => {
    if (!text) return null;
    const tokenMatch = text.match(/\b([A-Z]{2}-[A-Z0-9]{2,6}-[A-Z0-9]{4})\b/);
    if (!tokenMatch) return null;
    
    const token = tokenMatch[1];
    
    // Try to parse store name
    let storeName = "MALL PROMO";
    const storeMatch = text.match(/Store:?\s*\*\*?([^\*\-\n\.\,]+)\*\*?/i);
    if (storeMatch) {
      storeName = storeMatch[1].trim();
    } else {
      const storeVaultMatch = text.match(/([a-zA-Z\s]+)\s+(?:deal|coupon|promotion|discount)/i);
      if (storeVaultMatch && !storeVaultMatch[1].toLowerCase().includes("activate")) {
        storeName = storeVaultMatch[1].trim();
      }
    }
    
    // Try to parse discount
    let discountDesc = "Exclusive Digital Discount";
    const discountMatch = text.match(/Discount:?\s*\*\*?([^\*\n]+)\*\*?/i);
    if (discountMatch) {
      discountDesc = discountMatch[1].trim();
    } else {
      const descMatch = text.match(/(?:details|desc|deal):?\s*\*\*?([^\*\n\-\.]+)\*\*?/i);
      if (descMatch) {
        discountDesc = descMatch[1].trim();
      }
    }
    
    return { token, storeName, discountDesc };
  };

  // Inline VIP Coupon Component
  const CouponTicket = ({ token, storeName, discountDesc }) => {
    return (
      <div className="coupon-ticket-wrapper">
        <div className="coupon-ticket-body">
          {/* Ticket Header */}
          <div className="coupon-ticket-header">
            <div className="coupon-ticket-store">{storeName}</div>
            <div className="coupon-ticket-badge">VIP ACTIVE</div>
          </div>
          
          {/* Discount Details */}
          <div className="coupon-ticket-details">
            <div className="coupon-ticket-discount">{discountDesc}</div>
            <div className="coupon-ticket-token-label">SECURE CHECKOUT CODE</div>
            <div className="coupon-ticket-token-code">{token}</div>
          </div>

          {/* Dashed Tear Line */}
          <div className="coupon-ticket-divider">
            <div className="divider-circle left"></div>
            <div className="divider-dashed-line"></div>
            <div className="divider-circle right"></div>
          </div>

          {/* Barcode Area */}
          <div className="coupon-ticket-barcode-container">
            <div className="glowing-red-scanline"></div>
            <div className="barcode-bars">
              {[2, 1, 3, 1, 2, 4, 1, 3, 2, 1, 2, 3, 1, 4, 2, 1, 3, 1, 2, 2, 1, 3, 2, 1, 3, 1, 2, 4, 1, 2].map((w, i) => (
                <div 
                  key={i} 
                  className="barcode-bar" 
                  style={{ 
                    width: `${w}px`, 
                    height: "32px", 
                    backgroundColor: "#ffffff", 
                    marginRight: "1px",
                    opacity: i % 4 === 0 ? 0.3 : 0.85
                  }} 
                />
              ))}
            </div>
            <div className="barcode-token-text">{token}</div>
          </div>
          
          <div className="coupon-ticket-footer">
            <span>⚡ SCAN AT REGISTER</span>
            <span>VALID FOR 24H</span>
          </div>
        </div>
      </div>
    );
  };

  // Maps an activity name to a corresponding visual emoji
  const getActivityEmoji = (activity) => {
    const act = activity.toLowerCase();
    if (act.includes("sneakervault") || act.includes("shoe")) return "👟";
    if (act.includes("sushi") || act.includes("japanese")) return "🍣";
    if (act.includes("caf") || act.includes("coffee") || act.includes("bloom")) return "☕";
    if (act.includes("burger")) return "🍔";
    if (act.includes("pizza")) return "🍕";
    if (act.includes("techzone") || act.includes("byteshop") || act.includes("phone") || act.includes("laptop")) return "💻";
    if (act.includes("glamcuts") || act.includes("salon") || act.includes("haircut")) return "💇";
    if (act.includes("quickfix")) return "🔧";
    if (act.includes("booknook") || act.includes("book") || act.includes("read")) return "📚";
    if (act.includes("homestyle") || act.includes("furniture")) return "🏠";
    if (act.includes("parking") || act.includes("car")) return "🚗";
    if (act.includes("entrance")) return "🚪";
    if (act.includes("fashionhub") || act.includes("stylecraft") || act.includes("apparel") || act.includes("clothing")) return "👕";
    return "🛍️";
  };

  // Helper to format/parse ESQL results in reasoning steps
  const formatOutput = (outputStr) => {
    try {
      const parsed = JSON.parse(outputStr);
      if (Array.isArray(parsed) && parsed.length > 0) {
        const headers = Object.keys(parsed[0]);
        return (
          <div className="esql-output-container">
            <div style={{ fontSize: "0.78rem", color: "#8c9bb3", marginBottom: "4px", fontWeight: "600" }}>Elastic Index Data:</div>
            <table className="esql-output-table">
              <thead>
                <tr>
                  {headers.map(h => <th key={h}>{h}</th>)}
                </tr>
              </thead>
              <tbody>
                {parsed.slice(0, 4).map((row, idx) => (
                  <tr key={idx}>
                    {headers.map(h => <td key={h}>{String(row[h])}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
            {parsed.length > 4 && <div className="esql-more-records">+ {parsed.length - 4} more rows</div>}
          </div>
        );
      }
      return <div className="esql-output-grid">{outputStr}</div>;
    } catch (e) {
      return <div className="esql-output-grid">{outputStr}</div>;
    }
  };

  // Custom regex markdown parser
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
    
    // Paragraphs
    html = html.replace(/^(?!<(h1|h2|h3|h4|ul|ol|li|table|thead|tbody|tr|td|th|div|pre|input|p)).+$/gm, "<p>$&</p>");
    
    return <div className="message-content" dangerouslySetInnerHTML={{ __html: html }} />;
  };

  // Primary stream runner
  const executeChatStream = async (messageText) => {
    if (isGenerating || !messageText.trim()) return;
    
    setIsGenerating(true);
    
    const userMsgId = "msg-" + Date.now();
    const agentMsgId = "agent-" + Date.now();
    
    const newUserMessage = {
      id: userMsgId,
      sender: "user",
      content: messageText,
      reasoningSteps: [],
      isStreaming: false
    };
    
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
      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: messageText,
          role: "customer" // Sends "customer" role to route to customer agent runner
        })
      });
      
      if (!response.ok) {
        throw new Error("Failed to reach personal shopping co-pilot server.");
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();
        
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
                    updatedReasoning = updatedReasoning.map((step) => {
                      if (step.type === "tool_call" && step.tool === event.tool && !step.output) {
                        return { ...step, output: event.output };
                      }
                      return step;
                    });
                  } else if (event.type === "final_answer") {
                    updatedContent = event.content;
                  } else if (event.type === "error") {
                    updatedContent += `\n\n*[Connection Error: ${event.content}]*`;
                  }
                  
                  return {
                    ...msg,
                    content: updatedContent,
                    reasoningSteps: updatedReasoning
                  };
                });
              });
            } catch (err) {
              console.error("SSE parse error", err);
            }
          }
        }
      }
    } catch (error) {
      console.error("Stream error", error);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === agentMsgId 
            ? { 
                ...msg, 
                content: `## ⚠️ Offline/Connection Interrupted\n\nUnable to connect with your Mall Personal Co-Pilot. Make sure your local FastAPI backend is active (\`make start-backend\` on port 8000).\n\n*(Reason: ${error.message})*`, 
                isStreaming: false 
              }
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

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (prompt.trim()) {
        executeChatStream(prompt);
      }
    }
  };

  return (
    <div className={`customer-view-container ${isMobilePreview ? "mobile-mode-active" : ""}`}>
      {/* Dynamic Style Injection for modular layout */}
      <style dangerouslySetInnerHTML={{ __html: `
        .customer-view-container {
          background-color: #f8fafc;
          background-image: radial-gradient(circle at 10% 20%, rgba(219, 234, 254, 0.6) 0%, rgba(248, 250, 252, 1) 90%),
                            radial-gradient(circle at 90% 80%, rgba(239, 246, 255, 0.5) 0%, rgba(248, 250, 252, 0) 60%);
          --panel-bg: rgba(255, 255, 255, 0.7);
          --panel-border: 1px solid rgba(15, 23, 42, 0.08);
          --glass-shadow: 0 10px 30px rgba(15, 23, 42, 0.04), 0 1px 3px rgba(15, 23, 42, 0.02);
          --text-primary: #0f172a;
          --text-secondary: #475569;
          --text-muted: #64748b;
          width: 100vw;
          height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          font-family: var(--font-sans);
          color: var(--text-primary);
          overflow: hidden;
          position: relative;
          padding: 40px 20px;
        }

        /* 🖥️ KIOSK WIDESCREEN LAYOUT */
        .kiosk-widescreen-view {
          display: none;
          width: 100%;
          height: 100%;
          max-width: 1440px;
          max-height: 900px;
          gap: 24px;
          z-index: 10;
          position: relative;
        }

        .kiosk-left-panel {
          width: 480px;
          height: 100%;
          background: var(--panel-bg);
          backdrop-filter: blur(25px);
          -webkit-backdrop-filter: blur(25px);
          border: var(--panel-border);
          border-radius: 28px;
          box-shadow: var(--glass-shadow);
          display: flex;
          flex-direction: column;
          overflow: hidden;
          min-height: 0;
        }

        .kiosk-right-panel {
          flex: 1;
          height: 100%;
          display: flex;
          flex-direction: column;
          gap: 16px;
          min-height: 0;
        }

        .kiosk-header {
          padding: 24px;
          background: rgba(255, 255, 255, 0.4);
          border-bottom: 1px solid rgba(15, 23, 42, 0.06);
          display: flex;
          align-items: center;
          justify-content: space-between;
          flex-shrink: 0;
        }
        .kiosk-title-group {
          display: flex;
          align-items: center;
          gap: 14px;
        }
        .kiosk-icon {
          font-size: 1.8rem;
          background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%);
          width: 48px;
          height: 48px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          box-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
        }
        .kiosk-title {
          font-size: 1.25rem;
          font-weight: 800;
          color: #0f172a;
          letter-spacing: -0.5px;
        }
        .kiosk-subtitle {
          font-size: 0.72rem;
          color: #10b981;
          font-weight: 700;
          display: flex;
          align-items: center;
          gap: 4px;
          text-transform: uppercase;
          margin-top: 1px;
        }

        .kiosk-directory-card {
          background: var(--panel-bg);
          backdrop-filter: blur(25px);
          -webkit-backdrop-filter: blur(25px);
          border: var(--panel-border);
          border-radius: 28px;
          padding: 16px 20px;
          box-shadow: var(--glass-shadow);
          display: flex;
          flex-direction: column;
          gap: 10px;
        }

        .directory-header-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1px solid rgba(15,23,42,0.06);
          padding-bottom: 10px;
        }
        .directory-title {
          font-size: 0.95rem;
          font-weight: 800;
          color: #1d4ed8;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }

        .floor-filters-row {
          display: flex;
          gap: 6px;
          flex-wrap: wrap;
        }
        .floor-filter-btn {
          background: rgba(15, 23, 42, 0.03);
          border: 1px solid rgba(15, 23, 42, 0.06);
          color: var(--text-secondary);
          font-size: 0.72rem;
          padding: 6px 12px;
          border-radius: 10px;
          cursor: pointer;
          font-weight: 600;
          transition: all 0.2s ease;
        }
        .floor-filter-btn:hover {
          background: rgba(15, 23, 42, 0.08);
          color: #0f172a;
        }
        .floor-filter-btn.active {
          background: rgba(59, 130, 246, 0.12);
          border-color: rgba(59, 130, 246, 0.3);
          color: #1d4ed8;
          box-shadow: 0 0 10px rgba(59, 130, 246, 0.1);
        }

        .kiosk-map-card {
          flex: 1.8;
          background: var(--panel-bg);
          border: var(--panel-border);
          border-radius: 28px;
          position: relative;
          overflow: hidden;
          box-shadow: var(--glass-shadow);
          display: flex;
          flex-direction: column;
          min-height: 0;
        }
        .kiosk-map-header {
          padding: 16px 20px;
          border-bottom: 1px solid rgba(15, 23, 42, 0.06);
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: rgba(255, 255, 255, 0.3);
          color: var(--text-primary);
        }
        .kiosk-map-body {
          flex: 1;
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 20px;
          background: radial-gradient(circle at center, rgba(219, 234, 254, 0.2) 0%, rgba(248, 250, 252, 0.8) 100%);
          min-height: 0;
        }
        .kiosk-render-img {
          max-width: 100%;
          max-height: 100%;
          object-fit: contain;
          border-radius: 16px;
          box-shadow: 0 15px 35px rgba(15, 23, 42, 0.08);
          border: 1px solid rgba(15, 23, 42, 0.06);
          transition: all 0.5s ease;
        }

        .mobile-chips-area {
          display: flex !important;
          flex-direction: row !important;
          flex-wrap: nowrap !important;
          gap: 8px !important;
          padding: 12px 16px 12px 16px !important;
          overflow-x: auto !important;
          scrollbar-width: none !important;
          border-top: 1px solid rgba(15, 23, 42, 0.06) !important;
          flex-shrink: 0 !important;
        }
        .mobile-chips-area::-webkit-scrollbar {
          display: none !important;
        }
        
        .mobile-chip {
          padding: 8px 16px !important;
          background: rgba(255, 255, 255, 0.8) !important;
          border: 1px solid rgba(15, 23, 42, 0.08) !important;
          border-radius: 20px !important;
          font-size: 0.75rem !important;
          color: var(--text-secondary) !important;
          cursor: pointer !important;
          white-space: nowrap !important;
          transition: all 0.2s ease !important;
          font-weight: 600 !important;
          box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04) !important;
          flex-shrink: 0 !important;
          display: inline-block !important;
        }
        .mobile-chip:hover {
          background: rgba(59, 130, 246, 0.1) !important;
          border-color: rgba(59, 130, 246, 0.3) !important;
          color: #1d4ed8 !important;
          transform: translateY(-1px) !important;
        }
        .mobile-chip:disabled {
          opacity: 0.5 !important;
          cursor: not-allowed !important;
        }

        .mobile-input-area {
          padding: 12px 16px 20px 16px !important;
          border-top: 1px solid rgba(15, 23, 42, 0.06) !important;
          flex-shrink: 0 !important;
        }
        
        .mobile-input-row {
          display: flex !important;
          gap: 10px !important;
          align-items: center !important;
          position: relative !important;
          width: 100% !important;
        }

        .mobile-chat-textarea {
          flex: 1 !important;
          background: #ffffff !important;
          border: 1px solid rgba(15, 23, 42, 0.12) !important;
          border-radius: 14px !important;
          padding: 12px 48px 12px 14px !important;
          color: #0f172a !important;
          font-family: var(--font-sans) !important;
          font-size: 0.82rem !important;
          resize: none !important;
          height: 48px !important;
          outline: none !important;
          transition: all 0.25s ease !important;
          line-height: 1.4 !important;
        }
        .mobile-chat-textarea:focus {
          border-color: rgba(59, 130, 246, 0.5) !important;
          background: #ffffff !important;
          box-shadow: 0 0 10px rgba(59, 130, 246, 0.15) !important;
        }

        .mobile-send-btn {
          position: absolute !important;
          right: 8px !important;
          top: 50% !important;
          transform: translateY(-50%) !important;
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
          width: 32px !important;
          height: 32px !important;
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%) !important;
          border: none !important;
          border-radius: 10px !important;
          color: #ffffff !important;
          cursor: pointer !important;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
          box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3) !important;
          z-index: 5 !important;
        }
        .mobile-send-btn:hover {
          transform: translateY(-50%) scale(1.05) !important;
          box-shadow: 0 4px 14px rgba(59, 130, 246, 0.5) !important;
        }
        .mobile-send-btn:disabled {
          background: rgba(255, 255, 255, 0.04) !important;
          color: #4b5563 !important;
          box-shadow: none !important;
          cursor: not-allowed !important;
        }

        .map-deal-hotspot {
          position: absolute;
          background: rgba(245, 158, 11, 0.2);
          border: 2px solid #f59e0b;
          border-radius: 50%;
          width: 24px;
          height: 24px;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.65rem;
          color: #ffffff;
          box-shadow: 0 0 10px #f59e0b;
          animation: pulseHotspot 2.5s infinite;
          transition: all 0.3s ease;
        }
        .map-deal-hotspot:hover {
          transform: scale(1.3);
          background: rgba(245, 158, 11, 0.5);
          box-shadow: 0 0 15px #f59e0b;
        }
        @keyframes pulseHotspot {
          0% { box-shadow: 0 0 5px #f59e0b; }
          50% { box-shadow: 0 0 15px #f59e0b, 0 0 25px rgba(245,158,11,0.4); }
          100% { box-shadow: 0 0 5px #f59e0b; }
        }

        .map-deal-hotspot.active {
          border-color: #3b82f6;
          background: rgba(59, 130, 246, 0.35);
          box-shadow: 0 0 18px 6px #3b82f6;
          animation: pulseActiveHotspot 1.8s infinite;
          width: 32px;
          height: 32px;
          font-size: 0.95rem;
          z-index: 100;
        }
        @keyframes pulseActiveHotspot {
          0% { box-shadow: 0 0 8px #3b82f6; transform: scale(1); }
          50% { box-shadow: 0 0 22px #3b82f6, 0 0 35px rgba(59, 130, 246, 0.6); transform: scale(1.15); }
          100% { box-shadow: 0 0 8px #3b82f6; transform: scale(1); }
        }

        .glowing-red-scanline {
          position: absolute;
          left: 0;
          right: 0;
          height: 2px;
          background: #ef4444;
          box-shadow: 0 0 8px 1px #ef4444, 0 0 12px 2px rgba(239, 68, 68, 0.5);
          animation: scanVertical 2.2s infinite ease-in-out;
          z-index: 10;
        }
        @keyframes scanVertical {
          0% { top: 4px; }
          50% { top: calc(100% - 6px); }
          100% { top: 4px; }
        }

        .kiosk-split-panels {
          display: flex;
          gap: 20px;
          flex: 2.2;
          min-height: 0;
        }
        .kiosk-info-panel {
          flex: 1;
          background: var(--panel-bg);
          backdrop-filter: blur(25px);
          -webkit-backdrop-filter: blur(25px);
          border: var(--panel-border);
          border-radius: 24px;
          padding: 18px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 12px;
          min-height: 0;
          scrollbar-gutter: stable;
        }
        .kiosk-info-panel::-webkit-scrollbar {
          width: 4px;
        }
        .kiosk-info-panel::-webkit-scrollbar-thumb {
          background: rgba(15, 23, 42, 0.1);
          border-radius: 2px;
        }

        .kiosk-store-list-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 12px;
          background: rgba(15, 23, 42, 0.02);
          border: 1px solid rgba(15, 23, 42, 0.04);
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        .kiosk-store-list-item:hover {
          background: rgba(59, 130, 246, 0.06);
          border-color: rgba(59, 130, 246, 0.2);
        }
        .kiosk-store-list-item.selected {
          background: rgba(59, 130, 246, 0.1);
          border-color: rgba(59, 130, 246, 0.35);
        }

        .kiosk-happenings-panel {
          flex: 1;
          background: var(--panel-bg);
          backdrop-filter: blur(25px);
          -webkit-backdrop-filter: blur(25px);
          border: var(--panel-border);
          border-radius: 24px;
          padding: 18px;
          overflow-y: auto;
          display: flex;
          flex-direction: column;
          gap: 12px;
          min-height: 0;
          scrollbar-gutter: stable;
        }
        .kiosk-happenings-panel::-webkit-scrollbar {
          width: 4px;
        }
        .kiosk-happenings-panel::-webkit-scrollbar-thumb {
          background: rgba(15, 23, 42, 0.1);
          border-radius: 2px;
        }
        
        .happenings-title {
          font-size: 0.95rem;
          font-weight: 800;
          color: #047857; /* Emerald/Green theme for active promos */
          text-transform: uppercase;
          letter-spacing: 0.5px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        
        .happenings-list-container {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        
        .happening-card {
          background: rgba(255, 255, 255, 0.45);
          border: 1px solid rgba(15, 23, 42, 0.05);
          border-radius: 16px;
          padding: 12px 14px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          cursor: pointer;
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          box-shadow: 0 4px 12px rgba(15, 23, 42, 0.02);
        }
        
        .happening-card:hover {
          transform: translateY(-2px);
          background: rgba(255, 255, 255, 0.85);
          border-color: rgba(16, 185, 129, 0.25);
          box-shadow: 0 8px 24px rgba(16, 185, 129, 0.08);
        }
        
        .happening-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .happening-type-badge {
          font-size: 0.58rem;
          font-weight: 800;
          padding: 2px 8px;
          border-radius: 20px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        .happening-type-badge.event {
          background: rgba(59, 130, 246, 0.1);
          color: #1d4ed8;
          border: 1px solid rgba(59, 130, 246, 0.15);
        }
        
        .happening-type-badge.promo {
          background: rgba(245, 158, 11, 0.1);
          color: #b45309;
          border: 1px solid rgba(245, 158, 11, 0.15);
        }
        
        .happening-type-badge.music {
          background: rgba(139, 92, 246, 0.1);
          color: #6d28d9;
          border: 1px solid rgba(139, 92, 246, 0.15);
        }
        
        .happening-title-text {
          font-size: 0.82rem;
          font-weight: 800;
          color: var(--text-primary);
        }
        
        .happening-desc {
          font-size: 0.68rem;
          color: var(--text-secondary);
          line-height: 1.35;
        }
        
        .happening-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.62rem;
          color: var(--text-muted);
          font-weight: 600;
          border-top: 1px dashed rgba(15, 23, 42, 0.05);
          padding-top: 8px;
          margin-top: 2px;
        }
        
        .happening-btn {
          align-self: flex-start;
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: #ffffff;
          border: none;
          border-radius: 8px;
          padding: 4px 10px;
          font-size: 0.62rem;
          font-weight: 700;
          cursor: pointer;
          transition: all 0.2s ease;
          box-shadow: 0 2px 6px rgba(16, 185, 129, 0.2);
        }
        
        .happening-btn:hover {
          opacity: 0.9;
          box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
        }



        /* 📱 MOBILE DEVICE MOCKUP FRAME */
        .mobile-device-frame {
          width: 420px;
          height: 100%;
          max-height: 840px;
          border: 12px solid rgba(255, 255, 255, 0.1);
          border-radius: 44px;
          background: #000000;
          position: relative;
          box-shadow: 0 30px 60px -15px rgba(0, 0, 0, 0.9),
                      inset 0 0 10px rgba(255, 255, 255, 0.15),
                      0 0 40px rgba(59, 130, 246, 0.1);
          display: flex;
          flex-direction: column;
          z-index: 10;
          overflow: hidden;
          transition: all 0.3s ease;
        }

        /* Notch mockup style */
        .dynamic-island {
          width: 110px;
          height: 25px;
          background: #000;
          border-radius: 20px;
          margin: 10px auto 0 auto;
          position: absolute;
          left: 50%;
          transform: translateX(-50%);
          z-index: 100;
          box-shadow: 0 4px 10px rgba(0,0,0,0.5);
          display: flex;
          align-items: center;
          justify-content: center;
        }
        .dynamic-island::after {
          content: "";
          display: block;
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: #1e293b;
          margin-left: 60px;
        }

        .mobile-screen {
          flex: 1;
          background: #f8fafc;
          backdrop-filter: blur(25px);
          -webkit-backdrop-filter: blur(25px);
          border-radius: 32px;
          overflow: hidden;
          display: flex;
          flex-direction: column;
          position: relative;
          border: 1px solid rgba(15, 23, 42, 0.06);
        }

        .mobile-screen-header {
          padding: 36px 16px 12px 16px;
          background: rgba(255, 255, 255, 0.85);
          border-bottom: 1px solid rgba(15, 23, 42, 0.06);
          display: flex;
          align-items: center;
          justify-content: space-between;
          z-index: 10;
        }

        .co-pilot-avatar-group {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .avatar-glow-ring {
          position: relative;
          width: 38px;
          height: 38px;
          border-radius: 50%;
          background: linear-gradient(135deg, #3b82f6 0%, #10b981 100%);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.15rem;
          box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
        }
        
        .avatar-pulse-dot {
          position: absolute;
          bottom: 0;
          right: 0;
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: #10b981;
          border: 2px solid #fff;
          box-shadow: 0 0 6px #10b981;
          animation: statusGlow 2s infinite ease-in-out;
        }
        @keyframes statusGlow {
          0%, 100% { opacity: 0.6; }
          50% { opacity: 1; }
        }

        .header-title-container {
          display: flex;
          flex-direction: column;
        }
        .header-app-name {
          font-size: 0.95rem;
          font-weight: 700;
          color: #0f172a;
          letter-spacing: -0.2px;
        }
        .header-status-text {
          font-size: 0.68rem;
          color: #10b981;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 3px;
        }

        .back-portal-btn {
          display: flex;
          align-items: center;
          gap: 4px;
          background: rgba(15, 23, 42, 0.03);
          border: 1px solid rgba(15, 23, 42, 0.06);
          border-radius: 12px;
          padding: 6px 10px;
          color: var(--text-secondary);
          font-size: 0.72rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
          text-decoration: none;
        }
        .back-portal-btn:hover {
          background: rgba(15, 23, 42, 0.06);
          color: #0f172a;
          border-color: rgba(15, 23, 42, 0.12);
          box-shadow: 0 0 10px rgba(59, 130, 246, 0.08);
        }

        .layout-switch-floating-btn {
          position: fixed;
          bottom: 24px;
          right: 24px;
          background: rgba(255, 255, 255, 0.85);
          border: 1px solid rgba(59, 130, 246, 0.3);
          border-radius: 30px;
          padding: 12px 24px;
          color: #1d4ed8;
          font-size: 0.85rem;
          font-weight: 700;
          cursor: pointer;
          z-index: 999;
          box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08),
                      0 0 15px rgba(59, 130, 246, 0.15);
          backdrop-filter: blur(16px);
          display: none;
          transition: all 0.2s ease;
        }
        .layout-switch-floating-btn:hover {
          background: #ffffff;
          transform: translateY(-2px);
          box-shadow: 0 15px 30px rgba(15, 23, 42, 0.12),
                      0 0 20px rgba(59, 130, 246, 0.25);
        }

        .promo-carousel-container {
          background: rgba(255, 255, 255, 0.3);
          border-bottom: 1px solid rgba(15, 23, 42, 0.06);
          padding: 8px 12px;
          z-index: 5;
        }
        .promo-carousel-label {
          font-size: 0.65rem;
          font-weight: 800;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 0.5px;
          margin-bottom: 4px;
          display: block;
        }
        .promo-carousel-strip {
          display: flex;
          gap: 8px;
          overflow-x: auto;
          scrollbar-width: none;
          padding-bottom: 2px;
        }
        .promo-carousel-strip::-webkit-scrollbar {
          display: none;
        }
        .promo-card {
          flex: 0 0 185px;
          background: rgba(255, 255, 255, 0.6);
          border: 1px solid rgba(15, 23, 42, 0.06);
          border-radius: 10px;
          padding: 6px 8px;
          cursor: pointer;
          transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
          display: flex;
          flex-direction: column;
        }
        .promo-card:hover {
          background: rgba(59, 130, 246, 0.06);
          border-color: rgba(59, 130, 246, 0.25);
          transform: translateY(-1px);
        }
        .promo-card-badge {
          font-size: 0.58rem;
          font-weight: 700;
          color: #f59e0b;
          text-transform: uppercase;
          margin-bottom: 2px;
        }
        .promo-card-discount {
          font-size: 0.75rem;
          font-weight: 800;
          color: var(--text-primary);
          margin-bottom: 1px;
        }
        .promo-card-copy {
          font-size: 0.6rem;
          color: var(--text-secondary);
          line-height: 1.2;
        }

        .timeline-widget-container {
          margin: 16px 0;
          background: rgba(15, 23, 42, 0.015);
          border: 1px solid rgba(15, 23, 42, 0.05);
          border-radius: 14px;
          padding: 14px;
          position: relative;
        }
        .timeline-widget-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          margin-bottom: 16px;
          border-bottom: 1px solid rgba(15, 23, 42, 0.05);
          padding-bottom: 6px;
        }
        .timeline-widget-title {
          font-size: 0.85rem;
          font-weight: 800;
          color: #1d4ed8;
          text-transform: uppercase;
          letter-spacing: 0.8px;
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .vertical-timeline {
          position: relative;
          padding-left: 24px;
          display: flex;
          flex-direction: column;
          gap: 0px;
        }
        .vertical-timeline::before {
          content: "";
          position: absolute;
          left: 7px;
          top: 8px;
          bottom: 8px;
          width: 2px;
          background: linear-gradient(to bottom, #3b82f6 20%, #10b981 50%, #f59e0b 80%, #ef4444 100%);
          opacity: 0.6;
          box-shadow: 0 0 6px rgba(59, 130, 246, 0.2);
        }

        .timeline-step {
          position: relative;
          padding-bottom: 18px;
        }
        .timeline-step:last-child {
          padding-bottom: 0;
        }
        .timeline-node {
          position: absolute;
          left: -24px;
          top: 2px;
          width: 16px;
          height: 16px;
          border-radius: 50%;
          background: #ffffff;
          border: 2px solid #3b82f6;
          box-shadow: 0 0 8px rgba(59, 130, 246, 0.3);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 2;
          transition: all 0.3s ease;
        }
        .timeline-card {
          background: rgba(255, 255, 255, 0.8);
          border: 1px solid rgba(15, 23, 42, 0.05);
          border-radius: 10px;
          padding: 10px 12px;
          transition: all 0.2s ease;
        }
        .timeline-card-header {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 6px;
          margin-bottom: 4px;
        }
        .timeline-card-time {
          font-size: 0.68rem;
          font-family: var(--font-mono);
          color: #1d4ed8;
          background: rgba(59, 130, 246, 0.08);
          padding: 2px 6px;
          border-radius: 4px;
          font-weight: 600;
        }
        .timeline-card-badges {
          display: flex;
          gap: 4px;
        }
        .floor-badge {
          font-size: 0.58rem;
          font-weight: 700;
          padding: 1px 4px;
          border-radius: 3px;
          text-transform: uppercase;
        }
        .floor-badge.floor-1 { background: rgba(59, 130, 246, 0.08); color: #1d4ed8; border: 1px solid rgba(59, 130, 246, 0.15); }
        .floor-badge.floor-2 { background: rgba(139, 92, 246, 0.08); color: #6d28d9; border: 1px solid rgba(139, 92, 246, 0.15); }
        .floor-badge.floor-3 { background: rgba(239, 68, 68, 0.08); color: #b91c1c; border: 1px solid rgba(239, 68, 68, 0.15); }
        .floor-badge.floor-parking { background: rgba(107, 114, 128, 0.1); color: #4b5563; border: 1px solid rgba(107, 114, 128, 0.15); }
        .floor-badge.floor-entrance { background: rgba(16, 185, 129, 0.08); color: #047857; border: 1px solid rgba(16, 185, 129, 0.15); }
        .timeline-card-title {
          font-size: 0.82rem;
          font-weight: 700;
          color: var(--text-primary);
          display: flex;
          align-items: center;
          gap: 6px;
          margin-bottom: 4px;
        }
        .timeline-card-duration {
          font-size: 0.65rem;
          color: var(--text-secondary);
          display: flex;
          align-items: center;
          gap: 3px;
        }
        .timeline-card-notes {
          font-size: 0.68rem;
          color: #b45309;
          background: rgba(245, 158, 11, 0.06);
          border: 1px dashed rgba(245, 158, 11, 0.2);
          border-radius: 6px;
          padding: 4px 8px;
          margin-top: 6px;
          display: flex;
          align-items: center;
          gap: 4px;
        }
        .timeline-transit-node {
          padding: 8px 12px;
          margin: 4px 0 10px 0;
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 0.68rem;
          color: var(--text-secondary);
          background: rgba(15, 23, 42, 0.01);
          border-radius: 8px;
          border-left: 2px solid rgba(16, 185, 129, 0.3);
          font-style: italic;
        }

        .mobile-chat-feed {
          flex: 1;
          overflow-y: auto;
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 16px;
          scrollbar-width: none;
        }
        .mobile-bubble {
          max-width: 90% !important;
          padding: 12px 14px !important;
          border-radius: 16px !important;
        }
        .mobile-bubble.user {
          border-bottom-right-radius: 4px !important;
          background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%) !important;
        }
        .mobile-bubble.user .message-content,
        .mobile-bubble.user .message-content * {
          color: #ffffff !important;
        }
        .mobile-bubble.agent {
          border-bottom-left-radius: 4px !important;
          background: rgba(255, 255, 255, 0.85) !important;
          border: 1px solid rgba(15, 23, 42, 0.06) !important;
          color: var(--text-primary) !important;
          box-shadow: 0 2px 8px rgba(15, 23, 42, 0.02) !important;
        }
        .mobile-bubble.agent .message-content,
        .mobile-bubble.agent .message-content * {
          color: var(--text-primary) !important;
        }
        .mobile-reasoning-drawer {
          background: rgba(15, 23, 42, 0.02) !important;
          border: 1px solid rgba(15, 23, 42, 0.05) !important;
          padding: 8px 10px !important;
          margin-bottom: 10px !important;
          border-radius: 6px !important;
        }

        @media (min-width: 1024px) {
          .customer-view-container:not(.mobile-mode-active) .kiosk-widescreen-view {
            display: flex !important;
          }
          .customer-view-container:not(.mobile-mode-active) .mobile-device-frame {
            display: none !important;
          }
          .customer-view-container.mobile-mode-active .kiosk-widescreen-view {
            display: none !important;
          }
          .customer-view-container.mobile-mode-active .mobile-device-frame {
            display: flex !important;
          }
          .layout-switch-floating-btn {
            display: block !important;
          }
        }
        @media (max-width: 1023px) {
          .kiosk-widescreen-view {
            display: none !important;
          }
          .mobile-device-frame {
            display: flex !important;
            width: 100vw !important;
            height: 100vh !important;
            max-height: 100vh !important;
            border: none !important;
            border-radius: 0 !important;
            box-shadow: none !important;
          }
          .dynamic-island { display: none !important; }
          .customer-view-container { padding: 0 !important; }
        }

        /* 🎟️ GLASSMORPHIC VIP COUPON TICKET DRAWER & BARCODE */
        .coupon-ticket-wrapper {
          margin: 16px 0;
          perspective: 1000px;
          display: flex;
          justify-content: center;
          width: 100%;
          animation: ticketSlideIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }

        @keyframes ticketSlideIn {
          from {
            opacity: 0;
            transform: translateY(20px) rotateX(-15deg);
          }
          to {
            opacity: 1;
            transform: translateY(0) rotateX(0deg);
          }
        }

        .coupon-ticket-body {
          width: 100%;
          max-width: 320px;
          background: linear-gradient(135deg, rgba(20, 26, 60, 0.9) 0%, rgba(8, 12, 36, 0.98) 100%);
          border: 1px solid rgba(16, 185, 129, 0.3); /* Emerald VIP border */
          box-shadow: 0 15px 35px rgba(0, 0, 0, 0.6), 0 0 20px rgba(16, 185, 129, 0.15);
          border-radius: 16px;
          position: relative;
          overflow: hidden;
          font-family: var(--font-sans);
          transition: all 0.3s ease;
          backdrop-filter: blur(12px);
          -webkit-backdrop-filter: blur(12px);
        }

        .coupon-ticket-body:hover {
          border-color: rgba(16, 185, 129, 0.6);
          box-shadow: 0 20px 40px rgba(0, 0, 0, 0.7), 0 0 30px rgba(16, 185, 129, 0.3);
          transform: translateY(-2px);
        }

        .coupon-ticket-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background: rgba(16, 185, 129, 0.12);
          border-bottom: 1px solid rgba(16, 185, 129, 0.15);
        }

        .coupon-ticket-store {
          font-weight: 800;
          font-size: 0.88rem;
          color: #ffffff;
          letter-spacing: 0.5px;
          text-transform: uppercase;
        }

        .coupon-ticket-badge {
          background: linear-gradient(135deg, #10b981 0%, #059669 100%);
          color: #ffffff;
          font-size: 0.58rem;
          font-weight: 800;
          padding: 3px 8px;
          border-radius: 20px;
          letter-spacing: 1px;
          box-shadow: 0 0 10px rgba(16, 185, 129, 0.4);
          animation: badgePulse 2s infinite alternate;
        }

        @keyframes badgePulse {
          0% { transform: scale(1); box-shadow: 0 0 5px rgba(16, 185, 129, 0.4); }
          100% { transform: scale(1.05); box-shadow: 0 0 15px rgba(16, 185, 129, 0.7); }
        }

        .coupon-ticket-details {
          padding: 16px;
          text-align: center;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
        }

        .coupon-ticket-discount {
          font-size: 1.15rem;
          font-weight: 800;
          color: #10b981;
          letter-spacing: -0.5px;
          line-height: 1.2;
          margin-bottom: 4px;
        }

        .coupon-ticket-token-label {
          font-size: 0.52rem;
          color: #8c9bb3;
          font-weight: 700;
          letter-spacing: 1.5px;
          text-transform: uppercase;
        }

        .coupon-ticket-token-code {
          font-family: var(--font-mono);
          font-size: 1.05rem;
          font-weight: 700;
          color: #ffffff;
          letter-spacing: 2px;
          background: rgba(0, 0, 0, 0.35);
          padding: 6px 14px;
          border-radius: 6px;
          border: 1px solid rgba(255, 255, 255, 0.05);
          display: inline-block;
          box-shadow: inset 0 2px 4px rgba(0,0,0,0.5);
        }

        .coupon-ticket-divider {
          position: relative;
          height: 20px;
          display: flex;
          align-items: center;
          justify-content: center;
          overflow: visible;
        }

        .divider-circle {
          width: 16px;
          height: 16px;
          background: #f8fafc; /* Match premium light portal background */
          border-radius: 50%;
          position: absolute;
          top: 2px;
          z-index: 2;
          box-shadow: inset 0 0 5px rgba(15, 23, 42, 0.15);
        }

        .divider-circle.left {
          left: -8px;
          border-right: 1px solid rgba(16, 185, 129, 0.3);
        }

        .divider-circle.right {
          right: -8px;
          border-left: 1px solid rgba(16, 185, 129, 0.3);
        }

        .divider-dashed-line {
          width: calc(100% - 24px);
          border-bottom: 2px dashed rgba(16, 185, 129, 0.3);
          height: 0;
        }

        .coupon-ticket-barcode-container {
          padding: 12px;
          background: rgba(0, 0, 0, 0.45);
          margin: 0 16px 14px 16px;
          border-radius: 10px;
          border: 1px solid rgba(255, 255, 255, 0.03);
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
          position: relative;
          overflow: hidden;
        }

        .barcode-bars {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 32px;
          width: 100%;
        }

        .barcode-token-text {
          font-family: var(--font-mono);
          font-size: 0.6rem;
          color: #8c9bb3;
          letter-spacing: 2px;
          margin-top: 2px;
        }

        .glowing-red-scanline {
          position: absolute;
          left: 0;
          right: 0;
          height: 2px;
          background: #ef4444;
          box-shadow: 0 0 8px #ef4444, 0 0 15px rgba(239, 68, 68, 0.8);
          opacity: 0.8;
          z-index: 10;
          animation: laserScan 2.5s infinite ease-in-out;
        }

        @keyframes laserScan {
          0% { top: 10%; }
          50% { top: 85%; }
          100% { top: 10%; }
        }

        .coupon-ticket-footer {
          display: flex;
          justify-content: space-between;
          padding: 10px 16px 12px 16px;
          border-top: 1px solid rgba(255, 255, 255, 0.04);
          font-size: 0.58rem;
          color: #8c9bb3;
          font-weight: 700;
        }
      ` }} />

      <div className="glowing-orb one" />
      <div className="glowing-orb two" />

      <div className="kiosk-widescreen-view">
        <div className="kiosk-left-panel">
          <header className="kiosk-header">
            <div className="kiosk-title-group">
              <div className="kiosk-icon">🏬</div>
              <div>
                <h1 className="kiosk-title">Mall Navigation Terminal</h1>
                <span className="kiosk-subtitle">
                  <span style={{ display: "inline-block", width: "5px", height: "5px", background: "#10b981", borderRadius: "50%" }}></span>
                  Entrance Kiosk A — Active
                </span>
              </div>
            </div>
            <a href="/" className="back-portal-btn"><span>🖥️</span> Admin Cockpit</a>
          </header>
          <div className="promo-carousel-container">
            <span className="promo-carousel-label">🎟️ Click to plan route for a deal:</span>
            <div className="promo-carousel-strip">
              {featuredPromotions.map((promo) => (
                <div key={promo.id} className="promo-card" onClick={() => { setPrompt(promo.prompt); executeChatStream(promo.prompt); }}>
                  <span className="promo-card-badge">{promo.badge}</span>
                  <span className="promo-card-discount">{promo.discount}</span>
                  <span className="promo-card-copy">{promo.copy}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="mobile-chat-feed" style={{ background: "rgba(0,0,0,0.15)" }}>
            {messages.map((msg) => {
              const parsedTimeline = parseItineraryTable(msg.content);
              return (
                <div key={msg.id} className={`message-bubble mobile-bubble glass-panel ${msg.sender}`} style={{ maxWidth: "85%" }}>
                  <span className="sender-tag" style={{ fontSize: "0.6rem", color: msg.sender === "user" ? "#93c5fd" : "#34d399" }}>
                    {msg.sender === "user" ? "Shopper Touchscreen" : "AI Mall Assistant"}
                  </span>
                  {msg.sender === "agent" && msg.reasoningSteps.length > 0 && (
                    <div className="reasoning-drawer mobile-reasoning-drawer">
                      <div className="reasoning-toggle mobile-reasoning-toggle" onClick={() => setIsReasoningOpen(!isReasoningOpen)}>
                        <div className="reasoning-header-text" style={{ fontSize: "0.7rem" }}>
                          <span>🧠</span> {msg.isStreaming ? "Synthesizing schedule..." : "View reasoning trace"}
                        </div>
                      </div>
                      {isReasoningOpen && (
                        <div className="reasoning-steps-list mobile-reasoning-list">
                          {msg.reasoningSteps.map((step, idx) => (
                            <div key={step.id || idx} className="reasoning-step-item mobile-reasoning-item">
                                <div className={`step-bullet ${step.output ? "success" : ""}`} style={{ width: "14px", height: "14px", fontSize: "0.55rem" }}>{step.type === "tool_call" ? "⚒️" : "✓"}</div>
                                <div className="step-details">
                                  {step.type === "reasoning" && <div className="step-desc" style={{ color: "#d1d5db" }}>{step.description}</div>}
                                  {step.type === "tool_call" && (
                                    <>
                                      <div className="step-desc" style={{ color: "#93c5fd", fontWeight: 600 }}>Called Elastic Server: <span style={{ fontFamily: "monospace", fontSize: "0.68rem" }}>{step.tool}</span></div>
                                      {step.output && <div style={{ marginTop: "4px" }}>{formatOutput(step.output)}</div>}
                                    </>
                                  )}
                                </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  {parsedTimeline && (
                    <div className="timeline-widget-container">
                      <div className="timeline-widget-header"><span className="timeline-widget-title">🗺️ Walk Itinerary Schedule</span></div>
                      <div className="vertical-timeline">
                        {parsedTimeline.map((step, idx) => (
                           <div key={idx} className="timeline-step">
                             <div className="timeline-node" />
                             <div className="timeline-card">
                               <div className="timeline-card-header"><span className="timeline-card-time">{step.time}</span></div>
                               <div className="timeline-card-title">{getActivityEmoji(step.activity)} {step.activity}</div>
                             </div>
                           </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {msg.content && renderMarkdown(msg.content)}
                  {msg.sender === "agent" && (() => {
                    const coupon = extractCouponDetails(msg.content);
                    return coupon ? (
                      <CouponTicket 
                        token={coupon.token} 
                        storeName={coupon.storeName} 
                        discountDesc={coupon.discountDesc} 
                      />
                    ) : null;
                  })()}
                </div>
              );
            })}
            <div ref={feedEndRef} />
          </div>
          <div className="mobile-chips-area" style={{ background: "rgba(255, 255, 255, 0.45)" }}>
            {quickActions.map((chip, idx) => (
              <button key={idx} className="mobile-chip" onClick={() => { setPrompt(chip.prompt); executeChatStream(chip.prompt); }} disabled={isGenerating}>{chip.label}</button>
            ))}
          </div>
          <div className="mobile-input-area" style={{ paddingBottom: "16px", background: "var(--panel-bg)", borderTop: "var(--panel-border)" }}>
            <div className="mobile-input-row">
              <textarea className="mobile-chat-textarea" placeholder="Ask co-pilot..." value={prompt} onChange={(e) => setPrompt(e.target.value)} onKeyDown={handleKeyDown} disabled={isGenerating} />
              <button className="mobile-send-btn" onClick={() => executeChatStream(prompt)} disabled={isGenerating || !prompt.trim()}>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z" /></svg>
              </button>
            </div>
          </div>
        </div>

        <div className="kiosk-right-panel">
          <div className="kiosk-map-card">
            <div className="kiosk-map-header">
              <span>LIVE 3D SITE PLAN DIRECTORY</span>
              <span style={{ fontSize: "0.68rem", color: "#3b82f6", fontWeight: "700" }}>
                {selectedKioskStore ? `📍 CURRENT SELECTION: ${selectedKioskStore.name.toUpperCase()}` : "⚡ TAP PIN OR STORE FOR DETAILS"}
              </span>
            </div>
            <div className="kiosk-map-body" style={{ position: "relative" }}>
              <img src="/mall_map.png" alt="Mall Map" className="kiosk-render-img" />
              
              {/* Selected Store Target Hotspot */}
              {selectedKioskStore && storeCoordinates[selectedKioskStore.name] && (
                <div 
                  className="map-deal-hotspot active" 
                  style={{ 
                    top: storeCoordinates[selectedKioskStore.name].top, 
                    left: storeCoordinates[selectedKioskStore.name].left 
                  }}
                  onClick={() => setSelectedKioskStore(null)}
                >
                  🎯
                </div>
              )}

              {/* Promo highlights hotspots */}
              {featuredPromotions.map((promo) => {
                const coords = storeCoordinates[promo.store];
                if (!coords) return null;
                if (selectedKioskStore && selectedKioskStore.name === promo.store) return null;
                return (
                  <div 
                    key={promo.id}
                    className="map-deal-hotspot promo" 
                    style={{ 
                      top: coords.top, 
                      left: coords.left,
                      borderColor: "#f59e0b",
                      boxShadow: "0 0 10px #f59e0b"
                    }}
                    onClick={() => {
                      const storeObj = storesList.find(s => s.name === promo.store);
                      if (storeObj) setSelectedKioskStore(storeObj);
                    }}
                  >
                    🏷️
                  </div>
                );
              })}
            </div>
          </div>

          <div className="kiosk-split-panels">
            {/* Left Column: Unified Interactive Touch Directory */}
            <div className="kiosk-info-panel">
              <span className="directory-title" style={{ fontSize: "0.95rem", fontWeight: "800", color: "#1d4ed8", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                🏢 Mall Interactive Touch Directory
              </span>
              
              <div className="floor-filters-row" style={{ display: "flex", gap: "6px", flexWrap: "wrap", marginTop: "4px" }}>
                {["all", "3", "2", "1", "0", "-1"].map((fl) => (
                  <button 
                    key={fl} 
                    className={`floor-filter-btn ${selectedFloorFilter === fl ? "active" : ""}`} 
                    onClick={() => setSelectedFloorFilter(fl)}
                  >
                    {fl === "all" ? "🏢 All Floors" : `Floor ${fl}`}
                  </button>
                ))}
              </div>
              
              {/* Widescreen Glassmorphic Search Bar */}
              <div className="directory-search-row" style={{ position: "relative", marginTop: "4px" }}>
                <input 
                  type="text" 
                  className="directory-search-input" 
                  placeholder="🔍 Search stores, dining, categories (e.g. shoes, sushi, salon, parking)..."
                  value={storeSearchQuery}
                  onChange={(e) => setStoreSearchQuery(e.target.value)}
                  style={{
                    width: "100%",
                    background: "rgba(255, 255, 255, 0.9)",
                    border: "1px solid rgba(15, 23, 42, 0.15)",
                    borderRadius: "12px",
                    padding: "10px 14px 10px 38px",
                    color: "#0f172a",
                    fontSize: "0.82rem",
                    outline: "none",
                    transition: "all 0.2s ease"
                  }}
                />
                <span style={{ position: "absolute", left: "14px", top: "50%", transform: "translateY(-50%)", color: "#64748b", fontSize: "0.85rem" }}>🔍</span>
                {storeSearchQuery && (
                  <button 
                    onClick={() => setStoreSearchQuery("")}
                    style={{
                      position: "absolute",
                      right: "12px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "transparent",
                      border: "none",
                      color: "#64748b",
                      cursor: "pointer",
                      fontSize: "0.85rem"
                    }}
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Scrollable Listings or Details */}
              <div style={{ flex: 1, minHeight: 0, marginTop: "8px", display: "flex", flexDirection: "column" }}>
                {selectedKioskStore ? (
                  <div className="kiosk-selected-store-detail" style={{ position: "relative", width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center" }}>
                    <button 
                      onClick={() => setSelectedKioskStore(null)}
                      style={{
                        position: "absolute",
                        right: "0",
                        top: "0",
                        background: "rgba(0,0,0,0.05)",
                        border: "none",
                        color: "var(--text-secondary)",
                        borderRadius: "50%",
                        width: "24px",
                        height: "24px",
                        cursor: "pointer",
                        fontSize: "0.75rem",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        transition: "all 0.2s ease"
                      }}
                    >
                      ✕
                    </button>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                      <span style={{ fontSize: "1.2rem" }}>{getActivityEmoji(selectedKioskStore.name)}</span>
                      <h3 style={{ fontSize: "1rem", fontWeight: "800", color: "#1d4ed8" }}>{selectedKioskStore.name}</h3>
                      <span className="floor-badge floor-1" style={{ fontSize: "0.6rem", padding: "2px 6px" }}>
                        {selectedKioskStore.floor}
                      </span>
                    </div>
                    <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "10px", lineHeight: "1.35" }}>
                      {selectedKioskStore.desc}
                    </p>
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <button
                        onClick={() => {
                          const pathPrompt = `Plan a walking route starting from Entrance A to visit ${selectedKioskStore.name}. Format the itinerary in a beautiful timetable schedule.`;
                          setPrompt(pathPrompt);
                          executeChatStream(pathPrompt);
                        }}
                        style={{
                          background: "linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)",
                          border: "none",
                          borderRadius: "8px",
                          color: "#ffffff",
                          padding: "6px 14px",
                          fontSize: "0.7rem",
                          fontWeight: "700",
                          cursor: "pointer",
                          boxShadow: "0 4px 12px rgba(59, 130, 246, 0.3)",
                          transition: "all 0.2s ease"
                        }}
                      >
                        🧭 Route From Entrance A
                      </button>
                      {(() => {
                        const promo = featuredPromotions.find(p => p.store.toLowerCase() === selectedKioskStore.name.toLowerCase());
                        return promo ? (
                          <button
                            onClick={() => {
                              const actPrompt = `Activate customer coupon for Store: **${promo.store}** and Discount: **${promo.discount}**`;
                              setPrompt(actPrompt);
                              executeChatStream(actPrompt);
                            }}
                            style={{
                              background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                              border: "none",
                              borderRadius: "8px",
                              color: "#ffffff",
                              padding: "6px 14px",
                              fontSize: "0.7rem",
                              fontWeight: "700",
                              cursor: "pointer",
                              boxShadow: "0 4px 12px rgba(16, 185, 129, 0.3)",
                              transition: "all 0.2s ease"
                            }}
                          >
                            🎟️ Claim Coupon
                          </button>
                        ) : null;
                      })()}
                      <span style={{ fontSize: "0.68rem", color: "#10b981", fontWeight: "700", textTransform: "uppercase" }}>
                        📍 Zone: {selectedKioskStore.zone}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px", height: "100%", overflowY: "auto" }}>
                    <div style={{ fontSize: "0.75rem", fontWeight: "800", color: "var(--text-secondary)", textTransform: "uppercase", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span>🏬 Tenants & Directory ({filteredStores.length})</span>
                      {selectedFloorFilter !== "all" && <span style={{ color: "#3b82f6", marginLeft: "auto" }}>Filter: Floor {selectedFloorFilter}</span>}
                    </div>
                    <div className="kiosk-stores-scroll-container" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      {filteredStores.length > 0 ? (
                        filteredStores.map((store) => (
                          <div 
                            key={store.name} 
                            className={`kiosk-store-list-item ${selectedKioskStore?.name === store.name ? "selected" : ""}`}
                            onClick={() => setSelectedKioskStore(store)}
                          >
                            <div style={{ display: "flex", flexDirection: "column", gap: "2px", alignItems: "flex-start" }}>
                              <span style={{ fontSize: "0.78rem", fontWeight: "700", color: "var(--text-primary)" }}>
                                {getActivityEmoji(store.name)} {store.name}
                              </span>
                              {store.deal && (
                                <span style={{
                                  fontSize: "0.6rem",
                                  fontWeight: "600",
                                  color: "#b45309",
                                  background: "rgba(245, 158, 11, 0.15)",
                                  border: "1px dashed rgba(245, 158, 11, 0.4)",
                                  borderRadius: "4px",
                                  padding: "1px 6px",
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "2px",
                                  marginTop: "2px"
                                }}>
                                  🏷️ {store.deal}
                                </span>
                              )}
                            </div>
                            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                              <span className="floor-badge floor-1" style={{ fontSize: "0.55rem", padding: "1px 4px" }}>
                                {store.floor}
                              </span>
                              <span style={{ fontSize: "0.62rem", color: "var(--text-secondary)", fontFamily: "monospace" }}>{store.zone}</span>
                            </div>
                          </div>
                        ))
                      ) : (
                        <div style={{ padding: "20px 0", textAlign: "center", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                          No stores match your search or filter level.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: Happenings & Offers */}
            <div className="kiosk-happenings-panel">
              <span className="happenings-title">
                🎉 Live Happenings & Deals
              </span>
              <div className="happenings-list-container" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {mallHappenings.map((happening) => (
                  <div 
                    key={happening.id} 
                    className="happening-card"
                    onClick={() => {
                      const storeObj = storesList.find(s => s.name === happening.store);
                      if (storeObj) setSelectedKioskStore(storeObj);
                    }}
                  >
                    <div className="happening-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span className={`happening-type-badge ${happening.type}`}>
                        {happening.badge}
                      </span>
                      <span style={{ fontSize: "0.58rem", color: "var(--text-muted)", fontWeight: "600" }}>
                        {happening.time}
                      </span>
                    </div>
                    <div className="happening-title-text" style={{ fontSize: "0.82rem", fontWeight: "800", color: "var(--text-primary)" }}>
                      {happening.title}
                    </div>
                    <p className="happening-desc" style={{ fontSize: "0.68rem", color: "var(--text-secondary)", lineHeight: "1.35", margin: 0 }}>
                      {happening.desc}
                    </p>
                    <div className="happening-meta" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.62rem", color: "var(--text-muted)", fontWeight: "600", borderTop: "1px dashed rgba(15, 23, 42, 0.05)", paddingTop: "8px", marginTop: "2px" }}>
                      <span>{happening.location}</span>
                      <button 
                        className="happening-btn"
                        onClick={(e) => {
                          e.stopPropagation(); // Avoid selecting the store when clicking the action button
                          setPrompt(happening.prompt);
                          executeChatStream(happening.prompt);
                        }}
                      >
                        {happening.actionLabel}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="mobile-device-frame">
        <div className="dynamic-island" />
        <div className="mobile-screen">
          <header className="mobile-screen-header">
             <div className="co-pilot-avatar-group"><div className="avatar-glow-ring">🛍️</div></div>
          </header>
          <div className="mobile-chat-feed">
             {messages.map((msg) => {
                const coupon = extractCouponDetails(msg.content);
                return (
                  <div key={msg.id} className={`message-bubble mobile-bubble glass-panel ${msg.sender}`}>
                    {renderMarkdown(msg.content)}
                    {msg.sender === "agent" && coupon && (
                      <CouponTicket 
                        token={coupon.token} 
                        storeName={coupon.storeName} 
                        discountDesc={coupon.discountDesc} 
                      />
                    )}
                  </div>
                );
             })}
          </div>
        </div>
      </div>

      <button className="layout-switch-floating-btn" onClick={() => setIsMobilePreview(!isMobilePreview)}>
        {isMobilePreview ? "🖥️ Entrance Kiosk Widescreen View" : "📱 Simulated Mobile View"}
      </button>

    </div>
  );
}
