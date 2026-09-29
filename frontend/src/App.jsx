import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_URL || "";
const API_CANDIDATES = [
    `${API_BASE_URL}/api`,
    "http://127.0.0.1:8000/api",
].filter((value, index, list) => list.indexOf(value) === index);

function getErrorMessage(data, fallback) {
    if (typeof data?.detail === "string") return data.detail;
    if (Array.isArray(data?.detail)) {
        return data.detail.map((item) => item?.msg || String(item)).join("; ");
    }
    if (data?.detail && typeof data.detail === "object") {
        return data.detail.message || data.detail.msg || JSON.stringify(data.detail);
    }
    return fallback;
}

async function apiRequest(path, options = {}) {
    let lastError = null;
    const timeoutMs = options.timeoutMs ?? 8000;
    const { timeoutMs: _timeoutMs, ...fetchOptions } = options;

    for (const base of API_CANDIDATES) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), timeoutMs);
        try {
            const headers = { ...(fetchOptions.headers || {}) };
            const token = localStorage.getItem("medha_token");
            if (token) headers.Authorization = `Bearer ${token}`;
            if (fetchOptions.signal) {
                fetchOptions.signal.addEventListener("abort", () => controller.abort(), { once: true });
            }

            const response = await fetch(`${base}${path}`, {
                ...fetchOptions,
                headers,
                signal: controller.signal,
                cache: "no-store",
            });
            return response;
        } catch (error) {
            lastError = error.name === "AbortError"
                ? new Error("Medha backend request timed out or was cancelled.")
                : error;
        } finally {
            clearTimeout(timer);
        }
    }
    throw lastError || new Error("Unable to reach Medha backend");
}

async function jsonRequest(path, options = {}) {
    const response = await apiRequest(path, options);
    let data = {};
    try { data = await response.json(); } catch {}
    if (!response.ok) {
        const error = new Error(getErrorMessage(data, `HTTP ${response.status}`));
        error.status = response.status;
        throw error;
    }
    return data;
}

