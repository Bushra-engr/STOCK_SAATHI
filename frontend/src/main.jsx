import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createAuthClient } from '@neondatabase/auth';
import { createRoot } from 'react-dom/client';
import { 
  Activity, ArrowDownLeft, ArrowUpRight, AudioLines, BarChart3, Bell, Boxes, 
  Check, ChevronDown, ChevronRight, CircleHelp, Command, LayoutDashboard, 
  Mic, Package, Pencil, Plus, RefreshCw, Search, Send, Sparkles, 
  TrendingUp, UserRound, Volume2, X, MessageSquare, Trash2, Store, ShoppingBag, 
  ShoppingCart, Trophy, Camera, MapPin, Phone 
} from 'lucide-react';
import { 
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, 
  Tooltip, XAxis, YAxis, PieChart, Pie 
} from 'recharts';
import './style.css';
import './auth.css';
import './landing.css';
import './app-theme.css';

const rawApi = import.meta.env.VITE_API_URL || '';
const API = rawApi.replace(/\/+$/, '');
const NEON_DEFAULT_AUTH_URL = 'https://ep-wispy-darkness-bdu093v2.neonauth.c-8.us-east-2.aws.neon.tech/neondb/auth';
const authClient = createAuthClient(
  import.meta.env.VITE_NEON_AUTH_BASE_URL ||
  import.meta.env.NEON_AUTH_BASE_URL ||
  NEON_DEFAULT_AUTH_URL
);
const getToken = () => localStorage.getItem('stocksaathi_token') || '';
const OAUTH_PENDING_KEY = 'stocksaathi_oauth_pending';
const firstJwt = (...values) => values.find((value) => {
  if (typeof value !== 'string' || value.split('.').length !== 3) return false;
  try {
    const headerSegment = value.split('.')[0].replace(/-/g, '+').replace(/_/g, '/');
    const header = JSON.parse(atob(headerSegment.padEnd(Math.ceil(headerSegment.length / 4) * 4, '=')));
    return typeof header.alg === 'string' && header.alg !== 'none';
  } catch { return false; }
}) || '';

const money = (n) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(n || 0));
const CATEGORY_COLORS = ['#ea580c', '#f59e0b', '#06b6d4', '#10b981', '#8b5cf6', '#ec4899', '#3b82f6'];

const getGreeting = (name) => {
  const hour = new Date().getHours();
  let salutation = 'Good Morning';
  if (hour >= 5 && hour < 12) salutation = 'Good Morning';
  else if (hour >= 12 && hour < 17) salutation = 'Good Afternoon';
  else if (hour >= 17 && hour < 22) salutation = 'Good Evening';
  else salutation = 'Good Night';
  const firstName = (name || '').trim().split(' ')[0];
  const displayName = firstName ? `${firstName} ji` : 'ji';
  return `${salutation}, ${displayName}! 👋`;
};

