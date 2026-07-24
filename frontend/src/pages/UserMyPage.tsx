import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'

interface BotInfo {
  bot_name: string; mood: string; level: number; exp: number
  intimacy: number; tone: string; chat_count: number; bot_id: string
}
interface UserInfo { id: number; username: string; role: string; managed_pages: string[]; bot: BotInfo }
interface Schedule { id: number; title: string; event_date: string; description: string; location: string; color: string; departure_time?: string; return_time?: string; travel_min?: number }
interface Draft { id: number; title: string; status: string; category: string; content: string; updated_at: string }
interface Friend { id: number; name: string; username: string; town: string; village: string }
interface ChatRoomT { id: number; name: string; created_at: string }
interface ChatMsg { id: number; username: string; message: string; is_bot: boolean; time: string }
const MOODS: Record<string, { emoji: string; label: string }> = {
  warm: { emoji: '💕', label: '따스한' }, proud: { emoji: '🥲', label: '대견한' },
  encourage: { emoji: '💪', label: '응원' }, worried: { emoji: '😌', label: '걱정' },
  happy: { emoji: '😊', label: '기쁜' }, blessing: { emoji: '🙏', label: '축복' },
}
const LEVELS: Record<number, { emoji: string; name: string }> = {
  1: { emoji: '🥚', name: '알' }, 2: { emoji: '🐣', name: '새싹' },
  3: { emoji: '🌱', name: '묘목' }, 4: { emoji: '🪴', name: '나무' },
  5: { emoji: '🌸', name: '꽃' }, 6: { emoji: '🌟', name: '별' },
  7: { emoji: '👑', name: '수호자' },
}
const BOARD_RULES: Record<string, string> = {
  share: '사진·가게·나눔 정보를 공유합니다', dream: '마을에 바라는 제안을 올립니다',
  news: '마을 소식을 전합니다', legal: '법률 상담을 요청합니다', psycho: '심리 상담을 요청합니다',
}

type TabId = 'write' | 'friendchat' | 'schedule' | 'task'

