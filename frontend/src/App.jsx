import {useState} from "react";
import "./App.css";

function App(){
    const [messages,setMessages]=useState([]);
    const [input,setInput]=useState("");
    const [loading,setLoading]=useState(false);

    const sendMessage=async()=>{
        const message=input.trim();

        if(!message||loading){
            return;
        }

        setMessages(prev=>[
            ...prev,
            {
                role:"user",
                message:message
            }
        ]);

        setInput("");
        setLoading(true);

        try{
            const response=await fetch("http://127.0.0.1:8000/api/chat",{
                method:"POST",
                headers:{
                    "Content-Type":"application/json"
                },
                body:JSON.stringify({
                    message:message
                })
            });

            if(!response.ok){
                throw new Error("Backend request failed");
            }

            const data=await response.json();

            setMessages(prev=>[
                ...prev,
                {
                    role:"assistant",
                    message:data.response
                }
            ]);
        }
        catch(error){
            console.error(error);

            setMessages(prev=>[
                ...prev,
                {
                    role:"assistant",
                    message:"I couldn't connect to my backend."
                }
            ]);
        }
        finally{
            setLoading(false);
        }
    };

    const handleKeyDown=(event)=>{
        if(event.key==="Enter"&&!event.shiftKey){
            event.preventDefault();
            sendMessage();
        }
    };

    return(
        <div className="app">
            <header className="header">
                <div>
                    <h1>Medha</h1>
                    <p>Your personal assistant</p>
                </div>

                <div className="status">
                    <span className="status-dot"></span>
                    Online
                </div>
            </header>

            <main className="chat-container">
                {messages.length===0&&(
                    <div className="welcome">
                        <h2>Hello, Sathwik.</h2>
                        <p>I'm Medha. Talk to me.</p>
                    </div>
                )}

                {messages.map((item,index)=>(
                    <div
                        key={index}
                        className={`message-row ${item.role}`}
                    >
                        <div className="message">
                            {item.message}
                        </div>
                    </div>
                ))}

                {loading&&(
                    <div className="message-row assistant">
                        <div className="message loading">
                            Medha is thinking...
                        </div>
                    </div>
                )}
            </main>

            <div className="input-area">
                <textarea
                    value={input}
                    onChange={event=>setInput(event.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Talk to Medha..."
                    rows="1"
                />

                <button
                    onClick={sendMessage}
                    disabled={loading||!input.trim()}
                >
                    Send
                </button>
            </div>
        </div>
    );
}

export default App;