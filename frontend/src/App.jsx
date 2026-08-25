import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  UserCheck, 
  FileText, 
  GitFork, 
  MessageSquare, 
  History, 
  Plus, 
  Trash2, 
  Save, 
  Link2, 
  Activity, 
  TrendingUp, 
  Clock, 
  User, 
  CheckCircle2, 
  XCircle,
  AlertTriangle,
  Play,
  Zap,
  Info,
  MessageCircle,
  Edit,
  LogOut
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

// Initial mocks for Demo Mode fallback
const MOCK_ACCOUNTS = [
  {
    id: 1,
    instagram_business_account_id: "98765",
    username: "fitlife_co",
    name: "FitLife Apparel",
    profile_picture_url: "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80",
    page_id: "12345",
    page_name: "FitLife Page",
    connected_at: "2026-08-01T10:00:00Z"
  }
];

const MOCK_FACEBOOK_ACCOUNTS = [
  {
    id: 101,
    facebook_page_id: "fb_page_123",
    username: "fitlife_fb",
    name: "FitLife Facebook Page",
    profile_picture_url: "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=150&auto=format&fit=crop&q=80",
    connected_at: "2026-08-01T10:00:00Z"
  }
];

const MOCK_POSTS = [
  {
    id: "media_post_1",
    media_url: "https://images.unsplash.com/photo-1517838277536-f5f99be501cd?w=500&auto=format&fit=crop&q=80",
    caption: "Drop the word 'GUIDE' below to get our 7-day home workout plan! 🏋️‍♂️💪 #homeworkout #fitness",
    media_type: "IMAGE",
    permalink: "https://instagram.com/p/media_post_1",
    timestamp: "2026-08-02T12:00:00Z"
  },
  {
    id: "media_post_2",
    media_url: "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=500&auto=format&fit=crop&q=80",
    caption: "Want 20% off your next order? Comment 'PROMO' and we will DM you a secret discount code! 🏷️",
    media_type: "IMAGE",
    permalink: "https://instagram.com/p/media_post_2",
    timestamp: "2026-08-03T08:30:00Z"
  }
];

const MOCK_FACEBOOK_POSTS = [
  {
    id: "fb_post_1",
    facebook_account_id: 101,
    caption: "Comment 'GUIDE' below to receive our exclusive Facebook Page optimization blueprint! 📘🚀",
    media_type: "post",
    media_url: "https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=500&auto=format&fit=crop&q=80",
    permalink: "https://facebook.com/posts/fb_post_1",
    timestamp: "2026-08-02T12:00:00Z"
  },
  {
    id: "fb_post_2",
    facebook_account_id: 101,
    caption: "Comment 'DISCOUNT' to get 30% off our social media growth toolkit! 🏷️📈",
    media_type: "post",
    media_url: "https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=500&auto=format&fit=crop&q=80",
    permalink: "https://facebook.com/posts/fb_post_2",
    timestamp: "2026-08-03T08:30:00Z"
  }
];

const MOCK_FLOWS = [
  {
    id: "flow_1",
    name: "Workout Guide Lead Magnet",
    is_active: true,
    nodes: [
      { id: "node_1", type: "trigger", config: { keywords: ["guide"], exact_word: true } },
      { id: "node_2", type: "action_reply", config: { message: "Hey {{username}}! I just sent the link to your DMs. Let me know what you think! 👍" } },
      { id: "node_3", type: "action_dm", config: { message: "Hi {{username}}! Here is your workout plan: https://fitlife.co/home-guide" } },
      { id: "node_4", type: "action_tag", config: { tag: "lead_guide" } }
    ],
    edges: [
      { id: "e1", source_node_id: "node_1", target_node_id: "node_2" },
      { id: "e2", source_node_id: "node_2", target_node_id: "node_3" },
      { id: "e3", source_node_id: "node_3", target_node_id: "node_4" }
    ]
  }
];

const MOCK_COMMENTS = [
  {
    comment_id: "c_101",
    media_id: "media_post_1",
    text: "Can I have the guide please?",
    username: "john_doe",
    timestamp: "2026-08-03T10:15:00Z",
    status: "processed",
    platform: "instagram"
  },
  {
    comment_id: "fb_c_101",
    media_id: "fb_post_1",
    text: "Can I get the Facebook Page Optimization Guide?",
    username: "fb_user_1",
    timestamp: "2026-08-03T10:16:00Z",
    status: "processed",
    platform: "facebook"
  },
  {
    comment_id: "c_102",
    media_id: "media_post_2",
    text: "I want the promo code!",
    username: "sara_fit",
    timestamp: "2026-08-03T11:02:00Z",
    status: "processed",
    platform: "instagram"
  },
  {
    comment_id: "c_103",
    media_id: "media_post_1",
    text: "looks cool",
    username: "fitness_fan",
    timestamp: "2026-08-03T11:05:00Z",
    status: "ignored",
    platform: "instagram"
  }
];

const MOCK_LOGS = [
  { id: 1, flow_id: "flow_1", comment_id: "c_101", action_type: "trigger_match", status: "success", created_at: "2026-08-03T10:15:02Z", details: { matched_keywords: ["guide"] } },
  { id: 2, flow_id: "flow_1", comment_id: "c_101", action_type: "reply_sent", status: "success", created_at: "2026-08-03T10:15:04Z", details: { reply_id: "rep_999" } },
  { id: 3, flow_id: "flow_1", comment_id: "c_101", action_type: "dm_sent", status: "success", created_at: "2026-08-03T10:15:05Z", details: { message_id: "msg_888" } },
  { id: 4, flow_id: "flow_1", comment_id: "c_101", action_type: "tag_added", status: "success", created_at: "2026-08-03T10:15:06Z", details: { tag: "lead_guide" } }
];

const MOCK_DM_RULES = [
  {
    id: "dm_rule_1",
    instagram_account_id: 1,
    name: "Exact Guide DM Trigger",
    trigger_type: "exact_keyword",
    keyword: "guide",
    reply_text: "Welcome! Here is your exclusive direct workout guide link: https://fitlife.co/dm-guide",
    is_active: true,
    created_at: "2026-08-01T10:00:00Z",
    updated_at: "2026-08-01T10:00:00Z"
  },
  {
    id: "dm_rule_2",
    instagram_account_id: 1,
    name: "First Contact greeting",
    trigger_type: "first_message",
    keyword: null,
    reply_text: "Hey! Thanks for sending us your first direct message. How can we help you today?",
    is_active: true,
    created_at: "2026-08-02T11:00:00Z",
    updated_at: "2026-08-02T11:00:00Z"
  }
];

const MOCK_DM_MESSAGES = [
  {
    id: "mid_dm_101",
    instagram_account_id: 1,
    sender_id: "sender_alex",
    recipient_id: "98765",
    text: "guide",
    timestamp: "2026-08-04T12:00:00Z",
    status: "processed",
    processed_at: "2026-08-04T12:00:02Z",
    error_message: null
  },
  {
    id: "mid_dm_102",
    instagram_account_id: 1,
    sender_id: "sender_alex",
    recipient_id: "98765",
    text: "Hello! This is my first time message.",
    timestamp: "2026-08-04T12:10:00Z",
    status: "processed",
    processed_at: "2026-08-04T12:10:01Z",
    error_message: null
  },
  {
    id: "mid_dm_103",
    instagram_account_id: 1,
    sender_id: "sender_bob",
    recipient_id: "98765",
    text: "How much is your premium plan?",
    timestamp: "2026-08-04T13:00:00Z",
    status: "ignored",
    processed_at: null,
    error_message: null
  }
];

const MOCK_DM_CONVERSATIONS = [
  {
    id: "1_sender_alex",
    instagram_account_id: 1,
    participant_id: "sender_alex",
    last_message_at: "2026-08-04T12:10:00Z",
    created_at: "2026-08-04T12:00:00Z"
  },
  {
    id: "1_sender_bob",
    instagram_account_id: 1,
    participant_id: "sender_bob",
    last_message_at: "2026-08-04T13:00:00Z",
    created_at: "2026-08-04T13:00:00Z"
  }
];

const MOCK_DM_EXECUTIONS = [
  {
    id: "exec_dm_101",
    automation_id: "dm_rule_1",
    message_id: "mid_dm_101",
    status: "success",
    error_message: null,
    executed_at: "2026-08-04T12:00:02Z"
  },
  {
    id: "exec_dm_102",
    automation_id: "dm_rule_2",
    message_id: "mid_dm_102",
    status: "success",
    error_message: null,
    executed_at: "2026-08-04T12:10:01Z"
  }
];


const renderDmText = (text) => {
  if (!text) return '""';
  try {
    const parsed = JSON.parse(text);
    if (parsed && parsed.dm_type === 'button_template') {
      return `[Button Template] "${parsed.text || parsed.reply_text || ''}" -> Button: "${parsed.button_text || ''}" (${parsed.button_url || ''})`;
    }
    if (parsed && parsed.dm_type === 'image') {
      return `[Image Template] "${parsed.text || parsed.reply_text || ''}" -> Image: ${parsed.image_url || ''}`;
    }
  } catch (e) {}
  return `"${text}"`;
};


