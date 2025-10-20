import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import dolmaFace from "../assets/dolma_face.png";

export default function Home() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "Hello! I'm DOLMA, your intelligent personal assistant. How can I help you today?",
    },
  ]);
  const [input, setInput] = useState("");
  const chatEndRef = useRef(null);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = { role: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    // Only keep valid roles and non-empty messages
    const filteredConversation = messages.filter(
      (msg) =>
        msg &&
        (msg.role === "user" || msg.role === "assistant") &&
        msg.text.trim() !== ""
    );

    try {
      const response = await fetch("http://127.0.0.1:5000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userMsg.text,
          conversation: filteredConversation,
        }),
      });

      const data = await response.json();
      console.log("DOLMA response:", data);

      if (data && data.reply && data.reply.trim() !== "") {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: data.reply },
        ]);
      } else if (data.error) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: `⚠️ ${data.error}` },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            text: "Hmm… something went wrong. Please try again.",
          },
        ]);
      }
    } catch (err) {
      console.error("Network or parsing error:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: "Network error, please try again." },
      ]);
    }
  };

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="dolma-layout">
      {/* ===== Sidebar ===== */}
      <aside className="dolma-sidebar">
        <div className="sidebar-header">
          <h2 className="sidebar-logo">DOLMA</h2>
          <div className="dolma-avatar">
            <img src={dolmaFace} alt="Dolma avatar" />
            <p className="avatar-caption">Your AI Assistant</p>
          </div>
        </div>

        <div className="sidebar-footer">
          <button
            className="sidebar-btn"
            onClick={() => navigate("/settings")}
          >
            ⚙️ Settings
          </button>
          <button
            className="sidebar-btn"
            onClick={() => {
              alert("Logged out!");
              navigate("/signin");
            }}
          >
            Logout
          </button>
        </div>
      </aside>

      {/* ===== Chat Window ===== */}
      <main className="dolma-chat">
        <div className="chat-messages">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`message-row ${
                msg.role === "user" ? "user" : "assistant"
              }`}
            >
              <div className="message-bubble">{msg.text}</div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        <form className="chat-input-bar" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Ask DOLMA anything..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="chat-input"
          />
          <button type="submit" className="send-btn">
            ➤
          </button>
        </form>
      </main>
    </div>
  );
}
