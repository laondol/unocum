export default function TermsPage() {
  return (
    <div className="container py-4" style={{ maxWidth: 800 }}>
      <h3 className="fw-bold text-center mb-4">📋 회원약관 및 닢 운영 규칙</h3>
      <p className="text-center text-muted small mb-4">시행일: 2026년 6월 10일 | 함께사는양평 운영위원회</p>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 18 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold">제1장 총칙</h5>
          <hr />
          <h6 className="fw-bold mt-3">제1조 (목적)</h6>
          <p>본 약관은 함께사는양평(이하 &ldquo;서비스&rdquo;)이 제공하는 온라인 커뮤니티 서비스의 이용 조건 및 절차, 회원과 운영진의 권리·의무·책임을 규정함을 목적으로 합니다.</p>
          <h6 className="fw-bold mt-3">제2조 (용어의 정의)</h6>
          <ol className="small">
            <li><strong>&ldquo;회원&rdquo;</strong>이란 본 약관에 동의하고 서비스에 가입하여 서비스를 이용하는 자를 말합니다.</li>
            <li><strong>&ldquo;관리자(admin)&rdquo;</strong>란 서비스의 전반적인 운영 및 관리를 담당하는 자를 말합니다.</li>
            <li><strong>&ldquo;책임자(leader)&rdquo;</strong>란 권역별 커뮤니티 운영 책임을 맡은 자를 말합니다.</li>
            <li><strong>&ldquo;활동가(activist)&rdquo;</strong>란 같은 리(里) 주민과 소통하며 커뮤니티 활동을 촉진하는 자를 말합니다.</li>
            <li><strong>&ldquo;벗&rdquo;</strong>이란 회원 간 승인된 친구 관계를 말합니다.</li>
            <li><strong>&ldquo;닢&rdquo;</strong>이란 서비스 내에서 사용되는 가상 포인트를 말합니다.</li>
          </ol>
          <h6 className="fw-bold mt-3">제3조 (약관의 게시 및 개정)</h6>
          <p>본 약관은 서비스 가입 화면에 게시되며, 운영위원회의 의결을 거쳐 개정될 수 있습니다. 개정 시 최소 7일 전 공지사항을 통해 고지합니다.</p>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 18 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold">제2장 회원 가입 및 관리</h5>
          <hr />
          <h6 className="fw-bold mt-3">제4조 (가입 자격)</h6>
          <p>양평에 대해 관심이 있고 함께하는 양평의 회원약관과 운영규칙을 잘 준수할 수 있는 누구나 가입할 수 있습니다. 가입 시 실명, 연락처, 거주지 정보를 제공하여야 합니다.</p>
          <h6 className="fw-bold mt-3">제5조 (주민 인증 및 활동 범위)</h6>
          <ol className="small">
            <li>GPS 위치 기반 인증 또는 고지서·지역화폐카드 사진 제출을 통해 리(里) 단위 주민 인증을 받을 수 있습니다.</li>
            <li><strong>리 단위 인증을 완료한 회원</strong>은 오프라인 모임 참여, 마을 의사결정 투표, 활동가 보증 등 대면 활동이 가능합니다.</li>
            <li><strong>리 단위 인증을 하지 않은 회원</strong>은 온라인 활동(게시글, 댓글, 공유 등)만 가능하며, 오프라인 활동에 제약이 있을 수 있습니다.</li>
            <li>고지서 사진은 인증 확인 후 즉시 파기되며 별도 저장되지 않습니다.</li>
          </ol>
          <h6 className="fw-bold mt-3">제6조 (회원 탈퇴 및 자격 상실)</h6>
          <ol className="small">
            <li>회원은 언제든지 탈퇴를 요청할 수 있으며, 운영진은 지체 없이 처리합니다.</li>
            <li>다음 각 호에 해당하는 경우 회원 자격을 제한 또는 상실시킬 수 있습니다:
              <ul>
                <li>타인의 정보를 도용한 경우</li>
                <li>서비스를 이용하여 법령 또는 공서양속에 위반되는 행위를 한 경우</li>
                <li>타 회원에게 심각한 피해를 입히는 행위를 한 경우</li>
                <li>AI 지킴이의 연속 3회 이상 게시불가 판정을 받은 경우</li>
              </ul>
            </li>
          </ol>
          <h6 className="fw-bold mt-3">제7조 (벗 관계)</h6>
          <ol className="small">
            <li>회원은 다른 회원에게 벗 신청을 할 수 있으며, 상대방이 수락하면 벗 관계가 성립됩니다.</li>
            <li>벗 관계 해지는 일방의 요청으로 가능하며, 분쟁 발생 시 중재위원회의 조정을 따릅니다.</li>
            <li>벗 관계 해지 시에도 당사자 간 분쟁은 중재위원회의 조정 규칙을 따라야 합니다.</li>
            <li>벗 관계인 회원 간에만 쪽지 발송이 가능합니다(관리자, 책임자, 활동가 제외).</li>
          </ol>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 18 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold">제3장 닢</h5>
          <hr />
          <h6 className="fw-bold mt-3">제8조 (닢 지급)</h6>
          <table className="table table-bordered small">
            <thead className="table-light">
              <tr><th>구분</th><th>지급액</th><th>비고</th></tr>
            </thead>
            <tbody>
              <tr><td>회원 가입</td><td className="text-success fw-bold">+1,000닢</td><td>최초 1회. 전 회원 수 10,000명이 될 때까지 가입 시 선지급</td></tr>
              <tr><td>30일 주기 지급</td><td className="text-success fw-bold">+1,000닢</td><td>매 30일마다 로그인 시 자동 지급 (10,000명 도달 시까지)</td></tr>
            </tbody>
          </table>
          <h6 className="fw-bold mt-3">제9조 (닢 차감)</h6>
          <table className="table table-bordered small">
            <thead className="table-light">
              <tr><th>항목</th><th>차감액</th><th>비고</th></tr>
            </thead>
            <tbody>
              <tr><td>게시글 등록</td><td className="text-danger fw-bold">-100닢</td><td>게시판(누구의꿈) 등록 시</td></tr>
              <tr><td>게시글 수정</td><td className="text-danger fw-bold">-100닢</td><td>게시불가(-50점 이하) 게시물 수정 시에만 차감</td></tr>
              <tr><td>댓글 작성</td><td className="text-danger fw-bold">-10닢</td><td>게시글 댓글, 뉴스 댓글 포함</td></tr>
              <tr><td>타인 댓글에 답글</td><td className="text-danger fw-bold">-10닢</td><td>자신의 댓글에 답글은 무료</td></tr>
              <tr><td>쪽지 발송</td><td className="text-danger fw-bold">-10닢</td><td>1통당</td></tr>
              <tr><td>좋아요</td><td className="text-danger fw-bold">-5닢</td><td>좋아요 누른 회원 차감 (게시물당 1회만 가능)</td></tr>
              <tr><td>나빠요</td><td className="text-danger fw-bold">-5닢</td><td>나빠요 누른 회원 차감 (게시물당 1회만 가능)</td></tr>
            </tbody>
          </table>
          <h6 className="fw-bold mt-3">제10조 (닢 적립)</h6>
          <table className="table table-bordered small">
            <thead className="table-light">
              <tr><th>항목</th><th>적립액</th><th>비고</th></tr>
            </thead>
            <tbody>
              <tr><td>좋아요 받음</td><td className="text-success fw-bold">+1닢</td><td>게시글/뉴스/공유의 작성자</td></tr>
              <tr><td>나빠요 받음</td><td className="text-danger fw-bold">-1닢</td><td>게시글/뉴스/공유의 작성자 차감</td></tr>
            </tbody>
          </table>
          <h6 className="fw-bold mt-3">제11조 (회원 점수 한도)</h6>
          <ol className="small">
            <li>회원이 게시물 하나에 줄 수 있는 총 점수(멤버 점수)는 <strong>최대 ±30점</strong>입니다.</li>
            <li>투표자 30명까지는 1인당 ±1점, 30명 초과 시 <strong>30/전체투표자수</strong> 점수가 반영됩니다.</li>
          </ol>
          <h6 className="fw-bold mt-3">제12조 (닢 소멸 및 환급)</h6>
          <ol className="small">
            <li>닢은 별도의 소멸 시한을 두지 않으나, 회원 탈퇴 시 자동 소멸됩니다.</li>
            <li>닢은 현금으로 환급되지 않으며, 서비스 내에서만 사용 가능합니다.</li>
            <li>부정한 방법으로 닢을 취득한 경우 운영진은 해당 닢을 회수할 수 있습니다.</li>
          </ol>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 18 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold">제4장 AI 지킴이 콘텐츠 심사</h5>
          <hr />
          <h6 className="fw-bold mt-3">제12조 (AI 심사 원칙)</h6>
          <ol className="small">
            <li>게시글, 댓글, 공유 등 모든 콘텐츠는 등록 즉시 AI 지킴이가 분석하여 점수(-50~50)를 부여합니다.</li>
            <li>AI가 함께사는양평 공동체에 위해가 된다고 판단하는 내용은 <strong>즉시 노출되지 않으며</strong>, 회원이 내용을 수정한 후 재심사를 통과하여야 노출됩니다.</li>
            <li>게시불가(-50점 이하) 판정을 받은 게시글은 <strong>30일 이내</strong>에 수정하여 재심사를 받을 수 있으며, <strong>수정할 때마다 100닢이 차감</strong>됩니다.</li>
            <li>30일이 경과하면 수정 기회가 소멸되며 해당 게시글은 영구 비공개 처리됩니다.</li>
            <li>AI 심사 결과에 이의가 있는 경우 관리자(admin) 또는 책임자(leader)에게 토론을 요청할 수 있습니다.</li>
          </ol>
          <h6 className="fw-bold mt-3">제13조 (이미지·영상 방역)</h6>
          <ol className="small">
            <li>공유하기에 업로드된 이미지와 영상은 AI 지킴이가 48시간 이내에 방역 검사를 수행합니다.</li>
            <li>부적절한 내용(폭력, 성적 콘텐츠, 혐오 표현 등)이 감지된 경우 관리자 확인 후 비공개 처리됩니다.</li>
            <li>이미지 방역 검사 중에도 관리자와 책임자는 해당 콘텐츠를 미리 확인하고 점수를 부여할 수 있습니다.</li>
          </ol>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 18 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold">제5장 위치 기반 서비스</h5>
          <hr />
          <h6 className="fw-bold mt-3">제14조 (위치 정보)</h6>
          <ol className="small">
            <li>회원의 위치 정보는 서비스 내에서만 사용되며, 회원의 동의 없이 외부에 제공되지 않습니다.</li>
            <li>위치 공유 기능은 회원이 직접 활성화한 경우에만 벗 관계인 회원에게 표시됩니다.</li>
            <li>위치 정보는 양평군 내에서만 갱신 가능합니다.</li>
            <li>회원은 언제든지 위치 공유를 해제할 수 있습니다.</li>
          </ol>
        </div>
      </div>

      <div className="card border-0 shadow-sm mb-4" style={{ borderRadius: 18 }}>
        <div className="card-body p-4">
          <h5 className="fw-bold">제6장 분쟁 해결 및 중재</h5>
          <hr />
          <h6 className="fw-bold mt-3">제15조 (중재위원회)</h6>
          <ol className="small">
            <li>회원 간의 모든 분쟁은 함께사는양평 내부 중재위원회의 조정 규칙을 따라야 합니다.</li>
            <li>중재위원회는 운영진(관리자, 책임자)으로 구성되며, 분쟁 발생 시 사실 확인과 조정을 수행합니다.</li>
            <li>벗 관계 해지, 닢 정산, 콘텐츠 삭제 등 각종 분쟁에 대해 중재위원회의 결정에 따라야 합니다.</li>
            <li>중재 결과에 이의가 있는 회원은 별도 법적 절차를 진행할 수 있습니다.</li>
          </ol>
          <h6 className="fw-bold mt-3">제16조 (면책 조항)</h6>
          <ol className="small">
            <li>서비스는 천재지변, 시스템 장애 등 불가항력적 사유로 인한 서비스 중단에 대해 책임을 지지 않습니다.</li>
            <li>회원 간의 분쟁으로 인한 손해에 대해 서비스는 책임을 지지 않습니다.</li>
          </ol>
          <h6 className="fw-bold mt-3">제17조 (준거법)</h6>
          <p>본 약관은 대한민국 법률에 따라 규율되며, 약관 해석에 관한 분쟁은 서울중앙지방법원을 전속 관할 법원으로 합니다.</p>
        </div>
      </div>

      <div className="text-center mb-4">
        <p className="text-muted small">본 약관은 서비스 가입 시 자동 동의된 것으로 간주됩니다.</p>
      </div>
    </div>
  )
}
