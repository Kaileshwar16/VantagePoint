import axios from 'axios';

const API = axios.create({ baseURL: import.meta.env.VITE_API_URL || '/api', withCredentials: true, timeout: 180000 });
let csrfToken;
API.interceptors.request.use(config => {
  if (csrfToken) config.headers['X-CSRFToken'] = csrfToken;
  return config;
});
API.interceptors.response.use(response => {
  if (response.data?.csrfToken) csrfToken = response.data.csrfToken;
  return response;
}, error => {
  if (!error.config?.url?.includes('/session/')) {
    const detail = error.response?.data?.detail || error.response?.data?.error || error.response?.data?.errors;
    window.dispatchEvent(new CustomEvent('api-error', { detail: typeof detail === 'string' ? detail : 'Request failed. Check your connection and sign-in, then retry.' }));
  }
  return Promise.reject(error);
});

export const getSession = () => API.get('/session/');
export const signIn = data => API.post('/session/', data);
export const signOut = () => API.delete('/session/');
export const getDataQuality = () => API.get('/data-quality/');

// Existing views filter locally; follow pagination so they do not silently omit records.
async function getAll(path, params) {
  let page = 1;
  const results = [];
  while (true) {
    const response = await API.get(path, { params: { ...params, page, page_size: 200 } });
    if (!response.data.results) return response;
    results.push(...response.data.results);
    if (!response.data.next) return { ...response, data: { ...response.data, results } };
    page += 1;
  }
}

export const getCompanies = () => getAll('/companies/');
export const getCompany = (id) => API.get(`/companies/${id}/`);
export const createCompany = (data) => API.post('/companies/', data);
export const deleteCompany = (id) => API.delete(`/companies/${id}/`);
export const getCompanyTimeline = (id, days = 90) => API.get(`/companies/${id}/timeline/?days=${days}`);

export const getDataPoints = (params) => getAll('/datapoints/', params);
export const updateDataPoint = (id, data) => API.patch(`/datapoints/${id}/`, data);
export const getPatterns = (params) => getAll('/patterns/', params);
export const getInsights = (params) => getAll('/insights/', params);
export const updateInsight = (id, data) => API.patch(`/insights/${id}/`, data);

export const getDashboard = () => API.get('/dashboard/');

export const triggerScrape = (companyId, spider = 'news') =>
  API.post(`/companies/${companyId}/scrape/`, { spider });
export const runAnalysis = (companyId) =>
  API.post(`/analysis/run/${companyId}/`);
export const runAllAnalysis = () => API.post('/analysis/run-all/');

// Signal capture & advanced analysis
export const captureSignals = (companyId) =>
  API.post(`/companies/${companyId}/capture-signals/`);
export const runAdvancedAnalysis = (companyId) =>
  API.post(`/companies/${companyId}/advanced-analysis/`);

// Signals
export const getSignals = (params) => getAll('/signals/', params);
export const getCompoundSignals = (params) => getAll('/compound-signals/', params);
export const getPricingSnapshots = (params) => getAll('/pricing-snapshots/', params);

// Battlecards & Dead Reckoning
export const getBattlecards = (params) => getAll('/battlecards/', params);
export const getDeadReckonings = (params) => getAll('/dead-reckonings/', params);
export const createDeadReckoning = (data) => API.post('/dead-reckonings/', data);

// Timeline Overlay
export const getTimelineOverlay = (companyIds, days = 180) =>
  API.post('/timeline-overlay/', { company_ids: companyIds, days });

export default API;
