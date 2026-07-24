import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import NavBar from './components/NavBar'
import ShareList from './pages/ShareList'
import ShareDetail from './pages/ShareDetail'
import ShareReport from './pages/ShareReport'
import ShareEdit from './pages/ShareEdit'
import UserMyPage from './pages/UserMyPage'
import EpubList from './pages/EpubList'
import EpubEditor from './pages/EpubEditor'
import GuideList from './pages/GuideList'
import GuideTemplates from './pages/GuideTemplates'
import NewsList from './pages/NewsList'
import NewsDetail from './pages/NewsDetail'
import LegalList from './pages/LegalList'
import LegalDetail from './pages/LegalDetail'
import LegalWrite from './pages/LegalWrite'
import LegalSchedule from './pages/LegalSchedule'
import PsychoList from './pages/PsychoList'
import PsychoDetail from './pages/PsychoDetail'
import PsychoWrite from './pages/PsychoWrite'
import PsychoSchedule from './pages/PsychoSchedule'
import VillagePage from './pages/VillagePage'
import VillageEventList from './pages/VillageEventList'
import VillageEventDetail from './pages/VillageEventDetail'
import VillageMyWishes from './pages/VillageMyWishes'
import FriendsList from './pages/FriendsList'
import FriendsMap from './pages/FriendsMap'
import MessageInbox from './pages/MessageInbox'
import MessageSend from './pages/MessageSend'
import ConstructionPage from './pages/ConstructionPage'
import SchedulePage from './pages/SchedulePage'
import AdminDashboard from './pages/AdminDashboard'
import AdminUsers from './pages/AdminUsers'
import AdminNews from './pages/AdminNews'
import AdminShareReports from './pages/AdminShareReports'
import AdminStores from './pages/AdminStores'
import AdminAlerts from './pages/AdminAlerts'
import AdminAiChat from './pages/AdminAiChat'
import AdminAiFeedback from './pages/AdminAiFeedback'
import AdminAiTrain from './pages/AdminAiTrain'
import AdminPendingLetters from './pages/AdminPendingLetters'
import AdminPageManagers from './pages/AdminPageManagers'
import AdminMessage from './pages/AdminMessage'
import AdminPostgresql from './pages/AdminPostgresql'
import AdminRampApplications from './pages/AdminRampApplications'
import AdminPostDetail from './pages/AdminPostDetail'
import IntroPage from './pages/IntroPage'
import PresentationPage from './pages/PresentationPage'
import ProposalPage from './pages/ProposalPage'
import AllProposalsPage from './pages/AllProposalsPage'
import TermsPage from './pages/TermsPage'
import CharterPage from './pages/CharterPage'
import MainPage from './pages/MainPage'
import GoPage from './pages/GoPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import ResetConfirmPage from './pages/ResetConfirmPage'
import ServiceLegalPage from './pages/ServiceLegalPage'
import ServiceLegalEditPage from './pages/ServiceLegalEditPage'
import ServicePsychoPage from './pages/ServicePsychoPage'
import ServicePsychoEditPage from './pages/ServicePsychoEditPage'
import ServiceRampPage from './pages/ServiceRampPage'
import StoreDetailPage from './pages/StoreDetailPage'
import AiChatPage from './pages/AiChatPage'
import ChatPage from './pages/ChatPage'
import ViewPage from './pages/ViewPage'
import SearchPage from './pages/SearchPage'
import LegalIssuesPage from './pages/LegalIssuesPage'
import LegalIssueWritePage from './pages/LegalIssueWritePage'
import LegalIssueDetailPage from './pages/LegalIssueDetailPage'
import LegalIssuesAdminPage from './pages/LegalIssuesAdminPage'
import LeaderShareReportsPage from './pages/LeaderShareReportsPage'
import ShareMapPage from './pages/ShareMapPage'
import MyPagePointsPage from './pages/MyPagePointsPage'
import PointsChargePage from './pages/PointsChargePage'
import PsychoAdminPage from './pages/PsychoAdminPage'
import PsychoAdminAppointmentsPage from './pages/PsychoAdminAppointmentsPage'
import UserProfilePage from './pages/UserProfilePage'
import EditProfilePage from './pages/EditProfilePage'
import SchedulePopupPage from './pages/SchedulePopupPage'
import VillageAdminPage from './pages/VillageAdminPage'
import VillageQrPage from './pages/VillageQrPage'
import VillageEventCreatePage from './pages/VillageEventCreatePage'
import VillageEventQrPage from './pages/VillageEventQrPage'
import VillageJinConsentPage from './pages/VillageJinConsentPage'
import VillageJoinPage from './pages/VillageJoinPage'
import NewsTabsPage from './pages/NewsTabsPage'
import MyDID from './pages/MyDID'
import AdminIssueVC from './pages/AdminIssueVC'
import DIDClaimPage from './pages/DIDClaimPage'
import AdminNewsEdit from './pages/AdminNewsEdit'
import AdminNewsRecommendations from './pages/AdminNewsRecommendations'
import AdminStoreEdit from './pages/AdminStoreEdit'
import AdminAlertEdit from './pages/AdminAlertEdit'
import VillagePageEdit from './pages/VillagePageEdit'
import VillagePageView from './pages/VillagePageView'
import PsychoPostEdit from './pages/PsychoPostEdit'

