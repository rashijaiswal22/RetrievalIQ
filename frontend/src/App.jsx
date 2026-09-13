import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatWindow from './components/ChatWindow';
import MessageInput from './components/MessageInput';

function App() {
  const [messages, setMessages] = useState([]);
  const [streamingText, setStreamingText] = useState('');
  const [loading, setLoading] = useState(false);

  const [sessionId, setSessionId] = useState(
    'session_' + Math.random().toString(36).substring(7)
  );

  const handleNewChat = () => {
    setMessages([]);
    setStreamingText('');

    setSessionId(
      'session_' + Math.random().toString(36).substring(7)
    );
  };

  const handleSendMessage = async (question) => {
    setMessages((prev) => [
      ...prev,
      {
        sender: 'user',
        text: question,
      },
    ]);

    setLoading(true);
    setStreamingText('');

    try {
      const response = await fetch(
        'http://127.0.0.1:8000/chat/stream',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            question: question,
            session_id: sessionId,
          }),
        }
      );

      if (!response.ok) {
        throw new Error('Failed to get streaming response');
      }

      if (!response.body) {
        throw new Error('Streaming response body is unavailable');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');

      let fullBotResponse = '';
      let buffer = '';
      let doneReceived = false;

      while (!doneReceived) {
        const { done, value } = await reader.read();

        if (done) {
          break;
        }

        buffer += decoder.decode(value, {
          stream: true,
        });

        const events = buffer.split('\n\n');

        buffer = events.pop() || '';

        for (const event of events) {
          const line = event.trim();

          if (!line.startsWith('data: ')) {
            continue;
          }

          const dataStr = line.substring(6);

          if (dataStr.trim() === '[DONE]') {
            doneReceived = true;
            break;
          }

          try {
            const parsed = JSON.parse(dataStr);

            let text = '';

            if (typeof parsed === 'string') {
              text = parsed;
            } else if (Array.isArray(parsed)) {
              text = parsed
                .map((item) => {
                  if (typeof item === 'string') {
                    return item;
                  }

                  if (
                    item &&
                    typeof item === 'object' &&
                    typeof item.text === 'string'
                  ) {
                    return item.text;
                  }

                  return '';
                })
                .join('');
            } else if (
              parsed &&
              typeof parsed === 'object' &&
              typeof parsed.text === 'string'
            ) {
              text = parsed.text;
            }

            if (text) {
              fullBotResponse += text;
              setStreamingText(fullBotResponse);
            }
          } catch (error) {
            console.error('SSE parsing error:', error);
          }
        }
      }

      setMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: fullBotResponse,
        },
      ]);
    } catch (err) {
      console.error('Chat error:', err);

      setMessages((prev) => [
        ...prev,
        {
          sender: 'bot',
          text: '❌ Connection Error! Unable to fetch response from server.',
        },
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

          <ChatWindow
            messages={messages}
            streamingText={streamingText}
            loading={loading}
          />

          <MessageInput
            onSend={handleSendMessage}
            disabled={loading}
          />

        </div>

      </div>
    </div>
  );
}

export default App;
