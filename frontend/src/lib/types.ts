// User
export interface User {
  id: number; username: string; role: 'admin' | 'leader' | 'user';
  real_name?: string; phone?: string; email?: string; email_verified?: boolean;
  town?: string; village?: string; reg_town?: string; reg_village?: string;
  curr_town?: string; curr_village?: string; curr_address?: string;
  points?: number; is_paid?: boolean; is_verified_resident?: boolean;
  verified_method?: string; location_share?: boolean; village_notify?: boolean;
  is_neighbor?: boolean; managed_pages?: string;
  photo_path?: string; social_provider?: string;
  office_address?: string; temp_address?: string;
  login_latitude?: number; login_longitude?: number;
}

// Post (제안/꿈꾸기)
export interface Post {
  id: number; user_id?: number; author_name?: string;
  title: string; content: string;
  category?: string; status?: string;
  ai_score?: number; ai_summary?: string; ai_reason?: string;
  admin_score?: number; leader_score?: number; member_score?: number;
  total_score?: number; file_path?: string;
  like_count?: number; dislike_count?: number;
  is_finalized?: boolean; is_forced_approved?: boolean;
  created_at?: string; updated_at?: string; deadline?: string;
}
export interface Comment {
  id: number; post_id?: number; user_id?: number; author?: string;
  content: string; parent_id?: number; total_score?: number;
  created_at?: string; replies?: Comment[];
}

// Share (공유마당)
export interface ShareReport {
  id: number; user_id?: number; author_name?: string;
  title: string; description?: string;
  image_path?: string; extra_images?: string; drawing_path?: string; video_path?: string;
  latitude?: number; longitude?: number;
  town?: string; village?: string; address?: string;
  status?: string; admin_note?: string;
  ai_category?: string; ai_summary?: string;
  like_count?: number; dislike_count?: number;
  admin_score?: number; leader_score?: number; member_score?: number;
  total_score?: number;
  is_moderated?: boolean; moderation_result?: string;
  canonical_name?: string; sub_category?: string;
  created_at?: string; updated_at?: string;
}
export interface ShareComment {
  id: number; share_id: number; user_id?: number; author?: string;
  content: string; parent_id?: number;
  created_at?: string; replies?: ShareComment[];
}

// Store (가게)
export interface StoreInfo {
  id: number; name: string; latitude?: number; longitude?: number;
  town?: string; village?: string;
  our_link?: string; store_homepage?: string; smartplace?: string;
  phone?: string;
}
export interface StoreMenu {
  id: number; name: string; sub_category?: string; price?: string;
  description?: string; ai_generated?: boolean;
}

// Legal (법률상담)
export interface LegalPost {
  id: number; title: string; content: string; author_name?: string;
  answer?: string; status?: string; is_public?: boolean;
  created_at?: string; answered_at?: string;
}
export interface LegalAppointment {
  id: number; name: string; email: string; phone?: string;
  date: string; time_slot: string; location?: string; content?: string;
  status?: string; fee?: number;
}

// Psycho (심리상담)
export interface PsychoPost {
  id: number; title: string; content: string; author_name?: string;
  answer?: string; status?: string; is_public?: boolean;
  created_at?: string; answered_at?: string;
}
export interface PsychoAppointment {
  id: number; name: string; email: string; phone?: string;
  date: string; time_slot: string; location?: string; content?: string;
  status?: string; fee?: number;
}

// Village (마을)
export interface VillageEvent {
  id: number; myeon?: string; ri?: string;
  title: string; event_type?: string; description?: string;
  location?: string; event_date?: string; status?: string;
}
export interface VillageAlert {
  id: number; title: string; content?: string;
  town?: string; village?: string;
  alert_type?: string; urgency?: string; author_name?: string;
  is_active?: boolean; created_at?: string;
}
export interface VillageWish {
  id: number; user_id?: number; content: string;
  village_ri?: string; status?: string; reply?: string;
  created_at?: string;
}

// News (소식)
export interface NewsArticle {
  id: number; title: string; summary?: string; content?: string;
  source_url?: string; source_name?: string; image_path?: string;
  category?: string; ai_score?: number;
  like_count?: number; dislike_count?: number;
  created_at?: string;
}
export interface NewsComment {
  id: number; news_id: number; user_id?: number; author_name?: string;
  content: string; parent_id?: number; ai_score?: number; is_hidden?: boolean;
  created_at?: string; replies?: NewsComment[];
}

// Message (쪽지)
export interface Message {
  id: number; sender_id?: number; sender_name?: string;
  receiver_id?: number; subject?: string; content?: string;
  is_read?: boolean; letter_type?: string;
  created_at?: string;
}

// Friend (벗)
export interface Friend {
  id: number; requester_id: number; receiver_id: number;
  group_id?: number; status?: string;
  created_at?: string;
}

// Chat (채팅)
export interface ChatRoom {
  id: number; name?: string; creator_id: number;
  participants?: string; is_active?: boolean;
  created_at?: string; expires_at?: string;
}
export interface ChatMessage {
  id: number; room_id: number; user_id?: number; username?: string;
  message?: string; is_bot?: boolean;
  created_at?: string;
}

// Construction (위치기반안내)
export interface ConstructionNotice {
  id: number; title: string; description?: string; location?: string;
  latitude?: number; longitude?: number;
  source?: string; notice_type?: string;
  start_date?: string; end_date?: string;
  is_active?: boolean;
}

// Epub
export interface EpubBook {
  id: number; user_id?: number; title: string; description?: string;
  layout_type?: string; template_id?: number;
  town?: string; village?: string; cover_image?: string;
  status?: string; created_at?: string;
}
export interface EpubPage {
  id: number; book_id: number; order_index?: number;
  title?: string; content?: string;
  latitude?: number; longitude?: number;
}
export interface EpubMedia {
  id: number; page_id: number; file_path: string;
  media_type?: string; caption?: string; alt_text?: string;
  order_index?: number; latitude?: number; longitude?: number;
}

// Guide
export interface GuideSection {
  id: number; title: string; content?: string; icon?: string;
  order_index?: number; parent_id?: number;
  layout_type?: string; language?: string; status?: string;
  children?: GuideSection[];
}
export interface GuideTemplate {
  id: number; name: string; description?: string; html_content?: string;
  layout_type?: string; is_featured?: boolean; use_count?: number;
  preview_image?: string;
}

// TongBot (통벗)
export interface TongBot {
  id: number; user_id: number; bot_name: string; bot_id: string;
  personality?: string; level?: number; exp?: number;
  intimacy?: number; mood?: string; chat_count?: number;
  tone?: string;
}
export interface TongBotSchedule {
  id: number; user_id: number; title: string; description?: string;
  event_date: string; end_date?: string;
  location?: string; memo?: string;
  is_allday?: boolean; is_recurring?: boolean;
  reminder_minutes?: number; repeat_type?: string;
  kind?: string; parent_id?: number;
}
export interface TongBotDraft {
  id: number; user_id: number; title?: string; content?: string;
  category?: string; bot_review?: string; status?: string;
}

// API response wrappers
export interface ApiResponse<T = unknown> {
  status?: string; error?: string; msg?: string;
  data?: T;
}

export interface MeResponse {
  id: number | null; username?: string | null; role?: string | null;
  real_name?: string; points?: number; photo_path?: string;
  managed_pages?: string[];
  town?: string; village?: string; email?: string;
  is_verified_resident?: boolean;
}

export interface PaginatedResponse<T> {
  items: T[]; total: number; page: number; per_page: number;
  pages: number;
}
