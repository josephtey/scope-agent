import React from 'react'
import { monthlyMRR } from '../data/mockData'

function formatCurrency(value) {
  return '$' + value.toLocaleString()
}

function MRRTable() {
  return (
    <table>
      <thead>
        <tr>
          <th>Month</th>
          <th>Total MRR</th>
          <th>Gold</th>
          <th>Silver</th>
          <th>Bronze</th>
        </tr>
      </thead>
      <tbody>
        {monthlyMRR.map((row) => (
          <tr key={row.month}>
            <td>{row.month}</td>
            <td className="mrr-value mrr-total">{formatCurrency(row.total)}</td>
            <td className="mrr-value">{formatCurrency(row.gold)}</td>
            <td className="mrr-value">{formatCurrency(row.silver)}</td>
            <td className="mrr-value">{formatCurrency(row.bronze)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default MRRTable
