import React, { useEffect, useRef } from "react";
import "./ChatContainer.css";

interface Message {
  sender: string;
  message: string;
}

interface ChatContainerProps {
  chatMessages: Message[];
}

const ChatContainer: React.FC<ChatContainerProps> = ({ chatMessages }) => {
  const chatBoxRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTo({
        top: chatBoxRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [chatMessages]);

  return (
    <div className="chat-wrapper">
      <h2 className="chat-title">Conversation</h2>

      <div className="chat-box" ref={chatBoxRef}>
        {chatMessages.map((msg, index) => {
          const isAgent = msg.sender.toLowerCase() === "agent";

          return (
            <div
              key={index}
              className={`chat-message ${isAgent ? "agent" : "user"}`}
            >
              <div className="bubble fadeIn">
                <span className="sender">{msg.sender}</span>
                <p className="text">{msg.message}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ChatContainer;
