import React from 'react'
import { clients } from '../data/mockData'

function formatCurrency(value) {
  return '$' + value.toLocaleString()
}

function ClientTable() {
  return (
    <table>
      <thead>
        <tr>
          <th>Client</th>
          <th>Tier</th>
          <th>MRR</th>
          <th>Seats</th>
          <th>Since</th>
        </tr>
      </thead>
      <tbody>
        {clients.map((client) => (
          <tr key={client.id}>
            <td style={{ fontWeight: 500 }}>{client.name}</td>
            <td>
              <span className={`tier-badge tier-${client.tier.toLowerCase()}`}>
                {client.tier}
              </span>
            </td>
            <td className="mrr-value">{formatCurrency(client.mrr)}</td>
            <td>{client.seats}</td>
            <td style={{ color: '#888' }}>{client.signedDate}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default ClientTable
