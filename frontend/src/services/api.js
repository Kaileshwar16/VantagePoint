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
  API.post(`/scraping/trigger/${companyId}/`, { spider });
export const runAnalysis = (companyId) =>
  API.post(`/analysis/run/${companyId}/`);
export const runAllAnalysis = () => API.post('/analysis/run-all/');

export default API;
