import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' }
})

export function get(url, params) { return api.get(url, { params }).then(r => r.data) }
export function post(url, data) { return api.post(url, data).then(r => r.data) }

export function login(username, password, lat, lon) {
  const fd = new FormData()
  fd.append('username', username)
  fd.append('password', password)
  if (lat) fd.append('lat', lat)
  if (lon) fd.append('lon', lon)
  return api.post('/login', fd).then(r => r)
}

export default api
