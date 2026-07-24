export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new ApiError(res.status, body.error || body.msg || `HTTP ${res.status}`);
  }
  return res.json();
}

function buildQuery(params?: Record<string, string | number | boolean | undefined | null>): string {
  if (!params) return '';
  const parts: string[] = [];
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') parts.push(`${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  }
  return parts.length ? `?${parts.join('&')}` : '';
}

export const api = {
  get: <T>(url: string, params?: Record<string, string | number | boolean | undefined | null>) =>
    request<T>(`${url}${buildQuery(params)}`),

  post: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined }),

  put: <T>(url: string, body?: unknown) =>
    request<T>(url, { method: 'PUT', body: body !== undefined ? JSON.stringify(body) : undefined }),

  delete: <T>(url: string) =>
    request<T>(url, { method: 'DELETE' }),

  upload: <T>(url: string, formData: FormData) =>
    fetch(url, { method: 'POST', credentials: 'include', body: formData }).then(async (res) => {
      if (!res.ok) {
        const body = await res.json().catch(() => ({ error: res.statusText }));
        throw new ApiError(res.status, body.error || `HTTP ${res.status}`);
      }
      return res.json() as Promise<T>;
    }),
};

// Convenience API methods
export const authApi = {
  me: () => api.get<import('./types').MeResponse>('/api/me'),
  login: (username: string, password: string) =>
    api.post<{ status: string; msg?: string }>('/login', { username, password }),
  logout: () => api.post<{ status: string }>('/logout'),
};

export const userApi = {
  getProfile: (id: number) => api.get<import('./types').User>(`/api/user/${id}`),
  updateProfile: (data: Record<string, unknown>) =>
    api.post<{ status: string; msg?: string }>('/api/user/update', data),
  updateLocation: (lat: number, lon: number) =>
    api.post<{ status: string }>('/user/location/share', { lat, lon }),
  correctLocation: (manualLoc: string, gpsLat?: number, gpsLng?: number) =>
    api.post<{ status: string; msg?: string }>('/user/location/correct', { manual_loc: manualLoc, gps_lat: gpsLat, gps_lng: gpsLng }),
};

export const shareApi = {
  list: (params?: { town?: string; sort?: string; page?: number }) =>
    api.get<import('./types').ShareReport[]>('/api/share/reports', params as Record<string, string | number | undefined>),
  get: (id: number) => api.get<import('./types').ShareReport>(`/api/share/report/${id}`),
  create: (formData: FormData) => api.upload<{ id: number }>('/share-report', formData),
  update: (id: number, formData: FormData) => api.upload<{ status: string }>(`/share-report/edit/${id}`, formData),
  delete: (id: number) => api.post<{ status: string }>(`/share-report/delete/${id}`),
  like: (id: number) => api.post<{ status: string; liked?: boolean }>(`/share-report/like/${id}`),
  comment: (shareId: number, content: string, parentId?: number) =>
    api.post<import('./types').ShareComment>(`/share/comment/${shareId}`, { content, parent_id: parentId }),
  deleteComment: (id: number) => api.post<{ status: string }>(`/share/comment/delete/${id}`),
};

export const postApi = {
  list: (params?: { category?: string; status?: string; page?: number }) =>
    api.get<import('./types').Post[]>('/api/posts', params as Record<string, string | number | undefined>),
  get: (id: number) => api.get<import('./types').Post>(`/api/post/${id}`),
  create: (data: Partial<import('./types').Post>) => api.post<{ id: number }>('/api/post/create', data),
  vote: (id: number, vote: 'like' | 'dislike') => api.post<{ status: string }>(`/api/post/${id}/vote`, { vote }),
};

export const messageApi = {
  inbox: () => api.get<import('./types').Message[]>('/api/messages/inbox'),
  sent: () => api.get<import('./types').Message[]>('/api/messages/sent'),
  send: (receiverId: number, subject: string, content: string) =>
    api.post<{ status: string; msg?: string }>('/api/message/send', { receiver_id: receiverId, subject, content }),
  read: (id: number) => api.post<import('./types').Message>(`/api/message/${id}/read`),
};

