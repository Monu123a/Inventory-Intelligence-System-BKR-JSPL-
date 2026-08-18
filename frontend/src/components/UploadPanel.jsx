import { useRef, useState } from 'react';
import './UploadPanel.css';

import api from '../services/api';

export default function UploadPanel({ uploadedFiles, setUploadedFiles }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = async (fileList) => {
    const formData = new FormData();
    for (const f of fileList) {
      if (f.name.endsWith('.xlsx') || f.name.endsWith('.xls')) {
        formData.append('files', f);
      }
    }
    try {
      const res = await api.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      const data = res.data;
      if (data.files) {
        setUploadedFiles(prev => [...prev, ...data.files]);
      }
    } catch (err) {
      console.error('Upload failed:', err);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    handleFiles(e.dataTransfer.files);
  };

  const onDragOver = (e) => { e.preventDefault(); setDragOver(true); };
  const onDragLeave = () => setDragOver(false);

  const onChange = (e) => {
    handleFiles(e.target.files);
    e.target.value = '';
  };

  const removeFile = (name) => {
    setUploadedFiles(prev => prev.filter(f => f.name !== name));
  };

  const formatSize = (bytes) => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1048576).toFixed(1) + ' MB';
  };

  return (
    <div className="card">
      <div className="card-title">📁 Upload Files</div>
      <div
        className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
        onClick={() => inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
      >
        <span className="upload-icon">📤</span>
        <p className="upload-text">Drop Excel files here or click to browse</p>
        <p className="upload-hint">Supports .xlsx and .xls files</p>
        <input
          ref={inputRef}
          type="file"
          className="upload-input"
          multiple
          accept=".xlsx,.xls"
          onChange={onChange}
        />
      </div>

      {uploadedFiles.length > 0 && (
        <div className="file-list">
          {uploadedFiles.map((f, i) => (
            <div key={i} className="file-item">
              <div className="file-info">
                <span className="file-icon">📊</span>
                <div>
                  <div className="file-name">{f.name}</div>
                  <div className="file-size">{formatSize(f.size)}</div>
                </div>
              </div>
              <button className="file-remove" onClick={() => removeFile(f.name)}>✕</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
