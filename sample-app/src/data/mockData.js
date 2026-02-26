// Mock MRR data for GrowthOps dashboard
// This simulates a B2B SaaS company with contract tiers

export const CONTRACT_TIERS = ['Gold', 'Silver', 'Bronze']

export const clients = [
  { id: 1, name: 'Acme Corp', tier: 'Gold', mrr: 12500, seats: 50, signedDate: '2024-03-15' },
  { id: 2, name: 'TechFlow Inc', tier: 'Gold', mrr: 15000, seats: 75, signedDate: '2024-01-20' },
  { id: 3, name: 'DataSync Ltd', tier: 'Silver', mrr: 7500, seats: 30, signedDate: '2024-06-10' },
  { id: 4, name: 'CloudBase Co', tier: 'Silver', mrr: 6800, seats: 25, signedDate: '2024-04-22' },
  { id: 5, name: 'FinLogic', tier: 'Silver', mrr: 8200, seats: 35, signedDate: '2024-02-18' },
  { id: 6, name: 'RetailEdge', tier: 'Bronze', mrr: 3200, seats: 10, signedDate: '2024-08-05' },
  { id: 7, name: 'HealthTech Pro', tier: 'Gold', mrr: 18000, seats: 100, signedDate: '2023-11-30' },
  { id: 8, name: 'EduPlatform', tier: 'Bronze', mrr: 2800, seats: 8, signedDate: '2024-09-12' },
  { id: 9, name: 'LogiChain', tier: 'Silver', mrr: 9100, seats: 40, signedDate: '2024-05-03' },
  { id: 10, name: 'MediaPulse', tier: 'Bronze', mrr: 4100, seats: 15, signedDate: '2024-07-19' },
]

export const monthlyMRR = [
  { month: 'Sep 2025', total: 72000, gold: 38000, silver: 24000, bronze: 10000 },
  { month: 'Oct 2025', total: 75200, gold: 39500, silver: 25200, bronze: 10500 },
  { month: 'Nov 2025', total: 78100, gold: 41000, silver: 26600, bronze: 10500 },
  { month: 'Dec 2025', total: 81400, gold: 43000, silver: 27900, bronze: 10500 },
  { month: 'Jan 2026', total: 84500, gold: 44500, silver: 29500, bronze: 10500 },
  { month: 'Feb 2026', total: 87200, gold: 45500, silver: 31600, bronze: 10100 },
]