export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [demoMode, setDemoMode] = useState(false);
  const [isRunningAutomation, setIsRunningAutomation] = useState(false);
  const [runningFlowId, setRunningFlowId] = useState(null);
  const [isGuideOpen, setIsGuideOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(!!localStorage.getItem('authToken'));
  const [email, setEmail] = useState('admin@insta-automator.com');
  const [password, setPassword] = useState('adminpassword123');
  const [token, setToken] = useState(localStorage.getItem('authToken') || '');
  const [showPassword, setShowPassword] = useState(false);
  const [metaScopes, setMetaScopes] = useState('instagram_basic,instagram_manage_comments,pages_show_list,pages_read_engagement');
  
  // Data States
  const [accounts, setAccounts] = useState([]);
  const [facebookAccounts, setFacebookAccounts] = useState([]);
  const [posts, setPosts] = useState([]);
  const [facebookPosts, setFacebookPosts] = useState([]);
  const [flows, setFlows] = useState([]);
  const [comments, setComments] = useState([]);
  const [logs, setLogs] = useState([]);
  const [postsFilterPlatform, setPostsFilterPlatform] = useState("instagram");
  const [analytics, setAnalytics] = useState({
    total_comments: 0,
    replies_sent: 0,
    dms_sent: 0,
    failed_replies: 0,
    avg_response_time_seconds: 0.0,
    keyword_counts: {}
  });

  const [dmRules, setDmRules] = useState([]);
  const [dmMessages, setDmMessages] = useState([]);
  const [dmConversations, setDmConversations] = useState([]);
  const [dmExecutions, setDmExecutions] = useState([]);
  const [isDmsLoading, setIsDmsLoading] = useState(false);
  const [isDmsSaving, setIsDmsSaving] = useState(false);
  const [dmSubTab, setDmSubTab] = useState('rules');

  // DM Rule Form states
  const [editingDmRule, setEditingDmRule] = useState(null);
  const [showDmModal, setShowDmModal] = useState(false);
  const [deleteConfirmRuleId, setDeleteConfirmRuleId] = useState(null);
  const [deleteConfirmFlowId, setDeleteConfirmFlowId] = useState(null);
  const [previewDmRule, setPreviewDmRule] = useState(null);
  const [modalTab, setModalTab] = useState('dm_setup'); // 'dm_setup', 'trigger_setup', 'settings'
  const [dmRuleForm, setDmRuleForm] = useState({
    instagram_account_id: '',
    name: 'Draft #1',
    trigger_type: 'exact_keyword',
    keyword: '',
    reply_text: '',
    is_active: true,
    dm_type: 'button_template',
    title: 'Get workout guide',
    subtitle: 'Exclusive link below',
    button_text: 'Shop Now',
    button_url: 'https://fitlife.co/shop',
    image_url: 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500'
  });



  // Flow Builder states
  const [selectedFlow, setSelectedFlow] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [builderNodes, setBuilderNodes] = useState([]);
  const [builderEdges, setBuilderEdges] = useState([]);
  
  // UI helper states
  const [toasts, setToasts] = useState([]);
  const [isConnectingFB, setIsConnectingFB] = useState(false);
  const [isSyncingPosts, setIsSyncingPosts] = useState(false);
  const [postsFilter, setPostsFilter] = useState("all"); // "all", "posts", "reels"
  const [showConnectModal, setShowConnectModal] = useState(false);

  // Post Comments Modal state
  const [activeCommentsPost, setActiveCommentsPost] = useState(null);
  const [postComments, setPostComments] = useState([]);
  const [isFetchingComments, setIsFetchingComments] = useState(false);
  const [newCommentText, setNewCommentText] = useState("");
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const [replyingToCommentId, setReplyingToCommentId] = useState(null);
  const [newReplyText, setNewReplyText] = useState("");
  const [isSubmittingReply, setIsSubmittingReply] = useState(false);

  const addToast = (message, type = 'info') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  };

  // Auto-authenticate & fetch on start
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = localStorage.getItem('authToken');
      if (storedToken) {
        try {
          await fetchBackendData(storedToken);
        } catch (err) {
          console.warn("Stored token validation failed:", err);
        }
      } else {
        checkBackendHealth();
      }
    };
    initializeAuth();
  }, []);

  // Fetch Meta config and initialize FB SDK
  useEffect(() => {
    const initFacebookSDK = async () => {
      try {
        const res = await fetch(`${API_BASE}/auth/meta-config`);
        if (res.ok) {
          const config = await res.json();
          if (config.app_id) {
            if (config.scopes) {
              setMetaScopes(config.scopes);
            }
            // Load Facebook SDK script
            (function(d, s, id) {
              var js, fjs = d.getElementsByTagName(s)[0];
              if (d.getElementById(id)) return;
              js = d.createElement(s); js.id = id;
              js.src = "https://connect.facebook.net/en_US/sdk.js";
              fjs.parentNode.insertBefore(js, fjs);
            }(document, 'script', 'facebook-jssdk'));

            window.fbAsyncInit = function() {
              window.FB.init({
                appId      : config.app_id,
                cookie     : true,
                xfbml      : true,
                version    : 'v19.0'
              });
            };
          }
        }
      } catch (err) {
        console.warn("Failed to load Meta App Configuration for SDK:", err);
      }
    };

    if (isAuthenticated && !demoMode) {
      initFacebookSDK();
    }
  }, [isAuthenticated, demoMode]);

  const checkBackendHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/auth/meta-config`);
      if (res.ok) {
        // Backend is online
        addToast("Connected to FastAPI Automation Backend.", "success");
      } else {
        throw new Error("Offline");
      }
    } catch (err) {
      setDemoMode(true);
      setIsAuthenticated(true); // Skip login in demo mode for quick preview
      loadDemoData();
      addToast("FastAPI Database offline. Starting in interactive Demo Mode.", "warning");
    }
  };

  const loadDemoData = () => {
    setAccounts(MOCK_ACCOUNTS);
    setFacebookAccounts(MOCK_FACEBOOK_ACCOUNTS);
    setPosts(MOCK_POSTS);
    setFacebookPosts(MOCK_FACEBOOK_POSTS);
    setFlows(MOCK_FLOWS);
    setComments(MOCK_COMMENTS);
    setLogs(MOCK_LOGS);
    setDmRules(MOCK_DM_RULES);
    setDmMessages(MOCK_DM_MESSAGES);
    setDmConversations(MOCK_DM_CONVERSATIONS);
    setDmExecutions(MOCK_DM_EXECUTIONS);
    setAnalytics({
      total_comments: 4,
      replies_sent: 2,
      dms_sent: 2,
      failed_replies: 0,
      avg_response_time_seconds: 4.2,
      keyword_counts: { "guide": 2, "promo": 1 }
    });
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (demoMode) {
      setIsAuthenticated(true);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/auth/login-json`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });
      if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        setIsAuthenticated(true);
        localStorage.setItem('authToken', data.access_token);
        addToast("Signed in successfully.", "success");
        fetchBackendData(data.access_token);
      } else {
        const err = await res.json();
        addToast(err.detail || "Authentication failed.", "error");
      }
    } catch (err) {
      // Fallback
      setDemoMode(true);
      setIsAuthenticated(true);
      loadDemoData();
      addToast("Failed connecting to server. Running in Demo Mode.", "warning");
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('authToken');
    setToken('');
    setIsAuthenticated(false);
    setDemoMode(false);
    addToast("Logged out successfully.", "info");
  };

  const fetchBackendData = async (authToken = token) => {
    if (!authToken) return;
    const headers = { 'Authorization': `Bearer ${authToken}` };
    try {
      const [
        accRes, fbAccRes, postsRes, fbPostsRes, flowsRes, logsRes, commentsRes, fbCommentsRes, analyticsRes,
        dmRulesRes, dmMessagesRes, dmConversationsRes, dmExecutionsRes
      ] = await Promise.all([
        fetch(`${API_BASE}/accounts`, { headers }),
        fetch(`${API_BASE}/accounts/facebook`, { headers }),
        fetch(`${API_BASE}/posts`, { headers }),
        fetch(`${API_BASE}/posts/facebook`, { headers }),
        fetch(`${API_BASE}/automation`, { headers }),
        fetch(`${API_BASE}/logs`, { headers }),
        fetch(`${API_BASE}/comments`, { headers }),
        fetch(`${API_BASE}/comments/facebook`, { headers }),
        fetch(`${API_BASE}/analytics`, { headers }),
        fetch(`${API_BASE}/dm-automation`, { headers }),
        fetch(`${API_BASE}/dm-automation/messages`, { headers }),
        fetch(`${API_BASE}/dm-automation/conversations`, { headers }),
        fetch(`${API_BASE}/dm-automation/executions`, { headers })
      ]);

      if (accRes.status === 401 || fbAccRes.status === 401) {
        localStorage.removeItem('authToken');
        setIsAuthenticated(false);
        setToken('');
        addToast("Session expired. Please sign in again.", "warning");
        return;
      }

      if (accRes.ok) setAccounts(await accRes.json());
      if (fbAccRes.ok) setFacebookAccounts(await fbAccRes.json());
      if (postsRes.ok) setPosts(await postsRes.json());
      if (fbPostsRes.ok) setFacebookPosts(await fbPostsRes.json());
      if (flowsRes.ok) setFlows(await flowsRes.json());
      if (logsRes.ok) setLogs(await logsRes.json());
      if (analyticsRes.ok) setAnalytics(await analyticsRes.json());
      if (dmRulesRes.ok) setDmRules(await dmRulesRes.json());
      if (dmMessagesRes.ok) setDmMessages(await dmMessagesRes.json());
      if (dmConversationsRes.ok) setDmConversations(await dmConversationsRes.json());
      if (dmExecutionsRes.ok) setDmExecutions(await dmExecutionsRes.json());

      let igComments = [];
      let fbComments = [];
      if (commentsRes.ok) {
        igComments = (await commentsRes.json()).map(c => ({ ...c, platform: 'instagram' }));
      }
      if (fbCommentsRes && fbCommentsRes.ok) {
        fbComments = (await fbCommentsRes.json()).map(c => ({ ...c, platform: 'facebook' }));
      }
      const mergedComments = [...igComments, ...fbComments].sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
      setComments(mergedComments);
    } catch (err) {
      addToast("Error fetching live backend data.", "error");
    }
  };

  // Fetch updated info when changing tabs
  useEffect(() => {
    if (isAuthenticated && !demoMode && token) {
      fetchBackendData(token);
    }
  }, [activeTab, isAuthenticated]);

  const submitFacebookToken = async (userToken) => {
    try {
      let igSuccess = false;
      let fbSuccess = false;

      // Connect Instagram Business Accounts
      try {
        const res = await fetch(`${API_BASE}/auth/facebook-connect`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ access_token: userToken })
        });
        if (res.ok) {
          const data = await res.json();
          setAccounts(data);
          igSuccess = true;
        }
      } catch (err) {
        console.warn("Instagram connection error:", err);
      }

      // Connect Facebook Pages
      try {
        const res = await fetch(`${API_BASE}/auth/facebook-connect-page`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ access_token: userToken })
        });
        if (res.ok) {
          const data = await res.json();
          setFacebookAccounts(data);
          fbSuccess = true;
        }
      } catch (err) {
        console.warn("Facebook Page connection error:", err);
      }

      if (igSuccess || fbSuccess) {
        addToast("Successfully linked your Meta accounts, discovered Pages and Instagram Business channels.", "success");
        fetchBackendData();
      } else {
        addToast("Meta connection failed. Please check tokens and permissions.", "error");
      }
    } catch (err) {
      addToast("Failed to communicate with Meta discovery service.", "error");
    } finally {
      setIsConnectingFB(false);
    }
  };

  // Facebook Connect Handshake
  const handleFacebookConnect = (option = 'default') => {
    setIsConnectingFB(true);

    if (demoMode) {
      // Simulate mock connection
      setTimeout(() => {
        const randId = Math.floor(Math.random() * 900);
        const newAcc = {
          id: Date.now(),
          instagram_business_account_id: "99" + randId,
          username: `brand_growth_${randId}`,
          name: `Brand Growth Inc ${randId}`,
          profile_picture_url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
          page_id: `page_${randId}`,
          page_name: `Brand Growth FB ${randId}`,
          connected_at: new Date().toISOString()
        };
        const newFbAcc = {
          id: Date.now() + 1,
          facebook_page_id: "fb_page_" + randId,
          username: `brand_growth_fb_${randId}`,
          name: `Brand Growth Facebook Page ${randId}`,
          profile_picture_url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
          connected_at: new Date().toISOString()
        };
        setAccounts(prev => [...prev, newAcc]);
        setFacebookAccounts(prev => [...prev, newFbAcc]);
        addToast(`Connected Instagram Business account & Facebook Page: Brand Growth Inc ${randId} (Mock)`, "success");
        setIsConnectingFB(false);
      }, 1000);
      return;
    }

    if (option === 'manual') {
      const enteredToken = prompt(
        "Please enter your Facebook User Access Token manually:"
      );
      if (!enteredToken) {
        setIsConnectingFB(false);
        return;
      }
      submitFacebookToken(enteredToken.trim());
      return;
    }

    // Live Mode: Check if Meta SDK is available
    if (!window.FB) {
      const enteredToken = prompt(
        "Meta JavaScript SDK is not loaded (likely blocked by AdBlocker).\n\nPlease enter your Facebook User Access Token manually:"
      );
      if (!enteredToken) {
        setIsConnectingFB(false);
        return;
      }
      submitFacebookToken(enteredToken.trim());
      return;
    }

    const loginOptions = {
      scope: metaScopes
    };
    if (option === 'reauthenticate') {
      loginOptions.auth_type = 'reauthenticate';
    }

    // Trigger Facebook SDK login
    window.FB.login(function(response) {
      if (response.authResponse) {
        submitFacebookToken(response.authResponse.accessToken);
      } else {
        addToast("Facebook connection cancelled or not fully authorized.", "warning");
        setIsConnectingFB(false);
      }
    }, loginOptions);
  };

  const handleSyncPosts = async () => {
    if (demoMode) {
      if (postsFilterPlatform === 'facebook') {
        setFacebookPosts(MOCK_FACEBOOK_POSTS);
        addToast("Synchronized mock Facebook posts successfully.", "success");
      } else {
        setPosts(MOCK_POSTS);
        addToast("Synchronized mock Instagram posts successfully.", "success");
      }
      return;
    }

    const isFb = postsFilterPlatform === 'facebook';
    const isConnected = isFb ? facebookAccounts.length > 0 : accounts.length > 0;
    if (!isConnected) {
      addToast(`Please connect a ${isFb ? 'Facebook Page' : 'Instagram'} account first.`, "warning");
      return;
    }

    setIsSyncingPosts(true);
    const url = isFb ? `${API_BASE}/posts/facebook/sync` : `${API_BASE}/posts/sync`;
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        if (isFb) {
          setFacebookPosts(data);
        } else {
          setPosts(data);
        }
        addToast(`Synchronized ${isFb ? 'Facebook' : 'Instagram'} posts with Meta successfully.`, "success");
      } else {
        const err = await res.json();
        addToast(err.detail || "Failed to sync posts.", "error");
      }
    } catch (err) {
      addToast("Connection error while syncing posts.", "error");
    } finally {
      setIsSyncingPosts(false);
    }
  };

  const handleOpenNewDmRule = () => {
    setEditingDmRule(null);
    setDmRuleForm({
      instagram_account_id: accounts[0]?.id || '',
      name: 'Draft #1',
      trigger_type: 'exact_keyword',
      keyword: '',
      reply_text: 'Welcome! Click the link below to get started.',
      is_active: true,
      dm_type: 'button_template',
      title: 'Get workout guide',
      subtitle: 'Exclusive link below',
      button_text: 'Shop Now',
      button_url: 'https://fitlife.co/shop',
      image_url: 'https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=500'
    });
    setModalTab('dm_setup');
    setShowDmModal(true);
  };

  const handleOpenEditDmRule = (rule) => {
    setEditingDmRule(rule);
    let parsedReply = {
      text: rule.reply_text,
      dm_type: 'message_template',
      title: '',
      subtitle: '',
      button_text: '',
      button_url: '',
      image_url: ''
    };
    try {
      const stripped = rule.reply_text.trim();
      if (stripped.startsWith('{') && stripped.endsWith('}')) {
        const jsonReply = JSON.parse(stripped);
        parsedReply = {
          text: jsonReply.text || '',
          dm_type: jsonReply.dm_type || 'button_template',
          title: jsonReply.title || '',
          subtitle: jsonReply.subtitle || '',
          button_text: jsonReply.button_text || '',
          button_url: jsonReply.button_url || '',
          image_url: jsonReply.image_url || ''
        };
      }
    } catch (e) {
      // Plain text
    }

    setDmRuleForm({
      instagram_account_id: rule.instagram_account_id,
      name: rule.name,
      trigger_type: rule.trigger_type,
      keyword: rule.keyword || '',
      reply_text: parsedReply.text,
      is_active: rule.is_active,
      dm_type: parsedReply.dm_type,
      title: parsedReply.title,
      subtitle: parsedReply.subtitle,
      button_text: parsedReply.button_text,
      button_url: parsedReply.button_url,
      image_url: parsedReply.image_url
    });
    setModalTab('dm_setup');
    setShowDmModal(true);
  };

  const handleSaveDmRule = async (e) => {
    e.preventDefault();
    if (!dmRuleForm.instagram_account_id || !dmRuleForm.name || !dmRuleForm.reply_text) {
      addToast("Please fill all required fields.", "warning");
      return;
    }
    if ((dmRuleForm.trigger_type === 'exact_keyword' || dmRuleForm.trigger_type === 'contains_keyword') && !dmRuleForm.keyword) {
      setModalTab('trigger_setup');
      addToast("Keyword is required for keyword trigger types. Please configure it in the Trigger Setup tab.", "warning");
      return;
    }

    // Build the serialized reply text
    let replyText = dmRuleForm.reply_text;
    if (dmRuleForm.dm_type === 'button_template') {
      replyText = JSON.stringify({
        text: dmRuleForm.reply_text,
        dm_type: 'button_template',
        title: dmRuleForm.title || dmRuleForm.name,
        subtitle: dmRuleForm.subtitle || '',
        button_text: dmRuleForm.button_text || 'View Link',
        button_url: dmRuleForm.button_url || 'https://google.com',
        image_url: dmRuleForm.image_url || ''
      });
    } else if (dmRuleForm.dm_type === 'image') {
      replyText = JSON.stringify({
        text: dmRuleForm.reply_text,
        dm_type: 'image',
        image_url: dmRuleForm.image_url || ''
      });
    }

    setIsDmsSaving(true);
    if (demoMode) {
      if (editingDmRule) {
        setDmRules(prev => prev.map(r => r.id === editingDmRule.id ? { ...r, ...dmRuleForm, reply_text: replyText } : r));
        addToast("Rule updated successfully (Mock)", "success");
      } else {
        const newRule = {
          ...dmRuleForm,
          reply_text: replyText,
          id: 'dm_rule_' + Date.now(),
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        setDmRules(prev => [...prev, newRule]);
        addToast("Rule created successfully (Mock)", "success");
      }
      setShowDmModal(false);
      setEditingDmRule(null);
      setIsDmsSaving(false);
      return;
    }

    try {
      const isEdit = !!editingDmRule;
      const url = isEdit ? `${API_BASE}/dm-automation/${editingDmRule.id}` : `${API_BASE}/dm-automation`;
      const method = isEdit ? 'PUT' : 'POST';
      
      const payload = {
        instagram_account_id: parseInt(dmRuleForm.instagram_account_id),
        name: dmRuleForm.name,
        trigger_type: dmRuleForm.trigger_type,
        keyword: (dmRuleForm.trigger_type === 'exact_keyword' || dmRuleForm.trigger_type === 'contains_keyword') ? dmRuleForm.keyword : null,
        reply_text: replyText,
        is_active: dmRuleForm.is_active
      };

      const res = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      if (res.ok) {
        const savedRule = await res.json();
        addToast(`Rule ${isEdit ? 'updated' : 'created'} successfully!`, "success");
        setShowDmModal(false);
        setEditingDmRule(null);
        if (isEdit) {
          setDmRules(prev => prev.map(r => r.id === savedRule.id ? savedRule : r));
        } else {
          setDmRules(prev => [...prev, savedRule]);
        }
        fetchBackendData(token);
      } else {
        const err = await res.json();
        addToast(err.detail || "Failed to save rule.", "error");
      }
    } catch (err) {
      addToast("Connection error while saving rule.", "error");
    } finally {
      setIsDmsSaving(false);
    }
  };

  const handleDeleteDmRule = (ruleId) => {
    setDeleteConfirmRuleId(ruleId);
  };

  const handleConfirmDeleteDmRule = async () => {
    const ruleId = deleteConfirmRuleId;
    if (!ruleId) return;

    if (demoMode) {
      setDmRules(prev => prev.filter(r => r.id !== ruleId));
      addToast("Rule deleted successfully (Mock)", "success");
      setDeleteConfirmRuleId(null);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/dm-automation/${ruleId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        addToast("Rule deleted successfully!", "success");
        setDmRules(prev => prev.filter(r => r.id !== ruleId));
        fetchBackendData(token);
      } else {
        const err = await res.json();
        addToast(err.detail || "Failed to delete rule.", "error");
      }
    } catch (err) {
      addToast("Connection error while deleting rule.", "error");
    } finally {
      setDeleteConfirmRuleId(null);
    }
  };

  const handleDeleteFlow = (flowId) => {
    setDeleteConfirmFlowId(flowId);
  };

  const handleConfirmDeleteFlow = async () => {
    const flowId = deleteConfirmFlowId;
    if (!flowId) return;

    if (demoMode) {
      setFlows(prev => prev.filter(f => f.id !== flowId));
      addToast("Flow deleted successfully (Mock)", "success");
      setDeleteConfirmFlowId(null);
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/automation/${flowId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        addToast("Flow deleted successfully!", "success");
        setFlows(prev => prev.filter(f => f.id !== flowId));
        fetchBackendData(token);
      } else {
        const err = await res.json();
        addToast(err.detail || "Failed to delete flow.", "error");
      }
    } catch (err) {
      console.error("Delete flow error:", err);
      addToast("Connection error while deleting flow.", "error");
    } finally {
      setDeleteConfirmFlowId(null);
    }
  };

  const handleToggleDmRuleActive = async (rule) => {
    const updatedStatus = !rule.is_active;
    if (demoMode) {
      setDmRules(prev => prev.map(r => r.id === rule.id ? { ...r, is_active: updatedStatus } : r));
      addToast(`Rule is now ${updatedStatus ? 'active' : 'inactive'} (Mock)`, "success");
      return;
    }

    try {
      const res = await fetch(`${API_BASE}/dm-automation/${rule.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ is_active: updatedStatus })
      });
      if (res.ok) {
        addToast(`Rule is now ${updatedStatus ? 'active' : 'inactive'}!`, "success");
        setDmRules(prev => prev.map(r => r.id === rule.id ? { ...r, is_active: updatedStatus } : r));
        fetchBackendData(token);
      } else {
        addToast("Failed to toggle active state of rule.", "error");
      }
    } catch (err) {
      addToast("Connection error.", "error");
    }
  };

  const handleRunAutomation = async () => {
    if (demoMode) {
      setIsRunningAutomation(true);
      setTimeout(() => {
        const newMockComments = [
          {
            comment_id: "c_pending_1",
            media_id: "media_post_1",
            text: "I want the guide!",
            username: "alex_gym",
            timestamp: new Date().toISOString(),
            status: "processed"
          },
          {
            comment_id: "c_pending_2",
            media_id: "media_post_2",
            text: "Best",
            username: "clara_reads",
            timestamp: new Date().toISOString(),
            status: "processed"
          }
        ];
        
        setComments(prev => [...newMockComments, ...prev]);

        const newMockLogs = [
          { id: Math.random(), flow_id: "flow_1", comment_id: "c_pending_1", action_type: "trigger_match", status: "success", created_at: new Date().toISOString(), details: { matched_keywords: ["guide"] } },
          { id: Math.random(), flow_id: "flow_1", comment_id: "c_pending_1", action_type: "reply_sent", status: "success", created_at: new Date().toISOString(), details: { reply_id: "rep_p1" } },
          { id: Math.random(), flow_id: "flow_1", comment_id: "c_pending_2", action_type: "trigger_match", status: "success", created_at: new Date().toISOString(), details: { matched_keywords: ["Best"] } },
          { id: Math.random(), flow_id: "flow_1", comment_id: "c_pending_2", action_type: "reply_sent", status: "success", created_at: new Date().toISOString(), details: { reply_id: "rep_p2" } }
        ];
        setLogs(prev => [...newMockLogs, ...prev]);

        setAnalytics(prev => ({
          ...prev,
          total_comments: prev.total_comments + 2,
          replies_sent: prev.replies_sent + 2,
          dms_sent: prev.dms_sent + 2,
          keyword_counts: { ...prev.keyword_counts, "guide": (prev.keyword_counts["guide"] || 0) + 1, "Best": (prev.keyword_counts["Best"] || 0) + 1 }
        }));

        setIsRunningAutomation(false);
        addToast("Bulk automation completed! Processed 2 comments across Post and Reel.", "success");
      }, 1500);
      return;
    }

    setIsRunningAutomation(true);
    try {
      const res = await fetch(`${API_BASE}/automation/run`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        addToast(`Automation executed! Processed ${data.processed_count} comment(s).`, "success");
        await fetchBackendData();
      } else {
        const err = await res.json();
        addToast(err.detail || "Automation execution failed.", "error");
      }
    } catch (err) {
      addToast("Failed to connect to automation endpoint.", "error");
    } finally {
      setIsRunningAutomation(false);
    }
  };

  const handleRunSingleFlow = async (flowId) => {
    if (demoMode) {
      setRunningFlowId(flowId);
      setTimeout(() => {
        const targetFlow = flows.find(f => f.id === flowId);
        const keywords = targetFlow?.nodes
          ?.filter(n => n.type === 'trigger')
          ?.flatMap(n => n.config?.keywords || []) || [];

        const newMockComments = [];
        const newMockLogs = [];
        let count = 0;

        if (keywords.includes("guide")) {
          const cid = `c_single_${Date.now()}_1`;
          newMockComments.push({
            comment_id: cid,
            media_id: "media_post_1",
            text: "I want the guide!",
            username: "clara_reads",
            timestamp: new Date().toISOString(),
            status: "processed"
          });
          newMockLogs.push(
            { id: Math.random(), flow_id: flowId, comment_id: cid, action_type: "trigger_match", status: "success", created_at: new Date().toISOString(), details: { matched_keywords: ["guide"] } },
            { id: Math.random(), flow_id: flowId, comment_id: cid, action_type: "reply_sent", status: "success", created_at: new Date().toISOString(), details: { reply_id: `rep_s1_${Date.now()}` } }
          );
          count += 1;
        }

        if (keywords.includes("Best") || keywords.includes("View💯")) {
          const cid = `c_single_${Date.now()}_2`;
          newMockComments.push({
            comment_id: cid,
            media_id: "media_post_2",
            text: "Best",
            username: "alex_gym",
            timestamp: new Date().toISOString(),
            status: "processed"
          });
          newMockLogs.push(
            { id: Math.random(), flow_id: flowId, comment_id: cid, action_type: "trigger_match", status: "success", created_at: new Date().toISOString(), details: { matched_keywords: ["Best"] } },
            { id: Math.random(), flow_id: flowId, comment_id: cid, action_type: "reply_sent", status: "success", created_at: new Date().toISOString(), details: { reply_id: `rep_s2_${Date.now()}` } }
          );
          count += 1;
        }

        if (count > 0) {
          setComments(prev => [...newMockComments, ...prev]);
          setLogs(prev => [...newMockLogs, ...prev]);
          setAnalytics(prev => ({
            ...prev,
            total_comments: prev.total_comments + count,
            replies_sent: prev.replies_sent + count,
            dms_sent: prev.dms_sent + count
          }));
        }

        setRunningFlowId(null);
        addToast(`Flow "${targetFlow?.name || 'Selected'}" executed! Processed ${count} pending comment(s).`, "success");
      }, 1500);
      return;
    }

    setRunningFlowId(flowId);
    try {
      const res = await fetch(`${API_BASE}/automation/${flowId}/run`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        addToast(`Flow executed! Processed ${data.processed_count} comment(s).`, "success");
        await fetchBackendData();
      } else {
        const err = await res.json();
        addToast(err.detail || "Flow execution failed.", "error");
      }
    } catch (err) {
      addToast("Failed to connect to flow automation endpoint.", "error");
    } finally {
      setRunningFlowId(null);
    }
  };

  const handleOpenComments = async (post) => {
    setActiveCommentsPost(post);
    setPostComments([]);
    setIsFetchingComments(true);
    setReplyingToCommentId(null);
    setNewReplyText("");
    setNewCommentText("");
    const isFb = !!post.facebook_account_id;
    const url = isFb 
      ? `${API_BASE}/posts/facebook/${post.id}/comments`
      : `${API_BASE}/posts/${post.id}/comments`;
    try {
      const res = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        setPostComments(await res.json());
      } else {
        addToast("Failed to fetch comments for this post.", "error");
      }
    } catch (err) {
      addToast("Failed to connect to comments service.", "error");
    } finally {
      setIsFetchingComments(false);
    }
  };

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!newCommentText.trim()) return;
    setIsSubmittingComment(true);
    const isFb = !!activeCommentsPost.facebook_account_id;
    const url = isFb
      ? `${API_BASE}/posts/facebook/${activeCommentsPost.id}/comments`
      : `${API_BASE}/posts/${activeCommentsPost.id}/comments`;
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: newCommentText })
      });
      if (res.ok) {
        const createdComment = await res.json();
        setPostComments(prev => [...prev, createdComment]);
        setNewCommentText("");
        addToast(`Comment successfully posted to ${isFb ? 'Facebook' : 'Instagram'}!`, "success");
      } else {
        const err = await res.json();
        addToast(err.detail || "Failed to post comment.", "error");
      }
    } catch (err) {
      addToast("Failed to communicate with API server.", "error");
    } finally {
      setIsSubmittingComment(false);
    }
  };

  const handleAddReply = async (commentId) => {
    if (!newReplyText.trim()) return;
    setIsSubmittingReply(true);
    const isFb = !!activeCommentsPost.facebook_account_id;
    const url = isFb
      ? `${API_BASE}/posts/facebook/${activeCommentsPost.id}/comments/${commentId}/replies`
      : `${API_BASE}/posts/${activeCommentsPost.id}/comments/${commentId}/replies`;
    try {
      const res = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ message: newReplyText })
      });
      if (res.ok) {
        const createdReply = await res.json();
        setPostComments(prev => [...prev, createdReply]);
        setReplyingToCommentId(null);
        setNewReplyText("");
        addToast(`Reply successfully posted to ${isFb ? 'Facebook' : 'Instagram'}!`, "success");
      } else {
        const err = await res.json();
        addToast(err.detail || "Failed to post reply.", "error");
      }
    } catch (err) {
      addToast("Failed to communicate with API server.", "error");
    } finally {
      setIsSubmittingReply(false);
    }
  };

  const handleDeleteComment = async (commentId) => {
    const isFb = !!activeCommentsPost.facebook_account_id;
    const url = isFb
      ? `${API_BASE}/posts/facebook/${activeCommentsPost.id}/comments/${commentId}`
      : `${API_BASE}/posts/${activeCommentsPost.id}/comments/${commentId}`;
    try {
      const res = await fetch(url, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (res.ok) {
        setPostComments(prev => prev.filter(c => c.id !== commentId && c.parent_id !== commentId));
        addToast("Comment successfully deleted!", "success");
      } else {
        const err = await res.json();
        addToast(err.detail || "Failed to delete comment.", "error");
      }
    } catch (err) {
      addToast("Failed to communicate with API server.", "error");
    }
  };

  // Open Visual Flow Builder
  const handleOpenBuilder = (flow) => {
    setSelectedFlow(flow);
    setBuilderNodes(flow.nodes || []);
    setBuilderEdges(flow.edges || []);
    setSelectedNode(flow.nodes[0] || null);
    setActiveTab('builder');
  };

  const handleCreateNewFlow = () => {
    if (accounts.length === 0 && facebookAccounts.length === 0) {
      addToast("Please connect an Instagram or Facebook Account first.", "warning");
      return;
    }
    const timestamp = Date.now();
    const triggerId = "node_trig_" + timestamp;
    const replyId = "node_rep_" + timestamp;
    const dmId = "node_dm_" + timestamp;
    const edgeId1 = "edge_trig_rep_" + timestamp;
    const edgeId2 = "edge_rep_dm_" + timestamp;

    const defaultInstaId = accounts[0]?.id || null;
    const defaultFbId = !defaultInstaId ? (facebookAccounts[0]?.id || null) : null;

    const newFlow = {
      id: "flow_" + timestamp,
      name: "New Comment Flow " + (flows.length + 1),
      is_active: true,
      instagram_account_id: defaultInstaId,
      facebook_account_id: defaultFbId,
      nodes: [
        { id: triggerId, type: "trigger", config: { keywords: ["Guide", "Link"], exact_word: true } },
        { id: replyId, type: "action_reply", config: { message: "Thanks for commenting {{username}}! I just sent the link to your DMs." } },
        { id: dmId, type: "action_dm", config: { message: "Hi {{username}}! Here is your exclusive guide link: https://example.com/guide" } }
      ],
      edges: [
        { id: edgeId1, source_node_id: triggerId, target_node_id: replyId },
        { id: edgeId2, source_node_id: replyId, target_node_id: dmId }
      ]
    };
    
    setFlows(prev => [...prev, newFlow]);
    handleOpenBuilder(newFlow);
  };

  const handleAddNode = (type) => {
    const id = "node_" + Date.now();
    let config = {};
    if (type === 'trigger') config = { keywords: ['newkeyword'], exact_word: true };
    else if (type === 'action_reply') config = { message: 'Write a response message here...' };
    else if (type === 'action_dm') config = { message: 'Write a direct message link...' };
    else if (type === 'action_tag') config = { tag: 'customer_tag' };

    const newNode = { id, type, config };
    setBuilderNodes(prev => [...prev, newNode]);
    
    // Auto-create edge from previously selected node if applicable
    if (selectedNode) {
      const edgeId = "edge_" + Date.now();
      const newEdge = { id: edgeId, source_node_id: selectedNode.id, target_node_id: id };
      setBuilderEdges(prev => [...prev, newEdge]);
    }
    
    setSelectedNode(newNode);
    addToast(`Added ${type.replace('action_', '')} node.`, "info");
  };

  const handleDeleteNode = (nodeId) => {
    setBuilderNodes(prev => prev.filter(n => n.id !== nodeId));
    setBuilderEdges(prev => prev.filter(e => e.source_node_id !== nodeId && e.target_node_id !== nodeId));
    setSelectedNode(null);
  };

  const handleUpdateNodeConfig = (key, val) => {
    setBuilderNodes(prev => prev.map(n => {
      if (n.id === selectedNode.id) {
        return { ...n, config: { ...n.config, [key]: val } };
      }
      return n;
    }));
    // Sync current selection
    setSelectedNode(prev => ({ ...prev, config: { ...prev.config, [key]: val } }));
  };

  const handleSaveFlow = async () => {
    const payload = {
      instagram_account_id: selectedFlow.instagram_account_id,
      facebook_account_id: selectedFlow.facebook_account_id,
      name: selectedFlow.name,
      is_active: selectedFlow.is_active,
      nodes: builderNodes,
      edges: builderEdges
    };

    if (demoMode) {
      setFlows(prev => prev.map(f => {
        if (f.id === selectedFlow.id) {
          return { 
            ...f, 
            name: selectedFlow.name, 
            is_active: selectedFlow.is_active, 
            instagram_account_id: selectedFlow.instagram_account_id,
            facebook_account_id: selectedFlow.facebook_account_id,
            nodes: builderNodes, 
            edges: builderEdges 
          };
        }
        return f;
      }));
      addToast("Flow saved successfully (Local storage).", "success");
      setActiveTab('flows');
    } else {
      try {
        const isNew = selectedFlow.id.startsWith("flow_");
        const url = isNew ? `${API_BASE}/automation` : `${API_BASE}/automation/${selectedFlow.id}`;
        const method = isNew ? 'POST' : 'PUT';

        const res = await fetch(url, {
          method: method,
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify(payload)
        });
        if (res.ok) {
          addToast("Flow synchronized with Meta database successfully.", "success");
          fetchBackendData();
          setActiveTab('flows');
        } else {
          const err = await res.json();
          addToast(err.detail || "Save rejected by server.", "error");
        }
      } catch (err) {
        addToast("Error saving flow settings.", "error");
      }
    }
  };

  // Mocking Live Trigger Simulation (Awesome feature!)
  const handleSimulateWebhook = () => {
    addToast("Simulating webhook comment event...", "info");
    setTimeout(() => {
      const isFb = Math.random() > 0.5;
      const randomUser = isFb 
        ? ["fb_alex", "fb_clara", "fb_sam", "fb_david"][Math.floor(Math.random() * 4)]
        : ["alex_gym", "clara_reads", "sam_fit", "david_tech"][Math.floor(Math.random() * 4)];
      const randomText = ["I need the guide!", "send guide", "is the promo still open?", "what guide?"][Math.floor(Math.random() * 4)];
      
      const newComment = {
        comment_id: (isFb ? "fb_" : "") + "c_sim_" + Date.now(),
        media_id: isFb ? "fb_post_1" : "media_post_1",
        text: randomText,
        username: randomUser,
        timestamp: new Date().toISOString(),
        status: "processed",
        platform: isFb ? "facebook" : "instagram"
      };

      setComments(prev => [newComment, ...prev]);
      
      // Match logs simulation
      const newLogs = [
        { id: Math.random(), flow_id: "flow_1", comment_id: newComment.comment_id, action_type: "trigger_match", status: "success", created_at: new Date().toISOString(), details: { matched_keywords: ["guide"] } },
        { id: Math.random(), flow_id: "flow_1", comment_id: newComment.comment_id, action_type: "reply_sent", status: "success", created_at: new Date().toISOString(), details: { reply_id: "rep_sim" } },
        { id: Math.random(), flow_id: "flow_1", comment_id: newComment.comment_id, action_type: "dm_sent", status: "success", created_at: new Date().toISOString(), details: { message_id: "msg_sim" } }
      ];

      setLogs(prev => [...newLogs, ...prev]);
      
      // Update Analytics
      setAnalytics(prev => ({
        ...prev,
        total_comments: prev.total_comments + 1,
        replies_sent: prev.replies_sent + 1,
        dms_sent: prev.dms_sent + 1,
        keyword_counts: { ...prev.keyword_counts, "guide": (prev.keyword_counts["guide"] || 0) + 1 }
      }));

      addToast(`Webhook triggered ${isFb ? 'Facebook' : 'Instagram'} automation for @${randomUser}! Check Logs.`, "success");
    }, 1200);
  };

  if (!isAuthenticated) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <div className="auth-header">
            <div className="auth-logo">
              <GitFork size={30} />
            </div>
            <h2>CommentPilot</h2>
            <p>Instagram & Facebook Comment Automation Portal</p>
          </div>
          
          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label>Dashboard Email</label>
              <input 
                type="email" 
                className="form-control" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Security Password</label>
              <input 
                type={showPassword ? "text" : "password"} 
                className="form-control" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input 
                  type="checkbox" 
                  id="show-password" 
                  checked={showPassword} 
                  onChange={(e) => setShowPassword(e.target.checked)} 
                  style={{ cursor: 'pointer' }}
                />
                <label htmlFor="show-password" style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', cursor: 'pointer', margin: 0, userSelect: 'none' }}>
                  Show Password
                </label>
              </div>
            </div>
            
            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginBottom: '12px' }}>
              Sign In to Dashboard
            </button>
            
            <button 
              type="button" 
              className="btn btn-secondary" 
              style={{ width: '100%' }}
              onClick={() => {
                setDemoMode(true);
                setIsAuthenticated(true);
                loadDemoData();
                addToast("Launched in interactive offline Demo Mode.", "success");
              }}
            >
              Start in Demo Mode
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      {/* Toast Notification Container */}
      <div style={{ position: 'fixed', bottom: '20px', right: '20px', zIndex: 1000, display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {toasts.map(t => (
          <div key={t.id} className="toast" style={{
            borderLeft: `6px solid ${t.type === 'success' ? 'var(--success)' : t.type === 'warning' ? 'var(--warning)' : t.type === 'error' ? 'var(--error)' : 'var(--primary)'}`
          }}>
            {t.type === 'warning' && <AlertTriangle size={18} className="text-warning" />}
            <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>{t.message}</span>
          </div>
        ))}
      </div>

      {/* Comments & Replies Modal Overlay */}
      {activeCommentsPost && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: 'rgba(0,0,0,0.6)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000,
          backdropFilter: 'blur(4px)'
        }}>
          <div className="card" style={{
            width: '90%',
            maxWidth: '750px',
            maxHeight: '85vh',
            display: 'flex',
            flexDirection: 'column',
            padding: '24px',
            overflow: 'hidden',
            backgroundColor: '#11131c',
            border: '1px solid var(--border-color)',
            boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5), 0 10px 10px -5px rgba(0,0,0,0.4)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-color)', paddingBottom: '16px', marginBottom: '16px' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Comments Thread</h2>
              <button className="btn btn-secondary" style={{ padding: '6px 12px' }} onClick={() => setActiveCommentsPost(null)}>Close</button>
            </div>

            {/* Post Snippet */}
            <div style={{ display: 'flex', gap: '16px', backgroundColor: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '8px', marginBottom: '16px', border: '1px solid rgba(255,255,255,0.05)' }}>
              {activeCommentsPost.media_type === 'VIDEO' ? (
                <video 
                  src={activeCommentsPost.media_url} 
                  poster={activeCommentsPost.thumbnail_url || activeCommentsPost.media_url} 
                  controls 
                  playsInline
                  style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: '4px' }}
                />
              ) : (
                <img src={activeCommentsPost.thumbnail_url || activeCommentsPost.media_url} style={{ width: '60px', height: '60px', objectFit: 'cover', borderRadius: '4px' }} alt="Post preview" />
              )}
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {activeCommentsPost.caption || "No caption"}
                </p>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Posted on {new Date(activeCommentsPost.timestamp).toLocaleDateString()}
                </span>
              </div>
            </div>

            {/* Comments Thread Area */}
            <div style={{ flex: 1, overflowY: 'auto', marginBottom: '20px', display: 'flex', flexDirection: 'column', gap: '16px', paddingRight: '4px' }}>
              {isFetchingComments ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-secondary)' }}>Loading comments...</div>
              ) : postComments.filter(c => !c.parent_id).length === 0 ? (
                <div style={{ textAlign: 'center', padding: '40px 0', color: 'var(--text-muted)' }}>No comments on this post yet.</div>
              ) : (
                postComments.filter(c => !c.parent_id).map(parentComment => {
                  const replies = postComments.filter(r => r.parent_id === parentComment.id);
                  return (
                    <div key={parentComment.id} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {/* Parent Comment */}
                      <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                        <div style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '50%',
                          backgroundColor: 'rgba(99, 102, 241, 0.1)',
                          border: '1px solid rgba(99, 102, 241, 0.2)',
                          display: 'flex',
                          justifyContent: 'center',
                          alignItems: 'center',
                          fontWeight: 600,
                          color: 'var(--primary)',
                          fontSize: '0.8rem'
                        }}>
                          {parentComment.username ? parentComment.username.slice(0, 2).toUpperCase() : 'IG'}
                        </div>
                        <div style={{ flex: 1, backgroundColor: 'rgba(255,255,255,0.03)', padding: '12px', borderRadius: '12px', border: '1px solid rgba(255,255,255,0.04)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                            <strong style={{ fontSize: '0.85rem' }}>@{parentComment.username || 'user'}</strong>
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                              {new Date(parentComment.timestamp).toLocaleString()}
                            </span>
                          </div>
                          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>{parentComment.text}</p>
                          
                          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px', gap: '12px' }}>
                            <button 
                              onClick={() => setReplyingToCommentId(replyingToCommentId === parentComment.id ? null : parentComment.id)}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--primary)',
                                fontSize: '0.75rem',
                                cursor: 'pointer',
                                fontWeight: 500,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                            >
                              Reply
                            </button>
                            <button 
                              onClick={() => handleDeleteComment(parentComment.id)}
                              style={{
                                background: 'none',
                                border: 'none',
                                color: 'var(--error)',
                                fontSize: '0.75rem',
                                cursor: 'pointer',
                                fontWeight: 500,
                                display: 'flex',
                                alignItems: 'center',
                                gap: '4px'
                              }}
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Replies Thread */}
                      {replies.map(reply => (
                        <div key={reply.id} style={{ display: 'flex', gap: '12px', marginLeft: '44px', alignItems: 'flex-start' }}>
                          <div style={{
                            width: '28px',
                            height: '28px',
                            borderRadius: '50%',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            border: '1px solid rgba(16, 185, 129, 0.2)',
                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'center',
                            fontWeight: 600,
                            color: 'var(--success)',
                            fontSize: '0.75rem'
                          }}>
                            {reply.username ? reply.username.slice(0, 2).toUpperCase() : 'IG'}
                          </div>
                          <div style={{ flex: 1, backgroundColor: 'rgba(16, 185, 129, 0.03)', padding: '10px 12px', borderRadius: '12px', border: '1px solid rgba(16, 185, 129, 0.08)' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                <strong style={{ fontSize: '0.8rem' }}>@{reply.username || 'user'}</strong>
                                <span className="badge badge-success" style={{ fontSize: '0.65rem', padding: '2px 6px' }}>Bot Reply</span>
                              </span>
                              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                                {new Date(reply.timestamp).toLocaleString()}
                              </span>
                            </div>
                            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{reply.text}</p>
                            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                              <button 
                                onClick={() => handleDeleteComment(reply.id)}
                                style={{
                                  background: 'none',
                                  border: 'none',
                                  color: 'var(--error)',
                                  fontSize: '0.72rem',
                                  cursor: 'pointer',
                                  fontWeight: 500
                                }}
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        </div>
                      ))}

                      {/* Inline Reply Form */}
                      {replyingToCommentId === parentComment.id && (
                        <div style={{ marginLeft: '44px', display: 'flex', gap: '8px', alignItems: 'center', marginTop: '4px' }}>
                          <input 
                            type="text" 
                            placeholder="Write a reply..."
                            value={newReplyText}
                            onChange={(e) => setNewReplyText(e.target.value)}
                            style={{
                              flex: 1,
                              backgroundColor: 'rgba(255,255,255,0.04)',
                              border: '1px solid var(--border-color)',
                              borderRadius: '8px',
                              padding: '8px 12px',
                              color: 'white',
                              fontSize: '0.8rem'
                            }}
                          />
                          <button 
                            onClick={() => handleAddReply(parentComment.id)}
                            className="btn btn-primary" 
                            style={{ padding: '8px 12px', fontSize: '0.75rem' }}
                            disabled={isSubmittingReply}
                          >
                            {isSubmittingReply ? "..." : "Send"}
                          </button>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>

            {/* Add Top-level Comment Form */}
            <form onSubmit={handleAddComment} style={{ borderTop: '1px solid var(--border-color)', paddingTop: '16px', display: 'flex', gap: '12px' }}>
              <input 
                type="text" 
                placeholder="Write a public comment..."
                value={newCommentText}
                onChange={(e) => setNewCommentText(e.target.value)}
                style={{
                  flex: 1,
                  backgroundColor: 'rgba(255,255,255,0.04)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  color: 'white',
                  fontSize: '0.88rem'
                }}
              />
              <button 
                type="submit" 
                className="btn btn-primary" 
                style={{ padding: '10px 20px' }}
                disabled={isSubmittingComment}
              >
                {isSubmittingComment ? "Posting..." : "Post Comment"}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Sidebar navigation */}
      <div className="sidebar">
        <div className="logo-section">
          <div className="logo-icon">
            <GitFork size={20} />
          </div>
          <span className="logo-text">CommentPilot</span>
        </div>

        <div className="sidebar-nav">
          <div className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <LayoutDashboard size={18} /> Dashboard
          </div>
          <div className={`nav-item ${activeTab === 'accounts' ? 'active' : ''}`} onClick={() => setActiveTab('accounts')}>
            <UserCheck size={18} /> Linked Accounts
          </div>
          <div className={`nav-item ${activeTab === 'posts' ? 'active' : ''}`} onClick={() => setActiveTab('posts')}>
            <FileText size={18} /> Media & Feed
          </div>
          <div className={`nav-item ${activeTab === 'flows' ? 'active' : ''}`} onClick={() => setActiveTab('flows')}>
            <GitFork size={18} /> Automation Flows
          </div>
          <div className={`nav-item ${activeTab === 'comments' ? 'active' : ''}`} onClick={() => setActiveTab('comments')}>
            <MessageSquare size={18} /> Comment Ingestion
          </div>
          <div className={`nav-item ${activeTab === 'dms' ? 'active' : ''}`} onClick={() => setActiveTab('dms')}>
            <MessageCircle size={18} /> Personal DMs
          </div>
          <div className={`nav-item ${activeTab === 'logs' ? 'active' : ''}`} onClick={() => setActiveTab('logs')}>
            <History size={18} /> Execution Logs
          </div>
        </div>

        <div className="sidebar-footer">
          {demoMode && (
            <div style={{
              backgroundColor: 'rgba(245, 158, 11, 0.08)',
              border: '1px solid rgba(245, 158, 11, 0.2)',
              borderRadius: '6px',
              padding: '10px',
              marginBottom: '16px',
              fontSize: '0.78rem',
              color: 'var(--warning)',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}>
              <AlertTriangle size={14} /> Running in Demo Mode
            </div>
          )}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="user-badge">
              <div className="user-avatar">
                <User size={16} />
              </div>
              <div className="user-info">
                <span className="user-name">{demoMode ? 'Local Demo Admin' : 'Active Operator'}</span>
                <span className="user-role">{demoMode ? 'Sandbox Environment' : email}</span>
              </div>
            </div>
            
            <button 
              onClick={handleLogout} 
              className="btn btn-secondary" 
              style={{ 
                width: '100%', 
                padding: '8px 12px', 
                fontSize: '0.85rem', 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'center', 
                gap: '8px',
                border: '1px solid rgba(239, 68, 68, 0.2)',
                color: 'var(--error)',
                backgroundColor: 'rgba(239, 68, 68, 0.05)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
                e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.4)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.05)';
                e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.2)';
              }}
            >
              <LogOut size={14} /> Log Out
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="main-content">
        
        {/* Tab 1: Dashboard */}
        {activeTab === 'dashboard' && (
          <div>
            <div className="page-header">
              <div className="header-title">
                <h1>Engagement Analytics</h1>
                <p>Real-time campaign conversion rates and keyword statistics.</p>
              </div>
              <div className="header-actions" style={{ display: 'flex', gap: '12px' }}>
                <button 
                  className={`btn btn-primary ${isRunningAutomation ? 'btn-disabled' : ''}`}
                  onClick={handleRunAutomation}
                  disabled={isRunningAutomation}
                >
                  <Zap size={16} /> {isRunningAutomation ? "Running..." : "Run Automation"}
                </button>
                <button className="btn btn-accent" onClick={handleSimulateWebhook}>
                  <Play size={16} /> Mock Webhook Event
                </button>
              </div>
            </div>

            <div className="stats-grid">
              <div className="card stat-card">
                <div className="stat-header">
                  <span>Total Ingested</span>
                  <MessageSquare size={20} className="text-secondary" />
                </div>
                <span className="stat-value">{analytics.total_comments}</span>
                <span className="stat-label">Comments logged by Meta webhooks</span>
              </div>
              <div className="card stat-card">
                <div className="stat-header">
                  <span>Public Replies</span>
                  <CheckCircle2 size={20} style={{ color: 'var(--primary)' }} />
                </div>
                <span className="stat-value">{analytics.replies_sent}</span>
                <span className="stat-label">Comment response threads created</span>
              </div>
              <div className="card stat-card">
                <div className="stat-header">
                  <span>Private DMs Sent</span>
                  <CheckCircle2 size={20} style={{ color: 'var(--success)' }} />
                </div>
                <span className="stat-value">{analytics.dms_sent}</span>
                <span className="stat-label">Direct message links delivered</span>
              </div>
              <div className="card stat-card">
                <div className="stat-header">
                  <span>Response Time</span>
                  <Clock size={20} style={{ color: 'var(--warning)' }} />
                </div>
                <span className="stat-value">{analytics.avg_response_time_seconds}s</span>
                <span className="stat-label">Average latency to reply</span>
              </div>
            </div>

            <div className="content-grid">
              <div className="card">
                <div className="section-title">
                  <TrendingUp size={20} style={{ color: 'var(--accent)' }} /> Keyword Performance metrics
                </div>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Keyword Trigger</th>
                        <th>Matches Logged</th>
                        <th>Status</th>
                        <th>Conversion Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.keys(analytics.keyword_counts).length === 0 ? (
                        <tr>
                          <td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No matches recorded yet. Run a webhook simulation!</td>
                        </tr>
                      ) : (
                        Object.entries(analytics.keyword_counts).map(([kw, count]) => (
                          <tr key={kw}>
                            <td><span className="keyword-tag">{kw}</span></td>
                            <td><strong>{count}</strong></td>
                            <td><span className="badge badge-success">active</span></td>
                            <td>100.0%</td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              <div className="card">
                <div className="section-title">
                  <Activity size={20} style={{ color: 'var(--primary)' }} /> System Overview
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.88rem' }}>
                      <span>Celery Task Dispatch Success</span>
                      <span>100%</span>
                    </div>
                    <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '3px' }}>
                      <div style={{ width: '100%', height: '100%', backgroundColor: 'var(--success)', borderRadius: '3px' }} />
                    </div>
                  </div>
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.88rem' }}>
                      <span>API Rate Limit Consumption</span>
                      <span>2%</span>
                    </div>
                    <div style={{ width: '100%', height: '6px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '3px' }}>
                      <div style={{ width: '2%', height: '100%', backgroundColor: 'var(--primary)', borderRadius: '3px' }} />
                    </div>
                  </div>
                  <div style={{ borderTop: '1px solid var(--border-color)', paddingTop: '20px', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    <p style={{ marginBottom: '8px' }}>• Webhook Endpoints verified</p>
                    <p>• Redis connection stable</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Linked Accounts */}
        {activeTab === 'accounts' && (
          <div>
            <div className="page-header">
              <div className="header-title">
                <h1>Meta Connected Accounts</h1>
                <p>Manage authorization tokens, Facebook Pages and Instagram channels.</p>
              </div>
              <div className="header-actions">
                <button 
                  className={`btn btn-primary ${isConnectingFB ? 'btn-disabled' : ''}`} 
                  onClick={() => setShowConnectModal(true)}
                  disabled={isConnectingFB}
                >
                  <Link2 size={16} /> {isConnectingFB ? "Connecting..." : "Add Meta Account"}
                </button>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>
              {/* Instagram Section */}
              <div>
                <h2 className="section-title" style={{ fontSize: '1.1rem', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="badge badge-success" style={{ padding: '4px 8px' }}>Instagram</span> Business Channels
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {accounts.length === 0 ? (
                    <div className="card" style={{ padding: '24px', color: 'var(--text-secondary)', textAlign: 'center' }}>
                      No connected Instagram Business Accounts.
                    </div>
                  ) : (
                    accounts.map(acc => (
                      <div key={acc.id} className="card account-list-card" style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '16px' }}>
                        <img src={acc.profile_picture_url || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80'} className="account-avatar" alt="Avatar" style={{ width: '48px', height: '48px', borderRadius: '50%' }} />
                        <div className="account-details" style={{ flex: 1 }}>
                          <h3 style={{ margin: '0 0 4px 0' }}>{acc.name}</h3>
                          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>@{acc.username} • Linked to FB Page: {acc.page_name || 'Associated Page'}</p>
                        </div>
                        <div>
                          <span className="badge badge-success">Instagram Connected</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Facebook Section */}
              <div>
                <h2 className="section-title" style={{ fontSize: '1.1rem', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="badge badge-primary" style={{ padding: '4px 8px' }}>Facebook</span> Page Integrations
                </h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                  {facebookAccounts.length === 0 ? (
                    <div className="card" style={{ padding: '24px', color: 'var(--text-secondary)', textAlign: 'center' }}>
                      No connected Facebook Pages.
                    </div>
                  ) : (
                    facebookAccounts.map(acc => (
                      <div key={acc.id} className="card account-list-card" style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '16px' }}>
                        <img src={acc.profile_picture_url || 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=150&auto=format&fit=crop&q=80'} className="account-avatar" alt="Avatar" style={{ width: '48px', height: '48px', borderRadius: '50%' }} />
                        <div className="account-details" style={{ flex: 1 }}>
                          <h3 style={{ margin: '0 0 4px 0' }}>{acc.name}</h3>
                          <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Page ID: {acc.facebook_page_id} {acc.username ? `• @${acc.username}` : ''}</p>
                        </div>
                        <div>
                          <span className="badge badge-primary">Facebook Connected</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Connect Meta Account Modal */}
            {showConnectModal && (
              <div className="modal-overlay" style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.75)',
                backdropFilter: 'blur(8px)',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                zIndex: 2000,
                padding: '20px'
              }}>
                <div className="card" style={{
                  width: '100%',
                  maxWidth: '520px',
                  backgroundColor: '#111827',
                  border: '1px solid var(--border-color)',
                  borderRadius: '20px',
                  boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
                  position: 'relative',
                  padding: '24px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '20px'
                }}>
                  <button 
                    onClick={() => setShowConnectModal(false)}
                    style={{
                      position: 'absolute',
                      top: '20px',
                      right: '20px',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      fontSize: '1.5rem',
                      cursor: 'pointer',
                      transition: 'color 0.2s',
                      zIndex: 10
                    }}
                    onMouseEnter={(e) => e.target.style.color = 'white'}
                    onMouseLeave={(e) => e.target.style.color = 'var(--text-muted)'}
                  >
                    &times;
                  </button>

                  <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                    <h2 style={{ margin: 0, fontSize: '1.3rem', color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ color: 'var(--primary)' }}>🔗</span> Connect Meta Account
                    </h2>
                    <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
                      Choose your connection method to link Pages or Instagram Channels.
                    </p>
                  </div>

                  <div style={{
                    backgroundColor: 'rgba(59, 130, 246, 0.08)',
                    border: '1px solid rgba(59, 130, 246, 0.2)',
                    borderRadius: '10px',
                    padding: '12px',
                    fontSize: '0.82rem',
                    color: 'var(--text-secondary)',
                    lineHeight: '1.4'
                  }}>
                    <strong style={{ color: 'white', display: 'block', marginBottom: '4px' }}>💡 Browser Session Isolation</strong>
                    Facebook's JavaScript SDK binds to your active browser cookies. To connect a <strong>completely different</strong> account, you must first click the <strong>Log Out</strong> button below to clear the active profile session.
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                    <button
                      onClick={() => {
                        setShowConnectModal(false);
                        handleFacebookConnect('default');
                      }}
                      style={{
                        padding: '14px',
                        borderRadius: '12px',
                        backgroundColor: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        color: 'white',
                        textAlign: 'left',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(99, 102, 241, 0.08)';
                        e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.3)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.03)';
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                      }}
                    >
                      <strong style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        ⚡ Link Active Session
                      </strong>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        Quick connect using the Facebook profile currently active in your browser.
                      </span>
                    </button>

                    <button
                      onClick={() => {
                        setShowConnectModal(false);
                        handleFacebookConnect('reauthenticate');
                      }}
                      style={{
                        padding: '14px',
                        borderRadius: '12px',
                        backgroundColor: 'rgba(255, 255, 255, 0.03)',
                        border: '1px solid rgba(255, 255, 255, 0.08)',
                        color: 'white',
                        textAlign: 'left',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(16, 185, 129, 0.08)';
                        e.currentTarget.style.borderColor = 'rgba(16, 185, 129, 0.3)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.03)';
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.08)';
                      }}
                    >
                      <strong style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        ➕ Confirm Password / Re-authenticate
                      </strong>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        Forces a password entry prompt to verify or refresh permissions for the current active account.
                      </span>
                    </button>

                    <button
                      onClick={() => {
                        if (demoMode) {
                          addToast("Mock Facebook Log Out triggered.", "success");
                          setShowConnectModal(false);
                          return;
                        }
                        if (!window.FB) {
                          addToast("Meta SDK not loaded. Cannot trigger Facebook log out.", "warning");
                          return;
                        }
                        window.FB.logout(function(response) {
                          addToast("Logged out of Facebook browser session successfully. You can now connect a new account.", "success");
                        });
                        setShowConnectModal(false);
                      }}
                      style={{
                        padding: '14px',
                        borderRadius: '12px',
                        backgroundColor: 'rgba(239, 68, 68, 0.05)',
                        border: '1px solid rgba(239, 68, 68, 0.2)',
                        color: 'var(--error)',
                        textAlign: 'left',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.15)';
                        e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.4)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(239, 68, 68, 0.05)';
                        e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.2)';
                      }}
                    >
                      <strong style={{ fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        🔴 Log Out of Facebook Browser Session
                      </strong>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                        Clears your browser session. Use this if you want to switch and connect a different Facebook profile.
                      </span>
                    </button>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', borderTop: '1px solid var(--border-color)', paddingTop: '12px' }}>
                    <button className="btn btn-secondary" style={{ padding: '8px 16px' }} onClick={() => setShowConnectModal(false)}>
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 3: Media & Feed */}
        {activeTab === 'posts' && (
          <div>
            <div className="page-header">
              <div className="header-title">
                <h1>Cached Media Feed</h1>
                <p>Visual log of media synchronized from Meta APIs.</p>
              </div>
              <div className="header-actions">
                <button 
                  className={`btn btn-primary ${isSyncingPosts ? 'btn-disabled' : ''}`}
                  onClick={handleSyncPosts}
                  disabled={isSyncingPosts}
                >
                  <Activity size={16} /> {isSyncingPosts ? "Syncing..." : "Sync Feed"}
                </button>
              </div>
            </div>

            {/* Platform Selector */}
            <div style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
              <button 
                onClick={() => { setPostsFilterPlatform('instagram'); setPostsFilter('all'); }}
                className={`btn ${postsFilterPlatform === 'instagram' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
              >
                Instagram Accounts
              </button>
              <button 
                onClick={() => { setPostsFilterPlatform('facebook'); setPostsFilter('all'); }}
                className={`btn ${postsFilterPlatform === 'facebook' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
              >
                Facebook Pages
              </button>
            </div>

            {/* Media Type Filters */}
            {((postsFilterPlatform === 'instagram' ? posts.length : facebookPosts.length) > 0) && (
              <div style={{ display: 'flex', gap: '10px', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                <button 
                  onClick={() => setPostsFilter('all')}
                  className={`btn ${postsFilter === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                >
                  All Media ({postsFilterPlatform === 'instagram' ? posts.length : facebookPosts.length})
                </button>
                <button 
                  onClick={() => setPostsFilter('reels')}
                  className={`btn ${postsFilter === 'reels' ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                >
                  Reels / Videos ({postsFilterPlatform === 'instagram' ? posts.filter(p => p.media_type === 'VIDEO').length : facebookPosts.filter(p => p.media_type === 'VIDEO' || p.media_type === 'video').length})
                </button>
              </div>
            )}

            {/* Posts Grid */}
            {(postsFilterPlatform === 'instagram' ? posts : facebookPosts).length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-secondary)' }}>
                <p>No cached posts found. Link a {postsFilterPlatform === 'instagram' ? 'Instagram' : 'Facebook'} account and sync.</p>
              </div>
            ) : (postsFilterPlatform === 'instagram' ? posts : facebookPosts).filter(post => {
              const isVideo = post.media_type === 'VIDEO' || post.media_type === 'video';
              if (postsFilter === 'posts') return !isVideo;
              if (postsFilter === 'reels') return isVideo;
              return true;
            }).length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-secondary)' }}>
                <p>No media matching the selected filter.</p>
              </div>
            ) : (
              <div className="posts-grid">
                {(postsFilterPlatform === 'instagram' ? posts : facebookPosts)
                  .filter(post => {
                    const isVideo = post.media_type === 'VIDEO' || post.media_type === 'video';
                    if (postsFilter === 'posts') return !isVideo;
                    if (postsFilter === 'reels') return isVideo;
                    return true;
                  })
                  .map(post => {
                    const isVideo = post.media_type === 'VIDEO' || post.media_type === 'video';
                    return (
                      <div key={post.id} className="card post-card">
                        <div className="post-media-container" style={{ position: 'relative' }}>
                          {isVideo ? (
                            <video 
                              src={post.media_url} 
                              poster={post.thumbnail_url || post.media_url} 
                              controls 
                              playsInline
                              preload="metadata"
                              className="post-img"
                              style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                            />
                          ) : post.media_url ? (
                            <img 
                              src={post.media_url} 
                              className="post-img" 
                              alt="Media Feed" 
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                          ) : (
                            <div className="post-no-media" style={{ 
                              width: '100%', 
                              height: '200px', 
                              display: 'flex', 
                              alignItems: 'center', 
                              justifyContent: 'center', 
                              background: 'var(--card-bg-hover, #2a2b36)',
                              color: 'var(--text-secondary)',
                              fontSize: '0.85rem',
                              borderBottom: '1px solid var(--border-color)'
                            }}>
                              No Media Content
                            </div>
                          )}
                          {isVideo && (
                            <div style={{
                              position: 'absolute',
                              top: '10px',
                              right: '10px',
                              backgroundColor: 'rgba(0,0,0,0.7)',
                              color: 'white',
                              padding: '4px 8px',
                              borderRadius: '4px',
                              fontSize: '0.7rem',
                              fontWeight: 'bold',
                              letterSpacing: '0.05em'
                            }}>
                              VIDEO/REEL
                            </div>
                          )}
                        </div>
                        <div className="post-info">
                          <p className="post-caption">{post.caption || "No caption"}</p>
                          <div className="post-meta" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '10px' }}>
                            <span>{new Date(post.timestamp).toLocaleDateString()}</span>
                            <div style={{ display: 'flex', gap: '8px' }}>
                              <button onClick={() => handleOpenComments(post)} className="btn btn-primary" style={{ padding: '4px 10px', fontSize: '0.75rem' }}>
                                View Comments
                              </button>
                              <a href={post.permalink} target="_blank" rel="noopener noreferrer" className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '0.75rem' }}>Open Url</a>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
              </div>
            )}
          </div>
        )}

        {/* Tab 4: Flow List */}
        {activeTab === 'flows' && (
          <div>
            <div className="page-header">
              <div className="header-title">
                <h1>Automation Flows</h1>
                <p>Design triggers and response chains for comments and DMs.</p>
              </div>
              <div className="header-actions" style={{ display: 'flex', gap: '12px' }}>
                <button 
                  className="btn btn-secondary"
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                  onClick={() => setIsGuideOpen(true)}
                >
                  <Info size={16} /> User Guide
                </button>
                <button 
                  className={`btn btn-accent ${isRunningAutomation ? 'btn-disabled' : ''}`}
                  onClick={handleRunAutomation}
                  disabled={isRunningAutomation}
                >
                  <Zap size={16} /> {isRunningAutomation ? "Running..." : "Run Automation"}
                </button>
                <button className="btn btn-primary" onClick={handleCreateNewFlow}>
                  <Plus size={16} /> Create Automation Flow
                </button>
              </div>
            </div>

            <div className="flow-list">
              {flows.length === 0 ? (
                <div className="card" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-secondary)' }}>
                  <p>No automation flows created yet. Get started by creating your first flow.</p>
                </div>
              ) : (
                flows.map(flow => {
                  const matchedInsta = accounts.find(a => a.id === flow.instagram_account_id);
                  const matchedFb = facebookAccounts.find(a => a.id === flow.facebook_account_id);
                  const platformName = flow.facebook_account_id ? "Facebook" : "Instagram";
                  const accountName = matchedFb ? matchedFb.name : matchedInsta ? `@${matchedInsta.username}` : "Unlinked";
                  return (
                    <div key={flow.id} className="card flow-item">
                      <div className="flow-meta">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                          <h3 style={{ margin: 0 }}>{flow.name}</h3>
                          <span className={`badge ${flow.facebook_account_id ? 'badge-primary' : 'badge-success'}`} style={{ fontSize: '0.68rem', padding: '2px 8px' }}>
                            {platformName} ({accountName})
                          </span>
                        </div>
                        <p>
                          Triggers on keywords:{' '}
                          {flow.nodes
                            .filter(n => n.type === 'trigger')
                            .flatMap(n => n.config?.keywords || [])
                            .map(kw => (
                              <span key={kw} className="keyword-tag">{kw}</span>
                            ))}
                        </p>
                      </div>
                      <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                        <button 
                          className={`btn btn-accent ${runningFlowId === flow.id ? 'btn-disabled' : ''}`}
                          onClick={() => handleRunSingleFlow(flow.id)}
                          disabled={runningFlowId !== null}
                          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                        >
                          <Play size={14} /> 
                          {runningFlowId === flow.id ? "Running..." : "Run Flow"}
                        </button>
                        <button className="btn btn-secondary" onClick={() => handleOpenBuilder(flow)}>Edit Visual Flow</button>
                        <button className="btn btn-danger" style={{ padding: '10px' }} onClick={() => handleDeleteFlow(flow.id)}><Trash2 size={16} /></button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        )}

        {/* Tab 5: Comment Ingestion */}
        {activeTab === 'comments' && (
          <div>
            <div className="page-header">
              <div className="header-title">
                <h1>Comment Ingestion Log</h1>
                <p>Real-time feed of comment webhooks parsed from the platform's channels.</p>
              </div>
            </div>

            <div className="card">
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Comment ID</th>
                      <th>Commenter</th>
                      <th>Content</th>
                      <th>Timestamp</th>
                      <th>Ingestion Status</th>
                      <th>Automation Action / Response</th>
                    </tr>
                  </thead>
                  <tbody>
                    {comments.map(c => {
                      const relatedLogs = logs.filter(l => l.comment_id === c.comment_id);
                      const replyLog = relatedLogs.find(l => l.action_type === 'reply_sent');
                      const dmLog = relatedLogs.find(l => l.action_type === 'dm_sent');
                      const tagLog = relatedLogs.find(l => l.action_type === 'tag_added');

                      return (
                        <tr key={c.comment_id}>
                          <td><code>{c.comment_id}</code></td>
                          <td>
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                              <strong>@{c.username}</strong>
                              <span className={`badge ${c.platform === 'facebook' ? 'badge-primary' : 'badge-success'}`} style={{ alignSelf: 'flex-start', fontSize: '0.65rem', padding: '1px 6px', marginTop: '4px' }}>
                                {c.platform === 'facebook' ? 'Facebook' : 'Instagram'}
                              </span>
                            </div>
                          </td>
                          <td>"{c.text}"</td>
                          <td>{new Date(c.timestamp).toLocaleString()}</td>
                          <td>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              <span className={`badge ${c.status === 'processed' ? 'badge-success' : c.status === 'ignored' ? 'badge-warning' : 'badge-error'}`} style={{ alignSelf: 'flex-start' }}>
                                {c.status}
                              </span>
                              {c.error_message && (
                                <span style={{ fontSize: '0.75rem', color: 'var(--error)', marginTop: '2px' }}>
                                  {c.error_message}
                                </span>
                              )}
                            </div>
                          </td>
                          <td>
                            <div style={{ fontSize: '0.8rem', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              {replyLog && (
                                <span style={{ color: 'var(--text-secondary)' }}>
                                  💬 Reply: <strong style={{ color: 'white' }}>"{replyLog.details?.text}"</strong> 
                                  {replyLog.status === 'success' ? ' (Sent)' : ' (Failed)'}
                                </span>
                              )}
                              {dmLog && (
                                <span style={{ color: 'var(--text-secondary)' }}>
                                  ✉️ DM: <strong style={{ color: 'white' }}>{renderDmText(dmLog.details?.text)}</strong>
                                  {dmLog.status === 'success' ? ' (Sent)' : ' (Failed)'}
                                </span>
                              )}
                              {tagLog && (
                                <span style={{ color: 'var(--text-muted)' }}>
                                  🏷️ Tagged: <span className="keyword-tag">{tagLog.details?.tag}</span>
                                </span>
                              )}
                              {!replyLog && !dmLog && !tagLog && (
                                <span style={{ color: 'var(--text-muted)' }}>None</span>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Tab 6: Execution Logs */}
        {activeTab === 'logs' && (
          <div>
            <div className="page-header">
              <div className="header-title">
                <h1>Automation Engine Execution Logs</h1>
                <p>Auditable trail of keyword triggers, public replies, DMs and tags.</p>
              </div>
            </div>

            <div className="card">
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Comment ID</th>
                      <th>Action Executed</th>
                      <th>Status</th>
                      <th>Parameters / Response</th>
                    </tr>
                  </thead>
                  <tbody>
                    {logs.map(log => (
                      <tr key={log.id}>
                        <td>{new Date(log.created_at || Date.now()).toLocaleString()}</td>
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <code>{log.comment_id}</code>
                            {(() => {
                              const matchedFlow = flows.find(f => f.id === log.flow_id);
                              const isFb = matchedFlow ? !!matchedFlow.facebook_account_id : log.comment_id?.startsWith('fb_');
                              return (
                                <span className={`badge ${isFb ? 'badge-primary' : 'badge-success'}`} style={{ alignSelf: 'flex-start', fontSize: '0.65rem', padding: '1px 6px', marginTop: '4px' }}>
                                  {isFb ? 'Facebook' : 'Instagram'}
                                </span>
                              );
                            })()}
                          </div>
                        </td>
                        <td>
                          <strong style={{ color: 'var(--primary)', fontSize: '0.85rem', textTransform: 'uppercase' }}>
                            {log.action_type}
                          </strong>
                        </td>
                        <td>
                          <span className={`badge ${log.status === 'success' ? 'badge-success' : 'badge-error'}`}>
                            {log.status}
                          </span>
                        </td>
                        <td>
                          {log.action_type === 'reply_sent' && (
                            <div>
                              <p style={{ margin: 0, color: 'white' }}>💬 <strong>Reply:</strong> "{log.details?.text}"</p>
                              {log.details?.reply_id && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>ID: {log.details?.reply_id}</span>}
                              {log.details?.error && <p style={{ margin: '4px 0 0 0', color: 'var(--error)', fontSize: '0.75rem' }}>Error: {log.details?.error}</p>}
                            </div>
                          )}
                          {log.action_type === 'dm_sent' && (
                            <div>
                              <p style={{ margin: 0, color: 'white' }}>✉️ <strong>DM:</strong> {renderDmText(log.details?.text)}</p>
                              {log.details?.message_id && <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>ID: {log.details?.message_id}</span>}
                              {log.details?.error && <p style={{ margin: '4px 0 0 0', color: 'var(--error)', fontSize: '0.75rem' }}>Error: {log.details?.error}</p>}
                            </div>
                          )}
                          {log.action_type === 'tag_added' && (
                            <div>
                              <p style={{ margin: 0 }}>🏷️ Added Tag: <span className="keyword-tag">{log.details?.tag}</span></p>
                            </div>
                          )}
                          {log.action_type === 'trigger_match' && (
                            <div>
                              <p style={{ margin: 0 }}>🎯 Matched text: <strong>"{log.details?.comment_text}"</strong></p>
                              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Keywords: {log.details?.matched_keywords?.join(', ')}</span>
                            </div>
                          )}
                          {log.action_type === 'condition_check' && (
                            <div>
                              <p style={{ margin: 0 }}>⚙️ Checked field: <strong>{log.details?.field}</strong> ({log.details?.operator})</p>
                              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Expected: {log.details?.expected} | Matched: {log.details?.matched ? 'Yes' : 'No'}</span>
                            </div>
                          )}
                          {log.action_type !== 'reply_sent' && log.action_type !== 'dm_sent' && log.action_type !== 'tag_added' && log.action_type !== 'trigger_match' && log.action_type !== 'condition_check' && (
                            <pre style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', fontFamily: 'monospace', margin: 0 }}>
                              {JSON.stringify(log.details)}
                            </pre>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'dms' && (
          <div>
            <div className="page-header">
              <div className="header-title">
                <h1>Personal DM Automation</h1>
                <p>Automate replies to direct messages sent by users to your connected Instagram Business accounts.</p>
              </div>
              <div className="header-actions">
                <button className="btn btn-primary" onClick={handleOpenNewDmRule}>
                  <Plus size={16} /> Create DM Automation
                </button>
              </div>
            </div>

            {/* Sub-tab selection header */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '20px', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
              <button 
                className={`btn ${dmSubTab === 'rules' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                onClick={() => setDmSubTab('rules')}
              >
                Rules & Triggers
              </button>
              <button 
                className={`btn ${dmSubTab === 'messages' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                onClick={() => setDmSubTab('messages')}
              >
                Message History ({dmMessages.length})
              </button>
              <button 
                className={`btn ${dmSubTab === 'conversations' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                onClick={() => setDmSubTab('conversations')}
              >
                Active Conversations ({dmConversations.length})
              </button>
              <button 
                className={`btn ${dmSubTab === 'executions' ? 'btn-primary' : 'btn-secondary'}`}
                style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                onClick={() => setDmSubTab('executions')}
              >
                Rule Executions ({dmExecutions.length})
              </button>
            </div>

            {/* Rules list sub-tab */}
            {dmSubTab === 'rules' && (
              <div className="flow-list">
                {dmRules.length === 0 ? (
                  <div className="card" style={{ textAlign: 'center', padding: '48px', color: 'var(--text-secondary)' }}>
                    <p>No Personal DM automation rules created yet. Get started by creating your first rule.</p>
                  </div>
                ) : (
                  dmRules.map(rule => {
                    const matchedInsta = accounts.find(a => a.id === rule.instagram_account_id);
                    const accountName = matchedInsta ? `@${matchedInsta.username}` : "Unlinked";
                    
                    let replyDisplay = rule.reply_text;
                    let isJsonTemplate = false;
                    let templateType = '';
                    try {
                      const stripped = rule.reply_text.trim();
                      if (stripped.startsWith('{') && stripped.endsWith('}')) {
                        const jsonReply = JSON.parse(stripped);
                        replyDisplay = jsonReply.text || jsonReply.reply_text || '';
                        isJsonTemplate = true;
                        templateType = jsonReply.dm_type || 'button_template';
                      }
                    } catch (e) {
                      // Plain text
                    }

                    return (
                      <div key={rule.id} className="card flow-item">
                        <div className="flow-meta">
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                            <h3 style={{ margin: 0 }}>{rule.name}</h3>
                            <span className="badge badge-success" style={{ fontSize: '0.68rem', padding: '2px 8px' }}>
                              Instagram ({accountName})
                            </span>
                            <span className={`badge ${rule.is_active ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.68rem', padding: '2px 8px' }}>
                              {rule.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </div>
                          <p style={{ margin: '8px 0', fontSize: '0.9rem' }}>
                            <strong>Trigger type:</strong> <span style={{ textTransform: 'capitalize', color: 'var(--primary-color)' }}>{rule.trigger_type.replace('_', ' ')}</span>
                            {rule.keyword && (
                              <>
                                {' | '}<strong>Keyword:</strong> <span className="keyword-tag">{rule.keyword}</span>
                              </>
                            )}
                          </p>
                          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.85rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '600px' }}>
                            <strong>Reply with:</strong> {isJsonTemplate ? (
                              <span className="badge" style={{ fontSize: '0.65rem', padding: '2px 6px', marginRight: '6px', textTransform: 'capitalize', backgroundColor: 'var(--primary)', color: 'white', display: 'inline-block', borderRadius: '4px', verticalAlign: 'middle' }}>
                                📋 {templateType.replace('_', ' ')}
                              </span>
                            ) : null} <span style={{ verticalAlign: 'middle' }}>"{replyDisplay}"</span>
                          </p>
                        </div>
                        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                          <button 
                            className={`btn ${rule.is_active ? 'btn-secondary' : 'btn-accent'}`}
                            onClick={() => handleToggleDmRuleActive(rule)}
                            style={{ padding: '8px 16px', fontSize: '0.85rem' }}
                          >
                            {rule.is_active ? "Deactivate" : "Activate"}
                          </button>
                          <button 
                            className="btn btn-secondary" 
                            onClick={() => handleOpenEditDmRule(rule)}
                            style={{ display: 'flex', alignItems: 'center', gap: '4px', padding: '8px 12px' }}
                          >
                            <Edit size={14} /> Edit
                          </button>
                          <button 
                            className="btn btn-danger" 
                            style={{ padding: '8px 10px' }} 
                            onClick={() => handleDeleteDmRule(rule.id)}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* Message log sub-tab */}
            {dmSubTab === 'messages' && (
              <div className="card">
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Message ID</th>
                        <th>Account</th>
                        <th>Sender</th>
                        <th>Content</th>
                        <th>Timestamp</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dmMessages.length === 0 ? (
                        <tr>
                          <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No messages logged yet.</td>
                        </tr>
                      ) : (
                        dmMessages.map(msg => {
                          const matchedInsta = accounts.find(a => a.id === msg.instagram_account_id);
                          const accountName = matchedInsta ? `@${matchedInsta.username}` : "Unlinked";
                          return (
                            <tr key={msg.id}>
                              <td><code>{msg.id.substring(0, 12)}...</code></td>
                              <td><span className="badge badge-success">{accountName}</span></td>
                              <td><strong>@{msg.sender_id}</strong></td>
                              <td>"{msg.text}"</td>
                              <td>{new Date(msg.timestamp).toLocaleString()}</td>
                              <td>
                                <div style={{ display: 'flex', flexDirection: 'column' }}>
                                  <span className={`badge ${msg.status === 'processed' ? 'badge-success' : msg.status === 'ignored' ? 'badge-warning' : 'badge-error'}`} style={{ alignSelf: 'flex-start' }}>
                                    {msg.status}
                                  </span>
                                  {msg.error_message && (
                                    <span style={{ fontSize: '0.72rem', color: 'var(--error)', marginTop: '2px' }}>
                                      {msg.error_message}
                                    </span>
                                  )}
                                </div>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Conversation sub-tab */}
            {dmSubTab === 'conversations' && (
              <div className="card">
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Conversation ID</th>
                        <th>Account</th>
                        <th>Participant</th>
                        <th>Last Active</th>
                        <th>Started At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dmConversations.length === 0 ? (
                        <tr>
                          <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No active conversations discovered yet.</td>
                        </tr>
                      ) : (
                        dmConversations.map(conv => {
                          const matchedInsta = accounts.find(a => a.id === conv.instagram_account_id);
                          const accountName = matchedInsta ? `@${matchedInsta.username}` : "Unlinked";
                          return (
                            <tr key={conv.id}>
                              <td><code>{conv.id}</code></td>
                              <td><span className="badge badge-success">{accountName}</span></td>
                              <td><strong>@{conv.participant_id}</strong></td>
                              <td>{new Date(conv.last_message_at).toLocaleString()}</td>
                              <td>{new Date(conv.created_at).toLocaleString()}</td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Executions sub-tab */}
            {dmSubTab === 'executions' && (
              <div className="card">
                <div className="table-container">
                  <table>
                    <thead>
                      <tr>
                        <th>Execution ID</th>
                        <th>Matched Automation Rule</th>
                        <th>Trigger Message ID</th>
                        <th>Status</th>
                        <th>Executed At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dmExecutions.length === 0 ? (
                        <tr>
                          <td colSpan={5} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No rule executions recorded yet.</td>
                        </tr>
                      ) : (
                        dmExecutions.map(ex => {
                          const matchedRule = dmRules.find(r => r.id === ex.automation_id);
                          const ruleName = matchedRule ? matchedRule.name : `Rule (${ex.automation_id})`;
                          return (
                            <tr key={ex.id}>
                              <td><code>{ex.id}</code></td>
                              <td><strong>{ruleName}</strong></td>
                              <td><code>{ex.message_id.substring(0, 12)}...</code></td>
                              <td>
                                <div style={{ display: 'flex', flexDirection: 'column' }}>
                                  <span className={`badge ${ex.status === 'success' ? 'badge-success' : 'badge-error'}`} style={{ alignSelf: 'flex-start' }}>
                                    {ex.status}
                                  </span>
                                  {ex.error_message && (
                                    <span style={{ fontSize: '0.72rem', color: 'var(--error)', marginTop: '2px' }}>
                                      {ex.error_message}
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td>{new Date(ex.executed_at).toLocaleString()}</td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* DM Rule Edit Modal Overlay */}
            {showDmModal && (
              <div className="modal-overlay" style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.75)',
                backdropFilter: 'blur(8px)',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                zIndex: 2000,
                padding: '20px'
              }}>
                <div className="card" style={{
                  width: '100%',
                  maxWidth: '950px',
                  maxHeight: '95vh',
                  overflowY: 'auto',
                  backgroundColor: '#111827',
                  border: '1px solid var(--border-color)',
                  borderRadius: '20px',
                  boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
                  position: 'relative',
                  padding: '24px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '16px'
                }}>
                  {/* Close button */}
                  <button 
                    onClick={() => { setShowDmModal(false); setEditingDmRule(null); }}
                    style={{
                      position: 'absolute',
                      top: '20px',
                      right: '20px',
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      fontSize: '1.5rem',
                      cursor: 'pointer',
                      transition: 'color 0.2s',
                      zIndex: 10
                    }}
                    onMouseEnter={(e) => e.target.style.color = 'white'}
                    onMouseLeave={(e) => e.target.style.color = 'var(--text-muted)'}
                  >
                    &times;
                  </button>

                  {/* Header Title */}
                  <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                    <h2 style={{ margin: 0, fontSize: '1.4rem', color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ color: 'var(--primary)' }}>⚡</span> {editingDmRule ? "Edit Draft & Automation" : "Create Draft"}
                    </h2>
                    <p style={{ margin: '4px 0 0 0', color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
                      Build your automated reply flow template and match it with triggers.
                    </p>
                  </div>

                  {/* Two-Column Body Content */}
                  <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
                    
                    {/* Left Column: Form Settings (Tabs) */}
                    <div style={{ flex: '1 1 500px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      
                      {/* Tabs Navigation Header */}
                      <div style={{
                        display: 'flex',
                        borderBottom: '1px solid var(--border-color)',
                        gap: '4px',
                        paddingBottom: '2px'
                      }}>
                        <button
                          type="button"
                          onClick={() => setModalTab('dm_setup')}
                          style={{
                            padding: '8px 16px',
                            background: 'none',
                            border: 'none',
                            color: modalTab === 'dm_setup' ? 'var(--primary)' : 'var(--text-secondary)',
                            borderBottom: modalTab === 'dm_setup' ? '2px solid var(--primary)' : '2px solid transparent',
                            fontWeight: '600',
                            fontSize: '0.85rem',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                          }}
                        >
                          ✉️ DM Setup
                        </button>
                        <button
                          type="button"
                          onClick={() => setModalTab('trigger_setup')}
                          style={{
                            padding: '8px 16px',
                            background: 'none',
                            border: 'none',
                            color: modalTab === 'trigger_setup' ? 'var(--primary)' : 'var(--text-secondary)',
                            borderBottom: modalTab === 'trigger_setup' ? '2px solid var(--primary)' : '2px solid transparent',
                            fontWeight: '600',
                            fontSize: '0.85rem',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                          }}
                        >
                          ⚙️ Trigger Setup
                        </button>
                        <button
                          type="button"
                          onClick={() => setModalTab('settings')}
                          style={{
                            padding: '8px 16px',
                            background: 'none',
                            border: 'none',
                            color: modalTab === 'settings' ? 'var(--primary)' : 'var(--text-secondary)',
                            borderBottom: modalTab === 'settings' ? '2px solid var(--primary)' : '2px solid transparent',
                            fontWeight: '600',
                            fontSize: '0.85rem',
                            cursor: 'pointer',
                            transition: 'all 0.2s'
                          }}
                        >
                          ⚙️ Settings
                        </button>
                      </div>

                      {/* Tab Body Contents */}
                      <div style={{ minHeight: '340px' }}>
                        
                        {/* TAB 1: DM SETUP */}
                        {modalTab === 'dm_setup' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                            <div style={{ display: 'flex', gap: '12px' }}>
                              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Draft Name</label>
                                <input 
                                  type="text" 
                                  className="form-control"
                                  value={dmRuleForm.name}
                                  onChange={(e) => setDmRuleForm(prev => ({ ...prev, name: e.target.value }))}
                                  required
                                />
                              </div>
                              <div style={{ width: '180px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>DM Type</label>
                                <select 
                                  className="form-control"
                                  value={dmRuleForm.dm_type}
                                  onChange={(e) => setDmRuleForm(prev => ({ ...prev, dm_type: e.target.value }))}
                                >
                                  <option value="button_template">Button Template</option>
                                  <option value="message_template">Message Template</option>
                                  <option value="image">Image Only</option>
                                </select>
                              </div>
                            </div>

                            {/* Carousel slides simulated selector */}
                            {dmRuleForm.dm_type === 'button_template' && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Carousel Slides</label>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                  <button type="button" className="btn btn-primary" style={{ padding: '4px 12px', fontSize: '0.75rem' }}>1</button>
                                  <button type="button" className="btn btn-secondary" style={{ padding: '4px 12px', fontSize: '0.75rem' }}>+ Slide</button>
                                </div>
                              </div>
                            )}

                            {/* Image slot configuration */}
                            {(dmRuleForm.dm_type === 'button_template' || dmRuleForm.dm_type === 'image') && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Image URL</label>
                                <input 
                                  type="text" 
                                  className="form-control"
                                  placeholder="Paste an Unsplash image URL or host link..."
                                  value={dmRuleForm.image_url}
                                  onChange={(e) => setDmRuleForm(prev => ({ ...prev, image_url: e.target.value }))}
                                />
                                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginTop: '2px' }}>
                                  <button 
                                    type="button" 
                                    onClick={() => setDmRuleForm(prev => ({ ...prev, image_url: 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=500' }))}
                                    style={{ fontSize: '0.7rem', padding: '3px 8px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'var(--text-secondary)', cursor: 'pointer' }}
                                  >
                                    🐶 Cute Dog
                                  </button>
                                  <button 
                                    type="button" 
                                    onClick={() => setDmRuleForm(prev => ({ ...prev, image_url: 'https://images.unsplash.com/photo-1522071820081-009f0129c71c?w=500' }))}
                                    style={{ fontSize: '0.7rem', padding: '3px 8px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'var(--text-secondary)', cursor: 'pointer' }}
                                  >
                                    💻 Developer Code
                                  </button>
                                  <button 
                                    type="button" 
                                    onClick={() => setDmRuleForm(prev => ({ ...prev, image_url: 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=500' }))}
                                    style={{ fontSize: '0.7rem', padding: '3px 8px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.05)', border: '1px solid var(--border-color)', color: 'var(--text-secondary)', cursor: 'pointer' }}
                                  >
                                    🥗 Fit Life Meal
                                  </button>
                                </div>
                              </div>
                            )}

                            {/* Card title & subtitle configuration */}
                            {dmRuleForm.dm_type === 'button_template' && (
                              <div style={{ display: 'flex', gap: '12px' }}>
                                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Card Title</label>
                                  <input 
                                    type="text" 
                                    className="form-control"
                                    placeholder="e.g. Free Workout Guide"
                                    value={dmRuleForm.title}
                                    onChange={(e) => setDmRuleForm(prev => ({ ...prev, title: e.target.value }))}
                                  />
                                </div>
                                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                  <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Card Subtitle</label>
                                  <input 
                                    type="text" 
                                    className="form-control"
                                    placeholder="e.g. Get fit in 30 days"
                                    value={dmRuleForm.subtitle}
                                    onChange={(e) => setDmRuleForm(prev => ({ ...prev, subtitle: e.target.value }))}
                                  />
                                </div>
                              </div>
                            )}

                            {/* Core description/message content */}
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                              <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                {dmRuleForm.dm_type === 'button_template' ? 'Card Description / Text Reply' : 'Automated Message Body *'}
                              </label>
                              <textarea 
                                className="form-control"
                                rows="3"
                                placeholder="Type the automated response message..."
                                required
                                value={dmRuleForm.reply_text}
                                onChange={(e) => setDmRuleForm(prev => ({ ...prev, reply_text: e.target.value }))}
                                style={{ resize: 'vertical' }}
                              />
                            </div>

                            {/* Button actions builder */}
                            {dmRuleForm.dm_type === 'button_template' && (
                              <div style={{ border: '1px solid var(--border-color)', borderRadius: '8px', padding: '12px', backgroundColor: 'rgba(0,0,0,0.2)' }}>
                                <div style={{ fontSize: '0.78rem', color: 'white', fontWeight: 'bold', marginBottom: '8px' }}>🔗 Button Destination</div>
                                <div style={{ display: 'flex', gap: '12px' }}>
                                  <div style={{ flex: '1', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Button Text</label>
                                    <input 
                                      type="text" 
                                      className="form-control"
                                      value={dmRuleForm.button_text}
                                      onChange={(e) => setDmRuleForm(prev => ({ ...prev, button_text: e.target.value }))}
                                    />
                                  </div>
                                  <div style={{ flex: '2', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                    <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>Destination URL</label>
                                    <div style={{ display: 'flex', gap: '6px' }}>
                                      <input 
                                        type="text" 
                                        className="form-control"
                                        value={dmRuleForm.button_url}
                                        onChange={(e) => setDmRuleForm(prev => ({ ...prev, button_url: e.target.value }))}
                                      />
                                      <button type="button" className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>Add URL</button>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            )}

                          </div>
                        )}

                        {/* TAB 2: TRIGGER SETUP */}
                        {modalTab === 'trigger_setup' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Instagram Account *</label>
                              <select 
                                className="form-control"
                                required
                                value={dmRuleForm.instagram_account_id}
                                onChange={(e) => setDmRuleForm(prev => ({ ...prev, instagram_account_id: e.target.value }))}
                              >
                                {accounts.length === 0 ? (
                                  <option value="">No linked Instagram accounts</option>
                                ) : (
                                  accounts.map(acc => (
                                    <option key={acc.id} value={acc.id}>@{acc.username} ({acc.name})</option>
                                  ))
                                )}
                              </select>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Trigger Type *</label>
                              <select 
                                className="form-control"
                                required
                                value={dmRuleForm.trigger_type}
                                onChange={(e) => setDmRuleForm(prev => ({ ...prev, trigger_type: e.target.value }))}
                              >
                                <option value="exact_keyword">Exact Keyword Match</option>
                                <option value="contains_keyword">Contains Keyword Match</option>
                                <option value="first_message">First Message Ever Received</option>
                                <option value="any_message">Any Message / Default Response</option>
                              </select>
                            </div>

                            {(dmRuleForm.trigger_type === 'exact_keyword' || dmRuleForm.trigger_type === 'contains_keyword') && (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                                <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Keyword *</label>
                                <input 
                                  type="text" 
                                  className="form-control"
                                  placeholder="e.g. guide"
                                  required
                                  value={dmRuleForm.keyword}
                                  onChange={(e) => setDmRuleForm(prev => ({ ...prev, keyword: e.target.value }))}
                                />
                              </div>
                            )}
                          </div>
                        )}

                        {/* TAB 3: SETTINGS */}
                        {modalTab === 'settings' && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '16px', border: '1px solid var(--border-color)', borderRadius: '8px', backgroundColor: 'rgba(255,255,255,0.02)' }}>
                              <input 
                                type="checkbox" 
                                id="dm_is_active"
                                checked={dmRuleForm.is_active}
                                onChange={(e) => setDmRuleForm(prev => ({ ...prev, is_active: e.target.checked }))}
                                style={{ width: '18px', height: '18px', cursor: 'pointer' }}
                              />
                              <div style={{ display: 'flex', flexDirection: 'column' }}>
                                <label htmlFor="dm_is_active" style={{ fontSize: '0.88rem', color: 'white', fontWeight: 'bold', cursor: 'pointer', margin: 0 }}>
                                  Keep Rule Active
                                </label>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Enable or disable this automation flow instantly.</span>
                              </div>
                            </div>
                          </div>
                        )}

                      </div>

                      {/* Modal Footer Controls */}
                      <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', borderTop: '1px solid var(--border-color)', paddingTop: '16px', marginTop: 'auto' }}>
                        <button 
                          type="button" 
                          className="btn btn-secondary" 
                          onClick={() => { setShowDmModal(false); setEditingDmRule(null); }}
                        >
                          Cancel
                        </button>
                        <button 
                          onClick={handleSaveDmRule}
                          type="submit" 
                          className={`btn btn-primary ${isDmsSaving ? 'btn-disabled' : ''}`}
                          disabled={isDmsSaving}
                        >
                          {isDmsSaving ? "Saving..." : (editingDmRule ? "Update Draft" : "Save Draft")}
                        </button>
                      </div>

                    </div>

                    {/* Right Column: Live Device Mockup Preview */}
                    <div style={{
                      flex: '0 0 320px',
                      display: 'flex',
                      justifyContent: 'center',
                      alignItems: 'center',
                      paddingLeft: '24px',
                      borderLeft: '1px solid var(--border-color)'
                    }}>
                      
                      {/* Phone container */}
                      <div style={{
                        width: '280px',
                        height: '520px',
                        borderRadius: '36px',
                        border: '12px solid #1f2937',
                        backgroundColor: '#030712',
                        position: 'relative',
                        boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
                        overflow: 'hidden',
                        display: 'flex',
                        flexDirection: 'column'
                      }}>
                        
                        {/* Status bar / Notch */}
                        <div style={{
                          width: '110px',
                          height: '18px',
                          backgroundColor: '#1f2937',
                          borderBottomLeftRadius: '12px',
                          borderBottomRightRadius: '12px',
                          position: 'absolute',
                          top: 0,
                          left: '50%',
                          transform: 'translateX(-50%)',
                          zIndex: 10
                        }} />

                        {/* Instagram DM Header */}
                        <div style={{
                          height: '56px',
                          borderBottom: '1px solid #1f2937',
                          display: 'flex',
                          alignItems: 'center',
                          padding: '16px 12px 0 12px',
                          gap: '8px',
                          backgroundColor: '#090d16'
                        }}>
                          <div style={{ fontSize: '0.8rem', color: '#9ca3af', cursor: 'pointer' }}>❮</div>
                          <div style={{
                            width: '28px',
                            height: '28px',
                            borderRadius: '50%',
                            backgroundColor: 'var(--primary)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '0.65rem',
                            color: 'white',
                            fontWeight: 'bold'
                          }}>
                            ig
                          </div>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ fontSize: '0.72rem', fontWeight: 'bold', color: 'white' }}>instagram_page</span>
                            <span style={{ fontSize: '0.6rem', color: '#6b7280' }}>Active now</span>
                          </div>
                        </div>

                        {/* Message Panel Area */}
                        <div style={{
                          flex: 1,
                          padding: '12px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '12px',
                          overflowY: 'auto',
                          backgroundColor: '#030712'
                        }}>
                          {/* Simulated user trigger message */}
                          {(dmRuleForm.trigger_type === 'exact_keyword' || dmRuleForm.trigger_type === 'contains_keyword') && (
                            <div style={{
                              alignSelf: 'flex-start',
                              backgroundColor: '#1f2937',
                              color: 'white',
                              borderRadius: '14px',
                              padding: '8px 12px',
                              fontSize: '0.72rem',
                              maxWidth: '80%',
                              wordBreak: 'break-word'
                            }}>
                              {dmRuleForm.keyword || 'keyword'}
                            </div>
                          )}

                          {/* Outgoing automated response preview */}
                          <div style={{ alignSelf: 'flex-end', maxWidth: '85%' }}>
                            {dmRuleForm.dm_type === 'button_template' ? (
                              /* Rich Template Response */
                              <div style={{
                                width: '200px',
                                backgroundColor: '#1f2937',
                                borderRadius: '14px',
                                overflow: 'hidden',
                                border: '1px solid #374151',
                                display: 'flex',
                                flexDirection: 'column'
                              }}>
                                {/* Card image */}
                                <div style={{
                                  height: '110px',
                                  backgroundColor: '#374151',
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  overflow: 'hidden',
                                  position: 'relative'
                                }}>
                                  {dmRuleForm.image_url ? (
                                    <img 
                                      src={dmRuleForm.image_url} 
                                      alt="Preview" 
                                      style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    />
                                  ) : (
                                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px', color: '#9ca3af' }}>
                                      <span style={{ fontSize: '1.4rem' }}>☁️</span>
                                      <span style={{ fontSize: '0.62rem' }}>Drop Image Here</span>
                                    </div>
                                  )}
                                </div>

                                {/* Title, Subtitle and Description */}
                                <div style={{ padding: '8px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                  <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'white', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {dmRuleForm.title || "Card Title"}
                                  </div>
                                  <div style={{ fontSize: '0.62rem', color: '#9ca3af', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                    {dmRuleForm.subtitle || "Card Subtitle"}
                                  </div>
                                  <div style={{ fontSize: '0.65rem', color: '#d1d5db', marginTop: '4px', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                    {dmRuleForm.reply_text || "Welcome! Click the link below."}
                                  </div>
                                </div>

                                {/* Destination button link */}
                                <div style={{
                                  borderTop: '1px solid #374151',
                                  padding: '8px 0',
                                  color: '#3b82f6',
                                  fontSize: '0.72rem',
                                  fontWeight: 'bold',
                                  textAlign: 'center',
                                  backgroundColor: 'rgba(0,0,0,0.1)',
                                  cursor: 'pointer'
                                }}>
                                  {dmRuleForm.button_text || "Shop Now"}
                                </div>
                                <div style={{
                                  borderTop: '1px dashed #4b5563',
                                  padding: '6px 0',
                                  color: '#6b7280',
                                  fontSize: '0.62rem',
                                  textAlign: 'center',
                                  backgroundColor: 'rgba(0,0,0,0.05)'
                                }}>
                                  + Add Button
                                </div>
                              </div>
                            ) : dmRuleForm.dm_type === 'image' ? (
                              /* Image Only Response */
                              <div style={{
                                width: '180px',
                                borderRadius: '14px',
                                overflow: 'hidden',
                                border: '1px solid #374151',
                                display: 'flex',
                                flexDirection: 'column'
                              }}>
                                <img 
                                  src={dmRuleForm.image_url || 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=500'} 
                                  alt="Preview" 
                                  style={{ width: '100%', height: 'auto', maxHeight: '180px', objectFit: 'cover' }}
                                />
                                {dmRuleForm.reply_text && (
                                  <div style={{ padding: '6px 10px', fontSize: '0.72rem', color: 'white', backgroundColor: '#3b82f6' }}>
                                    {dmRuleForm.reply_text}
                                  </div>
                                )}
                              </div>
                            ) : (
                              /* Plain Text Message Response */
                              <div style={{
                                backgroundColor: '#3b82f6',
                                color: 'white',
                                borderRadius: '14px',
                                padding: '8px 12px',
                                fontSize: '0.72rem',
                                wordBreak: 'break-word'
                              }}>
                                {dmRuleForm.reply_text || "Welcome!"}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Input Footer */}
                        <div style={{
                          height: '48px',
                          borderTop: '1px solid #1f2937',
                          padding: '8px 12px',
                          display: 'flex',
                          alignItems: 'center',
                          backgroundColor: '#090d16'
                        }}>
                          <div style={{
                            flex: 1,
                            backgroundColor: '#1f2937',
                            borderRadius: '18px',
                            padding: '6px 12px',
                            color: '#6b7280',
                            fontSize: '0.68rem',
                            border: '1px solid #374151'
                          }}>
                            Message...
                          </div>
                        </div>

                      </div>

                    </div>

                  </div>
                </div>
              </div>
            )}

            {deleteConfirmRuleId && (
              <div className="modal-overlay" style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.8)',
                backdropFilter: 'blur(10px)',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                zIndex: 3000,
                padding: '20px'
              }}>
                <div className="card" style={{
                  width: '100%',
                  maxWidth: '420px',
                  backgroundColor: '#111827',
                  border: '1px solid var(--border-color)',
                  borderRadius: '16px',
                  boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
                  padding: '24px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  textAlign: 'center',
                  gap: '16px'
                }}>
                  <div style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '50%',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    border: '1px solid rgba(239, 68, 68, 0.2)',
                    color: '#ef4444',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '1.8rem',
                    fontWeight: 'bold',
                    marginBottom: '8px'
                  }}>
                    ⚠️
                  </div>

                  <h3 style={{ margin: 0, fontSize: '1.25rem', color: 'white', fontWeight: 'bold' }}>Delete Automation Rule</h3>
                  <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: '1.5' }}>
                    Are you sure you want to delete this DM automation rule? This action cannot be undone and will stop this automation instantly.
                  </p>

                  <div style={{ display: 'flex', gap: '12px', width: '100%', marginTop: '8px' }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      style={{ flex: 1, padding: '10px 16px', fontSize: '0.9rem', justifyContent: 'center' }}
                      onClick={() => setDeleteConfirmRuleId(null)}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger"
                      style={{ flex: 1, padding: '10px 16px', fontSize: '0.9rem', justifyContent: 'center', backgroundColor: '#ef4444', border: 'none', color: 'white' }}
                      onClick={handleConfirmDeleteDmRule}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            )}

          </div>
        )}


        {/* Tab 7: Visual Flow Builder (Canvas) */}
        {activeTab === 'builder' && selectedFlow && (
          <div>
            <div className="page-header">
              <div className="header-title">
                <h1>Flow Editor: {selectedFlow.name}</h1>
                <p>Manage automation node graph connections and keyword replies.</p>
              </div>
              <div className="header-actions">
                <button className="btn btn-secondary" onClick={() => setActiveTab('flows')}>Cancel</button>
                <button className="btn btn-primary" onClick={handleSaveFlow}><Save size={16} /> Sync Flow</button>
              </div>
            </div>

            <div className="builder-layout">
              {/* Node Graph Canvas Area */}
              <div className="canvas-area">
                <div className="canvas-nodes-container">
                  {builderNodes.map((node, index) => {
                    const isSelected = selectedNode?.id === node.id;
                    return (
                      <div 
                        key={node.id} 
                        className={`node-card ${isSelected ? 'selected' : ''} ${
                          node.type === 'trigger' ? 'trigger-node' :
                          node.type === 'action_reply' ? 'reply-node' :
                          node.type === 'action_dm' ? 'dm-node' : 'tag-node'
                        }`}
                        onClick={() => setSelectedNode(node)}
                      >
                        <div className="node-header">
                          {node.type === 'trigger' ? '🔑 Keyword Trigger' :
                           node.type === 'action_reply' ? '💬 Public Reply' :
                           node.type === 'action_dm' ? '✉️ Private DM' : '🏷️ Customer Tag'}
                        </div>
                        <div className="node-body">
                          {node.type === 'trigger' && (
                            <div>
                              <span>Triggers on:</span>
                              <div>
                                {node.config.keywords?.map(kw => (
                                  <span key={kw} className="keyword-tag">{kw}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {node.type === 'action_reply' && (
                            <p style={{ fontStyle: 'italic' }}>"{node.config.message}"</p>
                          )}
                          {node.type === 'action_dm' && (
                            <p style={{ fontStyle: 'italic' }}>"{node.config.message}"</p>
                          )}
                          {node.type === 'action_tag' && (
                            <p>Apply Tag: <strong style={{ color: 'var(--warning)' }}>#{node.config.tag}</strong></p>
                          )}
                        </div>

                        {index < builderNodes.length - 1 && (
                          <div className="node-handle-out" />
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Sidebar Settings Editor */}
              <div className="builder-sidebar">
                <h3 style={{ marginBottom: '16px', fontSize: '1.05rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                  Flow Settings
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '24px', paddingBottom: '20px', borderBottom: '1px solid var(--border-color)' }}>
                  <div className="form-group">
                    <label>Flow Name</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      value={selectedFlow.name} 
                      onChange={(e) => setSelectedFlow(prev => ({ ...prev, name: e.target.value }))}
                    />
                  </div>
                  <div className="form-group">
                    <label>Target Platform / Account</label>
                    <select
                      className="form-control"
                      value={selectedFlow.facebook_account_id ? `fb_${selectedFlow.facebook_account_id}` : selectedFlow.instagram_account_id ? `ig_${selectedFlow.instagram_account_id}` : ""}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val.startsWith('fb_')) {
                          const fbId = val.replace('fb_', '');
                          setSelectedFlow(prev => ({
                            ...prev,
                            facebook_account_id: isNaN(fbId) ? fbId : parseInt(fbId),
                            instagram_account_id: null
                          }));
                        } else if (val.startsWith('ig_')) {
                          const igId = val.replace('ig_', '');
                          setSelectedFlow(prev => ({
                            ...prev,
                            instagram_account_id: isNaN(igId) ? igId : parseInt(igId),
                            facebook_account_id: null
                          }));
                        }
                      }}
                      style={{ backgroundColor: 'rgba(255,255,255,0.05)', color: 'white', border: '1px solid var(--border-color)', borderRadius: '6px', padding: '8px', width: '100%', fontSize: '0.85rem' }}
                    >
                      <option value="" disabled>-- Select Platform / Account --</option>
                      {accounts.map(acc => (
                        <option key={`ig_${acc.id}`} value={`ig_${acc.id}`} style={{ backgroundColor: '#111827' }}>
                          Instagram: @{acc.username}
                        </option>
                      ))}
                      {facebookAccounts.map(acc => (
                        <option key={`fb_${acc.id}`} value={`fb_${acc.id}`} style={{ backgroundColor: '#111827' }}>
                          Facebook Page: {acc.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <input 
                      type="checkbox" 
                      id="flow-active-toggle"
                      checked={selectedFlow.is_active} 
                      onChange={(e) => setSelectedFlow(prev => ({ ...prev, is_active: e.target.checked }))}
                    />
                    <label htmlFor="flow-active-toggle" style={{ margin: 0, cursor: 'pointer' }}>Active Status</label>
                  </div>
                </div>

                <h3 style={{ marginBottom: '16px', fontSize: '1.05rem', borderBottom: '1px solid var(--border-color)', paddingBottom: '12px' }}>
                  Node Settings
                </h3>

                {selectedNode ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', flexGrow: 1 }}>
                    <div className="form-group">
                      <label>Node ID</label>
                      <input type="text" className="form-control" value={selectedNode.id} disabled />
                    </div>

                    {selectedNode.type === 'trigger' && (
                      <div>
                        <div className="form-group">
                          <label>Trigger Keywords (comma separated)</label>
                          <input 
                            type="text" 
                            className="form-control" 
                            value={selectedNode.config.keywords?.join(', ')} 
                            onChange={(e) => handleUpdateNodeConfig('keywords', e.target.value.split(',').map(s => s.trim()))}
                          />
                        </div>
                        <div className="form-group" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <input 
                            type="checkbox" 
                            checked={selectedNode.config.exact_word} 
                            onChange={(e) => handleUpdateNodeConfig('exact_word', e.target.checked)}
                          />
                          <label style={{ margin: 0 }}>Exact Word Boundary Match</label>
                        </div>
                      </div>
                    )}

                    {selectedNode.type === 'action_reply' && (
                      <div className="form-group">
                        <label>Message Content (supports `{"{{username}}"}`)</label>
                        <textarea 
                          className="form-control" 
                          rows="4" 
                          value={selectedNode.config.message} 
                          onChange={(e) => handleUpdateNodeConfig('message', e.target.value)}
                        />
                      </div>
                    )}

                    {selectedNode.type === 'action_dm' && (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        <div className="form-group">
                          <label>Link with Personal DM Draft / Template</label>
                          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                            <select
                              className="form-control"
                              style={{ flex: 1 }}
                              value={selectedNode.config.dm_automation_id || 'custom'}
                              onChange={(e) => {
                                const val = e.target.value;
                                if (val === 'custom') {
                                  handleUpdateNodeConfig('dm_automation_id', '');
                                  handleUpdateNodeConfig('message', 'Write a direct message link...');
                                } else {
                                  const matchedRule = dmRules.find(r => r.id.toString() === val.toString());
                                  if (matchedRule) {
                                    handleUpdateNodeConfig('dm_automation_id', matchedRule.id);
                                    handleUpdateNodeConfig('message', matchedRule.reply_text);
                                  }
                                }
                              }}
                            >
                              <option value="custom">Custom Message (Plain Text)</option>
                              {dmRules.map(rule => (
                                <option key={rule.id} value={rule.id}>
                                  {rule.name} ({rule.trigger_type.replace('_', ' ')})
                                </option>
                              ))}
                            </select>
                            {selectedNode.config.dm_automation_id && selectedNode.config.dm_automation_id !== 'custom' && (
                              <button 
                                className="btn btn-secondary btn-sm"
                                type="button"
                                style={{ height: '38px', padding: '0 12px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px', whiteSpace: 'nowrap' }}
                                onClick={() => {
                                  const matchedRule = dmRules.find(r => r.id.toString() === selectedNode.config.dm_automation_id.toString());
                                  if (matchedRule) {
                                    setPreviewDmRule(matchedRule);
                                  }
                                }}
                              >
                                👁️ Preview
                              </button>
                            )}
                          </div>
                        </div>

                        {(!selectedNode.config.dm_automation_id || selectedNode.config.dm_automation_id === 'custom') ? (
                          <div className="form-group">
                            <label>Message Content (supports `{"{{username}}"}`)</label>
                            <textarea 
                              className="form-control" 
                              rows="4" 
                              value={selectedNode.config.message} 
                              onChange={(e) => handleUpdateNodeConfig('message', e.target.value)}
                            />
                          </div>
                        ) : (
                          <div style={{ padding: '12px', backgroundColor: 'rgba(255,255,255,0.05)', borderRadius: '6px', border: '1px solid var(--border-color)' }}>
                            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '4px', fontWeight: 'bold' }}>Linked Template Details</div>
                            {(() => {
                              try {
                                const msg = selectedNode.config.message || '';
                                if (msg.trim().startsWith('{') && msg.trim().endsWith('}')) {
                                  const parsed = JSON.parse(msg);
                                  return (
                                    <div style={{ fontSize: '0.78rem', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                      <div><strong>Type:</strong> {parsed.dm_type || 'button_template'}</div>
                                      <div><strong>Text:</strong> {parsed.text || parsed.reply_text}</div>
                                      {parsed.title && <div><strong>Title:</strong> {parsed.title}</div>}
                                      {parsed.button_text && <div><strong>Button:</strong> {parsed.button_text} ({parsed.button_url})</div>}
                                    </div>
                                  );
                                }
                              } catch (err) {}
                              return <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{selectedNode.config.message}</div>;
                            })()}
                          </div>
                        )}
                      </div>
                    )}

                    {selectedNode.type === 'action_tag' && (
                      <div className="form-group">
                        <label>Contact Tag Name</label>
                        <input 
                          type="text" 
                          className="form-control" 
                          value={selectedNode.config.tag} 
                          onChange={(e) => handleUpdateNodeConfig('tag', e.target.value)}
                        />
                      </div>
                    )}

                    <button 
                      className="btn btn-danger" 
                      style={{ marginTop: 'auto', width: '100%' }}
                      onClick={() => handleDeleteNode(selectedNode.id)}
                    >
                      Delete Node
                    </button>
                  </div>
                ) : (
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', textAlign: 'center', margin: 'auto' }}>
                    Select a node on the canvas to configure settings.
                  </p>
                )}

                <div style={{ marginTop: '24px', borderTop: '1px solid var(--border-color)', paddingTop: '20px' }}>
                  <h4 style={{ fontSize: '0.88rem', marginBottom: '12px' }}>Add Actions</h4>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <button className="btn btn-secondary" style={{ fontSize: '0.82rem', justifyContent: 'flex-start' }} onClick={() => handleAddNode('action_reply')}>
                      + Public Reply
                    </button>
                    <button className="btn btn-secondary" style={{ fontSize: '0.82rem', justifyContent: 'flex-start' }} onClick={() => handleAddNode('action_dm')}>
                      + Private DM Link
                    </button>
                    <button className="btn btn-secondary" style={{ fontSize: '0.82rem', justifyContent: 'flex-start' }} onClick={() => handleAddNode('action_tag')}>
                      + Add Customer Tag
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {isGuideOpen && (
          <div className="modal-overlay" style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(8px)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 2000,
            padding: '20px'
          }}>
            <div className="card" style={{
              width: '100%',
              maxWidth: '750px',
              maxHeight: '90vh',
              overflowY: 'auto',
              backgroundColor: '#111827',
              border: '1px solid var(--border-color)',
              borderRadius: '16px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
              position: 'relative',
              padding: '28px'
            }}>
              <button 
                onClick={() => setIsGuideOpen(false)}
                style={{
                  position: 'absolute',
                  top: '20px',
                  right: '20px',
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  fontSize: '1.5rem',
                  cursor: 'pointer',
                  transition: 'color 0.2s'
                }}
                onMouseEnter={(e) => e.target.style.color = 'white'}
                onMouseLeave={(e) => e.target.style.color = 'var(--text-muted)'}
              >
                &times;
              </button>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '24px' }}>
                <div style={{
                  backgroundColor: 'rgba(59, 130, 246, 0.15)',
                  color: 'var(--primary-color)',
                  padding: '10px',
                  borderRadius: '10px'
                }}>
                  <Info size={24} />
                </div>
                <div>
                  <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 700 }}>Automation Flows User Guide</h2>
                  <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Learn how to create, configure, and optimize response chains.</p>
                </div>
              </div>

              <div className="guide-content" style={{ display: 'flex', flexDirection: 'column', gap: '20px', fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                
                {/* Section 1: Visual Walkthrough */}
                <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
                  <h3 style={{ color: 'white', margin: '0 0 10px 0', fontSize: '1.1rem' }}>How Automation Flows Work</h3>
                  <p style={{ marginBottom: '16px' }}>
                    Automation flows connect trigger keywords detected in user comments to actions like automated public replies, private DMs, or profile tags.
                  </p>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'space-between',
                    backgroundColor: 'rgba(255,255,255,0.02)',
                    padding: '16px',
                    borderRadius: '12px',
                    border: '1px solid rgba(255,255,255,0.05)',
                    textAlign: 'center',
                    gap: '8px'
                  }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, color: 'var(--accent-color)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: '4px' }}>Step 1</div>
                      <div style={{ color: 'white', fontWeight: 500 }}>User Comments</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>"Send me the guide!"</div>
                    </div>
                    <div style={{ color: 'var(--text-muted)', fontWeight: 700 }}>➔</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, color: 'var(--accent-color)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: '4px' }}>Step 2</div>
                      <div style={{ color: 'white', fontWeight: 500 }}>Keyword Trigger</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Matches "guide"</div>
                    </div>
                    <div style={{ color: 'var(--text-muted)', fontWeight: 700 }}>➔</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, color: 'var(--accent-color)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: '4px' }}>Step 3</div>
                      <div style={{ color: 'white', fontWeight: 500 }}>Public Reply</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>"Check your DMs!"</div>
                    </div>
                    <div style={{ color: 'var(--text-muted)', fontWeight: 700 }}>➔</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 600, color: 'var(--accent-color)', fontSize: '0.8rem', textTransform: 'uppercase', marginBottom: '4px' }}>Step 4</div>
                      <div style={{ color: 'white', fontWeight: 500 }}>Private DM</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Sends Guide Link</div>
                    </div>
                  </div>
                </div>

                {/* Section 2: Creating a Flow */}
                <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
                  <h3 style={{ color: 'white', margin: '0 0 10px 0', fontSize: '1.1rem' }}>How to Create a Flow</h3>
                  <ol style={{ paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <li>Click the **Create Automation Flow** button.</li>
                    <li>In the visual builder, configure your **Trigger Node** (specify keywords, and match precision).</li>
                    <li>Connect nodes by dragging edges to **Action Nodes** (e.g. public comment reply or private DM).</li>
                    <li>Save your changes and make the flow **Active** to start automatic execution.</li>
                  </ol>
                </div>

                {/* Section 3: Keyword Configuration */}
                <div style={{ borderBottom: '1px solid var(--border-color)', paddingBottom: '16px' }}>
                  <h3 style={{ color: 'white', margin: '0 0 10px 0', fontSize: '1.1rem' }}>Triggers & Keywords</h3>
                  <p style={{ margin: '0 0 8px 0' }}>Keywords are matched case-insensitively:</p>
                  <ul style={{ paddingLeft: '20px', margin: 0, display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    <li><strong>Exact Match:</strong> Matches full words only (e.g. "guide" matches "give me the guide" but not "guidebook").</li>
                    <li><strong>Fuzzy Match:</strong> Matches substrings anywhere.</li>
                    <li><strong>Comma-Separated Keywords:</strong> Triggers on *any* of the words listed.</li>
                  </ul>
                </div>

                {/* Section 4: Best Practices & Common Examples */}
                <div>
                  <h3 style={{ color: 'white', margin: '0 0 10px 0', fontSize: '1.1rem' }}>Best Practices & Examples</h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    <div style={{ backgroundColor: 'rgba(255,255,255,0.01)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.03)' }}>
                      <strong style={{ color: 'white', fontSize: '0.85rem' }}>💡 Tip 1: Avoid spam flags</strong>
                      <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem' }}>Meta can flag accounts that reply with the exact same message repeatedly. Use conversational language or rotate templates.</p>
                    </div>
                    <div style={{ backgroundColor: 'rgba(255,255,255,0.01)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.03)' }}>
                      <strong style={{ color: 'white', fontSize: '0.85rem' }}>💡 Tip 2: Clear call-to-actions</strong>
                      <p style={{ margin: '4px 0 0 0', fontSize: '0.8rem' }}>Tell users exactly what keyword to comment in your post captions (e.g. <em>"Comment 'INFO' to receive the download link!"</em>).</p>
                    </div>
                  </div>
                </div>

              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
                <button className="btn btn-primary" onClick={() => setIsGuideOpen(false)}>Got It, Close Guide</button>
              </div>

            </div>
          </div>
        )}

        {deleteConfirmFlowId && (
          <div className="modal-overlay" style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 3000,
            padding: '20px'
          }}>
            <div className="card" style={{
              width: '100%',
              maxWidth: '420px',
              backgroundColor: '#111827',
              border: '1px solid var(--border-color)',
              borderRadius: '16px',
              boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              gap: '16px'
            }}>
              <div style={{
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.2)',
                color: '#ef4444',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.8rem',
                fontWeight: 'bold',
                marginBottom: '8px'
              }}>
                ⚠️
              </div>

              <h3 style={{ margin: 0, fontSize: '1.25rem', color: 'white', fontWeight: 'bold' }}>Delete Automation Flow</h3>
              <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: '0.88rem', lineHeight: '1.5' }}>
                Are you sure you want to delete this automation flow? This action cannot be undone and will stop this automation instantly.
              </p>

              <div style={{ display: 'flex', gap: '12px', width: '100%', marginTop: '8px' }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  style={{ flex: 1, padding: '10px 16px', fontSize: '0.9rem', justifyContent: 'center' }}
                  onClick={() => setDeleteConfirmFlowId(null)}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn btn-danger"
                  style={{ flex: 1, padding: '10px 16px', fontSize: '0.9rem', justifyContent: 'center', backgroundColor: '#ef4444', border: 'none', color: 'white' }}
                  onClick={handleConfirmDeleteFlow}
                >
                  Delete
                </button>
              </div>
            </div>
          </div>
        )}

        {previewDmRule && (
          <div className="modal-overlay" style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            backdropFilter: 'blur(10px)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 3000,
            padding: '20px'
          }}>
            <div className="card" style={{
              width: '100%',
              maxWidth: '360px',
              backgroundColor: '#111827',
              border: '1px solid var(--border-color)',
              borderRadius: '16px',
              padding: '20px',
              boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', marginBottom: '16px', alignItems: 'center' }}>
                <h3 style={{ margin: 0, color: 'white', fontSize: '1.1rem' }}>Template Preview</h3>
                <button 
                  style={{ background: 'none', border: 'none', color: '#9ca3af', cursor: 'pointer', fontSize: '1.2rem' }}
                  onClick={() => setPreviewDmRule(null)}
                >
                  ✕
                </button>
              </div>

              {/* Phone container */}
              <div style={{
                width: '280px',
                height: '520px',
                borderRadius: '36px',
                border: '12px solid #1f2937',
                backgroundColor: '#030712',
                position: 'relative',
                boxShadow: '0 25px 50px -12px rgba(0,0,0,0.5)',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column'
              }}>
                {/* Notch */}
                <div style={{
                  width: '110px',
                  height: '18px',
                  backgroundColor: '#1f2937',
                  borderBottomLeftRadius: '12px',
                  borderBottomRightRadius: '12px',
                  position: 'absolute',
                  top: 0,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  zIndex: 10
                }} />

                {/* Header */}
                <div style={{
                  height: '56px',
                  borderBottom: '1px solid #1f2937',
                  display: 'flex',
                  alignItems: 'center',
                  padding: '16px 12px 0 12px',
                  gap: '8px',
                  backgroundColor: '#090d16'
                }}>
                  <div style={{ fontSize: '0.8rem', color: '#9ca3af' }}>❮</div>
                  <div style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '0.65rem',
                    color: 'white',
                    fontWeight: 'bold'
                  }}>
                    ig
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontSize: '0.72rem', fontWeight: 'bold', color: 'white' }}>instagram_page</span>
                    <span style={{ fontSize: '0.6rem', color: '#6b7280' }}>Active now</span>
                  </div>
                </div>

                {/* Chat Message Panel */}
                <div style={{
                  flex: 1,
                  padding: '12px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  overflowY: 'auto',
                  backgroundColor: '#030712'
                }}>
                  {/* Trigger word bubble */}
                  {previewDmRule.keyword && (
                    <div style={{
                      alignSelf: 'flex-start',
                      backgroundColor: '#1f2937',
                      color: 'white',
                      borderRadius: '14px',
                      padding: '8px 12px',
                      fontSize: '0.72rem',
                      maxWidth: '80%',
                      wordBreak: 'break-word'
                    }}>
                      {previewDmRule.keyword}
                    </div>
                  )}

                  {/* Outgoing template bubble */}
                  <div style={{ alignSelf: 'flex-end', maxWidth: '85%' }}>
                    {(() => {
                      try {
                        const parsed = JSON.parse(previewDmRule.reply_text);
                        if (parsed && parsed.dm_type === 'button_template') {
                          return (
                            <div style={{
                              width: '200px',
                              backgroundColor: '#1f2937',
                              borderRadius: '14px',
                              overflow: 'hidden',
                              border: '1px solid #374151',
                              display: 'flex',
                              flexDirection: 'column'
                            }}>
                              <div style={{
                                height: '110px',
                                backgroundColor: '#374151',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                overflow: 'hidden',
                                position: 'relative'
                              }}>
                                {parsed.image_url ? (
                                  <img 
                                    src={parsed.image_url} 
                                    alt="Preview" 
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                  />
                                ) : (
                                  <div style={{ color: '#9ca3af', fontSize: '1.4rem' }}>☁️</div>
                                )}
                              </div>
                              <div style={{ padding: '8px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 'bold', color: 'white', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                  {parsed.title || "Card Title"}
                                </div>
                                <div style={{ fontSize: '0.62rem', color: '#9ca3af', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                  {parsed.subtitle || "Card Subtitle"}
                                </div>
                                <div style={{ fontSize: '0.65rem', color: '#d1d5db', marginTop: '4px', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                                  {parsed.text || parsed.reply_text || ""}
                                </div>
                              </div>
                              <div style={{
                                borderTop: '1px solid #374151',
                                padding: '8px 0',
                                color: '#3b82f6',
                                fontSize: '0.72rem',
                                fontWeight: 'bold',
                                textAlign: 'center',
                                backgroundColor: 'rgba(0,0,0,0.1)'
                              }}>
                                {parsed.button_text || "Shop Now"}
                              </div>
                            </div>
                          );
                        } else if (parsed && parsed.dm_type === 'image') {
                          return (
                            <div style={{
                              width: '180px',
                              borderRadius: '14px',
                              overflow: 'hidden',
                              border: '1px solid #374151',
                              display: 'flex',
                              flexDirection: 'column'
                            }}>
                              <img 
                                src={parsed.image_url || 'https://images.unsplash.com/photo-1517841905240-472988babdf9?w=500'} 
                                alt="Preview" 
                                style={{ width: '100%', height: 'auto', maxHeight: '180px', objectFit: 'cover' }}
                              />
                              {parsed.text && (
                                <div style={{ padding: '6px 10px', fontSize: '0.72rem', color: 'white', backgroundColor: '#3b82f6' }}>
                                  {parsed.text}
                                </div>
                              )}
                            </div>
                          );
                        }
                      } catch (e) {}
                      return (
                        <div style={{
                          backgroundColor: '#3b82f6',
                          color: 'white',
                          borderRadius: '14px',
                          padding: '8px 12px',
                          fontSize: '0.72rem',
                          wordBreak: 'break-word'
                        }}>
                          {previewDmRule.reply_text || "Welcome!"}
                        </div>
                      );
                    })()}
                  </div>
                </div>

                {/* Footer input */}
                <div style={{
                  height: '48px',
                  borderTop: '1px solid #1f2937',
                  padding: '8px 12px',
                  display: 'flex',
                  alignItems: 'center',
                  backgroundColor: '#090d16'
                }}>
                  <div style={{
                    flex: 1,
                    backgroundColor: '#1f2937',
                    borderRadius: '18px',
                    height: '28px',
                    padding: '0 12px',
                    fontSize: '0.68rem',
                    color: '#9ca3af',
                    display: 'flex',
                    alignItems: 'center'
                  }}>
                    Message...
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', width: '100%', marginTop: '16px' }}>
                <button type="button" className="btn btn-secondary" onClick={() => setPreviewDmRule(null)}>Close</button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
