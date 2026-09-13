import React, { useState } from 'react';
import { FiUploadCloud, FiFileText, FiPlus } from 'react-icons/fi';

const Sidebar = ({ onNewChat }) => {
  const [uploading, setUploading] = useState(false);
  const [statusMsg, setStatusMsg] = useState('');

  const handleFileUpload = async (e) => {
    const files = e.target.files;
    if (!files.length) return;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append('files', files[i]);
    }

    setUploading(true);
    setStatusMsg("Processing Document's...");

    try {
      const res = await fetch('http://127.0.0.1:8000/upload', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (res.ok) {
        setStatusMsg(`✅ Successfully Processed ${files.length} file(s) into ${data.chunks} chunks.`);
      } else {
        setStatusMsg(`❌ Error: ${data.detail}`);
      }
    } catch (err) {
      setStatusMsg('❌ Upload failed! Unable to connect with Server.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="col-md-3 col-lg-2 sidebar-bg p-3 d-flex flex-column h-100">
      <button className="btn btn-outline-light text-start mb-4 d-flex align-items-center gap-2" onClick={onNewChat}>
        <FiPlus /> New Chat
      </button>

      <div className="mb-4">
        <label className="form-label text-secondary fw-semibold small">UPLOAD DOCUMENTS</label>
        <div className="p-3 border border-secondary rounded text-center" style={{ backgroundColor: '#2a2b32', borderStyle: 'dashed' }}>
          <FiUploadCloud size={30} className="mb-2 text-success" />
          <p className="small mb-2 text-light">Select Multi-Documents</p>
          <input type="file" multiple accept=".pdf,.docx,.pptx,.ppt" id="pdfInput" className="d-none" onChange={handleFileUpload} />
          <label htmlFor="pdfInput" className="btn btn-sm btn-success w-100 fw-bold cursor-pointer">
            {uploading ? 'Processing...' : 'Browse Documents'}
          </label>
        </div>
        {statusMsg && <p className="small mt-2 text-info" style={{ wordBreak: 'break-word' }}>{statusMsg}</p>}
      </div>

      <div className="mt-auto border-top border-secondary pt-3">
        <div className="d-flex align-items-center gap-2 text-secondary small">
          <FiFileText /> RetrievalIQ Core • Hybrid AI Engine
        </div>
      </div>
    </div>
  );
};

export default Sidebar;


