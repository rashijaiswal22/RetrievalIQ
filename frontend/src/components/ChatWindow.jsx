import React, { useEffect, useRef } from 'react';
import { FiUser, FiCpu } from 'react-icons/fi';
import ReactMarkdown from 'react-markdown'; // 👈 Yahan Import kiya

const ChatWindow = ({ messages, streamingText, loading }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText, loading]);

  return (
    <div className="flex-grow-1 overflow-auto p-0">
      {messages.length === 0 && !streamingText && !loading ? (
        <div className="h-100 d-flex flex-column justify-content-center align-items-center text-center p-4">
          <h2 className="fw-bold mb-3 text-light">Document RAG AI</h2>
          <p className="text-secondary" style={{ maxWidth: '400px' }}>
            Upload the file from Left panel and start the conversation. Conversation History is restored!
          </p>
        </div>
      ) : (
        <div>
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`py-4 px-4 px-md-5 ${
                msg.sender === 'user'
                  ? 'user-msg'
                  : 'bot-msg border-top border-bottom border-secondary border-opacity-25'
              }`}
            >
              <div className="container-lg d-flex gap-3 max-w-3xl">
                <div className="avatar">
                  {msg.sender === 'user' ? (
                    <div className="bg-primary rounded p-2 text-white">
                      <FiUser size={18} />
                    </div>
                  ) : (
                    <div className="bg-success rounded p-2 text-white">
                      <FiCpu size={18} />
                    </div>
                  )}
                </div>
                <div className="text-light align-self-center markdown-body" style={{ width: '100%' }}>
                  <ReactMarkdown>{msg.text}</ReactMarkdown>
                </div>
              </div>
            </div>
          ))}

          {loading && !streamingText && (
            <div className="py-4 px-4 px-md-5 bot-msg border-top border-bottom border-secondary border-opacity-25">
              <div className="container-lg d-flex gap-3">
                <div className="avatar">
                  <div className="bg-success rounded p-2 text-white">
                    <FiCpu size={18} />
                  </div>
                </div>
                <div className="text-secondary align-self-center fst-italic">
                  Thinking and searching documents...
                </div>
              </div>
            </div>
          )}

          {streamingText && (
            <div className="py-4 px-4 px-md-5 bot-msg border-top border-bottom border-secondary border-opacity-25">
              <div className="container-lg d-flex gap-3">
                <div className="avatar">
                  <div className="bg-success rounded p-2 text-white">
                    <FiCpu size={18} />
                  </div>
                </div>
                <div className="text-light align-self-center markdown-body" style={{ width: '100%' }}>
                  <ReactMarkdown>{streamingText}</ReactMarkdown>
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      )}
    </div>
  );
};

export default ChatWindow;