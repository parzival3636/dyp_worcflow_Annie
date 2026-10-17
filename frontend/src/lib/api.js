import axios from 'axios'
import { Capacitor } from '@capacitor/core'

const isNative = Capacitor.isNativePlatform()
const fallbackHost = isNative && Capacitor.getPlatform() === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000'
const baseURL = import.meta.env.VITE_API_URL || fallbackHost

const api = axios.create({
  baseURL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

export default api
