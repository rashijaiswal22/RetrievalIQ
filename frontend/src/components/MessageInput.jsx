import React, { useState } from 'react';
import { FiSend } from 'react-icons/fi';

const MessageInput = ({ onSend, disabled }) => {
  const [text, setText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (text.trim() && !disabled) {
      onSend(text);
      setText('');
    }
  };

  return (
    <div className="p-3 chat-bg">
      <div className="container-lg">
        <form onSubmit={handleSubmit} className="position-relative">
          <input
            type="text"
            className="form-control form-control-lg chat-input-box pe-5 rounded-3"
            placeholder="Ask anything about your uploaded documents or files..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={disabled}
          />
          <button
            type="submit"
            className="btn btn-success position-absolute end-0 top-50 translate-middle-y me-2 rounded-2"
            disabled={disabled || !text.trim()}
          >
            <FiSend />
          </button>
        </form>
      </div>
    </div>
  );
};

export default MessageInput;