export default function UserMyPage() {
  const navigate = useNavigate()
  const [me, setMe] = useState<UserInfo | null>(null)
  const [bot, setBot] = useState<BotInfo | null>(null)
  const [tab, setTab] = useState<TabId>('write')
  const [greeting, setGreeting] = useState('')

  // chat
  const [chatMsg, setChatMsg] = useState('')
  const [chatLog, setChatLog] = useState<{role:string;text:string;name:string}[]>([])
  const [sending, setSending] = useState(false)
  const [showHistory, setShowHistory] = useState(false)
  const [historyData, setHistoryData] = useState<{role:string;text:string}[]>([])
  const [showRename, setShowRename] = useState(false)
  const [newName, setNewName] = useState('')
  const chatEndRef = useRef<HTMLDivElement>(null)

  // schedule
  const [schedules, setSchedules] = useState<Schedule[]>([])
  const [showSchedForm, setShowSchedForm] = useState(false)
  const [schedTitle, setSchedTitle] = useState('')
  const [schedDesc, setSchedDesc] = useState('')
  const [schedDate, setSchedDate] = useState('')
  const [schedLocation, setSchedLocation] = useState('')
  const [schedEndDate, setSchedEndDate] = useState('')
  const [routeModal, setRouteModal] = useState<{schedule:any;route:any}|null>(null)
  const [editingSteps, setEditingSteps] = useState<boolean>(false)
  const [editStepsData, setEditStepsData] = useState<any[]>([])
  const [showTempForm, setShowTempForm] = useState(false)
  const [tempAddr, setTempAddr] = useState('')
  const [tempStart, setTempStart] = useState('')
  const [tempEnd, setTempEnd] = useState('')
  const [tripInput, setTripInput] = useState('')
  const [tripPlanning, setTripPlanning] = useState(false)
  const [tripResult, setTripResult] = useState<any>(null)

  // write
  const [drafts, setDrafts] = useState<Draft[]>([])
  const [currentDraftId, setCurrentDraftId] = useState<number | null>(null)
  const [draftTitle, setDraftTitle] = useState('')
  const [draftCategory, setDraftCategory] = useState('')
  const [showReview, setShowReview] = useState(false)
  const [reviewOrig, setReviewOrig] = useState('')
  const [reviewText, setReviewText] = useState('')
  const [reviewSugg, setReviewSugg] = useState('')
  const editorRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [drawOpen, setDrawOpen] = useState(false)
  const drawing = useRef(false)
  const drawCtx = useRef<CanvasRenderingContext2D | null>(null)

  // friend chat
  const [friends, setFriends] = useState<Friend[]>([])
  const [chatRooms, setChatRooms] = useState<ChatRoomT[]>([])
  const [activeRoomId, setActiveRoomId] = useState<number | null>(null)
  const [activeRoomMsgs, setActiveRoomMsgs] = useState<ChatMsg[]>([])
  const [chatRoomMsg, setChatRoomMsg] = useState('')
  const [selectedFriendIds, setSelectedFriendIds] = useState<number[]>([])

  useEffect(() => {
    fetch('/api/me').then(r => r.json()).then(d => {
      if (d.id) {
        setMe(d); setBot(d.bot); setNewName(d.bot?.bot_name || '')
        fetch('/api/bot/history').then(r => r.json()).then(() => {
          const gc = [`${d.username}님, 반갑습니다!`, `오늘도 좋은 하루 되세요, ${d.username}님!`]
          setGreeting(gc[Math.floor(Math.random() * gc.length)])
        }).catch(() => {})
      }
    })
    loadSchedules(); loadDrafts(); loadChatRooms()
    const hh = window.location.hash.replace('#tab', '')
    if (hh && ['write', 'friendchat', 'schedule', 'task'].includes(hh)) setTab(hh as TabId)
  }, [])

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chatLog, sending])

  useEffect(() => {
    if (!activeRoomId) return
    const iv = setInterval(() => loadRoomMsgs(activeRoomId), 3000)
    return () => clearInterval(iv)
  }, [activeRoomId])

  function loadSchedules() {
    fetch('/api/bot/schedule').then(r => r.json()).then(d => {
      setSchedules(Array.isArray(d.schedules) ? d.schedules : [])
    }).catch(() => setSchedules([]))
  }
  function loadDrafts() {
    fetch('/api/bot/draft').then(r => r.json()).then(d => { if (d.drafts) setDrafts(d.drafts) }).catch(() => {})
  }
  function loadChatRooms() {
    fetch('/api/chat/rooms').then(r => r.json()).then(d => { if (d.rooms) setChatRooms(d.rooms) }).catch(() => {})
  }

  // Bot actions
  function doRename() {
    const name = newName.trim()
    if (!name) return alert('이름을 입력하세요.')
    fetch('/api/bot/rename', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name }) })
      .then(r => r.json()).then(d => {
        if (d.error) alert(d.error); else { setShowRename(false); if (bot) setBot({ ...bot, bot_name: name }) }
      })
  }
  function setTone(tone: string) {
    fetch('/api/bot/tone', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tone }) })
      .then(r => r.json()).then(d => { if (d.success && bot) setBot({ ...bot, tone }) })
  }

  // Route detail
  function openRouteModal(id: number) {
    fetch('/api/bot/route/' + id).then(r => r.json()).then(d => {
      setRouteModal(d); setEditingSteps(false)
      if (d.route?.steps) setEditStepsData(d.route.steps.map((ss:any)=>({...ss})))
      else setEditStepsData([])
    }).catch(() => alert('경로 불러오기 실패'))
  }
  function saveRouteSteps(scheduleId: number) {
    const data: any = {steps:editStepsData}
    if (routeModal?.schedule?.departure_location) data.departure_location = routeModal.schedule.departure_location
    if (routeModal?.schedule?.return_location) data.return_location = routeModal.schedule.return_location
    if (routeModal?.schedule?.title) data.title = routeModal.schedule.title
    fetch('/api/bot/route/' + scheduleId + '/save', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)
    }).then(r => r.json()).then(d => {
      if (d.success) { setEditingSteps(false); setRouteModal(prev => prev ? {...prev, route: d.route} : prev); loadSchedules() }
    }).catch(() => alert('저장 실패'))
  }
  function shareRoute(scheduleId: number) {
    fetch('/api/bot/route/' + scheduleId + '/share', { method:'POST' })
      .then(r => r.json()).then(d => {
        if (d.success) alert('✅ 경로가 공유되었습니다!')
        else alert(d.error || '공유 실패')
      }).catch(() => alert('공유 실패'))
  }
  function addStep() {
    setEditStepsData(prev => [...prev, {mode:'🚌 버스',from:'',to:'',detail:'',time_min:0}])
  }
  function updateStep(i: number, field: string, val: any) {
    const arr = [...editStepsData]; (arr as any)[i][field] = val; setEditStepsData(arr)
  }
  function removeStep(i: number) {
    setEditStepsData(prev => prev.filter((_,idx) => idx !== i))
  }

  // Chat
  function sendChat() {
    const msg = chatMsg.trim()
    if (!msg || sending) return
    setSending(true)
    setChatLog(prev => [...prev, { role: 'user', text: msg, name: '나' }])
    setChatMsg('')
    fetch('/api/bot/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) })
      .then(r => r.json()).then(d => {
        const msgs: {role:string;text:string;name:string}[] = [
          { role: 'bot', text: d.reply || '(응답 없음)', name: d.bot_name || bot?.bot_name || '통벗' }
        ]
        if (d.talent) msgs.push({ role: 'bot', text: `🌟 발견된 재능: ${d.talent}`, name: 'AI' })
        if (d.counselor) msgs.push({ role: 'bot', text: `${d.counselor.msg}`, name: 'AI' })
        if (d.schedule) { msgs.push({ role: 'bot', text: `📅 일정 등록됨: ${d.schedule.title}`, name: 'AI' }); loadSchedules() }
        if (d.shopping) msgs.push({ role: 'bot', text: d.shopping, name: '🛒' })
        if (d.suggestion) d.suggestion.forEach((s: {text:string}) => msgs.push({ role: 'bot', text: `💡 ${s.text}`, name: '제안' }))
        setChatLog(prev => [...prev, ...msgs])
      }).catch(() => setChatLog(prev => [...prev, { role: 'bot', text: '응답 실패', name: 'AI' }]))
      .finally(() => setSending(false))
  }
  function loadHistory() {
    if (showHistory) { setShowHistory(false); return }
    setShowHistory(true)
    fetch('/api/bot/history').then(r => r.json()).then(d => setHistoryData(d.history || [])).catch(() => setHistoryData([]))
  }

  // Schedule
  function addSchedule() {
    if (!schedTitle || !schedDate) return alert('제목과 날짜를 입력하세요.')
    fetch('/api/bot/schedule', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: schedTitle, description: schedDesc, event_date: schedDate, location: schedLocation, end_date: schedEndDate || undefined })
    }).then(r => r.json()).then(d => {
      if (d.success) {
        setShowSchedForm(false); setSchedTitle(''); setSchedDesc(''); setSchedDate(''); setSchedLocation(''); setSchedEndDate('')
        loadSchedules()
      }
    }).catch(() => {})
  }
  function deleteSchedule(id: number) {
    if (!confirm('삭제하시겠습니까?')) return
    fetch('/api/bot/schedule/delete', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) })
      .then(r => r.json()).then(() => loadSchedules()).catch(() => {})
  }
  function exportICS(tripRes: any) {
    const date = tripRes.date || ''
    const entries: any[] = tripRes.entries || []
    if (!date || !entries.length) return
    const fmt = (d: string, t: string) => `${d.replace(/-/g,'')}T${t.replace(/:/g,'')}00`
    const lines: string[] = ['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//Yangpyeong//TongBot//KO']
    for (const e of entries) {
      const st = e.time || e.arrival || '09:00'
      let durMin = e.total_min || 120
      if (e.type === 'meeting' && !e.total_min) durMin = 120
      const stMin = parseInt(st.split(':')[0])*60 + parseInt(st.split(':')[1])
      const etMin = stMin + durMin
      const et = `${String(Math.floor(etMin/60)%24).padStart(2,'0')}:${String(etMin%60).padStart(2,'0')}`
      const desc = (e.memo || '').replace(/\n/g,'\\n').replace(/;/g,'\\;')
      lines.push('BEGIN:VEVENT',
        `DTSTART:${fmt(date,st)}`,
        `DTEND:${fmt(date,et)}`,
        `SUMMARY:${e.title}`,
        `DESCRIPTION:${desc}`)
      if (e.location) lines.push(`LOCATION:${e.location}`)
      lines.push('END:VEVENT')
    }
    lines.push('END:VCALENDAR')
    const blob = new Blob([lines.join('\r\n')], {type:'text/calendar;charset=utf-8'})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `schedule_${date}.ics`; a.click()
    URL.revokeObjectURL(url)
  }

  // Write / Draft
  function execCmd(cmd: string) { document.execCommand(cmd); editorRef.current?.focus() }
  function loadDraft(d: Draft) {
    setCurrentDraftId(d.id); setDraftTitle(d.title || ''); setDraftCategory(d.category || '')
    if (editorRef.current) editorRef.current.innerHTML = d.content || ''
  }
  async function saveDraft() {
    const data = { id: currentDraftId, title: draftTitle, content: editorRef.current?.innerHTML || '', category: draftCategory, status: 'draft' }
    const r = await fetch('/api/bot/draft', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
    const d = await r.json()
    if (d.success) { setCurrentDraftId(d.id); alert('💾 임시저장 완료'); loadDrafts() }
  }
  async function requestReview() {
    if (!currentDraftId) await saveDraft()
    if (!currentDraftId) return alert('먼저 임시저장을 해주세요.')
    try {
      const r = await fetch('/api/bot/review/' + currentDraftId, { method: 'POST' })
      const d = await r.json()
      if (d.success) { setReviewOrig(editorRef.current?.innerHTML || ''); setReviewText(d.review || ''); setReviewSugg(d.suggestion || ''); setShowReview(true) }
      else alert(d.error || '교정 실패')
    } catch { alert('교정 중 오류 발생') }
  }
  function postToBoard(content: string) {
    if (!draftCategory) return alert('게시판을 선택해 주세요.')
    const urls: Record<string, string> = { share: '/share-report', dream: '/main', news: '/kr-yp-news', legal: '/legal/write', psycho: '/psycho/write' }
    sessionStorage.setItem('draftContent', content); sessionStorage.setItem('draftTitle', draftTitle)
    window.location.href = urls[draftCategory] || '/share-report'
  }

  // Drawing
  function openDraw() {
    setDrawOpen(true)
    setTimeout(() => {
      const canvas = canvasRef.current; if (!canvas) return
      const ctx = canvas.getContext('2d'); if (!ctx) return
      drawCtx.current = ctx
      const rect = canvas.getBoundingClientRect()
      canvas.onmousedown = (e) => { drawing.current = true; ctx.beginPath(); ctx.moveTo(e.clientX - rect.left, e.clientY - rect.top) }
      canvas.onmousemove = (e) => {
        if (!drawing.current) return
        ctx.lineTo(e.clientX - rect.left, e.clientY - rect.top)
        ctx.strokeStyle = (document.getElementById('drawColor') as HTMLInputElement)?.value || '#000'
        ctx.lineWidth = parseInt((document.getElementById('drawSize') as HTMLInputElement)?.value || '3')
        ctx.stroke()
      }
      canvas.onmouseup = () => { drawing.current = false }
    }, 100)
  }
  function clearDraw() { drawCtx.current?.clearRect(0, 0, 400, 300) }
  function insertDrawing() {
    const dataUrl = canvasRef.current?.toDataURL()
    if (dataUrl && editorRef.current) editorRef.current.innerHTML += `<img src="${dataUrl}" style="max-width:100%">`
    setDrawOpen(false)
  }
  function insertPhoto(file: File) {
    if (!file) return
    const reader = new FileReader()
    reader.onload = (e) => { if (editorRef.current && e.target?.result) editorRef.current.innerHTML += `<img src="${e.target.result}" style="max-width:300px"> ` }
    reader.readAsDataURL(file); uploadFile(file)
  }
  function uploadFile(file: File) {
    const form = new FormData(); form.append('file', file)
    fetch('/api/bot/upload', { method: 'POST', body: form }).catch(() => {})
  }

  // Friend Chat
  function loadFriends() { fetch('/api/chat/friends').then(r => r.json()).then(d => setFriends(d.friends || [])).catch(() => {}) }
  function toggleFriend(id: number) { setSelectedFriendIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]) }
  function createRoom() {
    if (selectedFriendIds.length === 0) return alert('벗을 선택해 주세요.')
    const name = prompt('채팅방 제목:', '우리들의 대화')
    if (!name) return
    fetch('/api/chat/rooms', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, friends: selectedFriendIds }) })
      .then(r => r.json()).then(d => { if (d.id) { alert('채팅방 개설! 2시간 유지됩니다.'); loadChatRooms(); openRoom(d.id) } else alert(d.error || '실패') })
  }
  function openRoom(id: number) { setActiveRoomId(id); loadRoomMsgs(id) }
  function closeRoom() { setActiveRoomId(null); setActiveRoomMsgs([]) }
  function loadRoomMsgs(id: number) { fetch('/api/chat/messages/' + id).then(r => r.json()).then(d => setActiveRoomMsgs(d.messages || [])).catch(() => {}) }
  function sendRoomMsg() {
    const msg = chatRoomMsg.trim()
    if (!msg || !activeRoomId) return
    setChatRoomMsg('')
    fetch('/api/chat/messages/' + activeRoomId, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) })
      .then(r => r.json()).then(() => loadRoomMsgs(activeRoomId)).catch(() => {})
  }

  const moodInfo = bot ? MOODS[bot.mood] || MOODS.warm : MOODS.warm
  const levelInfo = bot ? LEVELS[bot.level] || LEVELS[1] : LEVELS[1]
  const expPercent = bot ? (bot.exp % 100) : 0
  const tabLabels: Record<TabId, string> = { write: '✍️ 글쓰기', friendchat: '👥 벗 채팅', schedule: '📅 일정', task: '📋 일' }

  return (
    <div className="container mt-4" style={{ maxWidth: 800 }}>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h3 className="fw-bold mb-0">
          <span id="botNameDisplay">{bot?.bot_name || '통벗'}</span>
          <button className="btn btn-sm btn-outline-secondary ms-2" onClick={() => { setShowRename(!showRename); setNewName(bot?.bot_name || '') }}>✏️</button>
        </h3>
        <a href={`/user/${me?.id}`} className="btn btn-sm btn-outline-secondary">내 프로필</a>
      </div>

      <div className="row g-3 mb-3">
        <div className="col-4 text-center">
          <div className="fs-2" id="moodEmoji">{moodInfo.emoji}</div>
          <small className="text-muted" id="moodLabel">{moodInfo.label}</small>
        </div>
        <div className="col-4 text-center">
          <div className="fs-2">{levelInfo.emoji}</div>
          <small className="text-muted">{levelInfo.name} Lv.{bot?.level || 1}</small>
        </div>
        <div className="col-4 text-center">
          <div className="fs-2">💬</div>
          <small className="text-muted">친밀도 {bot?.intimacy || 0}</small>
        </div>
      </div>
      <div className="progress mb-3" style={{ height: 6 }}>
        <div className="progress-bar bg-warning" style={{ width: `${expPercent}%` }} />
      </div>

      {showRename && (
        <div className="mb-3" id="renameBox">
          <div className="input-group input-group-sm">
            <input type="text" id="newName" className="form-control" placeholder="새 이름 (2~20자)" maxLength={20}
              value={newName} onChange={e => setNewName(e.target.value)} />
            <button className="btn btn-primary" onClick={doRename}>저장</button>
            <button className="btn btn-outline-secondary" onClick={() => setShowRename(false)}>취소</button>
          </div>
          <small className="text-muted">다른 회원이 사용 중인 이름은 쓸 수 없습니다.</small>
        </div>
      )}

      <div className="d-flex justify-content-end gap-2 mb-3">
        <div className="btn-group btn-group-sm">
          {(['friendly', 'respectful', 'strict'] as const).map(t => (
            <button key={t}
              className={`btn btn-${bot?.tone === t ? 'primary' : 'outline-secondary'}`}
              onClick={() => setTone(t)}>
              {t === 'friendly' ? '💬 친근' : t === 'respectful' ? '🙇 존중' : '📋 엄격'}
            </button>
          ))}
        </div>
      </div>

      <ul className="nav nav-tabs mb-4" id="botTabs">
        {(['write', 'friendchat', 'schedule', 'task'] as TabId[]).map(t => (
          <li className="nav-item" key={t}>
            <button className={`nav-link ${tab === t ? 'active fw-bold' : ''}`}
              onClick={() => {
                setTab(t); window.location.hash = 'tab' + t
                if (t === 'friendchat') loadFriends()
                if (t === 'task') navigate('/schedule')
              }}>
              {tabLabels[t]}
            </button>
          </li>
        ))}
      </ul>

      {/* ── CHAT (always visible) ── */}
      <div id="tabChat">
        <div id="chatMessages" className="mb-3" style={{ maxHeight: 400, overflowY: 'auto', border: '1px solid #dee2e6', borderRadius: 12, padding: 12, background: '#f8f9fa' }}>
          {chatLog.length === 0 && (
            <div className="text-center text-muted small py-3">
              {greeting}<br />저는 <strong>{bot?.bot_name || '통벗'}</strong>입니다. 함께사는양평에서 도와드릴게요.
            </div>
          )}
          {chatLog.map((c, i) => (
            <div key={i} className={`mb-2 ${c.role === 'user' ? 'text-end' : 'text-start'}`}>
              <span className={`badge ${c.role === 'user' ? 'bg-primary' : c.name === '제안' ? 'bg-info text-dark' : 'bg-success'}`}>{c.name}</span>
              <span className="ms-1">{c.text}</span>
            </div>
          ))}
          {sending && <div className="text-start text-muted small">🤖 입력 중...</div>}
          <div ref={chatEndRef} />
        </div>
        <div className="d-flex gap-2 mb-2">
          <input type="text" id="chatInput" className="form-control" placeholder="메시지..."
            value={chatMsg} onChange={e => setChatMsg(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') sendChat() }} />
          <button className="btn btn-primary" onClick={sendChat} disabled={sending}>전송</button>
          <button className="btn btn-sm btn-outline-secondary" onClick={loadHistory}>📜 기록</button>
        </div>
        {showHistory && (
          <div id="historyPanel" className="card p-2 mb-2 small" style={{ maxHeight: 300, overflowY: 'auto' }}>
            <strong>📜 대화 기록 ({bot?.chat_count || 0}회)</strong><hr className="my-1" />
            {historyData.length === 0 && <div className="text-muted">대화 기록이 없습니다.</div>}
            {historyData.map((h, i) => (
              <div key={i} className={`mb-1 ${h.role === 'user' ? 'text-end' : 'text-start'}`}>
                <span className={`badge bg-${h.role === 'user' ? 'primary' : 'success'}`}>{h.role === 'user' ? '나' : '통벗'}</span> {h.text}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── WRITE TAB ── */}
      <div id="tabWrite" style={{ display: tab === 'write' ? '' : 'none' }}>
        <div className="row g-3">
          <div className="col-md-8">
            <div className="d-flex gap-2 mb-3">
              <select id="draftCategory" className="form-select form-select-sm" style={{ width: 'auto' }}
                value={draftCategory} onChange={e => setDraftCategory(e.target.value)}>
                <option value="">게시판 선택</option>
                <option value="share">공유마당</option>
                <option value="dream">꿈꾸기</option>
                <option value="news">소식</option>
                <option value="legal">법률상담</option>
                <option value="psycho">심리상담</option>
              </select>
              <span id="boardRule" className="small text-muted align-self-center">
                {BOARD_RULES[draftCategory] || ''}
              </span>
            </div>
            <input type="text" id="draftTitle" className="form-control mb-2" placeholder="제목"
              value={draftTitle} onChange={e => setDraftTitle(e.target.value)} />
            <div className="btn-group btn-group-sm mb-2" id="toolbar">
              <button className="btn btn-outline-secondary" onClick={() => execCmd('bold')} title="굵게"><b>B</b></button>
              <button className="btn btn-outline-secondary" onClick={() => execCmd('italic')} title="기울임"><i>I</i></button>
              <button className="btn btn-outline-secondary" onClick={() => execCmd('underline')} title="밑줄"><u>U</u></button>
              <button className="btn btn-outline-secondary" onClick={() => execCmd('insertUnorderedList')} title="목록">•</button>
              <button className="btn btn-outline-secondary" onClick={() => execCmd('insertOrderedList')} title="번호">1.</button>
              <button className="btn btn-outline-secondary" onClick={() => document.getElementById('photoInput')?.click()}>📷</button>
              <button className="btn btn-outline-secondary" onClick={() => document.getElementById('fileInput')?.click()}>📎</button>
              <button className="btn btn-outline-secondary" onClick={openDraw}>✏️</button>
            </div>
            <input type="file" id="photoInput" accept="image/*" style={{ display: 'none' }}
              onChange={e => { const f = e.target.files?.[0]; if (f) insertPhoto(f); e.target.value = '' }} />
            <input type="file" id="fileInput" style={{ display: 'none' }}
              onChange={e => { const f = e.target.files?.[0]; if (f) uploadFile(f); e.target.value = '' }} />
            <div id="editor" ref={editorRef} contentEditable
              className="form-control mb-2"
              style={{ minHeight: 200, maxHeight: 400, overflowY: 'auto', whiteSpace: 'pre-wrap' }} />
            {drawOpen && (
              <div id="drawPanel" className="card p-2 mb-2">
                <canvas ref={canvasRef} width={400} height={300}
                  style={{ border: '1px solid #ddd', borderRadius: 8, cursor: 'crosshair' }} />
                <div className="d-flex gap-2 mt-2">
                  <input type="color" id="drawColor" defaultValue="#000000" />
                  <input type="range" id="drawSize" min={1} max={10} defaultValue={3} />
                  <button className="btn btn-sm btn-outline-danger" onClick={clearDraw}>지우기</button>
                  <button className="btn btn-sm btn-primary" onClick={insertDrawing}>삽입</button>
                  <button className="btn btn-sm btn-outline-secondary" onClick={() => setDrawOpen(false)}>닫기</button>
                </div>
              </div>
            )}
            <div id="attachedFiles" className="small mb-2" />
            <div className="d-flex gap-2">
              <button className="btn btn-outline-secondary" onClick={saveDraft}>💾 임시저장</button>
              <button className="btn btn-outline-primary" onClick={requestReview}>🤖 {bot?.bot_name || '통벗'}교정부탁</button>
              <button className="btn btn-success" onClick={() => postToBoard(editorRef.current?.innerHTML || '')}>📤 게시하기</button>
            </div>
          </div>
          <div className="col-md-4">
            <h6 className="small text-muted">📝 임시저장</h6>
            <div id="draftList" className="small">
              {drafts.length === 0 && <div className="text-muted">저장된 글이 없습니다.</div>}
              {drafts.map(d => (
                <div key={d.id} className="border rounded p-2 mb-1" style={{ cursor: 'pointer' }} onClick={() => loadDraft(d)}>
                  <div className="fw-bold">{d.title || '(제목없음)'}</div>
                  <span className={`badge bg-${d.status === 'reviewed' ? 'success' : 'secondary'}`}>
                    {{ draft: '임시', reviewed: '교정완료', posted: '게시됨' }[d.status] || d.status}
                  </span>
                  <small className="text-muted ms-1">
                    {d.updated_at ? new Date(d.updated_at).toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''}
                  </small>
                </div>
              ))}
            </div>
          </div>
        </div>
        {showReview && (
          <div id="reviewResult" className="mt-3">
            <hr /><h6>🤖 {bot?.bot_name || '통벗'}의 교정 결과</h6>
            <div className="row g-3">
              <div className="col-6">
                <small className="text-muted">✍️ 내 원본</small>
                <div id="originalView" className="p-2 bg-light rounded small" style={{ whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto' }}
                  dangerouslySetInnerHTML={{ __html: reviewOrig }} />
              </div>
              <div className="col-6">
                <small className="text-muted">🤖 교정 제안</small>
                <div id="reviewView" className="p-2 bg-warning bg-opacity-10 rounded small" style={{ whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto' }}>
                  {reviewText}
                </div>
              </div>
            </div>
            {reviewSugg && <div id="reviewSuggestion" className="small text-primary mt-1">📌 추천 게시판: <strong>{reviewSugg}</strong></div>}
            <div className="mt-2 d-flex gap-2">
              <button className="btn btn-sm btn-success" onClick={() => postToBoard(reviewText)}>✅ 교정본으로 게시</button>
              <button className="btn btn-sm btn-outline-secondary" onClick={() => setShowReview(false)}>숨기기</button>
            </div>
          </div>
        )}
      </div>

      {/* ── FRIEND CHAT TAB ── */}
      <div id="tabFriendchat" style={{ display: tab === 'friendchat' ? '' : 'none' }}>
        <div className="row g-3">
          <div className="col-md-5">
            <h6 className="small text-muted">👥 내 벗 목록</h6>
            <div id="friendList" className="list-group small" style={{ maxHeight: 300, overflowY: 'auto' }}>
              {friends.length === 0 && (
                <div className="text-muted py-2">아직 벗이 없습니다.<br /><small>다른 회원님 프로필에서 벗 신청을 해보세요!</small></div>
              )}
              {friends.map(f => (
                <label key={f.id} className="list-group-item" style={{ cursor: 'pointer' }}>
                  <input type="checkbox" className="friend-check me-2" checked={selectedFriendIds.includes(f.id)}
                    onChange={() => toggleFriend(f.id)} />
                  {f.name} <small className="text-muted">@{f.username}</small><br />
                  <small className="text-muted">{f.town} {f.village}</small>
                </label>
              ))}
            </div>
          </div>
          <div className="col-md-7">
            <div id="chatRoomList">
              {chatRooms.length === 0 && (
                <div className="text-muted text-center py-3">
                  참여 중인 채팅방이 없습니다.<br />
                  <small>벗을 선택하고 채팅방을 만들어보세요!</small>
                </div>
              )}
              {chatRooms.map(r => (
                <div key={r.id} className="card mb-2" style={{ cursor: 'pointer' }} onClick={() => openRoom(r.id)}>
                  <div className="card-body p-2 small">
                    <strong>{r.name}</strong>
                    <small className="text-muted float-end">
                      {r.created_at ? new Date(r.created_at).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' }) : ''}
                    </small>
                  </div>
                </div>
              ))}
            </div>
            <button className="btn btn-sm btn-primary mt-2" id="chatCreateBtn" onClick={createRoom}
              disabled={selectedFriendIds.length === 0}>+ 선택한 벗과 채팅</button>
            {activeRoomId && (
              <div id="activeChat" className="card mt-2">
                <div className="card-header d-flex justify-content-between p-2">
                  <strong className="small" id="activeChatName">채팅방 #{activeRoomId}</strong>
                  <button className="btn btn-sm btn-outline-secondary" onClick={closeRoom}>✕</button>
                </div>
                <div id="activeChatMsgs" className="card-body p-2" style={{ maxHeight: 250, overflowY: 'auto' }}>
                  {activeRoomMsgs.map(m => (
                    <div key={m.id} className={`mb-1 ${m.is_bot ? 'text-center text-muted fst-italic' : ''}`}>
                      <span className={`badge bg-${m.is_bot ? 'warning' : 'primary'} small`}>{m.username}</span>
                      {' '}{m.message} <small className="text-muted">{m.time}</small>
                    </div>
                  ))}
                </div>
                <div className="card-footer p-2">
                  <div className="input-group input-group-sm">
                    <input type="text" id="chatMsgInput" className="form-control" placeholder="메시지..."
                      value={chatRoomMsg} onChange={e => setChatRoomMsg(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') sendRoomMsg() }} />
                    <button className="btn btn-primary" onClick={sendRoomMsg}>전송</button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── SCHEDULE TAB ── */}
      <div id="tabSchedule" style={{ display: tab === 'schedule' ? '' : 'none' }}>
        <button className="btn btn-sm btn-primary mb-3" onClick={() => setShowSchedForm(!showSchedForm)}>
          {showSchedForm ? '✕ 닫기' : '+ 새 일정'}
        </button>
          {showSchedForm && (
          <div id="addScheduleForm" className="card p-3 mb-3">
            <input type="text" className="form-control form-control-sm mb-2" placeholder="일정 제목"
              value={schedTitle} onChange={e => setSchedTitle(e.target.value)} />
            <textarea className="form-control form-control-sm mb-2" rows={2} placeholder="설명"
              value={schedDesc} onChange={e => setSchedDesc(e.target.value)} />
            <input type="datetime-local" className="form-control form-control-sm mb-2"
              value={schedDate} onChange={e => { setSchedDate(e.target.value); if (!schedEndDate || schedEndDate === schedDate) setSchedEndDate(e.target.value) }} />
            <input type="text" className="form-control form-control-sm mb-2" placeholder="장소"
              value={schedLocation} onChange={e => setSchedLocation(e.target.value)} />
            <input type="datetime-local" className="form-control form-control-sm mb-2" placeholder="종료 시간"
              value={schedEndDate} onChange={e => setSchedEndDate(e.target.value)} />
            <button className="btn btn-sm btn-primary" onClick={addSchedule}>저장</button>
            <button className="btn btn-sm btn-outline-secondary" onClick={() => setShowSchedForm(false)}>취소</button>
          </div>
        )}
        <div id="scheduleList">
          {schedules.length === 0 && <div className="text-muted text-center py-3">등록된 일정이 없습니다.</div>}
          {schedules.map(s => {
            const sc = s.color || 'gray'
            const borderClass = sc === 'red' ? 'border-danger' : sc === 'blue' ? 'border-primary' : sc === 'green' ? 'border-success' : sc === 'info' ? 'border-info' : 'border-secondary'
            const icon = sc === 'red' ? '🔴' : sc === 'blue' ? '🔵' : sc === 'green' ? '🟢' : sc === 'info' ? 'ℹ️' : '⚪'
            const dateStr = s.event_date || ''
            const isMove = s.title?.includes('이동') || s.title?.includes('귀가')
            return (
              <div key={s.id} className={`card mb-2 border-start border-3 ${borderClass}`} style={isMove ? {cursor:'pointer'} : {}}
                   onClick={() => isMove && openRouteModal(s.id)}>
                <div className="card-body p-2 small">
                  <div className="d-flex justify-content-between">
                    <strong>{icon} {s.title}</strong>
                    <button className="btn btn-sm btn-outline-danger py-0" onClick={(e) => { e.stopPropagation(); deleteSchedule(s.id) }}>🗑️</button>
                  </div>
                  <span className="text-muted">{dateStr}</span>
                  {s.location && <div><small>📍</small> {s.location}</div>}
                  {isMove && s.departure_time && <div className="text-primary small">🚶 출발 {s.departure_time}</div>}
                  {isMove && <div className="text-info small mt-1">👆 클릭하여 경로 보기</div>}
                </div>
              </div>
            )
          })}
        </div>

        <hr className="my-4" />
        <div className="mb-2">
          <button className="btn btn-sm btn-outline-warning" onClick={() => setShowTempForm(!showTempForm)}>
            {showTempForm ? '✕ 닫기' : '🏠 임시숙소 설정'}
          </button>
          {showTempForm && (
            <div className="card p-2 mt-2 bg-light small">
              <input type="text" className="form-control form-control-sm mb-1" placeholder="임시숙소 주소"
                value={tempAddr} onChange={e => setTempAddr(e.target.value)} />
              <div className="d-flex gap-1 mb-1">
                <input type="date" className="form-control form-control-sm" placeholder="시작일"
                  value={tempStart} onChange={e => setTempStart(e.target.value)} />
                <input type="date" className="form-control form-control-sm" placeholder="종료일"
                  value={tempEnd} onChange={e => setTempEnd(e.target.value)} />
              </div>
              <button className="btn btn-sm btn-warning" onClick={async () => {
                const r = await fetch('/api/user/temp', { method:'POST', headers:{'Content-Type':'application/json'},
                  body:JSON.stringify({temp_address:tempAddr,temp_start_date:tempStart,temp_end_date:tempEnd}) })
                const d = await r.json()
                if (d.status === 'success') { setShowTempForm(false); alert('✅ 임시숙소 저장됨') }
                else alert(d.error || '실패')
              }}>저장</button>
              {tempAddr && <div className="mt-1 text-muted small">현재: {tempAddr} ({tempStart || '?'} ~ {tempEnd || '?'})</div>}
            </div>
          )}
        </div>
        <h6 className="fw-bold mb-2">🚗 AI 일정짜기</h6>
        <p className="text-muted small">자연어로 하루 일정을 입력하면 AI가 경로를 분석하여 이동/귀가 일정을 자동 생성합니다.</p>
        <textarea className="form-control form-control-sm mb-2" rows={3}
          placeholder="예: 7월11일에 양평읍 리얼리스트에서 오전 10시 미팅 후 옥천 심재운집 오후2시, 용문 제일정육고기 저녁7시"
          value={tripInput} onChange={e => setTripInput(e.target.value)} />
        <button className="btn btn-sm btn-success mb-3" disabled={tripPlanning || !tripInput.trim()}
          onClick={async () => {
            setTripPlanning(true); setTripResult(null)
            try {
              const r = await fetch('/api/bot/trip/plan', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:tripInput}) })
              const d = await r.json()
              setTripResult(d)
              if (d.status === 'success') loadSchedules()
            } catch { setTripResult({error:'일정짜기 실패'}) }
            setTripPlanning(false)
          }}>
          {tripPlanning ? '⏳ 일정 짜는 중...' : '🤖 자동 일정 짜기'}
        </button>
        {tripResult?.error && <div className="alert alert-danger small py-2">{tripResult.error}</div>}
        {tripResult?.status === 'success' && (
          <div className="card bg-light p-2 small mb-3">
            <strong>📋 생성된 일정 ({tripResult.entries?.length || 0}개)</strong>
            {tripResult.parsed_stops && (
              <div className="mt-1 text-muted small">
                🗺️ {tripResult.parsed_stops.map((s:any) => s.name).join(' → ')}
              </div>
            )}
            {tripResult.entries?.map((e:any, i:number) => (
              <div key={i} className="border-bottom py-1">
                <span className={`badge me-1 ${e.title?.includes('이동') || e.title?.includes('귀가') ? 'bg-info text-dark' : e.type === 'return' ? 'bg-danger' : 'bg-success'}`}>{e.time || e.arrival || ''}</span>
                <strong>{e.title}</strong>
                {e.total_min && <small className="text-muted ms-1">({e.total_min}분)</small>}
                {e.memo && <pre className="mb-0 mt-1 text-muted" style={{fontSize:'0.75rem',whiteSpace:'pre-wrap',maxHeight:120,overflowY:'auto'}}>{e.memo}</pre>}
              </div>
            ))}
            <button className="btn btn-sm btn-outline-primary mt-2" onClick={() => exportICS(tripResult)}>
              📅 구글/아웃룩에 추가
            </button>
          </div>
        )}
      </div>

      {/* ── TASK TAB ── */}
      <div id="tabTask" style={{ display: tab === 'task' ? '' : 'none' }}>
        <div className="text-center py-4">
          <div className="fs-1 mb-2">📋</div>
          <p className="text-muted small">일정 페이지에서 관리할 수 있습니다.</p>
          <a href="/schedule" className="btn btn-success">일정 관리 열기</a>
        </div>
      </div>

      {/* ── ROUTE MODAL ── */}
      {routeModal && (
        <div className="modal d-block" style={{background:'rgba(0,0,0,0.4)'}} onClick={() => setRouteModal(null)}>
          <div className="modal-dialog modal-dialog-centered modal-lg" onClick={e => e.stopPropagation()}>
            <div className="modal-content small">
              <div className="modal-header py-2">
                <h6 className="modal-title">🗺️ {routeModal.schedule?.title}</h6>
                <button className="btn-close" onClick={() => setRouteModal(null)}></button>
              </div>
              <div className="modal-body py-2">
                <div className="mb-2">{routeModal.schedule?.departure_location} → {routeModal.schedule?.return_location || routeModal.schedule?.location}</div>
                {routeModal.route?.departure && <div className="text-muted mb-2">⏰ {routeModal.route.departure} 출발 → {routeModal.route.arrival} 도착 (총 {routeModal.route.total_min}분)</div>}
                {routeModal.schedule?.memo && (
                  <div className="mb-2 p-2 bg-light border rounded" dangerouslySetInnerHTML={{__html: routeModal.schedule.memo}} />
                )}

                {!editingSteps && routeModal.route?.steps?.map((st:any,i:number) => (
                  <div key={i} className="border-start border-2 border-info ps-2 py-1 mb-1">
                    <strong>{st.mode}</strong> {st.detail}
                  </div>
                ))}
                {routeModal.route?.from_lat && routeModal.route?.to_lat && (
                  <div className="d-flex gap-1 mt-2 flex-wrap">
                    {(() => {
                      const isOverseas = routeModal.route.from_lat > 43 || routeModal.route.from_lat < 33 || routeModal.route.from_lng > 132 || routeModal.route.from_lng < 124
                      return (
                        <>
                          {!isOverseas && (
                            <>
                              <a className="btn btn-sm btn-outline-success" target="_blank" rel="noopener noreferrer"
                                href={`https://map.kakao.com/link/by/traffic/${encodeURIComponent(routeModal.schedule?.departure_location || '출발')},${routeModal.route.from_lat},${routeModal.route.from_lng}/${encodeURIComponent(routeModal.schedule?.return_location || routeModal.schedule?.location || '도착')},${routeModal.route.to_lat},${routeModal.route.to_lng}`}>
                                📱 카카오맵
                              </a>
                              <a className="btn btn-sm btn-outline-info" target="_blank" rel="noopener noreferrer"
                                href={`https://map.naver.com/p/directions/${routeModal.route.from_lng},${routeModal.route.from_lat},${encodeURIComponent(routeModal.schedule?.departure_location || '출발')}/${routeModal.route.to_lng},${routeModal.route.to_lat},${encodeURIComponent(routeModal.schedule?.return_location || routeModal.schedule?.location || '도착')}`}>
                                🗺️ 네이버 지도
                              </a>
                            </>
                          )}
                          <a className="btn btn-sm btn-outline-danger" target="_blank" rel="noopener noreferrer"
                            href={`https://www.google.com/maps/dir/?api=1&origin=${routeModal.route.from_lat},${routeModal.route.from_lng}&destination=${routeModal.route.to_lat},${routeModal.route.to_lng}&travelmode=transit${isOverseas ? '&hl=ko' : ''}`}>
                            🌐 Google Maps
                          </a>
                        </>
                      )
                    })()}
                  </div>
                )}

                {editingSteps && (
                  <div>
                    {editStepsData.map((st:any,i:number) => (
                      <div key={i} className="border rounded p-2 mb-2 bg-light">
                        <div className="d-flex gap-1 mb-1">
                          <select className="form-select form-select-sm" style={{width:'auto'}}
                            value={st.mode} onChange={e => updateStep(i,'mode',e.target.value)}>
                            <option>🚶 도보</option><option>🚌 버스</option><option>🚄 전철</option><option>🚕 택시</option>
                          </select>
                          <button className="btn btn-sm btn-outline-danger py-0 ms-auto" onClick={() => removeStep(i)}>🗑️</button>
                        </div>
                        <input className="form-control form-control-sm mb-1" placeholder="출발지" value={st.from || ''} onChange={e => updateStep(i,'from',e.target.value)} />
                        <input className="form-control form-control-sm mb-1" placeholder="도착지" value={st.to || ''} onChange={e => updateStep(i,'to',e.target.value)} />
                        <input className="form-control form-control-sm" placeholder="상세 (예: 1번 버스 30분)" value={st.detail || ''} onChange={e => updateStep(i,'detail',e.target.value)} />
                      </div>
                    ))}
                    <button className="btn btn-sm btn-outline-primary" onClick={addStep}>+ 단계 추가</button>
                  </div>
                )}
              </div>
              <div className="modal-footer py-1">
                {!editingSteps && (
                  <button className="btn btn-sm btn-outline-warning" onClick={() => setEditingSteps(true)}>✏️ 경로 수정</button>
                )}
                {editingSteps && (
                  <button className="btn btn-sm btn-success" onClick={() => saveRouteSteps(routeModal.schedule.id)}>💾 저장</button>
                )}
                <button className="btn btn-sm btn-outline-info" onClick={() => shareRoute(routeModal.schedule.id)}>🌐 공유</button>
                <button className="btn btn-sm btn-outline-secondary" onClick={() => setRouteModal(null)}>닫기</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