function AuthScreen({ onLogin }) {
    const [mode, setMode] = useState("login");
    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [recoveryCode, setRecoveryCode] = useState("");
    const [error, setError] = useState("");
    const [notice, setNotice] = useState("");
    const [loading, setLoading] = useState(false);

    const submit = async (event) => {
        event.preventDefault();
        setError("");
        setNotice("");
        setLoading(true);
        try {
            if (mode === "reset") {
                await jsonRequest("/auth/password/reset", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ username, recovery_code: recoveryCode, new_password: password }),
                });
                setNotice("Password reset successfully. Sign in with your new password.");
                setPassword("");
                setRecoveryCode("");
                setMode("login");
                return;
            }

            const data = await jsonRequest(`/auth/${mode}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, password }),
            });
            localStorage.setItem("medha_token", data.token);
            localStorage.setItem("medha_username", data.username);

            if (mode === "register" && data.recovery_code) {
                window.alert(`Account created. Save this recovery code somewhere safe:\n\n${data.recovery_code}`);
            }
            onLogin(data.username);
        } catch (err) {
            setError(err.message || "Authentication failed");
        } finally {
            setLoading(false);
        }
    };

    const switchMode = (next) => {
        setMode(next);
        setError("");
        setNotice("");
        setPassword("");
        setRecoveryCode("");
    };

    return (
        <main className="auth-page">
            <section className="auth-card">
                <div className="brand-mark large">M</div>
                <p className="eyebrow">MEDHA</p>
                <h1>{mode === "login" ? "Welcome back" : mode === "register" ? "Create your Medha account" : "Reset your password"}</h1>
                <p className="auth-subtitle">
                    {mode === "login"
                        ? "Sign in to keep your conversations and memories separate."
                        : mode === "register"
                            ? "Create a private account for your conversations and memories."
                            : "Use your username and recovery code to set a new password."}
                </p>
                <form onSubmit={submit}>
                    <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" autoComplete="username" minLength={3} maxLength={40} required />
                    {mode === "reset" && (
                        <input value={recoveryCode} onChange={(e) => setRecoveryCode(e.target.value)} placeholder="Recovery code" autoComplete="off" minLength={12} maxLength={128} required />
                    )}
                    <input value={password} onChange={(e) => setPassword(e.target.value)} placeholder={mode === "login" ? "Password" : "New password (8+ characters)"} type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} minLength={8} maxLength={128} required />
                    {error && <div className="auth-error">{error}</div>}
                    {notice && <div className="auth-notice">{notice}</div>}
                    <button className="primary-button" disabled={loading}>
                        {loading ? "Please wait…" : mode === "login" ? "Sign in" : mode === "register" ? "Create account" : "Reset password"}
                    </button>
                </form>
                {mode === "login" && (
                    <>
                        <button className="link-button" onClick={() => switchMode("register")}>Create a new account</button>
                        <button className="link-button" onClick={() => switchMode("reset")}>Forgot password</button>
                    </>
                )}
                {mode === "register" && (
                    <button className="link-button" onClick={() => switchMode("login")}>I already have an account</button>
                )}
                {mode === "reset" && (
                    <button className="link-button" onClick={() => switchMode("login")}>Back to sign in</button>
                )}
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
    const activeChatIdRef = useRef(null);
    const requestControllerRef = useRef(null);

    const loadChats = async () => {
        const data = await jsonRequest("/chats");
        const nextChats = data.chats || [];
        setChats(nextChats);
        return nextChats;
    };

    const openChat = async (chatId) => {
        const data = await jsonRequest(`/chats/${chatId}`);
        setActiveChat(data.chat);
        setMessages(data.messages || []);
        setError("");
    };

    const newChat = async (initialPrompt = "") => {
        if (loading) return;
        setError("");
        try {
            const data = await jsonRequest("/chats", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: "New chat" }),
            });
            if (!data.chat_id) throw new Error("The backend did not return a chat ID.");

            const chat = {
                id: data.chat_id,
                title: "New chat",
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
            };
            setChats((current) => [chat, ...current]);
            setActiveChat(chat);
            setMessages([]);
            setInput(initialPrompt);
            setTimeout(() => textareaRef.current?.focus(), 0);
        } catch (err) {
            setError(`Could not create chat: ${err.message}`);
        }
    };

    useEffect(() => {
        activeChatIdRef.current = activeChat?.id ?? null;
    }, [activeChat]);

    const stopResponse = () => {
        requestControllerRef.current?.abort();
        requestControllerRef.current = null;
        setLoading(false);
    };

    const sendMessage = async () => {
        const message = input.trim();
        if (!message || loading || !activeChat) return;
        const sentChatId = activeChat.id;
        setInput("");
        setLoading(true);
        setError("");

        const controller = new AbortController();
        requestControllerRef.current = controller;
        setMessages((prev) => [...prev, { role: "user", message }]);

        try {
            const data = await jsonRequest("/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message, chat_id: activeChat.id }),
                signal: controller.signal,
                timeoutMs: 20000,
            });
            if (activeChatIdRef.current === sentChatId) {
                setMessages((prev) => [...prev, {
                    role: "assistant",
                    message: data.response,
                    source: data.source,
                    latency_ms: data.latency_ms,
                }]);
            }
            await loadChats();
            setActiveChat((current) => current ? { ...current, updated_at: new Date().toISOString() } : current);
        } catch (err) {
            if (err.name === "AbortError") return;
            if (activeChatIdRef.current === sentChatId) setError(err.message);
        } finally {
            if (requestControllerRef.current === controller) {
                requestControllerRef.current = null;
                setLoading(false);
            }
            setTimeout(() => textareaRef.current?.focus(), 0);
        }
    };

    const renameActive = async () => {
        if (!activeChat) return;
        const title = window.prompt("Chat name", activeChat.title);
        if (!title?.trim() || title.trim() === activeChat.title) return;
        try {
            const nextTitle = title.trim();
            await jsonRequest(`/chats/${activeChat.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: nextTitle }),
            });
            setChats((current) => current.map((item) => item.id === activeChat.id ? { ...item, title: nextTitle } : item));
            setActiveChat((current) => current ? { ...current, title: nextTitle } : current);
        } catch (err) {
            setError(`Could not rename chat: ${err.message}`);
        }
    };

    const renameChat = async (chat) => {
        const title = window.prompt("Rename chat", chat.title);
        if (!title?.trim() || title.trim() === chat.title) return;
        try {
            const nextTitle = title.trim();
            await jsonRequest(`/chats/${chat.id}`, {
                method: "PATCH",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ title: nextTitle }),
            });
            setChats((current) => current.map((item) => item.id === chat.id ? { ...item, title: nextTitle } : item));
            if (activeChat?.id === chat.id) setActiveChat((current) => current ? { ...current, title: nextTitle } : current);
        } catch (err) {
            setError(`Could not rename chat: ${err.message}`);
        }
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

    const changePassword = async () => {
        const currentPassword = window.prompt("Current password");
        if (!currentPassword) return;
        const newPassword = window.prompt("New password (8+ characters)");
        if (!newPassword) return;
        try {
            await jsonRequest("/auth/password/change", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
            });
            window.alert("Password changed successfully.");
        } catch (err) {
            setError(err.message);
        }
    };

    const generateRecoveryCode = async () => {
        try {
            const data = await jsonRequest("/auth/password/recovery-code", { method: "POST" });
            window.alert(`Save this recovery code somewhere safe. It will be needed if you forget your password:\n\n${data.recovery_code}`);
        } catch (err) {
            setError(err.message);
        }
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
        loadChats()
            .then((nextChats) => nextChats.length ? openChat(nextChats[0].id) : null)
            .catch((err) => {
                if (err.status === 401) logout();
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
                        <div key={chat.id} className={`chat-item-wrap ${activeChat?.id === chat.id ? "active" : ""}`}>
                            <button className="chat-item" onClick={() => openChat(chat.id)}><span>{chat.title}</span></button>
                            <button className="chat-rename" onClick={(event) => { event.stopPropagation(); renameChat(chat); }} title="Rename chat" aria-label={`Rename ${chat.title}`}>✎</button>
                        </div>
                    ))}
                    {!chats.length && <p className="empty-side">No conversations yet.</p>}
                </div>
                <div className="sidebar-bottom">
                    <div className="account"><span className="account-avatar">{username[0]?.toUpperCase()}</span><span>{username}</span></div>
                    <button className="side-action" onClick={renameActive} disabled={!activeChat}>Rename</button>
                    <button className="side-action" onClick={changePassword}>Change password</button>
                    <button className="side-action" onClick={generateRecoveryCode}>Recovery code</button>
                    <button className="side-action danger" onClick={deleteActive} disabled={!activeChat}>Delete</button>
                    <button className="side-action" onClick={logout}>Sign out</button>
                </div>
            </aside>

            <section className="chat-app">
                <header className="header">
                    <button className="mobile-menu" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
                    <div>
                        <h1>{activeChat?.title || "New chat"}</h1>
                        <p>Independent local AI · memory enabled · no runtime LLM</p>
                    </div>
                    {error && <span className="header-error">{error}</span>}
                </header>

                <main className="chat-container">
                    {!activeChat && (
                        <section className="welcome">
                            <div className="welcome-heading">
                                <div className="welcome-icon">M</div>
                                <div>
                                    <p className="eyebrow">MEDHA AI</p>
                                    <h2>How can I help, {username}?</h2>
                                    <p className="welcome-text">Your private mini assistant for learning, projects, research, memory, and everyday work.</p>
                                </div>
                            </div>
                            <div className="quick-grid">
                                <button className="quick-card" onClick={() => newChat("Help me learn a topic step by step")}><span className="quick-icon">✦</span><strong>Learn something</strong><small>Explain a topic clearly</small></button>
                                <button className="quick-card" onClick={() => newChat("Help me debug my code")}><span className="quick-icon">⌘</span><strong>Work on code</strong><small>Debug, design, or improve</small></button>
                                <button className="quick-card" onClick={() => newChat("Help me research this topic")}><span className="quick-icon">⌕</span><strong>Research</strong><small>Use knowledge and the web</small></button>
                                <button className="quick-card" onClick={() => newChat("Help me plan my next task")}><span className="quick-icon">✓</span><strong>Plan work</strong><small>Break a goal into steps</small></button>
                            </div>
                            <button className="primary-button welcome-button" onClick={newChat}>＋ Start new chat</button>
                        </section>
                    )}

                    {messages.map((item) => (
                        <div key={item.id || `${item.created_at}-${item.role}-${item.message}`} className={`message-row ${item.role}`}>
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
                        {loading ? <button className="stop-button" onClick={stopResponse} aria-label="Stop response" title="Stop response">■</button> : <button className="send-button" onClick={sendMessage} disabled={!input.trim() || !activeChat} aria-label="Send message" title="Send message">↑</button>}
                    </div>
                    <p className="composer-hint">Enter to send · Shift + Enter for a new line</p>
                </div>
            </section>
        </div>
    );
}

export default App;
