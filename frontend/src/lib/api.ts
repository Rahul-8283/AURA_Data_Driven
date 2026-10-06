import axios from 'axios';
import { supabase } from './supabase';

const isDev = import.meta.env.VITE_MODE === 'development';
const baseURL = isDev 
  ? (import.meta.env.VITE_API_DEV_URL || 'http://127.0.0.1:8000')
  : (import.meta.env.VITE_API_PRO_URL || 'https://project_name.onrender.com');

const api = axios.create({
  baseURL,
});

api.interceptors.request.use(async (config) => {
  if (supabase) {
    const { data: { session } } = await supabase.auth.getSession();
    if (session?.access_token) {
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }
  }
  return config;
});

export default api;