const getWsVoiceUrl = () => {
  const base = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');
  if (!base) {
    const loc = window.location;
    const proto = loc.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${proto}//${loc.host}/voice/ws/voice`;
  }
  const wsProto = base.startsWith('https:') ? 'wss:' : 'ws:';
  return base.replace(/^http(s)?:\/\//, `${wsProto}://`) + '/voice/ws/voice';
};

async function api(path, options = {}) {
  const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(getToken() ? { Authorization: `Bearer ${getToken()}` } : {}), ...options.headers };
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (!response.ok) {
    const error = new Error((await response.json().catch(() => ({}))).detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

async function resolveNeonSession() {
  let jwtFromSessionHeader = '';
  const sessionResult = await authClient.getSession({
    fetchOptions: {
      onSuccess: ({ response }) => { jwtFromSessionHeader = response.headers.get('set-auth-jwt') || ''; },
    },
  });
  if (sessionResult?.error) throw sessionResult.error;
  const user = sessionResult?.data?.user || null;
  if (!user) return { user: null, jwt: '' };

  const tokenResult = await authClient.token();
  const token = firstJwt(
    tokenResult?.data?.token,
    sessionResult?.data?.token,
    sessionResult?.data?.session?.token,
    jwtFromSessionHeader
  );
  return { user, jwt: token, tokenError: tokenResult?.error || null };
}

function authFailureMessage(e) {
  const message = e?.message || 'Google sign-in could not be completed.';
  const status = e?.status || e?.statusCode;
  if (status === 403 || /\b403\b|forbidden/i.test(message)) {
    return `Neon Auth returned 403 for ${window.location.origin}. Add this app origin under Neon Console → Auth → Allowed domains, then try again.`;
  }
  return message;
}

// -------------------------------------------------------------
// Indian Kirana SVG Icons & Vector Artwork
// -------------------------------------------------------------
function KiranaStoreLogo({ size = 26 }) {
  return (
    <div style={{ width: size, height: size, display: 'grid', placeItems: 'center', flexShrink: 0 }}>
      <svg viewBox="0 0 40 40" width={size} height={size} fill="none">
        <rect x="4" y="16" width="32" height="20" rx="4" fill="#ea580c" />
        <path d="M2 16 L20 6 L38 16 Z" fill="#c2410c" />
        <path d="M4 16 L12 16 L10 24 L4 24 Z" fill="#ffffff" />
        <path d="M16 16 L24 16 L24 24 L16 24 Z" fill="#ffffff" />
        <path d="M28 16 L36 16 L36 24 L30 24 Z" fill="#ffffff" />
        <rect x="14" y="24" width="12" height="12" rx="2" fill="#ffffff" />
      </svg>
    </div>
  );
}

function ShopkeeperAvatar({ size = 56, className = "" }) {
  return (
    <div className={`shopkeeper-avatar-wrap ${className}`} style={{ width: size, height: size, flexShrink: 0, position: 'relative' }}>
      <svg viewBox="0 0 100 100" style={{ width: '100%', height: '100%', borderRadius: '50%' }}>
        <defs>
          <linearGradient id="avatarBg" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ffedd5" />
            <stop offset="100%" stopColor="#fed7aa" />
          </linearGradient>
          <linearGradient id="kurtaGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ff7843" />
            <stop offset="100%" stopColor="#ea580c" />
          </linearGradient>
        </defs>
        <circle cx="50" cy="50" r="48" fill="url(#avatarBg)" stroke="#f97316" strokeWidth="2.5" />
        <rect x="44" y="52" width="12" height="14" rx="3" fill="#d49a6a" />
        <ellipse cx="50" cy="40" rx="18" ry="20" fill="#e0a97b" />
        <path d="M32 36 C32 20 68 20 68 36 C68 28 60 22 50 22 C40 22 32 28 32 36 Z" fill="#292524" />
        <path d="M37 32 Q42 29 45 32" stroke="#292524" strokeWidth="2" strokeLinecap="round" fill="none" />
        <path d="M55 32 Q58 29 63 32" stroke="#292524" strokeWidth="2" strokeLinecap="round" fill="none" />
        <ellipse cx="41" cy="36" rx="2" ry="2.5" fill="#292524" />
        <ellipse cx="59" cy="36" rx="2" ry="2.5" fill="#292524" />
        <path d="M50 37 L48 44 L52 44" stroke="#c08152" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" fill="none" />
        <path d="M39 46 Q50 44 50 48 Q50 44 61 46 Q57 51 50 48 Q43 51 39 46 Z" fill="#292524" />
        <path d="M44 51 Q50 55 56 51" stroke="#292524" strokeWidth="1.5" strokeLinecap="round" fill="none" />
        <circle cx="50" cy="27" r="1.5" fill="#dc2626" />
        <path d="M22 88 C24 65 38 61 50 61 C62 61 76 65 78 88 Z" fill="url(#kurtaGrad)" />
        <path d="M24 69 Q32 63 36 77 Q34 88 28 90 Z" fill="#ffffff" opacity="0.95" stroke="#dc2626" strokeWidth="1" strokeDasharray="2 2" />
        <path d="M45 61 L50 71 L55 61" stroke="#fed7aa" strokeWidth="2" fill="none" />
      </svg>
    </div>
  );
}

function ProductPackThumbnail({ name = "", category = "", size = 42 }) {
  const n = (name || "").toLowerCase();
  
  if (n.includes('parle') || n.includes('biscuit')) {
    return (
      <div className="pack-thumb" style={{ width: size, height: size }}>
        <svg viewBox="0 0 60 60" width={size} height={size}>
          <rect x="4" y="10" width="52" height="40" rx="6" fill="#facc15" stroke="#eab308" strokeWidth="1.5" />
          <rect x="8" y="14" width="44" height="32" rx="4" fill="#fef08a" />
          <rect x="12" y="24" width="36" height="12" rx="3" fill="#dc2626" />
          <text x="30" y="33" textAnchor="middle" fill="#ffffff" fontWeight="900" fontSize="8" fontFamily="sans-serif">Parle-G</text>
        </svg>
      </div>
    );
  }
  if (n.includes('tea') || n.includes('chai') || n.includes('tata')) {
    return (
      <div className="pack-thumb" style={{ width: size, height: size }}>
        <svg viewBox="0 0 60 60" width={size} height={size}>
          <path d="M12 10 L48 10 L44 52 L16 52 Z" fill="#15803d" stroke="#166534" strokeWidth="1.5" />
          <rect x="18" y="18" width="24" height="20" rx="3" fill="#fef08a" />
          <text x="30" y="28" textAnchor="middle" fill="#166534" fontWeight="900" fontSize="7" fontFamily="sans-serif">TATA</text>
          <text x="30" y="35" textAnchor="middle" fill="#dc2626" fontWeight="800" fontSize="6" fontFamily="sans-serif">TEA</text>
        </svg>
      </div>
    );
  }
  if (n.includes('atta') || n.includes('aashirvaad') || n.includes('flour')) {
    return (
      <div className="pack-thumb" style={{ width: size, height: size }}>
        <svg viewBox="0 0 60 60" width={size} height={size}>
          <rect x="10" y="8" width="40" height="46" rx="6" fill="#b91c1c" stroke="#991b1b" strokeWidth="1.5" />
          <ellipse cx="30" cy="30" rx="14" ry="16" fill="#fef3c7" />
          <text x="30" y="49" textAnchor="middle" fill="#ffffff" fontWeight="800" fontSize="6" fontFamily="sans-serif">ATTA</text>
        </svg>
      </div>
    );
  }
  if (n.includes('shampoo') || n.includes('शैंपू') || n.includes('शैम्पू') || n.includes('clinic') || n.includes('dove')) {
    return (
      <div className="pack-thumb" style={{ width: size, height: size }}>
        <svg viewBox="0 0 60 60" width={size} height={size}>
          <rect x="18" y="16" width="24" height="36" rx="6" fill="#0284c7" stroke="#0369a1" strokeWidth="1.5" />
          <rect x="25" y="8" width="10" height="8" rx="2" fill="#38bdf8" />
          <ellipse cx="30" cy="32" rx="8" ry="10" fill="#ffffff" />
          <text x="30" y="35" textAnchor="middle" fill="#0284c7" fontWeight="900" fontSize="7" fontFamily="sans-serif">SHAMPOO</text>
        </svg>
      </div>
    );
  }

  const cat = (category || '').toLowerCase();
  const color = cat.includes('snack') ? '#f59e0b' :
                cat.includes('bev') ? '#06b6d4' :
                cat.includes('dairy') ? '#3b82f6' :
                cat.includes('care') || cat.includes('person') ? '#ec4899' :
                cat.includes('clean') || cat.includes('home') ? '#10b981' : '#ea580c';

  return (
    <div className="pack-thumb default-pack" style={{ width: size, height: size, background: `${color}18`, borderColor: `${color}40`, color }}>
      <span>{(name || '?')[0].toUpperCase()}</span>
    </div>
  );
}

function KiranaStorefrontIllustration() {
  return (
    <div className="kirana-illustration-container">
      <svg viewBox="0 0 460 380" className="kirana-store-svg" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="230" cy="190" r="160" fill="url(#bgAuraKirana)" opacity="0.6" />
        <defs>
          <radialGradient id="bgAuraKirana" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#ffedd5" />
            <stop offset="100%" stopColor="#f8f7f4" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="micGradKirana" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ff7843" />
            <stop offset="100%" stopColor="#ea580c" />
          </linearGradient>
        </defs>
        
        <rect x="70" y="100" width="320" height="230" rx="14" fill="#faf5ee" stroke="#e5ded5" strokeWidth="3" />
        <rect x="100" y="55" width="260" height="42" rx="8" fill="#d97706" stroke="#b45309" strokeWidth="2" />
        <text x="230" y="82" textAnchor="middle" fill="#ffffff" fontWeight="800" fontSize="18" letterSpacing="2" fontFamily="sans-serif">KIRANA STORE</text>
        
        <path d="M55 100 L405 100 L385 145 L75 145 Z" fill="#dc2626" />
        <path d="M75 100 L115 100 L110 145 L75 145 Z" fill="#ffffff" />
        <path d="M150 100 L190 100 L185 145 L150 145 Z" fill="#ffffff" />
        <path d="M225 100 L265 100 L260 145 L225 145 Z" fill="#ffffff" />
        <path d="M300 100 L340 100 L335 145 L300 145 Z" fill="#ffffff" />
        <path d="M375 100 L405 100 L385 145 L370 145 Z" fill="#ffffff" />
        
        {Array.from({ length: 11 }).map((_, i) => (
          <path key={i} d={`M${65 + i * 30} 145 Q${80 + i * 30} 157 ${95 + i * 30} 145`} fill={i % 2 === 0 ? "#dc2626" : "#ffffff"} />
        ))}
        
        <rect x="90" y="165" width="130" height="150" rx="6" fill="#854d0e" opacity="0.15" />
        <line x1="90" y1="210" x2="220" y2="210" stroke="#b45309" strokeWidth="4" />
        <line x1="90" y1="260" x2="220" y2="260" stroke="#b45309" strokeWidth="4" />
        
        <rect x="100" y="178" width="18" height="28" rx="4" fill="#f59e0b" />
        <rect x="124" y="180" width="18" height="26" rx="4" fill="#10b981" />
        <rect x="148" y="176" width="20" height="30" rx="4" fill="#ef4444" />
        <rect x="174" y="178" width="18" height="28" rx="4" fill="#3b82f6" />
        <rect x="198" y="180" width="16" height="26" rx="4" fill="#8b5cf6" />
        
        <rect x="235" y="220" width="145" height="95" rx="8" fill="#d97706" opacity="0.3" stroke="#b45309" strokeWidth="2" />
        <text x="267" y="255" textAnchor="middle" fill="#0f172a" fontWeight="700" fontSize="11">BILL</text>
        
        <ellipse cx="90" cy="315" rx="26" ry="20" fill="#d4a373" stroke="#bc6c25" strokeWidth="2" />
        <text x="90" y="322" textAnchor="middle" fill="#7f4f24" fontWeight="800" fontSize="9">ATTA</text>
        
        <ellipse cx="140" cy="320" rx="28" ry="22" fill="#dda15e" stroke="#bc6c25" strokeWidth="2" />
        <text x="140" y="327" textAnchor="middle" fill="#7f4f24" fontWeight="800" fontSize="9">DAL</text>
        
        <g transform="translate(360, 140)">
          <circle cx="28" cy="28" r="42" fill="#ea580c" opacity="0.18" />
          <circle cx="28" cy="28" r="32" fill="url(#micGradKirana)" />
          <rect x="23" y="17" width="10" height="16" rx="5" fill="#ffffff" />
          <path d="M19 25 C19 31 37 31 37 25" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" fill="none" />
          <line x1="28" y1="31" x2="28" y2="38" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" />
          <line x1="22" y1="38" x2="34" y2="38" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" />
        </g>
      </svg>
    </div>
  );
}

// -------------------------------------------------------------
// Main Application Component
// -------------------------------------------------------------
export default function App() {
  // App navigation state: 'landing' or 'dashboard'
  // Shows landing page first as standard web flow!
  const [currentView, setCurrentView] = useState(() => {
    return window.location.hash === '#dashboard' ? 'dashboard' : 'landing';
  });

  const [page, setPage] = useState('Overview');
  const [profile, setProfile] = useState({ name: '', shop_name: '', shop_category: '', phone: '', shop_address: '' });
  const [isAuthenticated, setIsAuthenticated] = useState(Boolean(getToken()));
  const [authLoading, setAuthLoading] = useState(true);
  const [hasNeonSession, setHasNeonSession] = useState(false);
  const [authError, setAuthError] = useState('');
  
  // Modals
  const [productModal, setProductModal] = useState(false);
  const [editProductModal, setEditProductModal] = useState(false);
  const [deleteConfirmModal, setDeleteConfirmModal] = useState(false);
  const [selectDeleteModal, setSelectDeleteModal] = useState(false);
  const [selectedProductIdToDelete, setSelectedProductIdToDelete] = useState('');
  const [productToDelete, setProductToDelete] = useState(null);
  const [editingProduct, setEditingProduct] = useState(null);
  const [editDraft, setEditDraft] = useState({ name: '', brand: '', variant: '', category: '', unit: 'piece', purchase_price: '', selling_price: '' });
  const [editInventoryModal, setEditInventoryModal] = useState(false);
  const [addStockModal, setAddStockModal] = useState(false);
  const [editingInventory, setEditingInventory] = useState(null);
  const [editInventoryDraft, setEditInventoryDraft] = useState({ current_stock: '', purchase_price: '', selling_price: '', reorder_level: '' });
  const [addStockDraft, setAddStockDraft] = useState({ product_id: '', current_stock: '0', purchase_price: '', selling_price: '', reorder_level: '5' });
  const [productDraft, setProductDraft] = useState({ name: '', brand: '', variant: '', category: '', unit: 'piece', purchase_price: '', selling_price: '', initial_stock: '' });

  // Selection mode for batch delete
  const [isSelectMode, setIsSelectMode] = useState(false);
  const [selectedProductIds, setSelectedProductIds] = useState([]);

  // Dashboard Data State - STRICTLY REAL DATABASE DATA
  const [summary, setSummary] = useState(null);
  const [inventory, setInventory] = useState([]);
  const [products, setProducts] = useState([]);
  const [topProducts, setTopProducts] = useState([]);
  const [movements, setMovements] = useState([]);
  const [activity, setActivity] = useState([]);
  const [days, setDays] = useState(7);
  const [filter, setFilter] = useState('all');
  const [categoryFilter, setCategoryFilter] = useState('All');
  const [activityFilter, setActivityFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [toast, setToast] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Voice & Assistant State
  const [listening, setListening] = useState(false);
  const [status, setStatus] = useState('Ready when you are');
  const [transcript, setTranscript] = useState('');
  const [liveTranscript, setLiveTranscript] = useState('');
  const [heardRequest, setHeardRequest] = useState(false);
  const [reply, setReply] = useState('');
  const [text, setText] = useState('');
  const [pendingConfirmation, setPendingConfirmation] = useState(false);
  const [tasks, setTasks] = useState([]);
  const [assistantMode, setAssistantMode] = useState('voice');
  const [chatMessages, setChatMessages] = useState([
    { id: 1, sender: 'assistant', text: 'StockSaathi me aapka swagat hai. Bolkar ya chat se stock manage karein.', time: 'Abhi' }
  ]);

  const wsRef = useRef(null);
  const streamRef = useRef(null);
  const audioContextRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const socketReadyRef = useRef(null);
  const socketConnectedRef = useRef(false);
  const responseAudioRef = useRef(null);
  const chatEndRef = useRef(null);
  const recognitionRef = useRef(null);
  const listeningRef = useRef(false);
  const speechDetectedRef = useRef(false);
  const transcriptRef = useRef('');
  const workletNodeRef = useRef(null);
  const turnEndedRef = useRef(false);
  const expectingAudioRef = useRef(false);
  const audioPlayedForReplyRef = useRef(false);
  const fallbackTtsTimerRef = useRef(null);
  const latestReplyRef = useRef('');
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  useEffect(() => {
    if ('speechSynthesis' in window) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => {
        window.speechSynthesis.getVoices();
      };
    }
  }, []);

  const addMessage = (sender, messageText, extra = {}) => {
    const timeStr = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
    setChatMessages((prev) => [...prev, { id: Date.now() + Math.random(), sender, text: messageText, time: timeStr, ...extra }]);
  };

  // Auth Initialization
  useEffect(() => {
    let ignore = false;
    const initializeAuth = async () => {
      setAuthLoading(true); setAuthError('');
      try {
        const url = new URL(window.location.href);
        const urlError = url.searchParams.get('error');
        const urlErrorDesc = url.searchParams.get('error_description');
        if (urlError) {
          sessionStorage.removeItem(OAUTH_PENDING_KEY);
          window.history.replaceState({}, document.title, window.location.pathname);
          const errDetail = urlError === 'invalid_code'
            ? 'Google OAuth code verification failed (invalid_code). Google Cloud Console mein "Authorized redirect URIs" check karein.'
            : `Google login error: ${urlErrorDesc || urlError}`;
          setAuthError(errDetail);
          setIsAuthenticated(false);
          setAuthLoading(false);
          return;
        }
        if (url.searchParams.has('code') && !url.searchParams.has('neon_auth_session_verifier')) {
          sessionStorage.removeItem(OAUTH_PENDING_KEY);
          window.history.replaceState({}, document.title, window.location.pathname);
          setAuthError('Config error: Google redirected to Vercel directly instead of Neon Auth. Google Console Authorized redirect URI must be Neon Auth.');
          setIsAuthenticated(false);
          setAuthLoading(false);
          return;
        }
        const urlHadVerifier = url.searchParams.has('neon_auth_session_verifier');
        const hadOAuthPending = Boolean(sessionStorage.getItem(OAUTH_PENDING_KEY));
        let resolved = await resolveNeonSession();
        if (urlHadVerifier || hadOAuthPending) {
          sessionStorage.removeItem(OAUTH_PENDING_KEY);
          window.history.replaceState({}, document.title, window.location.pathname);
          if (resolved.user && !resolved.jwt) {
            for (let i = 0; i < 3 && !resolved.jwt; i++) {
              await new Promise((r) => setTimeout(r, 600));
              resolved = await resolveNeonSession();
            }
          }
        }
        if (ignore) return;
        if (resolved.user) {
          setHasNeonSession(true);
          if (resolved.jwt) {
            localStorage.setItem('stocksaathi_token', resolved.jwt);
            setIsAuthenticated(true);
            setHasNeonSession(false);
            if (urlHadVerifier || hadOAuthPending) {
              setCurrentView('dashboard');
            }
          } else {
            setIsAuthenticated(false);
            setAuthError(resolved.tokenError?.message || 'Signed in to Google, but could not retrieve your Neon session token.');
          }
        } else {
          setIsAuthenticated(false);
          setHasNeonSession(false);
        }
      } catch (e) {
        if (!ignore) {
          sessionStorage.removeItem(OAUTH_PENDING_KEY);
          setIsAuthenticated(false);
          setAuthError(authFailureMessage(e));
        }
      } finally {
        if (!ignore) setAuthLoading(false);
      }
    };
    initializeAuth();
    return () => { ignore = true; };
  }, []);

  // Authenticated WebSocket connection for real-time Gnani streaming STT & TTS
  useEffect(() => {
    if (!isAuthenticated || !getToken()) {
      if (wsRef.current) {
        try { wsRef.current.close(); } catch {}
        wsRef.current = null;
      }
      socketConnectedRef.current = false;
      setWsConnected(false);
      return;
    }

    let active = true;
    let reconnectTimer = null;

    const connectWs = () => {
      if (!active) return;
      try {
        const url = getWsVoiceUrl();
        const ws = new WebSocket(url);
        ws.binaryType = 'arraybuffer';
        wsRef.current = ws;

        ws.onopen = () => {
          ws.send(JSON.stringify({ event: 'auth', token: getToken() }));
        };

        ws.onmessage = (event) => {
          if (typeof event.data === 'string') {
            try {
              const msg = JSON.parse(event.data);
              if (msg.event === 'connected') {
                socketConnectedRef.current = true;
                setWsConnected(true);
              } else if (msg.event === 'transcript_segment') {
                if (msg.text) {
                  setLiveTranscript(msg.text);
                  speechDetectedRef.current = true;
                  setHeardRequest(true);
                }
              } else if (msg.event === 'transcript') {
                if (msg.text) {
                  setTranscript(msg.text);
                  addMessage('user', msg.text);
                }
              } else if (msg.event === 'assistant_text') {
                setReply(msg.text);
                latestReplyRef.current = msg.text;
                audioPlayedForReplyRef.current = false;
                if (msg.tasks) setTasks(msg.tasks);
                setPendingConfirmation(Boolean(msg.pending_confirmation));
                setStatus('Ready when you are');
                addMessage('assistant', msg.text, { tasks: msg.tasks, pending_confirmation: msg.pending_confirmation });
                refresh();
                // Fast fallback: If Gnani audio doesn't arrive within 1200ms, start browser TTS immediately
                if (fallbackTtsTimerRef.current) clearTimeout(fallbackTtsTimerRef.current);
                fallbackTtsTimerRef.current = setTimeout(() => {
                  if (!audioPlayedForReplyRef.current && latestReplyRef.current) {
                    speakBrowserTTS(latestReplyRef.current);
                  }
                }, 1200);
              } else if (msg.event === 'assistant_audio_failed') {
                if (fallbackTtsTimerRef.current) clearTimeout(fallbackTtsTimerRef.current);
                if (!audioPlayedForReplyRef.current && latestReplyRef.current) {
                  speakBrowserTTS(latestReplyRef.current);
                }
              } else if (msg.event === 'assistant_audio') {
                expectingAudioRef.current = true;
              } else if (msg.event === 'error') {
                setToast(msg.message || 'Voice error');
                setStatus('Ready when you are');
              }
            } catch (parseErr) {
              console.warn('WS JSON message parse error:', parseErr);
            }
          } else if (event.data instanceof ArrayBuffer) {
            // Binary studio-quality WAV audio from Gnani TTS
            audioPlayedForReplyRef.current = true;
            if (fallbackTtsTimerRef.current) clearTimeout(fallbackTtsTimerRef.current);
            if ('speechSynthesis' in window) {
              window.speechSynthesis.cancel();
            }
            if (window.__currentAudio) {
              try { window.__currentAudio.pause(); } catch {}
              window.__currentAudio = null;
            }
            try {
              const blob = new Blob([event.data], { type: 'audio/wav' });
              const blobUrl = URL.createObjectURL(blob);
              const audio = new Audio(blobUrl);
              window.__currentAudio = audio;
              audio.play().catch((playErr) => {
                console.warn('Gnani audio playback blocked by browser policy:', playErr);
                if (latestReplyRef.current) speakBrowserTTS(latestReplyRef.current);
              });
            } catch (audioErr) {
              console.warn('Gnani audio Blob decode error:', audioErr);
            }
          }
        };

        ws.onclose = () => {
          socketConnectedRef.current = false;
          setWsConnected(false);
          if (active) {
            reconnectTimer = setTimeout(connectWs, 2500);
          }
        };

        ws.onerror = () => {
          socketConnectedRef.current = false;
          setWsConnected(false);
        };
      } catch (wsErr) {
        console.warn('WebSocket connection init failed:', wsErr);
        if (active) reconnectTimer = setTimeout(connectWs, 3000);
      }
    };

    connectWs();

    return () => {
      active = false;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (wsRef.current) {
        try { wsRef.current.close(); } catch {}
        wsRef.current = null;
      }
      socketConnectedRef.current = false;
      setWsConnected(false);
    };
  }, [isAuthenticated]);

  // Fetch real data strictly from database with clear tactile feedback
  const refresh = async (manualClick = false) => {
    const token = getToken();
    if (!token) {
      if (manualClick) setToast('Please sign in to refresh data.');
      return;
    }
    setLoading(true);
    const startTime = Date.now();
    try {
      const results = await Promise.allSettled([
        api(`/dashboard/overview?days=${days}`),
        api('/users/me'),
        api('/inventory/'),
        api('/products/'),
        api('/voice/messages?limit=50'),
      ]);

      const [ovRes, uRes, invRes, prodsRes, msgsRes] = results;

      if (uRes.status === 'fulfilled' && uRes.value) {
        const u = uRes.value;
        setProfile({
          name: u.name || '',
          shop_name: u.shop_name || 'My Shop',
          shop_category: u.shop_category || 'Kirana Store',
          phone: u.phone || '',
          shop_address: u.shop_address || ''
        });
      }

      if (ovRes.status === 'fulfilled' && ovRes.value) {
        const ov = ovRes.value;
        setSummary(ov.summary);
        setTopProducts(Array.isArray(ov.top_products?.items) ? ov.top_products.items : []);
        setActivity(Array.isArray(ov.activity?.items) ? ov.activity.items : []);
        setMovements(Array.isArray(ov.movements?.items) ? ov.movements.items : []);
      }

      if (invRes.status === 'fulfilled' && Array.isArray(invRes.value)) {
        setInventory(invRes.value);
      }

      if (prodsRes.status === 'fulfilled' && Array.isArray(prodsRes.value)) {
        setProducts(prodsRes.value);
      }

      if (msgsRes.status === 'fulfilled' && msgsRes.value?.items?.length > 0) {
        setChatMessages(
          msgsRes.value.items.map((m) => ({
            id: m.id,
            sender: m.role,
            text: m.message,
            time: new Date(m.created_at).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
          }))
        );
      }

      // Ensure minimum 500ms spin feedback so user visibly sees the refresh action
      const elapsed = Date.now() - startTime;
      if (elapsed < 500) {
        await new Promise((r) => setTimeout(r, 500 - elapsed));
      }

      // Check if all primary calls failed (network/backend offline)
      const failedCount = results.filter((r) => r.status === 'rejected').length;
      if (failedCount === results.length) {
        const err = results[0].reason;
        const msg = err?.message || 'Backend server se connect nahi ho pa raha.';
        setError(msg);
        if (manualClick) setToast(`Sync failed: ${msg}`);
      } else {
        setError('');
        if (manualClick) setToast('Data updated successfully! ✨');
      }
    } catch (e) {
      setError(e.message || 'Could not refresh data');
      if (manualClick) setToast(`Sync failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) refresh();
  }, [isAuthenticated, days]);

  const speakAssistant = (textToSpeak, audioBase64 = null) => {
    if (!textToSpeak) return;

    // 1. Play natural Gnani AI voice audio if available
    if (audioBase64) {
      try {
        if (window.__currentAudio) {
          try { window.__currentAudio.pause(); } catch {}
          window.__currentAudio = null;
        }
        if ('speechSynthesis' in window) {
          window.speechSynthesis.cancel();
        }
        const audio = new Audio('data:audio/wav;base64,' + audioBase64);
        window.__currentAudio = audio;
        const playPromise = audio.play();
        if (playPromise !== undefined) {
          playPromise.catch((e) => {
            console.warn('Gnani audio play error, falling back to browser speech:', e);
            speakBrowserTTS(textToSpeak);
          });
        }
        return;
      } catch (err) {
        console.warn('Audio construction error:', err);
      }
    }

    // 2. High-reliability Web Speech API fallback
    speakBrowserTTS(textToSpeak);
  };

  const speakBrowserTTS = (textToSpeak) => {
    if (!textToSpeak || !('speechSynthesis' in window)) return;
    if (window.__currentAudio) {
      try { window.__currentAudio.pause(); } catch {}
      window.__currentAudio = null;
    }
    try {
      let clean = textToSpeak
        .replace(/this_month/gi, 'is mahine')
        .replace(/this_week/gi, 'is hafte')
        .replace(/today/gi, 'aaj')
        .replace(/yesterday/gi, 'kal')
        .replace(/last_month/gi, 'pichle mahine')
        .replace(/₹\s*(\d+)/g, '$1 rupaye')
        .replace(/₹/g, 'rupaye ')
        .replace(/[\*\_\#\`\[\]\(\)]/g, ' ')
        .trim();

      if (window.speechSynthesis.speaking) {
        window.speechSynthesis.cancel();
      }
      if (window.speechSynthesis.paused) {
        window.speechSynthesis.resume();
      }

      const utterance = new SpeechSynthesisUtterance(clean);
      window.__activeUtterance = utterance; // Prevent Chromium garbage collection bug

      const voices = window.speechSynthesis.getVoices() || [];
      const hindiVoice = voices.find((v) => v.lang === 'hi-IN' || v.lang === 'hi' || (v.name && v.name.toLowerCase().includes('hindi')));
      const indianVoice = voices.find((v) => v.lang === 'en-IN' || (v.name && v.name.toLowerCase().includes('india')));

      if (hindiVoice) {
        utterance.voice = hindiVoice;
        utterance.lang = hindiVoice.lang;
      } else if (indianVoice) {
        utterance.voice = indianVoice;
        utterance.lang = indianVoice.lang;
      } else if (voices.length > 0) {
        utterance.voice = voices[0];
        utterance.lang = voices[0].lang || 'en-US';
      }

      utterance.rate = 1.0;
      utterance.pitch = 1.0;
      utterance.onend = () => { window.__activeUtterance = null; };
      utterance.onerror = (e) => {
        console.warn('Utterance error:', e);
        window.__activeUtterance = null;
      };

      window.speechSynthesis.speak(utterance);
    } catch (err) {
      console.warn('Speech synthesis error:', err);
    }
  };

  const startVoice = async () => {
    if (!getToken()) { setIsAuthenticated(false); return; }
    try {
      if (window.__currentAudio) {
        try { window.__currentAudio.pause(); } catch {}
      }
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }

      setStatus('Listening… (Speak freely)');
      setReply('');
      setLiveTranscript('');
      setTranscript('');
      setHeardRequest(false);
      listeningRef.current = true;
      setListening(true);
      speechDetectedRef.current = false;
      turnEndedRef.current = false;
      audioPlayedForReplyRef.current = false;
      transcriptRef.current = '';

      const ws = wsRef.current;
      const isWsReady = ws && ws.readyState === WebSocket.OPEN && socketConnectedRef.current;

      const media = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = media;

      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(media);

      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);

      let workletActive = false;
      if (isWsReady && audioContext.audioWorklet) {
        try {
          await audioContext.audioWorklet.addModule('/pcm-worklet.js');
          const pcmNode = new AudioWorkletNode(audioContext, 'pcm-processor');
          workletNodeRef.current = pcmNode;
          source.connect(pcmNode);

          // Tell backend Gnani streaming STT to start turn
          ws.send(JSON.stringify({ event: 'start_turn' }));

          pcmNode.port.onmessage = (event) => {
            if (listeningRef.current && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              // Send binary mono 16 kHz PCM16 frames
              wsRef.current.send(event.data);
            }
          };
          workletActive = true;
        } catch (workletErr) {
          console.warn('AudioWorklet module load issue, falling back to Web Speech:', workletErr);
        }
      }

      // Real-time live transcription (runs concurrently with AudioWorklet for zero-latency instant preview: sath-sath)
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        try {
          const rec = new SpeechRecognition();
          recognitionRef.current = rec;
          rec.continuous = true;
          rec.interimResults = true;
          rec.lang = 'hi-IN';
          rec.onresult = (e) => {
            let interim = '';
            let finalT = '';
            for (let i = e.resultIndex; i < e.results.length; ++i) {
              if (e.results[i].isFinal) finalT += ' ' + e.results[i][0].transcript;
              else interim += e.results[i][0].transcript;
            }
            const spoken = (finalT + ' ' + interim).trim();
            if (spoken) {
              transcriptRef.current = spoken;
              setLiveTranscript(spoken);
              setTranscript(spoken);
              setHeardRequest(true);
              speechDetectedRef.current = true;
            }
          };
          rec.onerror = (e) => {
            if (e.error !== 'no-speech') {
              console.warn('SpeechRecognition note:', e.error);
            }
          };
          rec.start();
        } catch (recErr) {
          console.warn('SpeechRecognition concurrent start note:', recErr);
        }
      } else if (!workletActive) {
        setListening(false);
        listeningRef.current = false;
        setAssistantMode('chat');
        setToast('Voice input is not supported in this browser. Chat mode open kar diya hai.');
        setStatus('Chat mode active');
        return;
      }

      // Energy-based silence detector
      const buffer = new Uint8Array(analyser.frequencyBinCount);
      let lastSpokeTime = Date.now();

      const detectAudio = () => {
        if (!listeningRef.current) return;
        analyser.getByteFrequencyData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) sum += buffer[i];
        const average = sum / buffer.length;

        if (average > 18) {
          lastSpokeTime = Date.now();
          speechDetectedRef.current = true;
        } else if (speechDetectedRef.current && (Date.now() - lastSpokeTime > 2100)) {
          stopVoice();
          return;
        }
        silenceTimerRef.current = requestAnimationFrame(detectAudio);
      };
      silenceTimerRef.current = requestAnimationFrame(detectAudio);
    } catch (err) {
      setToast('Microphone permission required.');
      setListening(false);
      listeningRef.current = false;
    }
  };

  const stopVoice = () => {
    if (turnEndedRef.current) return;
    turnEndedRef.current = true;
    listeningRef.current = false;
    setListening(false);

    if (silenceTimerRef.current) cancelAnimationFrame(silenceTimerRef.current);
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch {}
      recognitionRef.current = null;
    }
    if (workletNodeRef.current) {
      try { workletNodeRef.current.disconnect(); } catch {}
      workletNodeRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current) {
      try { audioContextRef.current.close(); } catch {}
      audioContextRef.current = null;
    }

    const ws = wsRef.current;
    const isWsReady = ws && ws.readyState === WebSocket.OPEN && socketConnectedRef.current;

    // Requirement 6: Do NOT send previous commands if user opened mic but said nothing!
    if (!speechDetectedRef.current && !transcriptRef.current) {
      if (isWsReady) {
        try { ws.send(JSON.stringify({ event: 'stop' })); } catch {}
      }
      setLiveTranscript('');
      setStatus('Ready when you are');
      return;
    }

    // Streaming path: Send end_turn exactly once to complete Gnani turn!
    if (isWsReady) {
      setStatus('Thinking…');
      try {
        ws.send(JSON.stringify({
          event: 'end_turn',
          client_transcript: (transcriptRef.current || liveTranscript || '').trim()
        }));
      } catch (wsSendErr) {
        console.warn('end_turn send error:', wsSendErr);
      }
      return;
    }

    // Fallback path: HTTP command if WebSocket is not active
    const spokenText = transcriptRef.current.trim();
    transcriptRef.current = '';
    if (spokenText) {
      sendText(spokenText);
    } else {
      setStatus('Ready when you are');
    }
  };

  const sendText = async (customText = null) => {
    const textToSend = (customText !== null ? customText : text).trim();
    if (!textToSend) return;
    setText('');
    setReply('');
    setStatus('Thinking…');
    addMessage('user', textToSend);

    const ws = wsRef.current;
    const isWsReady = ws && ws.readyState === WebSocket.OPEN && socketConnectedRef.current;

    // Fast WebSocket path: Instant UI update (< 100ms)!
    if (isWsReady) {
      try {
        ws.send(JSON.stringify({ event: 'text', text: textToSend }));
        return;
      } catch (wsErr) {
        console.warn('WS send text failed, falling back to HTTP:', wsErr);
      }
    }

    // Reliable HTTP fallback
    try {
      const res = await api('/voice/text-command', {
        method: 'POST',
        body: JSON.stringify({ text: textToSend }),
      });
      setReply(res.reply);
      if (res.tasks) setTasks(res.tasks);
      setPendingConfirmation(Boolean(res.pending_confirmation));
      setStatus('Ready when you are');
      addMessage('assistant', res.reply, { tasks: res.tasks, pending_confirmation: res.pending_confirmation });
      speakAssistant(res.reply, res.audio);
      refresh();
    } catch (err) {
      console.error('Voice command error:', err);
      const isNetErr = err?.name === 'TypeError' || String(err?.message).includes('fetch') || String(err?.message).includes('NetworkError');
      setToast(isNetErr ? 'Backend server se connect nahi ho pa raha. Kripya check karein ki server chal raha hai.' : (err.message || 'Error processing request'));
      setStatus('Ready when you are');
    }
  };

  const openEditProduct = (prod) => {
    setEditingProduct(prod);
    const inv = inventory.find((i) => i.product_id === prod.id || i.product?.id === prod.id);
    setEditDraft({
      name: prod.name || '',
      brand: prod.brand || '',
      variant: prod.variant || '',
      category: prod.category || '',
      unit: prod.unit || 'piece',
      purchase_price: inv?.purchase_price ?? '',
      selling_price: inv?.selling_price ?? '',
      inventory_id: inv?.id,
    });
    setEditProductModal(true);
  };

  const updateProductSubmit = async (e) => {
    e.preventDefault();
    if (!editingProduct) return;
    try {
      await api(`/products/${editingProduct.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editDraft.name,
          brand: editDraft.brand || null,
          variant: editDraft.variant || null,
          category: editDraft.category || null,
          unit: editDraft.unit || 'piece',
        }),
      });
      if (editDraft.inventory_id && (editDraft.purchase_price !== '' || editDraft.selling_price !== '')) {
        await api(`/inventory/${editDraft.inventory_id}`, {
          method: 'PATCH',
          body: JSON.stringify({
            purchase_price: editDraft.purchase_price !== '' ? Number(editDraft.purchase_price) : undefined,
            selling_price: editDraft.selling_price !== '' ? Number(editDraft.selling_price) : undefined,
          }),
        });
      }
      setEditProductModal(false);
      setEditingProduct(null);
      setToast('Product updated successfully!');
      refresh();
    } catch (err) { setToast(err.message || 'Failed to update product'); }
  };

  const confirmDeleteProduct = (prod) => {
    setProductToDelete(prod);
    setDeleteConfirmModal(true);
  };

  const executeDeleteProduct = async () => {
    if (!productToDelete?.id) return;
    try {
      await api(`/products/${productToDelete.id}`, { method: 'DELETE' });
      setDeleteConfirmModal(false);
      setProductToDelete(null);
      if (editProductModal) setEditProductModal(false);
      setToast(`Product '${productToDelete.name}' deleted permanently`);
      refresh();
    } catch (err) { setToast(err.message || 'Failed to delete product'); }
  };

  const deleteProductById = async (productId, name = '') => {
    if (!productId) return false;
    try {
      await api(`/products/${productId}`, { method: 'DELETE' });
      setToast(`Product '${name || 'Selected'}' deleted permanently`);
      refresh();
      return true;
    } catch (err) {
      setToast(err.message || 'Failed to delete product');
      return false;
    }
  };

  const handleBatchDelete = async () => {
    if (!selectedProductIds.length) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedProductIds.length} selected product(s)?`)) return;
    setLoading(true);
    try {
      for (const pid of selectedProductIds) {
        await api(`/products/${pid}`, { method: 'DELETE' });
      }
      setToast(`${selectedProductIds.length} product(s) deleted permanently`);
      setSelectedProductIds([]);
      setIsSelectMode(false);
      refresh();
    } catch (err) {
      setToast(err.message || 'Failed to delete selected products');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelectProduct = (productId) => {
    setSelectedProductIds((prev) => 
      prev.includes(productId) ? prev.filter((id) => id !== productId) : [...prev, productId]
    );
  };

  const openEditInventory = (inv) => {
    setEditingInventory(inv);
    setEditInventoryDraft({
      current_stock: String(inv.current_stock ?? ''),
      purchase_price: String(inv.purchase_price ?? ''),
      selling_price: String(inv.selling_price ?? ''),
      reorder_level: String(inv.reorder_level ?? '5'),
    });
    setEditInventoryModal(true);
  };

  const updateInventorySubmit = async (e) => {
    e.preventDefault();
    if (!editingInventory) return;
    try {
      await api(`/inventory/${editingInventory.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          current_stock: Number(editInventoryDraft.current_stock),
          purchase_price: Number(editInventoryDraft.purchase_price),
          selling_price: Number(editInventoryDraft.selling_price),
          reorder_level: Number(editInventoryDraft.reorder_level),
        }),
      });
      setEditInventoryModal(false);
      setEditingInventory(null);
      setToast('Inventory stock updated!');
      refresh();
    } catch (err) { setToast(err.message || 'Failed to update inventory'); }
  };

  const saveNewInventory = async (e) => {
    e.preventDefault();
    try {
      await api('/inventory/', {
        method: 'POST',
        body: JSON.stringify({
          product_id: Number(addStockDraft.product_id),
          current_stock: Number(addStockDraft.current_stock || 0),
          purchase_price: Number(addStockDraft.purchase_price || 0),
          selling_price: Number(addStockDraft.selling_price || 0),
          reorder_level: Number(addStockDraft.reorder_level || 5),
        }),
      });
      setAddStockModal(false);
      setAddStockDraft({ product_id: '', current_stock: '0', purchase_price: '', selling_price: '', reorder_level: '5' });
      setToast('Inventory stock created!');
      refresh();
    } catch (err) { setToast(err.message || 'Failed to create inventory'); }
  };

  const saveProduct = async (e) => {
    e.preventDefault();
    try {
      const prod = await api('/products/', {
        method: 'POST',
        body: JSON.stringify({
          name: productDraft.name,
          brand: productDraft.brand || null,
          variant: productDraft.variant || null,
          category: productDraft.category || null,
          unit: productDraft.unit || 'piece',
        }),
      });

      if (prod?.id && productDraft.purchase_price !== '' && productDraft.selling_price !== '') {
        await api('/inventory/', {
          method: 'POST',
          body: JSON.stringify({
            product_id: prod.id,
            current_stock: Number(productDraft.initial_stock || 0),
            purchase_price: Number(productDraft.purchase_price),
            selling_price: Number(productDraft.selling_price),
            reorder_level: 5,
          }),
        });
      }

      setProductModal(false);
      setProductDraft({ name: '', brand: '', variant: '', category: '', unit: 'piece', purchase_price: '', selling_price: '', initial_stock: '' });
      setToast('Product added successfully!');
      refresh();
    } catch (err) { setToast(err.message); }
  };

  const signInWithGoogle = async () => {
    setAuthError('');
    localStorage.removeItem('stocksaathi_token');
    sessionStorage.setItem(OAUTH_PENDING_KEY, '1');
    try {
      const result = await authClient.signIn.social({ provider: 'google', callbackURL: `${window.location.origin}/` });
      if (result?.error) throw new Error(result.error.message || 'Google sign-in rejected.');
    } catch (e) {
      sessionStorage.removeItem(OAUTH_PENDING_KEY);
      setAuthError(authFailureMessage(e));
    }
  };

  const retryAuthToken = async () => {
    setAuthError(''); setAuthLoading(true);
    try {
      const resolved = await resolveNeonSession();
      if (!resolved.user) throw new Error('Google session expired. Sign in again.');
      if (!resolved.jwt) throw new Error(resolved.tokenError?.message || 'Token endpoint returned no session.');
      localStorage.setItem('stocksaathi_token', resolved.jwt);
      setHasNeonSession(false); setIsAuthenticated(true);
      setCurrentView('dashboard');
      await refresh();
    } catch (e) { setAuthError(authFailureMessage(e)); }
    finally { setAuthLoading(false); }
  };

  const signOut = async () => {
    try { await authClient.signOut(); } catch {}
    localStorage.removeItem('stocksaathi_token');
    setIsAuthenticated(false); setHasNeonSession(false);
    setCurrentView('landing');
    setProfile({ name: '', shop_name: '', shop_category: '', phone: '', shop_address: '' });
  };

  // Nav configuration
  const nav = [
    { label: 'Overview', icon: LayoutDashboard },
    { label: 'Inventory', icon: Boxes },
    { label: 'Products', icon: Package },
    { label: 'Activity', icon: Activity },
    { label: 'Insights', icon: BarChart3 },
    { label: 'Profile', icon: UserRound },
  ];

  // -------------------------------------------------------------------------
  // 100% REAL DERIVED DATA (ZERO FAKE DATA)
  // -------------------------------------------------------------------------
  const realChartData = useMemo(() => {
    const daysMap = {};
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date();
      d.setDate(d.getDate() - i);
      const key = d.toISOString().split('T')[0];
      const label = d.toLocaleDateString('en-IN', { weekday: 'short' });
      daysMap[key] = { label, day: label, sales: 0, purchases: 0 };
    }
    if (activity && activity.length > 0) {
      activity.forEach((item) => {
        const d = item.date ? item.date.split('T')[0] : '';
        if (daysMap[d]) {
          if (item.type === 'sale') daysMap[d].sales += Number(item.amount || 0);
          if (item.type === 'purchase') daysMap[d].purchases += Number(item.amount || 0);
        }
      });
    }
    return Object.values(daysMap);
  }, [activity, days]);

  const hasActivityData = useMemo(() => {
    return realChartData.some((d) => d.sales > 0 || d.purchases > 0);
  }, [realChartData]);

  const total7DaySales = useMemo(() => {
    return (activity || []).filter((i) => i.type === 'sale').reduce((acc, i) => acc + Number(i.amount || 0), 0);
  }, [activity]);

  const total7DayPurchases = useMemo(() => {
    return (activity || []).filter((i) => i.type === 'purchase').reduce((acc, i) => acc + Number(i.amount || 0), 0);
  }, [activity]);

  const topProductsList = useMemo(() => {
    if (topProducts && topProducts.length > 0) {
      return topProducts.map((tp) => ({
        name: tp.product,
        subtitle: `${parseFloat(tp.units_sold || 0)} units sold`,
        units_sold: parseFloat(tp.units_sold || 0),
      }));
    }
    return [];
  }, [topProducts]);

  const stockAlertsList = useMemo(() => {
    return inventory
      .filter((i) => Number(i.current_stock) <= Number(i.reorder_level))
      .map((item) => ({
        name: `${item.product?.name || 'Product'} ${item.product?.variant ? `(${item.product?.variant})` : ''}`,
        urgency: `Only ${item.current_stock} ${item.product?.unit || 'units'} left`,
        category: item.product?.category || 'Grocery',
      }));
  }, [inventory]);

  const pendingTask = useMemo(() => {
    if (tasks && tasks.length > 0) {
      const valid = tasks.find((t) => t.product_name && t.product_name.toLowerCase() !== 'product');
      if (valid) return valid;
    }
    return null;
  }, [tasks]);

  const categoryData = useMemo(() => {
    const m = {};
    inventory.forEach((i) => {
      const c = i.product?.category || 'General';
      m[c] = (m[c] || 0) + Number(i.current_stock || 0) * Number(i.purchase_price || 0);
    });
    return Object.entries(m).map(([name, value]) => ({ name, value }));
  }, [inventory]);

  // Inventory filtering - REAL DATA ONLY
  const filteredInventory = useMemo(() => {
    return inventory.filter((item) => {
      const name = `${item.product?.name || ''} ${item.product?.brand || ''} ${item.product?.variant || ''}`.toLowerCase();
      const matchSearch = name.includes(search.toLowerCase());
      const stock = Number(item.current_stock);
      const reorder = Number(item.reorder_level);
      if (!matchSearch) return false;
      if (filter === 'good') return stock > reorder;
      if (filter === 'low') return stock > 0 && stock <= reorder;
      if (filter === 'out') return stock === 0;
      return true;
    });
  }, [inventory, search, filter]);

  const goodStockCount = useMemo(() => inventory.filter((i) => Number(i.current_stock) > Number(i.reorder_level)).length, [inventory]);
  const lowStockCount = useMemo(() => inventory.filter((i) => Number(i.current_stock) > 0 && Number(i.current_stock) <= Number(i.reorder_level)).length, [inventory]);
  const outStockCount = useMemo(() => inventory.filter((i) => Number(i.current_stock) === 0).length, [inventory]);

  // Products filtering - STRICTLY REAL DATABASE PRODUCTS ONLY
  const catalogueProducts = useMemo(() => {
    return products.filter((p) => {
      const matchSearch = `${p.name} ${p.brand || ''} ${p.variant || ''} ${p.category || ''}`.toLowerCase().includes(search.toLowerCase());
      const matchCat = categoryFilter === 'All' || (p.category || '').toLowerCase() === categoryFilter.toLowerCase();
      return matchSearch && matchCat;
    });
  }, [products, search, categoryFilter]);

  const selectedProductToDeleteObj = useMemo(() => {
    if (!selectedProductIdToDelete) return null;
    return products.find((p) => String(p.id) === String(selectedProductIdToDelete)) || null;
  }, [selectedProductIdToDelete, products]);

  // Filtered Activity Movements
  const filteredMovements = useMemo(() => {
    if (activityFilter === 'all') return movements;
    return movements.filter((m) => m.type === activityFilter);
  }, [movements, activityFilter]);

  if (authLoading) {
    return (
      <div className="auth-loading">
        <KiranaStoreLogo size={42}/>
        <b>StockSaathi</b>
        <span>Loading your workspace…</span>
      </div>
    );
  }

  if (!isAuthenticated && hasNeonSession) {
    return <SessionRecoveryPage error={authError} onRetry={retryAuthToken} onGoogle={signInWithGoogle} />;
  }

  // STANDARD FLOW: Show Landing Page first if visitor hasn't entered dashboard
  if (currentView === 'landing' || !isAuthenticated) {
    return (
      <LandingPage
        onGoogle={signInWithGoogle}
        error={authError}
        toast={toast}
        isAuthenticated={isAuthenticated}
        userName={profile.name}
        onEnterDashboard={() => setCurrentView('dashboard')}
        onSignOut={signOut}
      />
    );
  }

  return (
    <div className="app-shell">
      <main className="main-content">
        {/* Dark Topbar */}
        <header className="topbar">
          <div className="topbar-left">
            <a className="brand" href="#dashboard" onClick={() => setPage('Overview')}>
              <KiranaStoreLogo size={28}/>
              <span>Stock<span>Saathi</span></span>
            </a>
          </div>

          <nav className="top-nav">
            {nav.map(({ label, icon: Icon }) => (
              <button
                key={label}
                type="button"
                className={`top-nav-item ${page === label ? 'active' : ''}`}
                onClick={() => setPage(label)}
              >
                <Icon size={16}/>
                <span>{label}</span>
                {label === 'Inventory' && summary?.low_stock_count > 0 && (
                  <span className="bell-badge" style={{ position: 'static', width: '16px', height: '16px', fontSize: '10px' }}>
                    {summary.low_stock_count}
                  </span>
                )}
              </button>
            ))}
          </nav>

          <div className="topbar-right">
            <button
              type="button"
              className="topbar-icon-btn"
              title="Landing Page"
              onClick={() => setCurrentView('landing')}
              style={{ width: 'auto', padding: '0 12px', borderRadius: '999px', fontSize: '12px', gap: '5px', display: 'flex' }}
            >
              <Store size={15}/> <span>Home</span>
            </button>
            <button type="button" className="topbar-icon-btn refresh-btn" title="Refresh data" aria-label="Refresh" onClick={() => refresh(true)} style={{ color: loading ? '#f97316' : '' }}>
              <RefreshCw size={17} className={loading ? 'spin' : ''} />
            </button>
            <button className="topbar-icon-btn" title="Low stock alerts" aria-label="Notifications" onClick={() => setPage('Inventory')}>
              <Bell size={17}/>
              {summary?.low_stock_count > 0 && <span className="bell-badge">{summary.low_stock_count}</span>}
            </button>
            <div className="shop-pill-btn" onClick={() => setPage('Profile')}>
              <ShopkeeperAvatar size={26}/>
              <span className="shop-pill-name">{profile.shop_name || profile.name || 'My Shop'}</span>
              <ChevronDown size={14}/>
            </div>
          </div>
        </header>

        {toast && <div className="toast">{toast}</div>}
        {error && <div className="error-banner"><CircleHelp size={16}/><span>{error}</span></div>}

        {/* ---------------- OVERVIEW PAGE ---------------- */}
        {page === 'Overview' && (
          <section className="page-view">
            {/* 1. Hero Voice Assistant Banner */}
            <section className="hero-voice-banner">
              {/* Left Column: Real dynamic greeting with actual user name */}
              <div className="hero-greeting-col">
                <div className="hero-shopkeeper-portrait">
                  <ShopkeeperAvatar size={112}/>
                </div>
                <div className="hero-greeting-text">
                  <h1>{getGreeting(profile.name)}</h1>
                  <p>Aapka business StockSaathi ke saath hamesha set hai!</p>
                </div>
              </div>

              {/* Center Column: Glowing Voice Orb OR Inline Chat */}
              <div className="hero-voice-col">
                {assistantMode === 'chat' ? (
                  <div className="kirana-chat-container">
                    <div className="kirana-chat-messages">
                      {chatMessages.map((m) => {
                        const isUser = m.sender === 'user';
                        return (
                          <div key={m.id} className={`kirana-chat-bubble-wrap ${isUser ? 'user' : 'assistant'}`}>
                            <div className={`kirana-chat-bubble ${isUser ? 'user' : 'assistant'}`}>
                              <p>{m.text}</p>
                              {m.tasks && m.tasks.filter((t) => t.product_name && t.product_name.toLowerCase() !== 'product').length > 0 && (
                                <div className="chat-detected-tasks">
                                  {m.tasks.filter((t) => t.product_name && t.product_name.toLowerCase() !== 'product').map((t, idx) => (
                                    <span key={idx} className="chat-task-tag">
                                      🏷️ {t.task?.replace('_', ' ')}: {t.product_name} {t.quantity ? `(${t.quantity} ${t.unit || ''})` : ''}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                            <span className="kirana-chat-time">{m.time}</span>
                          </div>
                        );
                      })}
                      <div ref={chatEndRef}/>
                    </div>

                    <form
                      className="kirana-chat-input-row"
                      onSubmit={(e) => { e.preventDefault(); sendText(); }}
                    >
                      <input
                        type="text"
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder="Type message e.g. '10 milk becha', 'sales batao'..."
                      />
                      <button type="submit" className="btn-chat-send" disabled={!text.trim()}>
                        <Send size={14}/>
                      </button>
                    </form>
                  </div>
                ) : (
                  <>
                    <div className={`voice-orb-wrapper ${listening ? 'is-listening' : ''}`}>
                      <div className="wave-bars left">
                        <span className="bar bar-1"/>
                        <span className="bar bar-2"/>
                        <span className="bar bar-3"/>
                        <span className="bar bar-4"/>
                      </div>
                      <button
                        type="button"
                        className="voice-orb-btn"
                        onClick={listening ? () => stopVoice() : startVoice}
                        aria-label={listening ? 'Stop listening' : 'Start speaking'}
                      >
                        {listening ? <AudioLines size={44}/> : <Mic size={44}/>}
                      </button>
                      <div className="wave-bars right">
                        <span className="bar bar-4"/>
                        <span className="bar bar-3"/>
                        <span className="bar bar-2"/>
                        <span className="bar bar-1"/>
                      </div>
                    </div>

                    <div className="voice-title-box">
                      <h3>Speak to StockSaathi</h3>
                      <span className="voice-subtitle">Boliye, jaise:</span>
                    </div>

                    <div className="voice-prompt-chips">
                      <button type="button" onClick={() => sendText(products[0]?.name ? `${products[0].name} 5 becha` : "10 packet doodh becha")}>
                        “{products[0]?.name ? `${products[0].name} 5 becha` : "10 packet doodh becha"}”
                      </button>
                      <button type="button" onClick={() => sendText("Aaj ki sales batao")}>
                        “Aaj ki sales batao”
                      </button>
                      <button type="button" onClick={() => sendText("Show low stock")}>
                        “Show low stock”
                      </button>
                    </div>
                  </>
                )}

                <div className="voice-subcontrols">
                  <button
                    type="button"
                    className={`mode-pill ${assistantMode === 'voice' ? 'active' : ''}`}
                    onClick={() => setAssistantMode('voice')}
                  >
                    <Mic size={11}/> Voice
                  </button>
                  <button
                    type="button"
                    className={`mode-pill ${assistantMode === 'chat' ? 'active' : ''}`}
                    onClick={() => setAssistantMode('chat')}
                  >
                    <MessageSquare size={11}/> Chat
                  </button>
                  <span className="voice-status-text">{status}</span>
                </div>
              </div>

              {/* Right Column: ONLY show Confirmation Card IF there is an actual task pending */}
              <div className="hero-action-col">
                {liveTranscript ? (
                  <div className="live-utterance-pill">
                    <Mic size={14} className="utterance-mic"/>
                    <span className="utterance-text">“{liveTranscript}”</span>
                    <span className="utterance-time">Listening…</span>
                  </div>
                ) : transcript ? (
                  <div className="live-utterance-pill">
                    <Mic size={14} className="utterance-mic"/>
                    <span className="utterance-text">“{transcript}”</span>
                    <span className="utterance-time">Just now</span>
                  </div>
                ) : null}

                {pendingConfirmation && pendingTask ? (
                  <div className="confirm-action-card">
                    <div className="confirm-card-header">
                      <span className="check-badge"><Check size={14}/></span>
                      <div>
                        <h4>Confirm {pendingTask.task?.replace('_', ' ')}</h4>
                        <span className="confirm-product-name">{pendingTask.product_name}</span>
                      </div>
                    </div>

                    <div className="confirm-card-details">
                      {(pendingTask.quantity ?? pendingTask.actual_count) != null && (
                        <div className="detail-row">
                          <span>Quantity</span>
                          <b>{pendingTask.quantity ?? pendingTask.actual_count} {pendingTask.unit || 'units'}</b>
                        </div>
                      )}
                      {pendingTask.purchase_price && (
                        <div className="detail-row">
                          <span>Price</span>
                          <b>₹{pendingTask.purchase_price}</b>
                        </div>
                      )}
                      {pendingTask.selling_price && (
                        <div className="detail-row">
                          <span>Selling Price</span>
                          <b>₹{pendingTask.selling_price}</b>
                        </div>
                      )}
                    </div>

                    <div className="confirm-card-btns">
                      <button type="button" className="btn-coral-confirm" onClick={() => sendText('haan')}>
                        <Check size={16}/> Haan
                      </button>
                      <button type="button" className="btn-outline-edit" onClick={() => sendText('nahi')}>
                        <X size={15}/> Nahi
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="confirm-action-card" style={{ textAlign: 'center', padding: '20px 14px' }}>
                    <Sparkles size={24} style={{ color: '#ea580c', margin: '0 auto 8px' }}/>
                    <h4 style={{ fontSize: '13px', fontWeight: '800', color: '#111827', margin: '0 0 4px' }}>
                      StockSaathi Voice Assistant
                    </h4>
                    <p style={{ fontSize: '12px', color: '#64748b', margin: 0, lineHeight: '1.4' }}>
                      {reply || 'Mic dabakar boliye ya type karein. Stock updates aur business hisaab turant sync hoga.'}
                    </p>
                    {reply && (
                      <button
                        type="button"
                        className="btn-table-action"
                        style={{ marginTop: '10px', alignSelf: 'center' }}
                        onClick={() => speakAssistant(reply)}
                      >
                        <Volume2 size={13}/> Listen
                      </button>
                    )}
                  </div>
                )}
              </div>
            </section>

            {/* 2. Four Metric Cards - REAL BACKEND DATA ONLY */}
            <div className="overview-metric-grid">
              <div className="overview-metric-card">
                <div className="metric-icon-box orange">
                  <Boxes size={22}/>
                </div>
                <div className="metric-info">
                  <span className="metric-label">Total Stock Value</span>
                  <h3 className="metric-value">{summary ? money(summary.stock_value_at_cost) : '₹0'}</h3>
                  <span className="trend-badge" style={{ color: '#64748b' }}>At purchase cost</span>
                </div>
              </div>

              <div className="overview-metric-card">
                <div className="metric-icon-box teal">
                  <ShoppingCart size={22}/>
                </div>
                <div className="metric-info">
                  <span className="metric-label">Today's Sales</span>
                  <h3 className="metric-value">{summary ? money(summary.today_sales_revenue) : '₹0'}</h3>
                  <span className="trend-badge" style={{ color: '#16a34a' }}>{parseFloat(summary?.today_units_sold || 0)} units sold today</span>
                </div>
              </div>

              <div className="overview-metric-card">
                <div className="metric-icon-box cyan">
                  <Package size={22}/>
                </div>
                <div className="metric-info">
                  <span className="metric-label">Products Tracked</span>
                  <h3 className="metric-value">{summary?.product_count ?? products.length ?? 0}</h3>
                  <span className="trend-badge" style={{ color: '#0284c7' }}>In catalogue</span>
                </div>
              </div>

              <div className="overview-metric-card">
                <div className="metric-icon-box coral">
                  <Activity size={22}/>
                </div>
                <div className="metric-info">
                  <span className="metric-label">Low Stock Alerts</span>
                  <h3 className="metric-value" style={{ color: summary?.low_stock_count > 0 ? '#ef4444' : '#111827' }}>
                    {summary?.low_stock_count ?? 0}
                  </h3>
                  <span className="trend-badge" style={{ color: summary?.out_of_stock_count > 0 ? '#ef4444' : '#64748b' }}>
                    {summary?.out_of_stock_count ?? 0} out of stock
                  </span>
                </div>
              </div>
            </div>

            {/* 3. Three-Column Bottom Grid - STRICTLY REAL DATA */}
            <div className="overview-bottom-grid">
              {/* Col 1: Real Sales & Purchases AreaChart */}
              <section className="overview-col-card chart-card">
                <div className="card-header-row">
                  <div className="card-title-group">
                    <BarChart3 size={18} className="title-icon orange"/>
                    <h3>Sales & Purchases</h3>
                  </div>
                  <div className="chart-legend-dots">
                    <span className="legend-dot"><i className="dot sales"/> Sales</span>
                    <span className="legend-dot"><i className="dot purchases"/> Purchases</span>
                  </div>
                </div>

                <div className="areachart-container">
                  <ResponsiveContainer width="100%" height={220}>
                    <AreaChart data={realChartData}>
                      <defs>
                        <linearGradient id="salesGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#ea580c" stopOpacity={0.3}/>
                          <stop offset="95%" stopColor="#ea580c" stopOpacity={0.0}/>
                        </linearGradient>
                        <linearGradient id="purchasesGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.25}/>
                          <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="#f0ebe3"/>
                      <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#8c827a', fontSize: 11 }}/>
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: '#8c827a', fontSize: 11 }} tickFormatter={(v) => v >= 1000 ? (v % 1000 === 0 ? `₹${v/1000}k` : `₹${(v/1000).toFixed(1)}k`) : `₹${v}`}/>
                      <Tooltip formatter={(v) => money(v)} contentStyle={{ borderRadius: 10, border: '1px solid #ede8e1' }}/>
                      <Area type="monotone" dataKey="sales" name="Sales" stroke="#ea580c" strokeWidth={2.5} fillOpacity={1} fill="url(#salesGrad)" />
                      <Area type="monotone" dataKey="purchases" name="Purchases" stroke="#06b6d4" strokeWidth={2.5} fillOpacity={1} fill="url(#purchasesGrad)" />
                    </AreaChart>
                  </ResponsiveContainer>
                  {!hasActivityData && (
                    <div style={{ textAlign: 'center', padding: '8px 0', fontSize: '11px', color: '#94a3b8' }}>
                      No sales or purchases recorded in the last 7 days.
                    </div>
                  )}
                  <div className="chart-summary-strip" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginTop: '14px', paddingTop: '12px', borderTop: '1px solid #f1ece4' }}>
                    <div style={{ background: '#fff7ed', borderRadius: '10px', padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', color: '#9a3412', fontWeight: 600 }}>7-Day Sales</span>
                      <b style={{ fontSize: '13px', color: '#ea580c' }}>{money(total7DaySales)}</b>
                    </div>
                    <div style={{ background: '#ecfeff', borderRadius: '10px', padding: '8px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', color: '#155e75', fontWeight: 600 }}>7-Day Purchases</span>
                      <b style={{ fontSize: '13px', color: '#0891b2' }}>{money(total7DayPurchases)}</b>
                    </div>
                  </div>
                </div>
              </section>

              {/* Col 2: REAL Top Products */}
              <section className="overview-col-card top-products-card">
                <div className="card-header-row">
                  <div className="card-title-group">
                    <Trophy size={18} className="title-icon gold"/>
                    <h3>Top Products (30 Days)</h3>
                  </div>
                </div>
                
                <div className="top-products-list">
                  {topProductsList.length > 0 ? (
                    topProductsList.map((item, idx) => (
                      <div key={idx} className="top-product-item">
                        <ProductPackThumbnail name={item.name} size={38}/>
                        <div className="top-item-info">
                          <h4 className="top-item-name">{item.name}</h4>
                          <span className="top-item-sub">{item.subtitle}</span>
                        </div>
                        <span className="top-item-price-tag">{item.units_sold} sold</span>
                      </div>
                    ))
                  ) : (
                    <div style={{ textAlign: 'center', padding: '40px 14px', color: '#94a3b8', fontSize: '13px' }}>
                      Sales history will build your top-seller list.
                    </div>
                  )}
                </div>
              </section>

              {/* Col 3: REAL Stock Alerts */}
              <section className="overview-col-card stock-alerts-card">
                <div className="card-header-row">
                  <div className="card-title-group">
                    <Bell size={18} className="title-icon red"/>
                    <h3>Stock Alerts</h3>
                    <span className="badge-count-red">{stockAlertsList.length}</span>
                  </div>
                </div>

                <div className="stock-alerts-list">
                  {stockAlertsList.length > 0 ? (
                    stockAlertsList.map((alert, idx) => (
                      <div key={idx} className="stock-alert-item" onClick={() => setPage('Inventory')}>
                        <ProductPackThumbnail name={alert.name} category={alert.category} size={38}/>
                        <div className="alert-item-info">
                          <h4 className="alert-item-name">{alert.name}</h4>
                          <span className="alert-urgency-text">{alert.urgency}</span>
                        </div>
                        <ChevronRight size={16} className="alert-chevron"/>
                      </div>
                    ))
                  ) : (
                    <div style={{ textAlign: 'center', padding: '40px 14px', color: '#16a34a', fontSize: '13px', fontWeight: '600' }}>
                      ✓ All stock is healthy! No low stock alerts.
                    </div>
                  )}
                </div>
              </section>
            </div>
          </section>
        )}

        {/* ---------------- INVENTORY PAGE ---------------- */}
        {page === 'Inventory' && (
          <section className="page-view">
            <div className="page-header-bar">
              <div>
                <h1>Inventory</h1>
                <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
                  Total {inventory.length} inventory records in your shop.
                </p>
              </div>
              <button type="button" className="primary-button" onClick={() => setAddStockModal(true)}>
                <Plus size={16}/> Add Stock Entry
              </button>
            </div>

            <div className="inventory-filter-bar">
              <div className="search-field-kirana">
                <Search size={16} style={{ color: '#94a3b8' }}/>
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search products by name or brand"
                />
              </div>
              <select className="select-kirana" value={filter} onChange={(e) => setFilter(e.target.value)}>
                <option value="all">All Stock</option>
                <option value="good">Good Stock</option>
                <option value="low">Low Stock</option>
                <option value="out">Out of Stock</option>
              </select>
            </div>

            {/* 4 Status Tabs */}
            <div className="inventory-status-pills-row">
              <button
                type="button"
                className={`status-tab-pill ${filter === 'all' ? 'active' : ''}`}
                onClick={() => setFilter('all')}
              >
                All ({inventory.length})
              </button>
              <button
                type="button"
                className={`status-tab-pill ${filter === 'good' ? 'active' : ''}`}
                onClick={() => setFilter('good')}
              >
                Good Stock ({goodStockCount})
              </button>
              <button
                type="button"
                className={`status-tab-pill ${filter === 'low' ? 'active' : ''}`}
                onClick={() => setFilter('low')}
              >
                Low Stock ({lowStockCount})
              </button>
              <button
                type="button"
                className={`status-tab-pill ${filter === 'out' ? 'active' : ''}`}
                onClick={() => setFilter('out')}
              >
                Out of Stock ({outStockCount})
              </button>
            </div>

            {/* Inventory Table */}
            <div className="kirana-table-container">
              <table className="kirana-table">
                <thead>
                  <tr>
                    <th>PRODUCT</th>
                    <th>STOCK</th>
                    <th>BUY PRICE</th>
                    <th>SELL PRICE</th>
                    <th>REORDER LEVEL</th>
                    <th>STATUS</th>
                    <th style={{ textAlign: 'right' }}>ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInventory.length ? (
                    filteredInventory.map((row) => {
                      const stock = Number(row.current_stock || 0);
                      const low = Number(row.reorder_level || 5);
                      const isGood = stock > low;
                      const isLow = stock > 0 && stock <= low;
                      const isOut = stock === 0;

                      return (
                        <tr key={row.id}>
                          <td>
                            <div className="product-cell">
                              <ProductPackThumbnail name={row.product?.name} category={row.product?.category} size={36}/>
                              <div>
                                <b>{row.product?.name}</b>
                                <small>{[row.product?.brand, row.product?.variant].filter(Boolean).join(' · ')}</small>
                              </div>
                            </div>
                          </td>
                          <td><strong>{stock}</strong> {row.product?.unit || 'units'}</td>
                          <td>{money(row.purchase_price)}</td>
                          <td>{money(row.selling_price)}</td>
                          <td>{row.reorder_level} {row.product?.unit || 'units'}</td>
                          <td>
                            {isGood && <span className="status-tag good">Good</span>}
                            {isLow && <span className="status-tag low">Low</span>}
                            {isOut && <span className="status-tag out">Out</span>}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <button
                              type="button"
                              className="btn-table-action"
                              onClick={() => openEditInventory(row)}
                            >
                              <Pencil size={12}/> Edit / Adjust
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="7" style={{ textAlign: 'center', padding: '36px', color: '#94a3b8' }}>
                        No inventory matching your filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ---------------- PRODUCTS CATALOGUE PAGE ---------------- */}
        {page === 'Products' && (
          <section className="page-view">
            <div className="page-header-bar">
              <div>
                <h1>Products Catalogue</h1>
                <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
                  Total {products.length} products tracked in your shop.
                </p>
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className="secondary-button"
                  style={{ color: '#dc2626', borderColor: '#fca5a5' }}
                  onClick={() => {
                    if (products.length > 0) {
                      setSelectedProductIdToDelete(String(products[0].id));
                      setSelectDeleteModal(true);
                    } else {
                      setToast('No products in catalogue to delete.');
                    }
                  }}
                  title="Select a product from dropdown to delete"
                >
                  <Trash2 size={14}/> Select & Delete Product
                </button>
                <button
                  type="button"
                  className={`secondary-button ${isSelectMode ? 'active' : ''}`}
                  onClick={() => {
                    setIsSelectMode(!isSelectMode);
                    setSelectedProductIds([]);
                  }}
                  title="Select multiple products with checkboxes"
                >
                  <Check size={14}/> {isSelectMode ? 'Done Selecting' : 'Multi-Select'}
                </button>
                <button type="button" className="primary-button" onClick={() => setProductModal(true)}>
                  <Plus size={16}/> Add Product
                </button>
              </div>
            </div>

            <div className="inventory-filter-bar">
              <div className="search-field-kirana" style={{ maxWidth: '420px' }}>
                <Search size={16} style={{ color: '#94a3b8' }}/>
                <input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search product, brand, or category"
                />
              </div>
            </div>

            {/* Category Filter Pills */}
            <div className="category-filter-pills">
              {['All', 'Grocery', 'Snacks', 'Beverages', 'Home Care', 'Personal Care'].map((cat) => (
                <button
                  key={cat}
                  type="button"
                  className={`category-tab-btn ${categoryFilter === cat ? 'active' : ''}`}
                  onClick={() => setCategoryFilter(cat)}
                >
                  {cat}
                </button>
              ))}
            </div>

            {/* Multi-Select Floating / Top Action Banner */}
            {selectedProductIds.length > 0 && (
              <div className="multi-select-action-bar">
                <b>✓ {selectedProductIds.length} product(s) selected</b>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  <button type="button" className="secondary-button" onClick={() => setSelectedProductIds([])}>
                    Clear
                  </button>
                  <button type="button" className="btn-batch-delete" onClick={handleBatchDelete}>
                    <Trash2 size={13}/> Delete Selected ({selectedProductIds.length})
                  </button>
                </div>
              </div>
            )}

            {/* Grid of Product Cards - STRICTLY REAL DATABASE PRODUCTS ONLY */}
            {catalogueProducts.length > 0 ? (
              <div className="products-catalogue-grid">
                {catalogueProducts.map((p) => {
                  const inv = inventory.find((i) => i.product_id === p.id || i.product?.id === p.id);
                  const price = inv?.selling_price || inv?.purchase_price || 0;
                  const isChecked = selectedProductIds.includes(p.id);

                  return (
                    <div key={p.id} className="kirana-product-card" style={isChecked ? { borderColor: '#ea580c', background: '#fffcf9' } : {}}>
                      {isSelectMode && (
                        <div className="card-checkbox-top">
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleSelectProduct(p.id)}
                            aria-label={`Select ${p.name}`}
                          />
                        </div>
                      )}

                      <div className="card-pack-preview">
                        <ProductPackThumbnail name={p.name} category={p.category} size={64}/>
                      </div>
                      <h3 className="card-product-title">{p.name}</h3>
                      <span className="card-product-sub">
                        {[p.brand, p.variant, p.category].filter(Boolean).join(' · ') || 'General'}
                      </span>
                      <span className="card-price-pill">
                        {price > 0 ? `₹${price} / ${p.unit || 'piece'}` : `${p.unit || 'piece'}`}
                      </span>

                      <div className="card-actions-row">
                        <button
                          type="button"
                          className="btn-card-edit"
                          onClick={() => openEditProduct(p)}
                        >
                          <Pencil size={11}/> Edit
                        </button>
                        <button
                          type="button"
                          className="btn-card-delete"
                          onClick={() => confirmDeleteProduct(p)}
                          title="Delete this product"
                        >
                          <Trash2 size={11}/> Delete
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="catalogue-empty-state">
                <Package size={52} style={{ color: '#ea580c', margin: '0 auto 12px' }}/>
                <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '18px', fontWeight: '800', color: '#111827', marginBottom: '6px' }}>
                  Aapke catalogue me koi product nahi hai
                </h3>
                <p style={{ color: 'var(--text-muted)', fontSize: '13px', maxWidth: '440px', margin: '0 auto 20px', lineHeight: '1.5' }}>
                  {search ? 'Search query ko clear karein.' : 'Naya product add karne ke liye niche button dabayein.'}
                </p>
                <button type="button" className="primary-button" onClick={() => setProductModal(true)}>
                  <Plus size={16}/> + Add Product
                </button>
              </div>
            )}
          </section>
        )}

        {/* ---------------- ACTIVITY LEDGER PAGE - 100% REAL MOVEMENTS TABLE ---------------- */}
        {page === 'Activity' && (
          <section className="page-view">
            <div className="page-header-bar">
              <div>
                <h1>Activity Ledger</h1>
                <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
                  A clear record of all real stock movements (sales, purchases, damage, adjustments).
                </p>
              </div>
              <select className="select-kirana" value={days} onChange={(e) => setDays(Number(e.target.value))}>
                <option value={7}>Last 7 Days</option>
                <option value={30}>Last 30 Days</option>
              </select>
            </div>

            <div className="ledger-top-filters">
              <div className="ledger-tab-group">
                <button
                  type="button"
                  className={`ledger-tab-btn ${activityFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setActivityFilter('all')}
                >
                  All ({movements.length})
                </button>
                <button
                  type="button"
                  className={`ledger-tab-btn ${activityFilter === 'sale' ? 'active' : ''}`}
                  onClick={() => setActivityFilter('sale')}
                >
                  Sales
                </button>
                <button
                  type="button"
                  className={`ledger-tab-btn ${activityFilter === 'purchase' ? 'active' : ''}`}
                  onClick={() => setActivityFilter('purchase')}
                >
                  Purchases
                </button>
              </div>
            </div>

            {/* REAL DATABASE STOCK MOVEMENTS TABLE */}
            <div className="kirana-table-container">
              <table className="kirana-table">
                <thead>
                  <tr>
                    <th>DATE</th>
                    <th>PRODUCT</th>
                    <th>ACTIVITY</th>
                    <th>QUANTITY</th>
                    <th style={{ textAlign: 'right' }}>AMOUNT</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredMovements.length ? (
                    filteredMovements.map((row, i) => {
                      const isSale = row.type === 'sale';
                      const isPurchase = row.type === 'purchase';
                      const dateStr = new Date(row.date).toLocaleDateString('en-IN', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      });

                      return (
                        <tr key={row.id || i}>
                          <td>{dateStr}</td>
                          <td>
                            <b>{row.product}</b>
                          </td>
                          <td>
                            <span className={`status-tag ${isSale ? 'good' : isPurchase ? 'out' : 'low'}`}>
                              {row.type?.replace('_', ' ')}
                            </span>
                          </td>
                          <td>
                            <strong>{row.quantity}</strong> {row.unit || 'units'}
                          </td>
                          <td style={{ textAlign: 'right' }}>
                            <strong style={{ color: isSale ? '#15803d' : isPurchase ? '#dc2626' : '#111827' }}>
                              {isSale ? '+' : isPurchase ? '-' : ''}{money(row.amount)}
                            </strong>
                          </td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan="5" style={{ textAlign: 'center', padding: '36px', color: '#94a3b8' }}>
                        No recent stock activity recorded yet.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ---------------- INSIGHTS PAGE - REAL DATA ---------------- */}
        {page === 'Insights' && (
          <section className="page-view">
            <div className="page-header-bar">
              <div>
                <h1>Insights</h1>
                <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-muted)' }}>
                  Simple business signals computed directly from your shop data.
                </p>
              </div>
              <select className="select-kirana" value={days} onChange={(e) => setDays(Number(e.target.value))}>
                <option value={7}>Last 7 Days</option>
                <option value={30}>Last 30 Days</option>
              </select>
            </div>

            {/* 3 Real Metric Cards */}
            <div className="insights-metric-grid">
              <div className="overview-metric-card">
                <div className="metric-icon-box teal">
                  <TrendingUp size={22}/>
                </div>
                <div className="metric-info">
                  <span className="metric-label">Today's Sales Revenue</span>
                  <h3 className="metric-value">{summary ? money(summary.today_sales_revenue) : '₹0'}</h3>
                  <span className="trend-badge" style={{ color: '#16a34a' }}>Recorded today</span>
                </div>
              </div>

              <div className="overview-metric-card">
                <div className="metric-icon-box orange">
                  <Boxes size={22}/>
                </div>
                <div className="metric-info">
                  <span className="metric-label">Inventory Value at Cost</span>
                  <h3 className="metric-value">{summary ? money(summary.stock_value_at_cost) : '₹0'}</h3>
                  <span className="trend-badge" style={{ color: '#64748b' }}>Current stock valuation</span>
                </div>
              </div>

              <div className="overview-metric-card">
                <div className="metric-icon-box coral">
                  <Activity size={22}/>
                </div>
                <div className="metric-info">
                  <span className="metric-label">Low Stock Items</span>
                  <h3 className="metric-value" style={{ color: summary?.low_stock_count > 0 ? '#ef4444' : '#111827' }}>
                    {summary?.low_stock_count ?? 0}
                  </h3>
                  <span className="trend-badge" style={{ color: summary?.out_of_stock_count > 0 ? '#ef4444' : '#64748b' }}>
                    {summary?.out_of_stock_count ?? 0} out of stock
                  </span>
                </div>
              </div>
            </div>

            {/* Dual Charts Grid - REAL DATA */}
            <div className="insights-charts-grid">
              {/* Sales & Purchases Timeline Bar Chart */}
              <div className="overview-col-card">
                <div className="card-header-row">
                  <div className="card-title-group">
                    <BarChart3 size={18} className="title-icon orange"/>
                    <h3>Sales & Purchases Timeline</h3>
                  </div>
                  <div className="chart-legend-dots">
                    <span className="legend-dot"><i className="dot sales"/> Sales</span>
                    <span className="legend-dot"><i className="dot purchases"/> Purchases</span>
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={realChartData}>
                    <CartesianGrid strokeDasharray="3 4" vertical={false} stroke="#f0ebe3"/>
                    <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: '#8c827a', fontSize: 11 }}/>
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#8c827a', fontSize: 11 }} tickFormatter={(v) => v >= 1000 ? (v % 1000 === 0 ? `₹${v/1000}k` : `₹${(v/1000).toFixed(1)}k`) : `₹${v}`}/>
                    <Tooltip formatter={(v) => money(v)} contentStyle={{ borderRadius: 10, border: '1px solid #ede8e1' }}/>
                    <Bar dataKey="sales" name="Sales" fill="#ea580c" radius={[6, 6, 0, 0]} maxBarSize={28}/>
                    <Bar dataKey="purchases" name="Purchases" fill="#06b6d4" radius={[6, 6, 0, 0]} maxBarSize={28}/>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Real Top Categories Donut Chart */}
              <div className="overview-col-card">
                <div className="card-header-row">
                  <div className="card-title-group">
                    <Boxes size={18} className="title-icon gold"/>
                    <h3>Stock by Category</h3>
                  </div>
                </div>

                {categoryData.length > 0 ? (
                  <div className="donut-legend-wrap">
                    <div className="donut-chart-box">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={categoryData}
                            dataKey="value"
                            nameKey="name"
                            cx="50%"
                            cy="50%"
                            innerRadius={36}
                            outerRadius={56}
                            paddingAngle={3}
                          >
                            {categoryData.map((_, i) => (
                              <Cell key={i} fill={CATEGORY_COLORS[i % CATEGORY_COLORS.length]} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(v) => money(v)} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>

                    <div className="donut-legend-list">
                      {categoryData.slice(0, 5).map((item, idx) => (
                        <div key={idx} className="donut-legend-row">
                          <div className="donut-legend-left">
                            <span className="donut-color-dot" style={{ background: CATEGORY_COLORS[idx % CATEGORY_COLORS.length] }}/>
                            <span>{item.name}</span>
                          </div>
                          <span className="donut-pct">{money(item.value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div style={{ textAlign: 'center', padding: '40px 14px', color: '#94a3b8', fontSize: '13px' }}>
                    Add inventory entries to view category stock distribution.
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {/* ---------------- SHOP PROFILE PAGE ---------------- */}
        {page === 'Profile' && (
          <section className="page-view">
            <div className="profile-card-kirana">
              <div className="profile-hero-header">
                <div className="profile-avatar-camera-wrap">
                  <ShopkeeperAvatar size={76}/>
                </div>
                <div className="profile-title-group">
                  <h2>{profile.shop_name || profile.name || 'My Shop'}</h2>
                  <p><MapPin size={14}/> {profile.shop_address || 'Shop address not set'}</p>
                </div>
              </div>

              <form
                className="kirana-form-grid"
                onSubmit={async (e) => {
                  e.preventDefault();
                  try {
                    const payload = {
                      name: profile.name,
                      shop_name: profile.shop_name,
                      shop_category: profile.shop_category || null,
                    };
                    const saved = await api('/users/me', { method: 'PATCH', body: JSON.stringify(payload) });
                    setProfile((prev) => ({ ...prev, ...saved }));
                    setToast('Shop profile updated successfully!');
                  } catch (err) { setToast(err.message); }
                }}
              >
                <div className="form-field-group">
                  <label>Shop Name</label>
                  <input
                    required
                    value={profile.shop_name}
                    onChange={(e) => setProfile({ ...profile, shop_name: e.target.value })}
                    placeholder="e.g. Bushra Kirana Store"
                  />
                </div>

                <div className="form-field-group">
                  <label>Owner Name</label>
                  <input
                    required
                    value={profile.name}
                    onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                    placeholder="Your Name"
                  />
                </div>

                <div className="form-field-group">
                  <label>Shop Type / Category</label>
                  <input
                    value={profile.shop_category || ''}
                    onChange={(e) => setProfile({ ...profile, shop_category: e.target.value })}
                    placeholder="Kirana, General Store, Pharmacy..."
                  />
                </div>

                <div className="dialog-actions" style={{ justifyContent: 'space-between', marginTop: '14px' }}>
                  <button type="button" className="secondary-button" onClick={signOut}>
                    Sign Out
                  </button>
                  <button type="submit" className="primary-button">
                    <Check size={16}/> Save Changes
                  </button>
                </div>
              </form>
            </div>
          </section>
        )}
      </main>

      {/* Select Product To Delete Modal */}
      <dialog open={selectDeleteModal} className="app-dialog" onClick={(e) => e.target === e.currentTarget && setSelectDeleteModal(false)}>
        <div className="dialog-card">
          <button type="button" className="close-button" onClick={() => setSelectDeleteModal(false)}><X size={18}/></button>
          <p className="eyebrow" style={{ color: '#dc2626' }}>SELECT OPTION TO DELETE</p>
          <h2>Delete Product by Selection</h2>
          <p className="subheading">Choose any product from your catalogue dropdown to permanently remove it.</p>

          <label>
            Select Product to Delete
            <select
              value={selectedProductIdToDelete}
              onChange={(e) => setSelectedProductIdToDelete(e.target.value)}
              style={{ height: '44px', fontSize: '13px', fontWeight: '600' }}
            >
              <option value="">-- Choose a product to delete --</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} {p.brand ? `(${p.brand})` : ''} - {p.category || 'General'} [{p.unit || 'piece'}]
                </option>
              ))}
            </select>
          </label>

          {selectedProductToDeleteObj && (
            <div className="select-delete-card-preview">
              <ProductPackThumbnail name={selectedProductToDeleteObj.name} category={selectedProductToDeleteObj.category} size={48}/>
              <div>
                <h4 style={{ margin: '0 0 2px', fontSize: '14px', fontWeight: '800', color: '#111827' }}>{selectedProductToDeleteObj.name}</h4>
                <span style={{ fontSize: '12px', color: '#64748b' }}>
                  {[selectedProductToDeleteObj.brand, selectedProductToDeleteObj.variant, selectedProductToDeleteObj.category].filter(Boolean).join(' · ')}
                </span>
                <div style={{ fontSize: '11px', color: '#dc2626', marginTop: '6px', fontWeight: '700' }}>
                  ⚠️ Permanently deletes product and all associated stock records.
                </div>
              </div>
            </div>
          )}

          <div className="dialog-actions">
            <button className="secondary-button" type="button" onClick={() => setSelectDeleteModal(false)}>Cancel</button>
            <button
              className="danger-button"
              type="button"
              disabled={!selectedProductIdToDelete}
              onClick={async () => {
                if (!selectedProductIdToDelete) return;
                const p = products.find((x) => String(x.id) === String(selectedProductIdToDelete));
                await deleteProductById(selectedProductIdToDelete, p?.name);
                setSelectDeleteModal(false);
                setSelectedProductIdToDelete('');
              }}
            >
              <Trash2 size={15}/> Yes, Delete Selected Product
            </button>
          </div>
        </div>
      </dialog>

      {/* Delete Product Confirmation Modal */}
      <dialog open={deleteConfirmModal} className="app-dialog" onClick={(e) => e.target === e.currentTarget && setDeleteConfirmModal(false)}>
        <div className="dialog-card">
          <button type="button" className="close-button" onClick={() => setDeleteConfirmModal(false)}><X size={18}/></button>
          <p className="eyebrow" style={{ color: '#dc2626' }}>CONFIRM DELETION</p>
          <h2>Delete Product?</h2>
          <p className="subheading">
            Are you sure you want to delete <strong>{productToDelete?.name}</strong>? This will permanently remove its stock.
          </p>
          <div className="dialog-actions">
            <button className="secondary-button" type="button" onClick={() => setDeleteConfirmModal(false)}>Cancel</button>
            <button className="danger-button" type="button" onClick={executeDeleteProduct}><Trash2 size={14}/> Yes, Delete</button>
          </div>
        </div>
      </dialog>

      {/* Add Product Modal */}
      <dialog open={productModal} className="app-dialog" onClick={(e) => e.target === e.currentTarget && setProductModal(false)}>
        <form className="dialog-card" onSubmit={saveProduct}>
          <button type="button" className="close-button" onClick={() => setProductModal(false)}><X size={18}/></button>
          <p className="eyebrow">PRODUCT CATALOGUE</p>
          <h2>Add a Product</h2>
          <p className="subheading">Enter product details for your shop catalogue.</p>
          <label>Product Name<input required minLength="2" value={productDraft.name} onChange={(e) => setProductDraft({ ...productDraft, name: e.target.value })} placeholder="e.g. Amul Milk"/></label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <label>Brand<input value={productDraft.brand} onChange={(e) => setProductDraft({ ...productDraft, brand: e.target.value })} placeholder="Amul"/></label>
            <label>Variant / Size<input value={productDraft.variant} onChange={(e) => setProductDraft({ ...productDraft, variant: e.target.value })} placeholder="500 ml"/></label>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <label>Category<input value={productDraft.category} onChange={(e) => setProductDraft({ ...productDraft, category: e.target.value })} placeholder="Dairy"/></label>
            <label>Unit<input required value={productDraft.unit} onChange={(e) => setProductDraft({ ...productDraft, unit: e.target.value })} placeholder="packet"/></label>
          </div>
          <div className="dialog-actions">
            <button className="secondary-button" type="button" onClick={() => setProductModal(false)}>Cancel</button>
            <button className="primary-button" type="submit"><Check size={16}/> Save Product</button>
          </div>
        </form>
      </dialog>

      {/* Edit Product Modal */}
      <dialog open={editProductModal} className="app-dialog" onClick={(e) => e.target === e.currentTarget && setEditProductModal(false)}>
        <form className="dialog-card" onSubmit={updateProductSubmit}>
          <button type="button" className="close-button" onClick={() => setEditProductModal(false)}><X size={18}/></button>
          <p className="eyebrow">EDIT PRODUCT</p>
          <h2>Update Product</h2>
          <label>Product Name<input required minLength="2" value={editDraft.name} onChange={(e) => setEditDraft({ ...editDraft, name: e.target.value })}/></label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <label>Brand<input value={editDraft.brand} onChange={(e) => setEditDraft({ ...editDraft, brand: e.target.value })}/></label>
            <label>Variant<input value={editDraft.variant} onChange={(e) => setEditDraft({ ...editDraft, variant: e.target.value })}/></label>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <label>Category<input value={editDraft.category} onChange={(e) => setEditDraft({ ...editDraft, category: e.target.value })}/></label>
            <label>Unit<input required value={editDraft.unit} onChange={(e) => setEditDraft({ ...editDraft, unit: e.target.value })}/></label>
          </div>
          <div className="dialog-actions" style={{ justifyContent: 'space-between' }}>
            <button className="danger-button" type="button" onClick={() => confirmDeleteProduct(editingProduct)}><Trash2 size={14}/> Delete</button>
            <div style={{ display: 'flex', gap: '8px' }}>
              <button className="secondary-button" type="button" onClick={() => setEditProductModal(false)}>Cancel</button>
              <button className="primary-button" type="submit"><Check size={16}/> Update</button>
            </div>
          </div>
        </form>
      </dialog>

      {/* Add Stock Modal */}
      <dialog open={addStockModal} className="app-dialog" onClick={(e) => e.target === e.currentTarget && setAddStockModal(false)}>
        <form className="dialog-card" onSubmit={saveNewInventory}>
          <button type="button" className="close-button" onClick={() => setAddStockModal(false)}><X size={18}/></button>
          <p className="eyebrow">INVENTORY SETUP</p>
          <h2>Add Stock Entry</h2>
          <label>Select Product
            <select required value={addStockDraft.product_id} onChange={(e) => setAddStockDraft({ ...addStockDraft, product_id: e.target.value })}>
              <option value="">-- Choose a product --</option>
              {products.map((p) => <option key={p.id} value={p.id}>{p.name} ({p.unit})</option>)}
            </select>
          </label>
          <label>Initial Stock Quantity<input required type="number" step="0.01" min="0" value={addStockDraft.current_stock} onChange={(e) => setAddStockDraft({ ...addStockDraft, current_stock: e.target.value })}/></label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <label>Purchase Price (₹)<input required type="number" step="0.01" min="0" value={addStockDraft.purchase_price} onChange={(e) => setAddStockDraft({ ...addStockDraft, purchase_price: e.target.value })}/></label>
            <label>Selling Price (₹)<input required type="number" step="0.01" min="0" value={addStockDraft.selling_price} onChange={(e) => setAddStockDraft({ ...addStockDraft, selling_price: e.target.value })}/></label>
          </div>
          <div className="dialog-actions">
            <button className="secondary-button" type="button" onClick={() => setAddStockModal(false)}>Cancel</button>
            <button className="primary-button" type="submit"><Check size={16}/> Create Stock</button>
          </div>
        </form>
      </dialog>

      {/* Edit Inventory Modal */}
      <dialog open={editInventoryModal} className="app-dialog" onClick={(e) => e.target === e.currentTarget && setEditInventoryModal(false)}>
        <form className="dialog-card" onSubmit={updateInventorySubmit}>
          <button type="button" className="close-button" onClick={() => setEditInventoryModal(false)}><X size={18}/></button>
          <p className="eyebrow">MANUAL ADJUSTMENT</p>
          <h2>Edit Stock & Inventory</h2>
          <label>Current Stock Count<input required type="number" step="0.01" min="0" value={editInventoryDraft.current_stock} onChange={(e) => setEditInventoryDraft({ ...editInventoryDraft, current_stock: e.target.value })}/></label>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <label>Purchase Price (₹)<input required type="number" step="0.01" min="0" value={editInventoryDraft.purchase_price} onChange={(e) => setEditInventoryDraft({ ...editInventoryDraft, purchase_price: e.target.value })}/></label>
            <label>Selling Price (₹)<input required type="number" step="0.01" min="0" value={editInventoryDraft.selling_price} onChange={(e) => setEditInventoryDraft({ ...editInventoryDraft, selling_price: e.target.value })}/></label>
          </div>
          <label>Reorder Alert Level<input required type="number" step="0.01" min="0" value={editInventoryDraft.reorder_level} onChange={(e) => setEditInventoryDraft({ ...editInventoryDraft, reorder_level: e.target.value })}/></label>
          <div className="dialog-actions">
            <button className="secondary-button" type="button" onClick={() => setEditInventoryModal(false)}>Cancel</button>
            <button className="primary-button" type="submit"><Check size={16}/> Save Changes</button>
          </div>
        </form>
      </dialog>
    </div>
  );
}

// -------------------------------------------------------------
// Landing Page (Standard Entrypoint)
// -------------------------------------------------------------
function LandingPage({ onGoogle, error, toast, isAuthenticated, userName, onEnterDashboard, onSignOut }) {
  const [busy, setBusy] = useState(false);
  const start = async () => { setBusy(true); await onGoogle(); setBusy(false); };

  return (
    <div className="landing-page" id="home">
      <div className="landing-nav-wrapper">
        <header className="landing-nav">
          <a className="brand" href="#home">
            <KiranaStoreLogo size={26}/>
            <span>Stock<span>Saathi</span></span>
          </a>

          <nav className="landing-nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How It Works</a>
            <a href="#about">About</a>
          </nav>

          <div className="landing-nav-actions">
            {isAuthenticated ? (
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <button className="landing-google-btn" style={{ height: '40px', padding: '0 18px', fontSize: '13px' }} onClick={onEnterDashboard}>
                  Go to Dashboard →
                </button>
                <button className="secondary-button" style={{ height: '40px' }} onClick={onSignOut}>
                  Sign Out
                </button>
              </div>
            ) : (
              <button className="landing-signin-btn" onClick={start} disabled={busy}>
                Sign in
              </button>
            )}
          </div>
        </header>
      </div>

      {/* Hero Section */}
      <section className="landing-hero-kirana">
        <div className="hero-kirana-copy">
          <h1>
            Aapke dukaan ka<br/>
            <span className="brush-highlight">Voice First</span><br/>
            Business Saathi
          </h1>
          <p className="hero-lead">
            Inventory, sales, purchases, reports — sab kuch bolkar manage karo.
          </p>

          {isAuthenticated ? (
            <button className="landing-google-btn" onClick={onEnterDashboard}>
              Open Dashboard ({userName || 'My Shop'}) →
            </button>
          ) : (
            <button className="landing-google-btn" onClick={start} disabled={busy}>
              <GoogleMark/>
              {busy ? 'Connecting…' : 'Continue with Google'}
            </button>
          )}
          <span className="hero-subcaption">Free setup · No credit card · Made for Indian shops</span>

          {(error || toast) && (
            <div className="error-banner" style={{ marginTop: '20px' }}>
              <CircleHelp size={16}/>
              <span>{error || toast}</span>
            </div>
          )}
        </div>

        <div className="hero-kirana-visual">
          <KiranaStorefrontIllustration/>
        </div>
      </section>

      {/* 3 Feature Pills */}
      <section className="hero-feature-pills">
        <div className="feature-pill-card">
          <span className="feature-pill-icon voice">🎙️</span>
          <div className="feature-pill-text">
            <h3>Bolkar Stock Manage Karo</h3>
            <p>Boliye "10 packet doodh becha" aur hisaab turant sync.</p>
          </div>
        </div>

        <div className="feature-pill-card">
          <span className="feature-pill-icon chart">📊</span>
          <div className="feature-pill-text">
            <h3>Sales & Profit Samjho</h3>
            <p>Har din ka accurate munafa aur sales report dekhein.</p>
          </div>
        </div>

        <div className="feature-pill-card">
          <span className="feature-pill-icon box">📦</span>
          <div className="feature-pill-text">
            <h3>Hamesha Sahi Stock Rakho</h3>
            <p>Low stock aur reorder alert se bikri kabhi na ruke.</p>
          </div>
        </div>
      </section>

      {/* Features Overview */}
      <section className="landing-features-section" id="features">
        <div className="section-head-kirana">
          <span className="section-eyebrow-kirana">BUILT FOR BHARAT</span>
          <h2>Dukaan chalana ab hua bilkul aasan</h2>
          <p>Local languages, Indian FMCG brands aur fast-paced counter rush ke liye specially design kiya gaya hai.</p>
        </div>

        <div className="features-grid-kirana">
          <div className="feature-card-kirana">
            <Mic size={24} style={{ color: '#ea580c' }}/>
            <h3>100% Voice First</h3>
            <p>Hindi, English ya Hinglish me boliye. Barcode scanner ya type karne ki koi jaroorat nahi.</p>
          </div>
          <div className="feature-card-kirana">
            <Boxes size={24} style={{ color: '#16a34a' }}/>
            <h3>Smart Low Stock Radar</h3>
            <p>Distributor aane se pehle pata chalega kaunsa item khatam hone wala hai.</p>
          </div>
          <div className="feature-card-kirana">
            <BarChart3 size={24} style={{ color: '#06b6d4' }}/>
            <h3>Daily Hisaab-Kitab</h3>
            <p>Khaata register band karo. Aaj ki sales, khareed aur profit ek click me samjho.</p>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <span>© 2026 StockSaathi. Voice-first business hub for Bharat.</span>
        <span>Made with ❤️ for Indian Retailers</span>
      </footer>
    </div>
  );
}

function SessionRecoveryPage({ error, onRetry, onGoogle }) {
  return (
    <div className="landing-page">
      <div style={{ maxWidth: '440px', margin: '100px auto', padding: '0 20px', textAlign: 'center' }}>
        <div style={{ background: '#ffffff', borderRadius: '20px', padding: '36px', border: '1px solid #ede8e1' }}>
          <KiranaStoreLogo size={36}/>
          <h2 style={{ fontFamily: 'var(--font-display)', margin: '18px 0 8px', fontSize: '20px' }}>Reconnecting Session</h2>
          <p style={{ fontSize: '13px', color: '#64748b', marginBottom: '20px' }}>Signing you into your secure shop dashboard.</p>
          {error && <div className="error-banner" style={{ textAlign: 'left' }}><CircleHelp size={16}/><span>{error}</span></div>}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <button className="primary-button" onClick={onRetry}><RefreshCw size={14}/> Retry Connection</button>
            <button className="secondary-button" onClick={onGoogle}>Sign in with Google</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function GoogleMark() {
  return (
    <svg viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11a9.5 9.5 0 0 1-4.1 6.2v5.1h6.6c3.9-3.6 6.1-8.8 6.1-15z"/>
      <path fill="#34A853" d="M24 44c5.5 0 10.1-1.8 13.5-4.9l-6.6-5.1c-1.8 1.2-4.1 2-6.9 2-5.3 0-9.8-3.6-11.4-8.5H5.8v5.3A20 20 0 0 0 24 44z"/>
      <path fill="#4285F4" d="M12.6 27.5a12 12 0 0 1 0-7v-5.3H5.8a20 20 0 0 0 0 17.6z"/>
      <path fill="#EA4335" d="M24 12c3 0 5.7 1 7.8 3.1l5.8-5.8A19.4 19.4 0 0 0 24 4 20 20 0 0 0 5.8 15.2l6.8 5.3C14.2 15.6 18.7 12 24 12z"/>
    </svg>
  );
}

createRoot(document.getElementById('root')).render(<React.StrictMode><App/></React.StrictMode>);
