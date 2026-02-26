import React from 'react'
import MRRTable from './components/MRRTable'
import ClientTable from './components/ClientTable'
import './App.css'

function App() {
  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">GrowthOps</div>
        <nav>
          <span className="nav-active">Dashboard</span>
          <span>Clients</span>
          <span>Billing</span>
          <span>Settings</span>
        </nav>
      </header>
      <main className="app-main">
        <h1>Revenue Dashboard</h1>
        <div className="dashboard-grid">
          <section className="card">
            <h2>Monthly Recurring Revenue</h2>
            <MRRTable />
          </section>
          <section className="card">
            <h2>Client Overview</h2>
            <ClientTable />
          </section>
        </div>
      </main>
    </div>
  )
}

export default App
