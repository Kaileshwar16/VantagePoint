import axios from 'axios';

const API = axios.create({ baseURL: 'http://localhost:8000/api' });

export const getCompanies = () => API.get('/companies/');
export const getCompany = (id) => API.get(`/companies/${id}/`);
export const createCompany = (data) => API.post('/companies/', data);
export const deleteCompany = (id) => API.delete(`/companies/${id}/`);
export const getCompanyTimeline = (id, days = 90) => API.get(`/companies/${id}/timeline/?days=${days}`);

export const getDataPoints = (params) => API.get('/datapoints/', { params });
export const getPatterns = (params) => API.get('/patterns/', { params });
export const getInsights = (params) => API.get('/insights/', { params });
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
export const getSignals = (params) => API.get('/signals/', { params });
export const getCompoundSignals = (params) => API.get('/compound-signals/', { params });
export const getPricingSnapshots = (params) => API.get('/pricing-snapshots/', { params });

// Battlecards & Dead Reckoning
export const getBattlecards = (params) => API.get('/battlecards/', { params });
export const getDeadReckonings = (params) => API.get('/dead-reckonings/', { params });
export const createDeadReckoning = (data) => API.post('/dead-reckonings/', data);

// Timeline Overlay
export const getTimelineOverlay = (companyIds, days = 180) =>
  API.post('/timeline-overlay/', { company_ids: companyIds, days });

export default API;
