import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";
const API_CANDIDATES = [
    `${API_BASE_URL}/api`,
    "http://127.0.0.1:8000/api",
].filter((value, index, list) => list.indexOf(value) === index);

async function apiRequest(path, options = {}) {
    let lastError = null;
    for (const base of API_CANDIDATES) {
        try {
            const headers = { ...(options.headers || {}) };
            const token = localStorage.getItem("medha_token");
            if (token) headers.Authorization = `Bearer ${token}`;
            const response = await fetch(`${base}${path}`, {
                ...options,
                headers,
                cache: "no-store",
            });
            return response;
        } catch (error) {
            lastError = error;
        }
    }
    throw lastError || new Error("Unable to reach Medha backend");
}

async function jsonRequest(path, options = {}) {
    const response = await apiRequest(path, options);
    let data = {};
    try { data = await response.json(); } catch {}
    if (!response.ok) throw new Error(data.detail || `HTTP ${response.status}`);
    return data;
}

function AuthScreen({ onLogin }) {
    const [mode, setMode] = useState("login");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async (event) => {
        event.preventDefault();
        setError("");
        setLoading(true);
        try {
            const data = await jsonRequest(`/auth/${mode}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });
            localStorage.setItem("medha_token", data.token);
            localStorage.setItem("medha_username", data.username);
            onLogin(data.username);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <main className="auth-page">
            <section className="auth-card">
                <div className="brand-mark large">M</div>
                <p className="eyebrow">MEDHA</p>
                <h1>Your personal AI assistant</h1>
                <p className="auth-subtitle">Sign in to keep your conversations and memories separate.</p>
                <form onSubmit={submit}>
                    <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" autoComplete="username" />
                    <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Password" type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} />
                    {error && <div className="auth-error">{error}</div>}
                    <button className="primary-button" disabled={loading}>
                        {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
                    </button>
                </form>
                <button className="link-button" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>
                    {mode === "login" ? "Create a new account" : "I already have an account"}
                </button>
            </section>
        </main>
    );
}

function App() {
    const [username, setUsername] = useState(localStorage.getItem("medha_username") || "");
    const [chats, setChats] = useState([]);
    const [activeChat, setActiveChat] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [sidebarOpen, setSidebarOpen] = useState(true);
    const [error, setError] = useState("");
    const textareaRef = useRef(null);
    const messagesEndRef = useRef(null);

    const loadChats = async () => {
        const data = await jsonRequest("/chats");
        setChats(data.chats || []);
        if (!activeChat && data.chats?.length) await openChat(data.chats[0].id);
    };

    const openChat = async (chatId) => {
        const data = await jsonRequest(`/chats/${chatId}`);
        setActiveChat(data.chat);
        setMessages(data.messages || []);
        setError("");
    };

    const newChat = async () => {
        const data = await jsonRequest("/chats", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: "New chat" }),
        });
        await loadChats();
        await openChat(data.chat_id);
        setInput("");
        textareaRef.current?.focus();
    };

    const sendMessage = async () => {
        const message = input.trim();
        if (!message || loading || !activeChat) return;
        setInput("");
        setLoading(true);
        setError("");

        setMessages((prev) => [...prev, { role: "user", message }]);

        try {
            const data = await jsonRequest("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message, chat_id: activeChat.id }),
            });
            setMessages((prev) => [...prev, {
                role: "assistant",
                message: data.response,
                source: data.source,
                latency_ms: data.latency_ms,
            }]);
            await loadChats();
            setActiveChat((current) => current ? { ...current, updated_at: new Date().toISOString() } : current);
        } catch (err) {
            setMessages((prev) => [...prev, { role: "assistant", message: "I couldn't process that message.", error: err.message }]);
            setError(err.message);
        } finally {
            setLoading(false);
            setTimeout(() => textareaRef.current?.focus(), 0);
        }
    };

    const renameActive = async () => {
        if (!activeChat) return;
        const title = window.prompt("Chat name", activeChat.title);
        if (!title?.trim()) return;
        await jsonRequest(`/chats/${activeChat.id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ title: title.trim() }),
        });
        await loadChats();
        await openChat(activeChat.id);
    };

    const deleteActive = async () => {
        if (!activeChat || !window.confirm("Delete this chat and its messages?")) return;
        await jsonRequest(`/chats/${activeChat.id}`, { method: "DELETE" });
        setActiveChat(null);
        setMessages([]);
        const data = await jsonRequest("/chats");
        setChats(data.chats || []);
        if (data.chats?.length) await openChat(data.chats[0].id);
    };

    const logout = () => {
        localStorage.removeItem("medha_token");
        localStorage.removeItem("medha_username");
        setUsername("");
        setChats([]);
        setMessages([]);
        setActiveChat(null);
    };

    useEffect(() => {
        if (!username) return;
        loadChats().catch((err) => {
            if (String(err.message).includes("401")) logout();
            else setError(err.message);
        });
    }, [username]);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages, loading]);

    if (!username) return <AuthScreen onLogin={setUsername} />;

    return (
        <div className="app-shell">
            <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
                <div className="sidebar-top">
                    <div className="side-brand"><div className="brand-mark">M</div><strong>Medha</strong></div>
                    <button className="new-chat" onClick={newChat}>＋ New chat</button>
                </div>
                <div className="chat-list">
                    {chats.map((chat) => (
                        <button key={chat.id} className={`chat-item ${activeChat?.id === chat.id ? "active" : ""}`} onClick={() => openChat(chat.id)}>
                            <span>{chat.title}</span>
                        </button>
                    ))}
                    {!chats.length && <p className="empty-side">No conversations yet.</p>}
                </div>
                <div className="sidebar-bottom">
                    <div className="account"><span className="account-avatar">{username[0]?.toUpperCase()}</span><span>{username}</span></div>
                    <button className="side-action" onClick={renameActive} disabled={!activeChat}>Rename</button>
                    <button className="side-action danger" onClick={deleteActive} disabled={!activeChat}>Delete</button>
                    <button className="side-action" onClick={logout}>Sign out</button>
                </div>
            </aside>

            <section className="chat-app">
                <header className="header">
                    <button className="mobile-menu" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
                    <div>
                        <h1>{activeChat?.title || "New chat"}</h1>
                        <p>Personal AI assistant</p>
                    </div>
                    {error && <span className="header-error">{error}</span>}
                </header>

                <main className="chat-container">
                    {!activeChat && (
                        <section className="welcome">
                            <div className="welcome-icon">M</div>
                            <p className="eyebrow">WELCOME BACK, {username.toUpperCase()}</p>
                            <h2>Start a new conversation</h2>
                            <button className="primary-button welcome-button" onClick={newChat}>＋ New chat</button>
                        </section>
                    )}

                    {messages.map((item) => (
                        <div key={item.id || `${item.created_at}-${Math.random()}`} className={`message-row ${item.role}`}>
                            {item.role === "assistant" && <div className="avatar">M</div>}
                            <div>
                                <div className={`message ${item.error ? "error-message" : ""}`}>{item.message}</div>
                                {item.error && <div className="message-error-detail">{item.error}</div>}
                                {item.role === "assistant" && !item.error && <div className="message-meta">{item.source || "medha"}{item.latency_ms ? ` · ${item.latency_ms} ms` : ""}</div>}
                            </div>
                        </div>
                    ))}
                    {loading && <div className="message-row assistant"><div className="avatar">M</div><div className="message loading"><span/><span/><span/></div></div>}
                    <div ref={messagesEndRef} />
                </main>

                <div className="composer-wrap">
                    <div className="input-area">
                        <textarea ref={textareaRef} value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); } }} placeholder={activeChat ? "Message Medha..." : "Create a chat first..."} rows="1" disabled={!activeChat}/>
                        <button className="send-button" onClick={sendMessage} disabled={loading || !input.trim() || !activeChat}>↑</button>
                    </div>
                    <p className="composer-hint">Enter to send · Shift + Enter for a new line</p>
                </div>
            </section>
        </div>
    );
}

export default App;