export const friendApi = {
  list: () => api.get<import('./types').Friend[]>('/api/friends'),
  request: (userId: number) => api.post<{ status: string }>('/api/friend/request', { user_id: userId }),
  accept: (friendId: number) => api.post<{ status: string }>('/api/friend/accept', { friend_id: friendId }),
  reject: (friendId: number) => api.post<{ status: string }>('/api/friend/reject', { friend_id: friendId }),
};

export const newsApi = {
  list: (category?: string, page?: number) =>
    api.get<import('./types').NewsArticle[]>('/api/news', { category, page }),
  get: (id: number) => api.get<import('./types').NewsArticle & { content?: string }>(`/api/news/content/${id}`),
  vote: (id: number, vote: 'like' | 'dislike') =>
    api.post<{ status: string; likes?: number; dislikes?: number }>(`/news/${vote}/${id}`),
  comment: (newsId: number, content: string, parentId?: number) => {
    const fd = new FormData();
    fd.append('news_id', String(newsId));
    fd.append('content', content);
    if (parentId) fd.append('parent_id', String(parentId));
    return api.upload<{ status: string; ai_score?: number; msg?: string }>('/news/comment', fd);
  },
  getComments: (newsId: number) =>
    api.get<import('./types').NewsComment[]>(`/news/${newsId}/comments`),
  recommend: (newsId: number, title: string, url: string, description?: string) => {
    const fd = new FormData();
    fd.append('title', title);
    fd.append('url', url);
    fd.append('description', description || '');
    return api.upload<{ status: string; msg?: string }>(`/news/${newsId}/recommend`, fd);
  },
};

export const constructionApi = {
  notices: (lat?: number, lng?: number) =>
    api.get<{ notices: import('./types').ConstructionNotice[]; town?: string; village?: string; based_on?: string }>('/api/construction/notices', { lat, lng }),
  transitSuggest: (fromLat: number, fromLng: number) =>
    api.get<{ already_home?: boolean; optimal_departure?: string; [key: string]: unknown }>(
      '/construction/transit/suggest', { from_lat: fromLat, from_lng: fromLng }),
};

export const legalApi = {
  posts: () => api.get<import('./types').LegalPost[]>('/api/legal/posts'),
  get: (id: number) => api.get<import('./types').LegalPost>(`/api/legal/post/${id}`),
  appointments: () => api.get<import('./types').LegalAppointment[]>('/api/legal/appointments'),
  schedules: () => api.get<{ available_dates: string[]; time_slots: { start: string; end: string }[] }>('/api/legal/schedules'),
  create: (formData: FormData) => api.upload<{ status: string; id?: number }>('/api/legal/create', formData),
  comment: (postId: number, content: string) => {
    const fd = new FormData(); fd.append('content', content)
    return api.upload<{ status: string }>(`/api/legal/post/${postId}/comment`, fd)
  },
  toggleStatus: (id: number) => api.post<{ status: string }>(`/legal/post/${id}/toggle-status`, {}),
  deletePost: (id: number) => api.post<{ status: string }>(`/legal/post/${id}/delete`, {}),
  editAnswer: (id: number, answer: string) => {
    const fd = new FormData(); fd.append('answer', answer)
    return api.upload<{ status: string }>(`/legal/admin/answer/edit/${id}`, fd)
  },
};

export const psychoApi = {
  posts: () => api.get<import('./types').PsychoPost[]>('/api/psycho/posts'),
  get: (id: number) => api.get<import('./types').PsychoPost>(`/api/psycho/post/${id}`),
  appointments: () => api.get<import('./types').PsychoAppointment[]>('/api/psycho/appointments'),
  schedules: () => api.get<{ available_dates: string[]; time_slots: { start: string; end: string }[] }>('/api/psycho/schedules'),
  create: (formData: FormData) => api.upload<{ status: string; id?: number }>('/api/psycho/create', formData),
  comment: (postId: number, content: string) => {
    const fd = new FormData(); fd.append('content', content)
    return api.upload<{ status: string }>(`/api/psycho/post/${postId}/comment`, fd)
  },
};

export const villageApi = {
  alerts: (town?: string, village?: string) =>
    api.get<import('./types').VillageAlert[]>('/api/village/alerts', { town, village }),
  events: (myeon?: string, ri?: string) =>
    api.get<import('./types').VillageEvent[]>('/api/village/events', { myeon, ri }),
  wishes: () => api.get<import('./types').VillageWish[]>('/api/village/wishes'),
};
