import React from 'react';

const AdminMessage: React.FC = () => {
  return (
    <div className="px-0 px-md-2">
      <div className="card border-0 shadow-sm" style={{ borderRadius: 16 }}>
        <div className="card-body p-4">
          <h2 className="fw-bold mb-3">📨 관리자 쪽지 조회</h2>
          <p className="text-muted mb-3">관리자 쪽지 조회 기능은 기존 페이지에서 이용 가능합니다.</p>
          <a
            href="/admin/message"
            target="_blank"
            rel="noopener noreferrer"
            className="btn btn-primary"
          >
            쪽지 조회 페이지 열기
          </a>
        </div>
      </div>
    </div>
  );
};

export default AdminMessage;
