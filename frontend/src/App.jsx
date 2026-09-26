import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

function App() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [backendOnline, setBackendOnline] = useState(false);
    const [backendError, setBackendError] = useState("");
    const textareaRef = useRef(null);
    const messagesEndRef = useRef(null);

    const checkBackend = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/health`, {
                cache: "no-store",
            });

            setBackendOnline(response.ok);
            setBackendError(
                response.ok ? "" : `Backend returned HTTP ${response.status}`
            );
        } catch (error) {
            setBackendOnline(false);
            setBackendError(error?.message || "Cannot reach FastAPI");
        }
    };

    useEffect(() => {
        checkBackend();
        const interval = setInterval(checkBackend, 10000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    const sendMessage = async () => {
        const message = input.trim();
        if (!message || loading) return;

        setMessages((prev) => [...prev, { role: "user", message }]);
        setInput("");
        setLoading(true);

        try {
            const response = await fetch(`${API_BASE_URL}/api/chat`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message }),
            });

            if (!response.ok) {
                let detail = `Backend returned HTTP ${response.status}`;
                try {
                    const errorData = await response.json();
                    detail = errorData.detail || detail;
                } catch {
                    // Keep the HTTP status when the server did not return JSON.
                }
                throw new Error(detail);
            }

            const data = await response.json();

            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    message:
                        data.response ||
                        "I received your message, but no response was returned.",
                    source: data.source,
                    latency: data.latency_ms,
                },
            ]);

            setBackendOnline(true);
            setBackendError("");
        } catch (error) {
            console.error("Medha backend error:", error);
            setBackendOnline(false);
            setBackendError(error?.message || "Connection failed");

            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    message: "I couldn't process that message.",
                    error: error?.message || "Backend connection failed",
                },
            ]);
        } finally {
            setLoading(false);
            setTimeout(() => textareaRef.current?.focus(), 0);
        }
    };

    const clearChat = () => {
        setMessages([]);
        setInput("");
        textareaRef.current?.focus();
    };

    const handleKeyDown = (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="app">
            <header className="header">
                <div className="brand">
                    <div className="brand-mark">M</div>
                    <div>
                        <h1>Medha</h1>
                        <p>Personal AI assistant</p>
                    </div>
                </div>

                <div className="header-actions">
                    {messages.length > 0 && (
                        <button className="clear-button" onClick={clearChat}>
                            Clear
                        </button>
                    )}

                    <button
                        className={`status ${backendOnline ? "online" : "offline"}`}
                        onClick={checkBackend}
                        title={backendError || "Backend connection"}
                    >
                        <span className="status-dot" />
                        {backendOnline ? "Connected" : "Offline"}
                    </button>
                </div>
            </header>

            <main className="chat-container">
                {messages.length === 0 && (
                    <section className="welcome">
                        <div className="welcome-icon">M</div>
                        <p className="eyebrow">YOUR PERSONAL ASSISTANT</p>
                        <h2>What can I help you with?</h2>
                        <p className="welcome-text">
                            Talk naturally. Medha learns useful conversations and
                            retrieves what it knows without Ollama.
                        </p>

                        {!backendOnline && (
                            <div className="connection-warning">
                                <strong>Backend offline</strong>
                                <span>
                                    Start FastAPI on port 8000, then click the status
                                    indicator to retry.
                                </span>
                                {backendError && <small>{backendError}</small>}
                            </div>
                        )}

                        <div className="suggestions">
                            <button onClick={() => setInput("Hi Medha")}>
                                Say hello
                            </button>
                            <button onClick={() => setInput("What do you remember?")}>
                                Test memory
                            </button>
                            <button onClick={() => setInput("What can you do?")}>
                                Ask about Medha
                            </button>
                        </div>
                    </section>
                )}

                {messages.map((item, index) => (
                    <div key={index} className={`message-row ${item.role}`}>
                        {item.role === "assistant" && <div className="avatar">M</div>}

                        <div>
                            <div className={`message ${item.error ? "error-message" : ""}`}>
                                {item.message}
                            </div>

                            {item.error && (
                                <div className="message-error-detail">
                                    {item.error}
                                </div>
                            )}

                            {item.role === "assistant" &&
                                !item.error &&
                                (item.source || item.latency) && (
                                    <div className="message-meta">
                                        {item.source || "medha"}
                                        {item.latency ? ` · ${item.latency} ms` : ""}
                                    </div>
                                )}
                        </div>
                    </div>
                ))}

                {loading && (
                    <div className="message-row assistant">
                        <div className="avatar">M</div>
                        <div className="message loading">
                            <span />
                            <span />
                            <span />
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </main>

            <div className="composer-wrap">
                <div className="input-area">
                    <textarea
                        ref={textareaRef}
                        value={input}
                        onChange={(event) => setInput(event.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Message Medha..."
                        rows="1"
                    />
                    <button
                        className="send-button"
                        onClick={sendMessage}
                        disabled={loading || !input.trim()}
                        aria-label="Send message"
                    >
                        {loading ? "…" : "↑"}
                    </button>
                </div>

                <p className="composer-hint">
                    Enter to send · Shift + Enter for a new line · Click Connected
                    to test the backend
                </p>
            </div>
        </div>
    );
}

export default App;
