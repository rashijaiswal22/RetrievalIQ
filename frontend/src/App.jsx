import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import MessageInput from './components/MessageInput';

function App() {
  const [messages, setMessages] = useState([]);
  const [streamingText, setStreamingText] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState('session_' + Math.random().toString(36).substring(7));

  const handleNewChat = () => {
    setMessages([]);
    setStreamingText('');
    setSessionId('session_' + Math.random().toString(36).substring(7));
  };

  const handleSendMessage = async (question) => {
    setMessages((prev) => [...prev, { sender: 'user', text: question }]);
    setLoading(true);
    setStreamingText('');

    try {
      const response = await fetch('http://127.0.0.1:8000/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question, session_id: sessionId }),
      });

      if (!response.ok) {
        throw new Error('Failed to get streaming response');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let fullBotResponse = '';
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop(); // Keep incomplete tail chunk in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '').trim();
            if (dataStr === '[DONE]') break;

            try {
              // Agar backend JSON ({ token: "..." }) bhej raha hai
              const parsed = JSON.parse(dataStr);
              if (parsed.token !== undefined) {
                fullBotResponse += parsed.token;
              } else {
                fullBotResponse += dataStr;
              }
            } catch (e) {
              // FIX: Agar backend Plain Text (yield f'data: {content}\n\n') bhej raha hai
              fullBotResponse += dataStr;
            }
            
            setStreamingText(fullBotResponse);
          }
        }
      }

      setMessages((prev) => [...prev, { sender: 'bot', text: fullBotResponse }]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { sender: 'bot', text: '❌ Connection Error! Unable to fetch response from server.' },
      ]);
    } finally {
      setStreamingText('');
      setLoading(false);
    }
  };

  return (
    <div className="container-fluid h-100 p-0">
      <div className="row g-0 h-100">
        <Sidebar onNewChat={handleNewChat} />
        <div className="col-md-9 col-lg-10 chat-bg d-flex flex-column h-100">
          <ChatWindow messages={messages} streamingText={streamingText} loading={loading} />
          <MessageInput onSend={handleSendMessage} disabled={loading} />
        </div>
      </div>
    </div>
  );
}

export default App;