function Footer() {
  const host = window.location.hostname
  const name = host === 'localhost' || host === '127.0.0.1' ? '함께사는로컬'
    : host === 'test.unocum.kr' ? '함께사는테스트' : '함께사는양평'
  return (
    <footer className="text-center py-4 border-top" style={{ background: '#f8f9fa' }}>
      <span className="fw-bold text-success">{name}</span>
      <span className="text-muted mx-2">|</span>
      <a href="mailto:unocumyp@gmail.com" className="text-muted text-decoration-none small">unocumyp@gmail.com</a>
    </footer>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <NavBar />
        <div className="container pb-5">
          <Routes>
            {/* Share (공유마당) */}
            <Route path="/share" element={<ShareList />} />
            <Route path="/share/detail/:id" element={<ShareDetail />} />
            <Route path="/share/report" element={<ShareReport />} />
            <Route path="/share/edit/:id" element={<ShareEdit />} />

            {/* Epub */}
            <Route path="/epub" element={<EpubList />} />
            <Route path="/epub/list" element={<EpubList />} />
            <Route path="/epub/new" element={<EpubList />} />
            <Route path="/epub/edit/:id" element={<EpubEditor />} />

            {/* Guide */}
            <Route path="/guide" element={<GuideList />} />
            <Route path="/guide/templates" element={<GuideTemplates />} />

            {/* User */}
            <Route path="/user/my" element={<UserMyPage />} />
            <Route path="/user/edit-profile" element={<EditProfilePage />} />
            <Route path="/user/:userId" element={<UserProfilePage />} />
            <Route path="/user/:userId/profile" element={<UserMyPage />} />

            {/* News (소식) */}
            <Route path="/news" element={<NewsList />} />
            <Route path="/news/:id" element={<NewsDetail />} />
            <Route path="/world-news" element={<NewsTabsPage />} />
            <Route path="/yp-news" element={<NewsTabsPage />} />
            <Route path="/kr-yp-news" element={<NewsTabsPage />} />

            {/* Legal (법률상담) */}
            <Route path="/legal" element={<LegalList />} />
            <Route path="/legal/:id" element={<LegalDetail />} />
            <Route path="/legal/write" element={<LegalWrite />} />
            <Route path="/legal/schedule" element={<LegalSchedule />} />
            {/* Psycho (심리상담) */}
            <Route path="/psycho" element={<PsychoList />} />
            <Route path="/psycho/:id" element={<PsychoDetail />} />
            <Route path="/psycho/write" element={<PsychoWrite />} />
            <Route path="/psycho/schedule" element={<PsychoSchedule />} />
            {/* Intro / Landing */}
            <Route path="/" element={<IntroPage />} />
            <Route path="/intro" element={<IntroPage />} />

            {/* Auth */}
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/reset-password/:token" element={<ResetConfirmPage />} />

            {/* Info pages */}
            <Route path="/presentation" element={<PresentationPage />} />
            <Route path="/proposal" element={<ProposalPage />} />
            <Route path="/all-proposals" element={<AllProposalsPage />} />
            <Route path="/terms" element={<TermsPage />} />
            <Route path="/charter" element={<CharterPage />} />
            <Route path="/main" element={<MainPage />} />
            <Route path="/go" element={<GoPage />} />

            {/* Service pages */}
            <Route path="/service/legal" element={<ServiceLegalPage />} />
            <Route path="/service/legal/edit" element={<ServiceLegalEditPage />} />
            <Route path="/service/psycho" element={<ServicePsychoPage />} />
            <Route path="/service/psycho/edit" element={<ServicePsychoEditPage />} />
            <Route path="/service/ramp" element={<ServiceRampPage />} />

            {/* AI Chat */}
            <Route path="/ai/chat" element={<AiChatPage />} />

            {/* Chat */}
            <Route path="/chat" element={<ChatPage />} />

            {/* Board (freeboard) */}
            <Route path="/post/:postId" element={<ViewPage />} />

            {/* Search */}
            <Route path="/search" element={<SearchPage />} />

            {/* Share (공유마당) */}
            <Route path="/share" element={<ShareList />} />
            <Route path="/share/detail/:id" element={<ShareDetail />} />
            <Route path="/share/report" element={<ShareReport />} />
            <Route path="/share/edit/:id" element={<ShareEdit />} />
            <Route path="/share/map" element={<ShareMapPage />} />
            <Route path="/leader/share-reports" element={<LeaderShareReportsPage />} />

            {/* Epub */}
            <Route path="/epub" element={<EpubList />} />
            <Route path="/epub/list" element={<EpubList />} />
            <Route path="/epub/new" element={<EpubList />} />
            <Route path="/epub/edit/:id" element={<EpubEditor />} />

            {/* Guide */}
            <Route path="/guide" element={<GuideList />} />
            <Route path="/guide/templates" element={<GuideTemplates />} />

            {/* User */}
            <Route path="/user/my" element={<UserMyPage />} />
            <Route path="/user/edit-profile" element={<EditProfilePage />} />
            <Route path="/user/:userId" element={<UserProfilePage />} />
            <Route path="/user/:userId/profile" element={<UserMyPage />} />

            {/* News (소식) */}
            <Route path="/news" element={<NewsList />} />
            <Route path="/news/:id" element={<NewsDetail />} />
            <Route path="/world-news" element={<NewsTabsPage />} />
            <Route path="/yp-news" element={<NewsTabsPage />} />
            <Route path="/kr-yp-news" element={<NewsTabsPage />} />

            {/* Legal (법률상담) - issues routes before :id to avoid conflict */}
            <Route path="/legal/issues/admin" element={<LegalIssuesAdminPage />} />
            <Route path="/legal/issues/write" element={<LegalIssueWritePage />} />
            <Route path="/legal/issues/:postId" element={<LegalIssueDetailPage />} />
            <Route path="/legal/issues" element={<LegalIssuesPage />} />
            <Route path="/legal" element={<LegalList />} />
            <Route path="/legal/:id" element={<LegalDetail />} />
            <Route path="/legal/write" element={<LegalWrite />} />
            <Route path="/legal/schedule" element={<LegalSchedule />} />

            {/* Psycho (심리상담) */}
            <Route path="/psycho/admin/appointments" element={<PsychoAdminAppointmentsPage />} />
            <Route path="/psycho/admin" element={<PsychoAdminPage />} />
            <Route path="/psycho" element={<PsychoList />} />
            <Route path="/psycho/:id" element={<PsychoDetail />} />
            <Route path="/psycho/:id/edit" element={<PsychoPostEdit />} />
            <Route path="/psycho/write" element={<PsychoWrite />} />
            <Route path="/psycho/schedule" element={<PsychoSchedule />} />

            {/* Village (마을) - specific routes before parameterized */}
            <Route path="/village/admin" element={<VillageAdminPage />} />
            <Route path="/village/qr" element={<VillageQrPage />} />
            <Route path="/village/event/create" element={<VillageEventCreatePage />} />
            <Route path="/village/event/:eventId/qr" element={<VillageEventQrPage />} />
            <Route path="/village/invite/:target" element={<VillageJinConsentPage />} />
            <Route path="/village/join" element={<VillageJoinPage />} />
            <Route path="/village" element={<VillagePage />} />
            <Route path="/village/page" element={<VillagePageEdit />} />
            <Route path="/village/view/:tmyeon/:tri" element={<VillagePageView />} />
            <Route path="/village/events" element={<VillageEventList />} />
            <Route path="/village/events/:id" element={<VillageEventDetail />} />
            <Route path="/village/my-wishes" element={<VillageMyWishes />} />

            {/* Friends (벗) */}
            <Route path="/friends" element={<FriendsList />} />
            <Route path="/friends/map" element={<FriendsMap />} />

            {/* Messages (쪽지) */}
            <Route path="/messages" element={<MessageInbox />} />
            <Route path="/message/inbox" element={<MessageInbox />} />
            <Route path="/message/send" element={<MessageSend />} />
            <Route path="/message/send/global" element={<MessageSend />} />
            <Route path="/message/send/admin" element={<MessageSend />} />
            <Route path="/message/send/village_leader" element={<MessageSend />} />
            <Route path="/message/admin/pending" element={<AdminPendingLetters />} />

            {/* MyPage / Points */}
            <Route path="/mypage/points" element={<MyPagePointsPage />} />
            <Route path="/mypage/points/charge" element={<PointsChargePage />} />

            {/* Construction (위치기반안내) */}
            <Route path="/construction" element={<ConstructionPage />} />
            <Route path="/construction/store/:storeName" element={<StoreDetailPage />} />

            {/* Schedule (일정관리) */}
            <Route path="/schedule" element={<SchedulePage />} />
            <Route path="/schedule2" element={<SchedulePage />} />
            <Route path="/schedule-popup" element={<SchedulePopupPage />} />
            <Route path="/my/did" element={<MyDID />} />
            <Route path="/did/claim" element={<DIDClaimPage />} />

            {/* Admin (관리자) */}
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/news" element={<AdminNews />} />
            <Route path="/admin/news/create" element={<AdminNewsEdit />} />
            <Route path="/admin/news/edit/:id" element={<AdminNewsEdit />} />
            <Route path="/admin/news/recommendations" element={<AdminNewsRecommendations />} />
            <Route path="/admin/share-reports" element={<AdminShareReports />} />
            <Route path="/admin/stores" element={<AdminStores />} />
            <Route path="/admin/stores/new" element={<AdminStoreEdit />} />
            <Route path="/admin/stores/edit/:id" element={<AdminStoreEdit />} />
            <Route path="/admin/alerts" element={<AdminAlerts />} />
            <Route path="/admin/alerts/new" element={<AdminAlertEdit />} />
            <Route path="/admin/alerts/edit/:id" element={<AdminAlertEdit />} />
            <Route path="/admin/ai-chat" element={<AdminAiChat />} />
            <Route path="/admin/ai-feedback" element={<AdminAiFeedback />} />
            <Route path="/admin/ai-train" element={<AdminAiTrain />} />
            <Route path="/admin/pending-letters" element={<AdminPendingLetters />} />
            <Route path="/admin/page-managers" element={<AdminPageManagers />} />
            <Route path="/admin/message" element={<AdminMessage />} />
            <Route path="/admin/postgresql" element={<AdminPostgresql />} />
            <Route path="/admin/ramp-applications" element={<AdminRampApplications />} />
            <Route path="/admin/post/:id" element={<AdminPostDetail />} />
            <Route path="/admin/did/issue" element={<AdminIssueVC />} />

            {/* Default */}
            <Route path="*" element={<IntroPage />} />
          </Routes>
        </div>
        <Footer />
      </BrowserRouter>
    </AuthProvider>
  )
}
