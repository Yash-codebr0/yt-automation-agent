import React, { useState, useEffect, useRef, useCallback } from 'react';
import { 
  LayoutDashboard, 
  Flame, 
  FileVideo, 
  BarChart3, 
  LogOut, 
  Cpu, 
  Play, 
  CheckCircle, 
  AlertTriangle, 
  RefreshCw, 
  UploadCloud, 
  FileText,
  TrendingUp,
  Activity,
  Award,
  ThumbsUp,
  ThumbsDown,
  DollarSign,
  Eye,
  Zap,
  Brain,
  Search,
  Users,
  ShieldCheck,
  Star,
  Globe,
  Calendar,
  BarChart2,
  Wifi,
  WifiOff,
  Youtube
} from 'lucide-react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  BarChart, 
  Bar, 
  LineChart, 
  Line 
} from 'recharts';

const API_BASE = "http://localhost:8000/api/v1";

class ErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { hasError: false, error: null }; }
  static getDerivedStateFromError(error) { return { hasError: true, error }; }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', minHeight:'100vh', gap:'20px', padding:'40px', textAlign:'center' }}>
          <span style={{ fontSize:'64px' }}>⚠️</span>
          <h2 style={{ color:'#f87171', fontFamily:'var(--font-heading)' }}>Render Error</h2>
          <p style={{ color:'var(--text-secondary)', maxWidth:'500px' }}>{this.state.error?.message}</p>
          <button className="btn btn-primary" style={{ width:'auto' }} onClick={() => { this.setState({ hasError: false }); window.location.reload(); }}>Reload App</button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  const initialToken = localStorage.getItem('token') || '';
  const [token, setToken] = useState(initialToken);
  const [user, setUser] = useState(null);
  const [isLoadingUser, setIsLoadingUser] = useState(Boolean(initialToken));
  const [activeTab, setActiveTab] = useState('dashboard');
  
  // Auth Form State
  const [isRegister, setIsRegister] = useState(false);
  const [authEmail, setAuthEmail] = useState('');
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [profileError, setProfileError] = useState('');

  // Dashboard Data State
  const [stats, setStats] = useState({
    total_views: 0,
    total_watch_time: 0,
    avg_ctr: 0,
    total_subscribers: 0,
    total_projects: 0,
    total_revenue: 0
  });

  // WebSocket ref for real-time log streaming
  const wsRef = useRef(null);

  // Health status for sidebar widget
  const [healthStatus, setHealthStatus] = useState({ db: null, redis: null, openai: null, elevenlabs: null, youtube: null });
  const [youtubeStatus, setYoutubeStatus] = useState({ configured: false, connected: false, active_account: null });
  const [ytAccounts, setYtAccounts] = useState([]);
  const [showAccountsModal, setShowAccountsModal] = useState(false);
  const [newChannelNickname, setNewChannelNickname] = useState('');
  const [showNicknamePrompt, setShowNicknamePrompt] = useState(false);
  const [chartData, setChartData] = useState([]);

  // Trends State
  const [trends, setTrends] = useState([]);
  const [isHunting, setIsHunting] = useState(false);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [selectedTrend, setSelectedTrend] = useState(null);
  const [newProjectNiche, setNewProjectNiche] = useState('');
  const [newProjectTitle, setNewProjectTitle] = useState('');
  const [nicheFilter, setNicheFilter] = useState('');
  const [selectedChannelId, setSelectedChannelId] = useState('');

  // Projects State
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState(null);
  const [projectLogs, setProjectLogs] = useState([]);
  const [activeProjectTab, setActiveProjectTab] = useState('script');
  const [isRunningWorkflow, setIsRunningWorkflow] = useState(false);

  const openProjectModal = (trend = null, defaultNiche = '') => {
    setSelectedTrend(trend);
    setNewProjectTitle(trend ? `Campaign: ${trend.title}` : (defaultNiche && defaultNiche !== 'AI' ? `${defaultNiche} Video` : ''));
    setNewProjectNiche(defaultNiche || trend?.category || nicheFilter || 'AI');
    const activeAcc = ytAccounts.find(a => a.is_active) || (ytAccounts.length > 0 ? ytAccounts[0] : null);
    setSelectedChannelId(activeAcc ? activeAcc.id : '');
    setShowProjectModal(true);
  };

  // Edit script state
  const [editedTitle, setEditedTitle] = useState('');
  const [editedHook, setEditedHook] = useState('');
  const [editedBody, setEditedBody] = useState('');
  const [editedCta, setEditedCta] = useState('');
  const [videoFormat, setVideoFormat] = useState('landscape'); // 'landscape' | 'shorts'

  // Full agent status board (including Custom Input)
  const [agentStatus, setAgentStatus] = useState({
    "Trend Hunter": "idle",
    "Custom Input": "idle",
    "Competitor Research": "idle",
    "Keyword Research": "idle",
    "Audience Research": "idle",
    "Analytics Feedback": "idle",
    "Memory Agent": "idle",
    "Idea Generator": "idle",
    "Script Writer": "idle",
    "Fact Checker": "idle",
    "Script Reviewer": "idle",
    "Brand Consistency": "idle",
    "Retention Optimizer": "idle",
    "Shorts Generator": "idle",
    "SEO Agent": "idle",
    "Translation Agent": "idle",
    "Content Calendar": "idle",
    "Thumbnail Agent": "idle",
    "Thumbnail Scorer": "idle",
    "Voice Agent": "idle",
    "Video Generator": "idle",
    "Publishing Agent": "idle",
    "Analytics Agent": "idle",
    "Memory Update": "idle",
  });

  const terminalEndRef = useRef(null);

  // Fetch current profile on token load
  useEffect(() => {
    if (token) {
      localStorage.setItem('token', token);
      setIsLoadingUser(true);
      fetchProfile().finally(() => setIsLoadingUser(false));
    } else {
      localStorage.removeItem('token');
      setUser(null);
      setIsLoadingUser(false);
    }
  }, [token]);

  // Handle periodic refreshing of data based on current tab
  useEffect(() => {
    if (!token) return;
    
    if (activeTab === 'dashboard') {
      fetchStats();
      fetchCharts();
      fetchProjects();
      fetchYoutubeStatus();
      fetchAccounts();
    } else if (activeTab === 'trends') {
      fetchTrends(nicheFilter || undefined);
    } else if (activeTab === 'projects') {
      fetchProjects();
    } else if (activeTab === 'analytics') {
      fetchCharts();
      fetchStats();
    }
  }, [token, activeTab]);

  useEffect(() => {
    if (!token) return;
    fetchYoutubeStatus();
  }, [token]);

  // Log auto-scroll
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [projectLogs]);

  // Poll project status every 5s as fallback; WebSocket handles live logs
  useEffect(() => {
    if (!token || !selectedProject) return;
    const interval = setInterval(() => {
      fetchProjectDetail(selectedProject.id);
    }, 5000);
    return () => clearInterval(interval);
  }, [token, selectedProject]);

  // WebSocket connection for real-time log streaming
  useEffect(() => {
    if (!token || !selectedProject) {
      if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
      return;
    }
    // Close any previous connection
    if (wsRef.current) wsRef.current.close();

    const ws = new WebSocket(`ws://localhost:8000/api/v1/projects/${selectedProject.id}/stream?token=${token}`);
    wsRef.current = ws;

    ws.onopen = () => console.log('WS connected for project', selectedProject.id);
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === 'log') {
          setProjectLogs(prev => [...prev, {
            agent_name: msg.agent,
            status: msg.status,
            log_message: msg.message,
            created_at: msg.timestamp
          }]);
          // Update agent board live
          if (msg.agent && msg.agent !== 'System') {
            setAgentStatus(prev => ({
              ...prev,
              [msg.agent]: msg.status === 'success' ? 'success' : msg.status === 'error' ? 'error' : 'running'
            }));
          }
        } else if (msg.type === 'connected') {
          console.log('WS live for project', msg.projectId);
        }
      } catch {}
    };
    ws.onerror = () => {
      // Fallback to polling if WebSocket fails
      const fallback = setInterval(() => fetchProjectLogs(selectedProject.id), 3000);
      ws.onclose = () => clearInterval(fallback);
    };
    ws.onclose = () => { wsRef.current = null; };

    return () => { ws.close(); wsRef.current = null; };
  }, [token, selectedProject?.id]);

  // Fetch health status every 30s
  useEffect(() => {
    if (!token) return;
    const fetchHealth = async () => {
      try {
        const res = await fetch(`${API_BASE}/health/`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (res.ok) {
          const data = await res.json();
          setHealthStatus(data.services || {});
        }
      } catch {}
    };
    fetchHealth();
    const hi = setInterval(fetchHealth, 30000);
    return () => clearInterval(hi);
  }, [token]);

  const fetchProfile = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/me`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
        setProfileError('');
      } else {
        if ([401, 403, 404].includes(res.status)) {
          setToken('');
          setAuthError('Session expired. Please log in again.');
          return;
        }
        setProfileError('Could not load your profile. Please check that the backend is running.');
      }
    } catch (e) {
      console.warn('fetchProfile failed (backend may be starting):', e.message);
      setProfileError('Could not connect to the backend. Please make sure it is running on port 8000.');
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    setAuthError('');
    const endpoint = isRegister ? '/auth/register' : '/auth/login';
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: authEmail, password: authPassword })
      });
      const data = await res.json();
      if (res.ok) {
        if (isRegister) {
          setIsRegister(false);
          setAuthError('Registration successful! Please log in.');
        } else {
          setUser(null);
          setProfileError('');
          setIsLoadingUser(true);
          setToken(data.access_token);
        }
      } else {
        setAuthError(data.detail || 'Authentication failed');
      }
    } catch {
      setAuthError('Connection error. Is backend running?');
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/analytics/stats`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchCharts = async () => {
    try {
      const res = await fetch(`${API_BASE}/analytics/charts`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setChartData(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchYoutubeStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/youtube/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setYoutubeStatus(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAccounts = async () => {
    try {
      const res = await fetch(`${API_BASE}/youtube/accounts`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) setYtAccounts(await res.json());
    } catch (e) { console.error(e); }
  };

  const connectYoutube = () => {
    // Show nickname prompt before starting OAuth
    setNewChannelNickname('');
    setShowNicknamePrompt(true);
  };

  const connectNewChannel = async () => {
    setShowNicknamePrompt(false);
    const nickname = newChannelNickname.trim() || 'My Channel';
    try {
      const res = await fetch(
        `${API_BASE}/youtube/oauth/start?nickname=${encodeURIComponent(nickname)}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      const data = await res.json();
      if (res.ok && data.authorization_url) {
        window.location.href = data.authorization_url;
      } else {
        alert(data.detail || 'YouTube OAuth is not configured. Add client credentials in .env first.');
      }
    } catch (e) {
      console.error(e);
      alert('Could not start YouTube connection. Is the backend running?');
    }
  };

  const activateAccount = async (accountId) => {
    try {
      const res = await fetch(`${API_BASE}/youtube/accounts/${accountId}/activate`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        await fetchAccounts();
        await fetchYoutubeStatus();
      }
    } catch (e) { console.error(e); }
  };

  const deleteAccount = async (accountId) => {
    if (!confirm('Disconnect this YouTube account?')) return;
    try {
      const res = await fetch(`${API_BASE}/youtube/accounts/${accountId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        await fetchAccounts();
        await fetchYoutubeStatus();
      }
    } catch (e) { console.error(e); }
  };

  const renameAccount = async (accountId, currentNickname) => {
    const name = prompt('New nickname for this channel:', currentNickname);
    if (!name || name === currentNickname) return;
    try {
      await fetch(`${API_BASE}/youtube/accounts/${accountId}?nickname=${encodeURIComponent(name)}`, {
        method: 'PATCH',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchAccounts();
    } catch (e) { console.error(e); }
  };


  const fetchTrends = async (niche) => {
    try {
      const params = niche ? `?niche=${encodeURIComponent(niche)}` : '';
      const res = await fetch(`${API_BASE}/trends/${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setTrends(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const triggerTrendHunt = async () => {
    setIsHunting(true);
    try {
      const params = nicheFilter ? `?niche=${encodeURIComponent(nicheFilter)}` : '';
      const res = await fetch(`${API_BASE}/trends/hunt${params}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setTimeout(() => {
          fetchTrends(nicheFilter || undefined);
          setIsHunting(false);
        }, 3000);
      } else {
        setIsHunting(false);
      }
    } catch {
      setIsHunting(false);
    }
  };

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects/`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setProjects(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchProjectDetail = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/projects/${id}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedProject(data);
        
        // Populate inputs if editing
        setEditedTitle(data.script_title || '');
        setEditedHook(data.script_hook || '');
        setEditedBody(data.script_body || '');
        setEditedCta(data.script_cta || '');
        
        // During a running workflow, logs are more accurate than the coarse
        // project status. Avoid repainting Script Writer as running forever.
        if (data.status !== 'running') {
          updateAgentStatuses(data.status);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const fetchProjectLogs = async (id) => {
    try {
      const res = await fetch(`${API_BASE}/projects/${id}/logs`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setProjectLogs(data);
        updateAgentStatusesFromLogs(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const updateAgentStatusesFromLogs = (logs) => {
    const sequence = [
      "Custom Input", "Trend Hunter", "Competitor Research", "Keyword Research", "Audience Research",
      "Analytics Feedback", "Memory Agent", "Idea Generator", "Script Writer",
      "Fact Checker", "Script Reviewer", "Brand Consistency", "Retention Optimizer",
      "Shorts Generator", "SEO Agent", "Translation Agent", "Content Calendar",
      "Thumbnail Agent", "Thumbnail Scorer", "Voice Agent",
      "Video Generator", "Publishing Agent", "Analytics Agent", "Memory Update"
    ];
    const nextStatuses = {};
    sequence.forEach(agent => { nextStatuses[agent] = 'idle'; });

    let isCustomFlow = false;
    logs.forEach(log => {
      if (!log.agent_name || log.agent_name === 'System') return;
      if (log.agent_name === 'Custom Input') {
        isCustomFlow = true;
        nextStatuses['Custom Input'] = log.status === 'success' ? 'success' : (log.status === 'error' ? 'error' : 'running');
      } else if (log.agent_name in nextStatuses) {
        if (log.status === 'success') nextStatuses[log.agent_name] = 'success';
        else if (log.status === 'error') nextStatuses[log.agent_name] = 'error';
        else if (nextStatuses[log.agent_name] !== 'success') nextStatuses[log.agent_name] = 'running';
      }
    });

    if (isCustomFlow && nextStatuses['Trend Hunter'] === 'idle') {
      nextStatuses['Trend Hunter'] = 'bypassed';
    }

    const latestActive = [...logs].reverse().find(log => log.agent_name && log.agent_name !== 'System' && log.agent_name in nextStatuses);
    if (latestActive && latestActive.status === 'running') {
      const activeIdx = sequence.indexOf(latestActive.agent_name);
      sequence.forEach((agent, idx) => {
        if (idx < activeIdx && nextStatuses[agent] === 'idle' && !(isCustomFlow && agent === 'Trend Hunter')) {
          nextStatuses[agent] = 'success';
        }
      });
    }

    setAgentStatus(nextStatuses);
  };

  const updateAgentStatuses = (status) => {
    const sequence = [
      "Competitor Research", "Keyword Research", "Audience Research",
      "Analytics Feedback", "Memory Agent", "Idea Generator", "Script Writer",
      "Fact Checker", "Script Reviewer", "Brand Consistency", "Retention Optimizer",
      "Shorts Generator", "SEO Agent", "Translation Agent", "Content Calendar",
      "Thumbnail Agent", "Thumbnail Scorer", "Voice Agent",
      "Video Generator", "Publishing Agent", "Analytics Agent", "Memory Update"
    ];
    const statusMap = {
      draft: -1, running: 6, script_generated: 6, voice_generated: 17,
      thumbnail_generated: 15, video_generated: 18, seo_generated: 12,
      waiting_for_approval: 18, published: 20, completed: 21
    };
    let activeIdx = statusMap[status] ?? -1;
    const newStatuses = { "Trend Hunter": "idle", "Custom Input": "idle" };
    sequence.forEach((agent, idx) => {
      if (idx < activeIdx) newStatuses[agent] = 'success';
      else if (idx === activeIdx) newStatuses[agent] = status === 'running' ? 'running' : 'success';
      else newStatuses[agent] = 'idle';
    });
    if (status === 'failed' && activeIdx >= 0) newStatuses[sequence[activeIdx]] = 'error';
    setAgentStatus(prev => ({ ...prev, ...newStatuses }));
  };

  const handleApprove = async () => {
    try {
      const res = await fetch(`${API_BASE}/projects/${selectedProject.id}/approve`, {
        method: 'POST', headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) { await fetchProjectDetail(selectedProject.id); }
      else { alert('Failed to approve. Please try again.'); }
    } catch (e) { console.error(e); }
  };

  const handleReject = async () => {
    const reason = prompt('Reason for rejection (optional):') || 'Revisions requested';
    try {
      const res = await fetch(`${API_BASE}/projects/${selectedProject.id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ reason })
      });
      if (res.ok) { await fetchProjectDetail(selectedProject.id); }
      else { alert('Failed to reject. Please try again.'); }
    } catch (e) { console.error(e); }
  };

  const createProject = async (e) => {
    e.preventDefault();
    try {
      const niche = (newProjectNiche || nicheFilter || 'AI').trim();
      const isCustom = !selectedTrend;
      const title = (newProjectTitle || '').trim() || (selectedTrend ? selectedTrend.title : `Custom ${niche} Video`);
      const res = await fetch(`${API_BASE}/projects/`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({
          title,
          niche,
          trend_id: selectedTrend?.id || null,
          youtube_account_id: selectedChannelId || null,
          is_custom: isCustom,
          custom_title: isCustom ? title : null
        })
      });
      if (res.ok) {
        const data = await res.json();
        setNewProjectTitle('');
        setShowProjectModal(false);
        setActiveTab('projects');
        setSelectedProject(data);
        fetchProjectDetail(data.id);
        fetchProjectLogs(data.id);

        // Automatically trigger workflow launch when Deploy Workflow is clicked in modal
        fetch(`${API_BASE}/projects/${data.id}/run`, {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        }).then(() => {
          fetchProjectDetail(data.id);
          fetchProjectLogs(data.id);
        }).catch(err => console.error("Auto-run error:", err));
      } else {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || 'Could not create project. Please check the niche and title.');
      }
    } catch (e) {
      console.error(e);
      alert('Could not create project. Is the backend running?');
    }
  };

  const handleUpdateProject = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/projects/${selectedProject.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          script_title: editedTitle,
          script_hook: editedHook,
          script_body: editedBody,
          script_cta: editedCta
        })
      });
      if (res.ok) {
        alert("Script saved successfully!");
        fetchProjectDetail(selectedProject.id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const runProjectWorkflow = async () => {
    setIsRunningWorkflow(true);
    try {
      const res = await fetch(`${API_BASE}/projects/${selectedProject.id}/run`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchProjectDetail(selectedProject.id);
        fetchProjectLogs(selectedProject.id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setIsRunningWorkflow(false);
    }
  };

  const deleteProject = async (id) => {
    if (!confirm("Are you sure you want to delete this project?")) return;
    try {
      const res = await fetch(`${API_BASE}/projects/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        setSelectedProject(null);
        fetchProjects();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const logout = () => {
    setToken('');
    localStorage.removeItem('token');
  };

  if (!token && !isLoadingUser) {
    return (
      <div className="auth-container">
        <div className="glass-panel auth-card">
          <div className="auth-header">
            <span style={{ fontSize: '48px' }}>🤖</span>
            <h2>{isRegister ? 'Join the YouTube Empire' : 'Welcome Back Commander'}</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
              {isRegister ? 'Register your workspace account' : 'Access your multi-agent controls'}
            </p>
          </div>
          
          {authError && (
            <div style={{
              background: 'rgba(244, 63, 94, 0.1)',
              border: '1px solid var(--accent-rose)',
              borderRadius: '8px',
              padding: '12px',
              marginBottom: '20px',
              fontSize: '14px',
              color: '#fda4af',
              textAlign: 'center'
            }}>
              {authError}
            </div>
          )}

          <form onSubmit={handleAuth}>
            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input 
                type="email" 
                className="form-input" 
                required 
                value={authEmail}
                onChange={e => setAuthEmail(e.target.value)}
                placeholder="commander@empire.ai"
              />
            </div>
            <div className="form-group" style={{ marginBottom: '30px' }}>
              <label className="form-label">Security Key/Password</label>
              <input 
                type="password" 
                className="form-input" 
                required 
                value={authPassword}
                onChange={e => setAuthPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
            
            <button type="submit" className="btn btn-primary" style={{ marginBottom: '16px' }}>
              {isRegister ? 'Initialize Account' : 'Authenticate Console'}
            </button>
            
            <button 
              type="button" 
              className="btn btn-secondary"
              onClick={() => {
                setIsRegister(!isRegister);
                setAuthError('');
              }}
            >
              {isRegister ? 'Have an account? Log In' : 'Create New Account'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  if (isLoadingUser) {
    return (
      <div style={{ display:'flex', alignItems:'center', justifyContent:'center', minHeight:'100vh', flexDirection:'column', gap:'20px' }}>
        <div style={{ width:'48px', height:'48px', border:'4px solid var(--border-glass)', borderTop:'4px solid var(--accent-purple)', borderRadius:'50%', animation:'spin 1s linear infinite' }} />
        <p style={{ color:'var(--text-muted)', fontFamily:'var(--font-heading)' }}>Connecting to backend...</p>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (token && !user) {
    return (
      <div className="auth-container">
        <div className="glass-panel auth-card">
          <div className="auth-header">
            <AlertTriangle size={48} style={{ color: 'var(--accent-amber)' }} />
            <h2>Unable to Load Console</h2>
            <p style={{ color: 'var(--text-secondary)', marginTop: '8px' }}>
              {profileError || 'Your session could not be verified.'}
            </p>
          </div>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => {
              setIsLoadingUser(true);
              fetchProfile().finally(() => setIsLoadingUser(false));
            }}
            style={{ marginBottom: '16px' }}
          >
            <RefreshCw size={16} />
            Retry Connection
          </button>
          <button type="button" className="btn btn-secondary" onClick={logout}>
            <LogOut size={16} />
            Back to Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary>
    <div className="app-container">
      {/* Sidebar Navigation */}
      <nav className="sidebar">
        <div className="brand">
          <span style={{ fontSize: '28px' }}>🎬</span>
          <span className="gradient-text">EMPIRE.AI</span>
        </div>
        
        <ul className="nav-links">
          <li 
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => { setActiveTab('dashboard'); setSelectedProject(null); }}
          >
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </li>
          <li 
            className={`nav-item ${activeTab === 'trends' ? 'active' : ''}`}
            onClick={() => { setActiveTab('trends'); setSelectedProject(null); }}
          >
            <Flame size={20} />
            <span>Trend Hunter</span>
          </li>
          <li 
            className={`nav-item ${activeTab === 'projects' ? 'active' : ''}`}
            onClick={() => { setActiveTab('projects'); }}
          >
            <FileVideo size={20} />
            <span>Campaign Projects</span>
          </li>
          <li 
            className={`nav-item ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => { setActiveTab('analytics'); setSelectedProject(null); }}
          >
            <BarChart3 size={20} />
            <span>Empire Analytics</span>
          </li>
        </ul>

        {user && (
          <div style={{ marginTop: 'auto', padding: '12px', borderTop: '1px solid var(--border-glass)', marginBottom: '4px' }}>
            <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>AUTHORIZED USER</p>
            <p style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>{user.email}</p>
          </div>
        )}

        {/* YouTube Channel Widget in Sidebar */}
        <div style={{ padding: '10px 12px', marginBottom: '8px', borderTop: '1px solid var(--border-glass)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', letterSpacing: '0.05em', fontWeight: '600' }}>YOUTUBE CHANNEL</span>
            <button 
              onClick={connectYoutube}
              style={{ background: 'none', border: 'none', color: '#c084fc', fontSize: '12px', cursor: 'pointer', padding: 0, fontWeight: '600' }}
            >
              + Add
            </button>
          </div>
          {youtubeStatus.active_account ? (
            <div 
              onClick={() => { setShowAccountsModal(true); fetchAccounts(); }}
              style={{
                display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 10px',
                borderRadius: '8px', background: 'rgba(16,185,129,0.08)',
                border: '1px solid rgba(16,185,129,0.3)', cursor: 'pointer'
              }}
              title="Click to manage or switch YouTube channels"
            >
              <Youtube size={16} style={{ color: '#34d399', flexShrink: 0 }} />
              <div style={{ overflow: 'hidden', flex: 1 }}>
                <p style={{ fontSize: '12px', fontWeight: '600', color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {youtubeStatus.active_account.nickname}
                </p>
                <p style={{ fontSize: '11px', color: '#34d399', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {youtubeStatus.active_account.channel_title || 'Active Channel'}
                </p>
              </div>
            </div>
          ) : (
            <button 
              className="btn btn-primary" 
              style={{ width: '100%', padding: '6px 10px', fontSize: '12px' }}
              onClick={connectYoutube}
            >
              <Youtube size={14} /> Connect YouTube
            </button>
          )}
        </div>

        {/* Health status widget */}
        <div style={{ padding: '10px 12px', marginBottom: '8px', borderTop: '1px solid var(--border-glass)' }}>
          <p style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px', letterSpacing: '0.05em' }}>SYSTEM HEALTH</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {Object.entries({ db: 'DB', redis: 'Redis', openai: 'OpenAI', elevenlabs: 'Eleven', youtube: 'YT' }).map(([key, label]) => {
              const serviceKey = key === 'db' ? 'database' : key;
              const serviceValue = healthStatus[serviceKey];
              const ok = ['ok', 'healthy', 'configured', 'connected'].includes(serviceValue) || serviceValue === true;
              const unknown = serviceValue === null || serviceValue === undefined;
              return (
                <span key={key} title={`${label}: ${serviceValue || 'unknown'}`} style={{
                  display: 'flex', alignItems: 'center', gap: '4px',
                  fontSize: '11px', padding: '2px 7px', borderRadius: '999px',
                  background: unknown ? 'rgba(255,255,255,0.05)' : ok ? 'rgba(16,185,129,0.1)' : 'rgba(244,63,94,0.1)',
                  color: unknown ? 'var(--text-muted)' : ok ? '#34d399' : '#f87171',
                  border: `1px solid ${unknown ? 'rgba(255,255,255,0.08)' : ok ? 'rgba(16,185,129,0.3)' : 'rgba(244,63,94,0.3)'}`
                }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: unknown ? '#6b7280' : ok ? '#34d399' : '#f87171', display: 'inline-block' }} />
                  {label}
                </span>
              );
            })}
          </div>
        </div>

        <button className="btn btn-secondary logout-btn" onClick={logout}>
          <LogOut size={16} />
          <span>Exit Console</span>
        </button>
      </nav>

      {/* Main Container */}
      <main className="main-content">
        
        {/* TAB 1: DASHBOARD */}
        {activeTab === 'dashboard' && !selectedProject && (
          <div>
            <div className="flex-row-between">
              <div>
                <h1 className="gradient-text" style={{ fontSize: '32px' }}>Empire Command Center</h1>
                <p style={{ color: 'var(--text-secondary)' }}>Observe metrics, logs, and schedule your agents.</p>
                {youtubeStatus.active_account && (
                  <p style={{ fontSize: '13px', color: '#34d399', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Youtube size={14} />
                    Active: <strong>{youtubeStatus.active_account.channel_title || youtubeStatus.active_account.nickname}</strong>
                  </p>
                )}
              </div>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', justifyContent: 'flex-end', alignItems: 'center' }}>
                {youtubeStatus.connected ? (
                  <button
                    className="btn btn-secondary"
                    style={{ width: 'auto', border: '1px solid rgba(16,185,129,0.35)', color: '#34d399' }}
                    onClick={() => { setShowAccountsModal(true); fetchAccounts(); }}
                  >
                    <Youtube size={18} /> Manage Channels ({ytAccounts.length})
                  </button>
                ) : (
                  <button className="btn btn-primary" style={{ width: 'auto' }} onClick={connectYoutube}>
                    <Youtube size={18} /> Connect YouTube
                  </button>
                )}
                <button
                  className="btn btn-secondary"
                  style={{ width: 'auto', border: '1px solid rgba(139,92,246,0.35)', color: '#c084fc' }}
                  onClick={connectYoutube}
                >
                  + Add Channel
                </button>
                <button className="btn btn-primary" style={{ width: 'auto' }} onClick={() => setActiveTab('trends')}>
                  <Flame size={18} /> Find New Trends
                </button>
              </div>
            </div>

            {/* Nickname prompt modal */}
            {showNicknamePrompt && (
              <div style={{
                position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(10px)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000
              }}>
                <div className="glass-panel" style={{ width: '100%', maxWidth: '420px' }}>
                  <h2 className="gradient-text" style={{ marginBottom: '8px' }}>Connect YouTube Channel</h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '20px' }}>
                    Give this channel a nickname so you can identify it easily.
                  </p>
                  <div className="form-group">
                    <label className="form-label">Channel Nickname</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. Gaming Channel, Finance Channel..."
                      value={newChannelNickname}
                      onChange={e => setNewChannelNickname(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') connectNewChannel(); }}
                      autoFocus
                    />
                  </div>
                  <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
                    <button className="btn btn-primary" onClick={connectNewChannel} style={{ flex: 1 }}>
                      <Youtube size={16} /> Authorize with Google
                    </button>
                    <button className="btn btn-secondary" onClick={() => setShowNicknamePrompt(false)} style={{ width: 'auto' }}>
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Accounts manager modal */}
            {showAccountsModal && (
              <div style={{
                position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(10px)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000
              }}>
                <div className="glass-panel" style={{ width: '100%', maxWidth: '620px', maxHeight: '80vh', overflowY: 'auto' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                    <h2 className="gradient-text">YouTube Channels</h2>
                    <button className="btn btn-secondary" style={{ width: 'auto' }} onClick={() => setShowAccountsModal(false)}>✕ Close</button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
                    {ytAccounts.length === 0 && (
                      <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '24px' }}>No channels connected yet.</p>
                    )}
                    {ytAccounts.map(acc => (
                      <div key={acc.id} style={{
                        display: 'flex', alignItems: 'center', gap: '14px',
                        padding: '14px 18px', borderRadius: '12px',
                        background: acc.is_active ? 'rgba(16,185,129,0.06)' : 'rgba(255,255,255,0.02)',
                        border: `1px solid ${acc.is_active ? 'rgba(16,185,129,0.3)' : 'var(--border-glass)'}`,
                      }}>
                        {acc.channel_thumbnail ? (
                          <img src={acc.channel_thumbnail} alt="" style={{ width: '44px', height: '44px', borderRadius: '50%', objectFit: 'cover' }} />
                        ) : (
                          <div style={{ width: '44px', height: '44px', borderRadius: '50%', background: 'rgba(139,92,246,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <Youtube size={20} style={{ color: '#c084fc' }} />
                          </div>
                        )}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={{ fontWeight: '600', fontSize: '15px' }}>{acc.nickname}</span>
                            {acc.is_active && <span style={{ fontSize: '11px', background: 'rgba(16,185,129,0.15)', color: '#34d399', padding: '2px 8px', borderRadius: '20px', border: '1px solid rgba(16,185,129,0.3)' }}>Active</span>}
                            {!acc.connected && <span style={{ fontSize: '11px', background: 'rgba(244,63,94,0.1)', color: '#f87171', padding: '2px 8px', borderRadius: '20px' }}>Token Expired</span>}
                          </div>
                          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {acc.channel_title || 'Channel title unknown'} {acc.channel_id ? `· ${acc.channel_id}` : ''}
                          </p>
                        </div>
                        <div style={{ display: 'flex', gap: '8px', flexShrink: 0 }}>
                          {!acc.is_active && (
                            <button
                              className="btn btn-secondary"
                              style={{ padding: '6px 12px', fontSize: '12px', width: 'auto', border: '1px solid rgba(16,185,129,0.3)', color: '#34d399' }}
                              onClick={() => activateAccount(acc.id)}
                            >
                              Set Active
                            </button>
                          )}
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '6px 10px', fontSize: '12px', width: 'auto' }}
                            onClick={() => renameAccount(acc.id, acc.nickname)}
                          >
                            Rename
                          </button>
                          <button
                            className="btn btn-secondary"
                            style={{ padding: '6px 10px', fontSize: '12px', width: 'auto', border: '1px solid rgba(244,63,94,0.2)', color: '#f87171' }}
                            onClick={() => deleteAccount(acc.id)}
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  <button
                    className="btn btn-primary"
                    onClick={() => { setShowAccountsModal(false); connectYoutube(); }}
                  >
                    <Youtube size={16} /> + Connect New Channel
                  </button>
                </div>
              </div>
            )}


            {/* Quick Stats Grid */}
            <div className="stats-grid">
              <div className="glass-panel stat-card">
                <div className="stat-icon" style={{ background: 'rgba(6, 182, 212, 0.1)', color: 'var(--accent-cyan)' }}>
                  <TrendingUp size={24} />
                </div>
                <div className="stat-info">
                  <h3>Total Video Views</h3>
                  <p>{(stats.total_views || 0).toLocaleString()}</p>
                </div>
              </div>
              <div className="glass-panel stat-card">
                <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-emerald)' }}>
                  <Activity size={24} />
                </div>
                <div className="stat-info">
                  <h3>Watch Time (Hours)</h3>
                  <p>{(stats.total_watch_time || 0).toFixed(1)}h</p>
                </div>
              </div>
              <div className="glass-panel stat-card">
                <div className="stat-icon" style={{ background: 'rgba(245, 158, 11, 0.1)', color: 'var(--accent-amber)' }}>
                  <Award size={24} />
                </div>
                <div className="stat-info">
                  <h3>Average CTR</h3>
                  <p>{(stats.avg_ctr || 0).toFixed(2)}%</p>
                </div>
              </div>
              <div className="glass-panel stat-card">
                <div className="stat-icon" style={{ background: 'rgba(139, 92, 246, 0.1)', color: 'var(--accent-purple)' }}>
                  <Cpu size={24} />
                </div>
                <div className="stat-info">
                  <h3>Total Projects</h3>
                  <p>{stats.total_projects}</p>
                </div>
              </div>
              <div className="glass-panel stat-card">
                <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#34d399' }}>
                  <DollarSign size={24} />
                </div>
                <div className="stat-info">
                  <h3>Est. Revenue</h3>
                  <p>${(stats.total_revenue || 0).toFixed(2)}</p>
                </div>
              </div>
            </div>

            {/* New AI Agents Showcase */}
            <div className="glass-panel" style={{ marginBottom: '0' }}>
              <h3 style={{ marginBottom: '16px', fontFamily: 'var(--font-heading)', fontSize: '16px' }}>🤖 13 New AI Agents Active</h3>
              <div className="agents-showcase-row">
                {[
                  { icon: '🔍', name: 'Competitor Research', desc: 'Analyzes top video angles' },
                  { icon: '🏷️', name: 'Keyword Research', desc: 'Finds high-volume tags' },
                  { icon: '👥', name: 'Audience Research', desc: 'Maps demographics & intent' },
                  { icon: '✅', name: 'Fact Checker', desc: 'Verifies all script claims' },
                  { icon: '📝', name: 'Script Reviewer', desc: 'Scores hook & retention' },
                  { icon: '🖼️', name: 'Thumbnail Scorer', desc: 'Multi-modal visual scoring' },
                  { icon: '🎨', name: 'Brand Consistency', desc: 'Checks brand guidelines' },
                  { icon: '📈', name: 'Retention Optimizer', desc: 'Injects scene cues' },
                  { icon: '📱', name: 'Shorts Generator', desc: 'Creates vertical clips' },
                  { icon: '🌍', name: 'Translation Agent', desc: 'Translates to Spanish' },
                  { icon: '📅', name: 'Content Calendar', desc: 'Plans publish schedule' },
                  { icon: '📊', name: 'Analytics Feedback', desc: 'Learn from past metrics' },
                  { icon: '🧠', name: 'Memory Agent', desc: 'Learns from video history' },
                ].map((a, i) => (
                  <div key={i} className="agent-showcase-card">
                    <span className="agent-showcase-icon">{a.icon}</span>
                    <span className="agent-showcase-name">{a.name}</span>
                    <span className="agent-showcase-desc">{a.desc}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Charts & Status Layout */}
            <div className="dashboard-grid">
              {/* Left Column: Views Chart */}
              <div className="glass-panel" style={{ height: '360px' }}>
                <h3 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)' }}>Views & Analytics Timeline</h3>
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="80%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="colorViews" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--accent-purple)" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="var(--accent-purple)" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                      <XAxis dataKey="date" stroke="var(--text-muted)" />
                      <YAxis stroke="var(--text-muted)" />
                      <Tooltip contentStyle={{ background: '#12121a', border: '1px solid var(--border-glass)', color: '#fff' }} />
                      <Area type="monotone" dataKey="views" stroke="var(--accent-purple)" fillOpacity={1} fill="url(#colorViews)" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ display: 'flex', height: '80%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                    No campaigns uploaded yet. Run an agent flow to generate metrics.
                  </div>
                )}
              </div>

              {/* Right Column: Live Agent Board */}
              <div className="glass-panel">
                <h3 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)' }}>Active Multi-Agent Matrix</h3>
                <div className="agent-node-list">
                  <div className="agent-node-card">
                    <span style={{ fontWeight: '500' }}>Multi-Agent System State</span>
                    <span className="status-badge badge-idle">Ready</span>
                  </div>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                    The multi-agent graph coordinates 9 specialized LLM workers via LangGraph. 
                    Select a project or trend to deploy the agents.
                  </p>
                  <button className="btn btn-secondary" onClick={() => setActiveTab('projects')} style={{ marginTop: '20px' }}>
                    View Video Projects
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: TREND HUNTER */}
        {activeTab === 'trends' && (
          <div>
            <div className="flex-row-between">
              <div>
                <h1 className="gradient-text" style={{ fontSize: '32px' }}>Trend Hunting Hub</h1>
                <p style={{ color: 'var(--text-secondary)' }}>Identify high-performing topics mined by Google and YouTube Data APIs.</p>
              </div>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                <input
                  type="text"
                  className="form-input"
                  style={{ width: '220px', padding: '10px 14px', margin: 0 }}
                  placeholder="Filter by niche (e.g. Gaming)"
                  value={nicheFilter}
                  onChange={e => setNicheFilter(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { fetchTrends(nicheFilter || undefined); } }}
                />
                <button
                  className="btn btn-secondary"
                  style={{ width: 'auto' }}
                  onClick={() => fetchTrends(nicheFilter || undefined)}
                >
                  <Search size={16} /> Filter
                </button>
                <button 
                  className="btn btn-primary" 
                  onClick={triggerTrendHunt}
                  disabled={isHunting}
                  style={{ width: 'auto' }}
                >
                  <RefreshCw size={18} className={isHunting ? "spin" : ""} />
                  {isHunting ? `Hunting${nicheFilter ? ` "${nicheFilter}"` : ''}...` : `Harvest${nicheFilter ? ` "${nicheFilter}"` : ''} Trends`}
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ width: 'auto' }}
                  onClick={() => openProjectModal(null, nicheFilter || 'AI')}
                >
                  <FileVideo size={16} /> Create Video Project
                </button>
              </div>
            </div>

            <div className="trends-grid">
              {trends.map((t, idx) => (
                <div key={idx} className="glass-panel trend-card">
                  <div className="trend-header">
                    <span className="trend-category">{t.category}</span>
                    <span className="trend-score">🔥 {(t.score || 0).toFixed(0)}</span>
                  </div>
                  
                  <h3 className="trend-title">{t.title}</h3>
                  
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Source: {t.source}</span>
                    <button 
                      className="btn btn-primary" 
                      style={{ padding: '6px 12px', fontSize: '12px', width: 'auto' }}
                      onClick={() => openProjectModal(t)}
                    >
                      Build Video
                    </button>
                  </div>
                </div>
              ))}
            </div>

            {/* Modal for creating project from trend */}
            {showProjectModal && (
              <div style={{
                position: 'fixed', top: 0, left: 0, width: '100%', height: '100%',
                background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)',
                display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000
              }}>
                <div className="glass-panel" style={{ width: '100%', maxWidth: '500px' }}>
                  <h2 className="gradient-text" style={{ marginBottom: '20px' }}>Deploy Empire Agents</h2>
                  <form onSubmit={createProject}>
                    <div className="form-group">
                      <label className="form-label">Campaign Project Title</label>
                      <input 
                        type="text" 
                        className="form-input" 
                        required 
                        value={newProjectTitle}
                        onChange={e => setNewProjectTitle(e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Target Audience Niche</label>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="e.g. Gaming, Fitness, Cooking, Finance..."
                        value={newProjectNiche}
                        onChange={e => setNewProjectNiche(e.target.value)}
                        required
                        list="niche-suggestions"
                      />
                      <datalist id="niche-suggestions">
                        <option value="AI" />
                        <option value="Programming" />
                        <option value="Finance" />
                        <option value="Startups" />
                        <option value="Gaming" />
                        <option value="car edit" />
                        <option value="automotive" />
                        <option value="Fitness" />
                        <option value="Cooking" />
                        <option value="Travel" />
                        <option value="Tech" />
                        <option value="Health" />
                        <option value="Beauty" />
                        <option value="Music" />
                        <option value="Education" />
                        <option value="Business" />
                        <option value="Sports" />
                      </datalist>
                      <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '6px' }}>Type any niche or pick from suggestions.</p>
                    </div>

                    <div className="form-group">
                      <label className="form-label">Target YouTube Channel</label>
                      <select 
                        className="form-input" 
                        value={selectedChannelId} 
                        onChange={e => setSelectedChannelId(e.target.value)}
                        style={{ cursor: 'pointer' }}
                      >
                        {ytAccounts.length === 0 ? (
                          <option value="">Default Active Channel</option>
                        ) : (
                          ytAccounts.map(acc => (
                            <option key={acc.id} value={acc.id}>
                              {acc.nickname} {acc.channel_title ? `(${acc.channel_title})` : ''} {acc.is_active ? '★ Active' : ''}
                            </option>
                          ))
                        )}
                      </select>
                      <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>Select which connected channel will publish this video.</p>
                    </div>
                    
                    <div style={{ display: 'flex', gap: '12px', marginTop: '30px' }}>
                      <button type="submit" className="btn btn-primary">Deploy Workflow</button>
                      <button 
                        type="button" 
                        className="btn btn-secondary" 
                        onClick={() => setShowProjectModal(false)}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: PROJECTS (LIST AND DETAILED VIEWER) */}
        {activeTab === 'projects' && (
          <div>
            {!selectedProject ? (
              <div>
                <div className="flex-row-between">
                  <div>
                    <h1 className="gradient-text" style={{ fontSize: '32px' }}>Video Campaigns</h1>
                    <p style={{ color: 'var(--text-secondary)' }}>Manage your automated script edits, generated clips, and SEO details.</p>
                  </div>
                  <button 
                    className="btn btn-primary" 
                    style={{ width: 'auto' }}
                    onClick={() => openProjectModal(null, 'AI')}
                  >
                    + Custom Campaign
                  </button>
                </div>

                <div className="glass-panel" style={{ padding: '0', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: 'rgba(255,255,255,0.02)', borderBottom: '1px solid var(--border-glass)' }}>
                        <th style={{ padding: '16px 24px' }}>Campaign Title</th>
                        <th style={{ padding: '16px 24px' }}>Niche</th>
                        <th style={{ padding: '16px 24px' }}>Target Channel</th>
                        <th style={{ padding: '16px 24px' }}>Status</th>
                        <th style={{ padding: '16px 24px' }}>Video Output</th>
                        <th style={{ padding: '16px 24px' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {projects.map((p, idx) => (
                        <tr key={idx} style={{ borderBottom: '1px solid var(--border-glass)', transition: '0.2s' }}>
                          <td style={{ padding: '16px 24px', fontWeight: '500' }}>{p.title}</td>
                          <td style={{ padding: '16px 24px' }}>
                            <span className="trend-category" style={{ background: 'rgba(139,92,246,0.1)', color: '#c084fc' }}>{p.niche}</span>
                          </td>
                          <td style={{ padding: '16px 24px' }}>
                            {(() => {
                              const acc = ytAccounts.find(a => a.id === p.youtube_account_id);
                              if (acc) {
                                return (
                                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '12px', background: 'rgba(16,185,129,0.12)', color: '#34d399', padding: '3px 8px', borderRadius: '6px', border: '1px solid rgba(16,185,129,0.25)' }}>
                                    <Youtube size={12} /> {acc.nickname}
                                  </span>
                                );
                              }
                              return (
                                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                                  {youtubeStatus.active_account ? `${youtubeStatus.active_account.nickname} (Default)` : 'Default Channel'}
                                </span>
                              );
                            })()}
                          </td>
                          <td style={{ padding: '16px 24px' }}>
                            <span className={`status-badge badge-${
                              p.status === "completed" || p.status === "published" ? "success" : 
                              (p.status === "failed" ? "error" : "running")
                            }`}>
                              {p.status}
                            </span>
                          </td>
                          <td style={{ padding: '16px 24px', color: 'var(--text-secondary)' }}>
                            {p.video_url ? (
                              <span style={{ color: 'var(--accent-cyan)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <CheckCircle size={14} /> Ready
                              </span>
                            ) : "Not rendered"}
                          </td>
                          <td style={{ padding: '16px 24px' }}>
                            <div style={{ display: 'flex', gap: '12px' }}>
                              <button 
                                className="btn btn-secondary" 
                                style={{ padding: '6px 12px', fontSize: '13px', width: 'auto' }}
                                onClick={() => fetchProjectDetail(p.id)}
                              >
                                View / Edit
                              </button>
                              <button 
                                className="btn btn-secondary" 
                                style={{ padding: '6px 12px', fontSize: '13px', width: 'auto', border: '1px solid rgba(244,63,94,0.2)', color: 'var(--accent-rose)' }}
                                onClick={() => deleteProject(p.id)}
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  
                  {projects.length === 0 && (
                    <div style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No campaigns found. Generate one by starting from Trend Hunter!
                    </div>
                  )}
                </div>
              </div>
            ) : (
              /* DETAILED VIEW MODE FOR A SELECTED PROJECT */
              <div>
                <div style={{ marginBottom: '24px' }}>
                  <button 
                    className="btn btn-secondary" 
                    style={{ width: 'auto', marginBottom: '15px' }}
                    onClick={() => { setSelectedProject(null); fetchProjects(); }}
                  >
                    ← Back to Campaigns
                  </button>
                  <div className="flex-row-between">
                    <div>
                      <h1 className="gradient-text" style={{ fontSize: '28px' }}>{selectedProject.title}</h1>
                      <p style={{ color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap', marginTop: '4px' }}>
                        <span>Niche: <strong>{selectedProject.niche}</strong></span>
                        <span>•</span>
                        <span>Status: <strong>{selectedProject.status}</strong></span>
                        {(() => {
                          const acc = ytAccounts.find(a => a.id === selectedProject.youtube_account_id);
                          const label = acc ? acc.nickname : (youtubeStatus.active_account ? youtubeStatus.active_account.nickname : null);
                          if (label) {
                            return (
                              <>
                                <span>•</span>
                                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#34d399' }}>
                                  <Youtube size={14} /> Channel: <strong>{label}</strong>
                                </span>
                              </>
                            );
                          }
                          return null;
                        })()}
                      </p>
                    </div>
                    
                    <button 
                      className="btn btn-primary"
                      style={{ width: 'auto' }}
                      onClick={runProjectWorkflow}
                      disabled={selectedProject.status === 'running' || selectedProject.status === 'waiting_for_approval'}
                    >
                      <Play size={16} />
                      {selectedProject.status === 'running' ? 'Agents Working...' : 'Deploy Automation Pipeline'}
                    </button>
                  </div>
                </div>

                {/* Human-in-the-loop approval banner */}
                {selectedProject.status === 'waiting_for_approval' && (
                  <div style={{
                    background: 'linear-gradient(135deg, rgba(245,158,11,0.12), rgba(16,185,129,0.08))',
                    border: '1px solid rgba(245,158,11,0.4)',
                    borderRadius: '16px',
                    padding: '24px',
                    marginBottom: '24px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '20px',
                    flexWrap: 'wrap'
                  }}>
                    <div>
                      <p style={{ fontWeight: '700', fontSize: '16px', color: '#fbbf24', marginBottom: '6px' }}>⏳ Awaiting Your Approval</p>
                      <p style={{ fontSize: '14px', color: 'var(--text-secondary)', maxWidth: '500px' }}>
                        The AI pipeline has finished generating your video and is waiting for your approval before publishing to YouTube.
                        Review the script, audio, and thumbnail below before deciding.
                      </p>
                    </div>
                    <div style={{ display: 'flex', gap: '12px', flexShrink: 0 }}>
                      <button
                        className="btn btn-primary"
                        style={{ width: 'auto', background: 'linear-gradient(135deg, #059669, #10b981)', boxShadow: '0 0 20px rgba(16,185,129,0.3)' }}
                        onClick={handleApprove}
                      >
                        <ThumbsUp size={16} /> Approve & Publish
                      </button>
                      <button
                        className="btn btn-secondary"
                        style={{ width: 'auto', border: '1px solid rgba(244,63,94,0.4)', color: '#f87171' }}
                        onClick={handleReject}
                      >
                        <ThumbsDown size={16} /> Reject & Revise
                      </button>
                    </div>
                  </div>
                )}

                {/* Project detailed panels */}
                <div className="project-container">
                  {/* Left Column: Visual Asset and Script Editor */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
                    
                    {/* Media Player with Dual 16:9 Landscape & 9:16 Shorts Support */}
                    <div className="glass-panel">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                        <h3 style={{ fontFamily: 'var(--font-heading)', margin: 0 }}>Final Render Output</h3>
                        {selectedProject.shorts_video_url && (
                          <div style={{ display: 'flex', gap: '6px', background: 'rgba(255,255,255,0.05)', padding: '3px', borderRadius: '8px' }}>
                            <button
                              type="button"
                              className={`btn ${videoFormat === 'landscape' ? 'btn-primary' : 'btn-secondary'}`}
                              style={{ padding: '4px 10px', fontSize: '12px', width: 'auto' }}
                              onClick={() => setVideoFormat('landscape')}
                            >
                              🎬 16:9 Landscape
                            </button>
                            <button
                              type="button"
                              className={`btn ${videoFormat === 'shorts' ? 'btn-primary' : 'btn-secondary'}`}
                              style={{ padding: '4px 10px', fontSize: '12px', width: 'auto' }}
                              onClick={() => setVideoFormat('shorts')}
                            >
                              📱 9:16 Shorts
                            </button>
                          </div>
                        )}
                      </div>
                      <div className="asset-player" style={{ textAlign: 'center', background: '#0a0b10', borderRadius: '12px', overflow: 'hidden' }}>
                        {(videoFormat === 'shorts' ? (selectedProject.shorts_video_url || selectedProject.video_url) : selectedProject.video_url) ? (
                          <video 
                            key={videoFormat}
                            controls 
                            poster={selectedProject.thumbnail_url ? `http://localhost:8000${selectedProject.thumbnail_url}` : ''}
                            src={`http://localhost:8000${videoFormat === 'shorts' && selectedProject.shorts_video_url ? selectedProject.shorts_video_url : selectedProject.video_url}`}
                            style={{ maxHeight: videoFormat === 'shorts' ? '480px' : '360px', width: '100%', objectFit: 'contain' }}
                          />
                        ) : (
                          <div className="asset-placeholder" style={{ padding: '40px 20px' }}>
                            <UploadCloud size={48} />
                            <p style={{ marginTop: '10px' }}>Video not compiled. Deploy agents to render.</p>
                          </div>
                        )}
                      </div>
                      
                      {selectedProject.voiceover_url && (
                        <div style={{ marginTop: '16px' }}>
                          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px' }}>Narration Voiceover Audio (MP3):</p>
                          <audio 
                            controls 
                            src={`http://localhost:8000${selectedProject.voiceover_url}`}
                            style={{ width: '100%' }}
                          />
                        </div>
                      )}
                    </div>

                    {/* Script editor form */}
                    <div className="glass-panel editor-section">
                      <div className="editor-tabs">
                        <span 
                          className={`editor-tab ${activeProjectTab === 'script' ? 'active' : ''}`}
                          onClick={() => setActiveProjectTab('script')}
                        >
                          Video Script
                        </span>
                        <span 
                          className={`editor-tab ${activeProjectTab === 'seo' ? 'active' : ''}`}
                          onClick={() => setActiveProjectTab('seo')}
                        >
                          YouTube SEO & Metadata
                        </span>
                      </div>

                      {activeProjectTab === 'script' ? (
                        <form onSubmit={handleUpdateProject}>
                          <div className="form-group">
                            <label className="form-label">Script Title / Hook Hook line</label>
                            <input 
                              type="text" 
                              className="form-input"
                              value={editedTitle}
                              onChange={e => setEditedTitle(e.target.value)}
                              placeholder="Title Draft"
                            />
                          </div>
                          <div className="form-group">
                            <label className="form-label">Opening Hook (First 15s)</label>
                            <input 
                              type="text" 
                              className="form-input"
                              value={editedHook}
                              onChange={e => setEditedHook(e.target.value)}
                              placeholder="Hook line"
                            />
                          </div>
                          <div className="form-group">
                            <label className="form-label">Body Narration Copy</label>
                            <textarea 
                              className="form-textarea"
                              rows={6}
                              value={editedBody}
                              onChange={e => setEditedBody(e.target.value)}
                              placeholder="Narration script copy"
                            />
                          </div>
                          <div className="form-group">
                            <label className="form-label">Call-To-Action (CTA)</label>
                            <input 
                              type="text" 
                              className="form-input"
                              value={editedCta}
                              onChange={e => setEditedCta(e.target.value)}
                              placeholder="CTA Line"
                            />
                          </div>
                          
                          <button type="submit" className="btn btn-secondary" style={{ width: 'auto' }}>
                            Save Script Edits
                          </button>
                        </form>
                      ) : (
                        <div>
                          <div className="form-group">
                            <label className="form-label">SEO Title</label>
                            <input 
                              type="text" 
                              className="form-input" 
                              disabled 
                              value={selectedProject.seo_title || 'Agents will generate optimized title'}
                            />
                          </div>
                          <div className="form-group">
                            <label className="form-label">SEO Description</label>
                            <textarea 
                              className="form-textarea" 
                              disabled 
                              rows={5}
                              value={selectedProject.seo_description || 'Agents will generate tag-optimized description block'}
                            />
                          </div>
                          <div className="form-group">
                            <label className="form-label">Tags / Hashtags</label>
                            <input 
                              type="text" 
                              className="form-input" 
                              disabled 
                              value={selectedProject.seo_tags || 'Agents will generate comma separated tags'}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Right Column: Agents Board & Terminal Log Console */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
                    
                    {/* Live status of graph execution */}
                    <div className="glass-panel">
                      <h3 style={{ marginBottom: '16px', fontFamily: 'var(--font-heading)' }}>Pipeline Execution Nodes</h3>
                      <div className="agent-node-list">
                        {Object.keys(agentStatus).map((agent, index) => (
                          <div 
                            key={index} 
                            className={`agent-node-card ${agentStatus[agent] === 'running' ? 'running' : ''}`}
                          >
                            <div className="agent-identity">
                              <div className="agent-avatar">
                                <Cpu size={16} />
                              </div>
                              <span style={{ fontSize: '14px', fontWeight: '500' }}>{agent}</span>
                            </div>
                            <span className={`status-badge badge-${agentStatus[agent]}`}>
                              {agentStatus[agent]}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Terminal Logger */}
                    <div className="glass-panel" style={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
                      <h3 style={{ marginBottom: '12px', fontFamily: 'var(--font-heading)' }}>Agent Execution Terminal</h3>
                      <div className="console-terminal">
                        {projectLogs.map((log, idx) => (
                          <div key={idx} className="console-line">
                            <span className="console-time">[{new Date(log.created_at).toLocaleTimeString()}]</span>
                            <span className="console-agent">[{log.agent_name}]</span>
                            <span style={{ color: log.status === 'error' ? '#f87171' : (log.status === 'success' ? '#34d399' : '#fff') }}>
                              {log.log_message}
                            </span>
                          </div>
                        ))}
                        <div ref={terminalEndRef} />
                      </div>
                    </div>

                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: EMPIRE ANALYTICS */}
        {activeTab === 'analytics' && (
          <div>
            <div className="flex-row-between">
              <div>
                <h1 className="gradient-text" style={{ fontSize: '32px' }}>Empire Analytics</h1>
                <p style={{ color: 'var(--text-secondary)' }}>Measure reach, audience retention, and review improvement suggestions.</p>
              </div>
            </div>

            <div className="stats-grid">
              <div className="glass-panel stat-card">
                <div className="stat-icon" style={{ background: 'rgba(6, 182, 212, 0.1)', color: 'var(--accent-cyan)' }}>
                  <TrendingUp size={24} />
                </div>
                <div className="stat-info">
                  <h3>Views</h3>
                  <p>{stats.total_views.toLocaleString()}</p>
                </div>
              </div>
              <div className="glass-panel stat-card">
                <div className="stat-icon" style={{ background: 'rgba(16, 185, 129, 0.1)', color: 'var(--accent-emerald)' }}>
                  <Activity size={24} />
                </div>
                <div className="stat-info">
                  <h3>Subscribers Gained</h3>
                  <p>+{stats.total_subscribers}</p>
                </div>
              </div>
              <div className="glass-panel stat-card">
                <div className="stat-icon" style={{ background: 'rgba(245, 158, 11, 0.1)', color: 'var(--accent-amber)' }}>
                  <Award size={24} />
                </div>
                <div className="stat-info">
                  <h3>Avg CTR</h3>
                  <p>{(stats.avg_ctr || 0).toFixed(2)}%</p>
                </div>
              </div>
              <div className="glass-panel stat-card">
                <div className="stat-icon" style={{ background: 'rgba(16,185,129,0.1)', color: '#34d399' }}>
                  <DollarSign size={24} />
                </div>
                <div className="stat-info">
                  <h3>Est. Revenue</h3>
                  <p>${(stats.total_revenue || 0).toFixed(2)}</p>
                </div>
              </div>
            </div>

            {/* Performance charts */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
              <div className="glass-panel" style={{ height: '360px' }}>
                <h3 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)' }}>Views & Subscribers Timeline</h3>
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="80%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                      <XAxis dataKey="date" stroke="var(--text-muted)" />
                      <YAxis stroke="var(--text-muted)" />
                      <Tooltip contentStyle={{ background: '#12121a', border: '1px solid var(--border-glass)', color: '#fff' }} />
                      <Line type="monotone" dataKey="subscribers" stroke="var(--accent-cyan)" strokeWidth={2} activeDot={{ r: 8 }} />
                      <Line type="monotone" dataKey="views" stroke="var(--accent-purple)" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <div style={{ display: 'flex', height: '80%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
                    Awaiting video upload to gather analytics data.
                  </div>
                )}
              </div>

              {/* Revenue & Retention charts */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '25px' }}>
                <div className="glass-panel" style={{ height: '300px' }}>
                  <h3 style={{ marginBottom: '16px', fontFamily: 'var(--font-heading)', fontSize: '15px' }}>💰 Estimated Revenue ($)</h3>
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="80%">
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                            <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                        <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fontSize: 11 }} />
                        <YAxis stroke="var(--text-muted)" tick={{ fontSize: 11 }} />
                        <Tooltip contentStyle={{ background: '#12121a', border: '1px solid var(--border-glass)', color: '#fff' }} formatter={(v) => [`$${v}`, 'Revenue']} />
                        <Area type="monotone" dataKey="revenue" stroke="#10b981" fillOpacity={1} fill="url(#revenueGrad)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  ) : <div style={{ display: 'flex', height: '80%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>No data yet</div>}
                </div>
                <div className="glass-panel" style={{ height: '300px' }}>
                  <h3 style={{ marginBottom: '16px', fontFamily: 'var(--font-heading)', fontSize: '15px' }}>📊 Retention Rate (%)</h3>
                  {chartData.length > 0 ? (
                    <ResponsiveContainer width="100%" height="80%">
                      <BarChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border-glass)" />
                        <XAxis dataKey="date" stroke="var(--text-muted)" tick={{ fontSize: 11 }} />
                        <YAxis stroke="var(--text-muted)" tick={{ fontSize: 11 }} domain={[0, 100]} />
                        <Tooltip contentStyle={{ background: '#12121a', border: '1px solid var(--border-glass)', color: '#fff' }} formatter={(v) => [`${v}%`, 'Retention']} />
                        <Bar dataKey="retention" fill="var(--accent-amber)" radius={[4,4,0,0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  ) : <div style={{ display: 'flex', height: '80%', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>No data yet</div>}
                </div>
              </div>

              {/* AI Agent Suggestions */}
              <div className="glass-panel">
                <h3 style={{ marginBottom: '20px', fontFamily: 'var(--font-heading)' }}>🤖 AI Analytics Agent Suggestions</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                  <div style={{ borderLeft: '3px solid var(--accent-purple)', paddingLeft: '16px' }}>
                    <p style={{ fontWeight: '600', marginBottom: '4px' }}>Optimize Intro Hook for Programming Niche</p>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                      Retention logs show viewers in the Programming niche drop off in the first 5 seconds. 
                      Start directly with the code syntax demo rather than title slides.
                    </p>
                  </div>
                  <div style={{ borderLeft: '3px solid var(--accent-cyan)', paddingLeft: '16px' }}>
                    <p style={{ fontWeight: '600', marginBottom: '4px' }}>Leverage High-Score Google Trend Queries</p>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                      Topics mined with score &gt;90 show a 45% increase in CTR. 
                      Deploy the Trend Hunter twice a week to secure early search indexes.
                    </p>
                  </div>
                  <div style={{ borderLeft: '3px solid #10b981', paddingLeft: '16px' }}>
                    <p style={{ fontWeight: '600', marginBottom: '4px' }}>Increase Average Retention Above 40%</p>
                    <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                      The Retention Optimizer agent will inject scene transition cues and pattern interrupts
                      every 45 seconds. Enable it in your next workflow run for better watch time.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

      </main>
    </div>
    </ErrorBoundary>
  );
}
