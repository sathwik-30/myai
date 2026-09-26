import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL =
    import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [backendOnline, setBackendOnline] = useState(false);
    const textareaRef = useRef(null);
    const messagesEndRef = useRef(null);

    const checkBackend = async () => {
        try {
            const response = await fetch(
                `${API_BASE_URL}/api/health`,
                { cache: "no-store" }
            );

            setBackendOnline(response.ok);
        } catch {
            setBackendOnline(false);
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
                throw new Error(`Backend returned HTTP ${response.status}`);
            }

            const data = await response.json();

            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    message: data.response || "I received your message, but no response was returned.",
                },
            ]);

            setBackendOnline(true);
        } catch (error) {
            console.error("Medha backend error:", error);
            setBackendOnline(false);

            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    message:
                        "I can't reach Medha's backend right now. Make sure the FastAPI server is running on port 8000.",
                },
            ]);
        } finally {
            setLoading(false);
            setTimeout(() => textareaRef.current?.focus(), 0);
        }
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

                <div className={`status ${backendOnline ? "online" : "offline"}`}>
                    <span className="status-dot" />
                    {backendOnline ? "Connected" : "Offline"}
                </div>
            </header>

            <main className="chat-container">
                {messages.length === 0 && (
                    <section className="welcome">
                        <div className="welcome-icon">M</div>
                        <p className="eyebrow">YOUR PERSONAL ASSISTANT</p>
                        <h2>What can I help you with?</h2>
                        <p className="welcome-text">
                            Talk naturally. Medha uses what it has learned from you
                            to understand and respond.
                        </p>
                        <div className="suggestions">
                            <button onClick={() => setInput("Hi Medha")}>Say hello</button>
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
                        <div className="message">{item.message}</div>
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
                        ↑
                    </button>
                </div>
                <p className="composer-hint">
                    Enter to send · Shift + Enter for a new line
                </p>
            </div>
        </div>
    );
}

export default App;
