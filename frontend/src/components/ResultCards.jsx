import React from 'react';

export function renderCard(type, data) {
  switch (type) {
    case 'ownership':
      return <OwnershipCard data={data} />;
    case 'history':
      return <HistoryCard data={data} />;
    case 'portfolio':
      return <PortfolioCard data={data} />;
    case 'analytics':
      return <AnalyticsCard data={data} />;
    case 'search':
    default:
      return <SearchResults data={data} />;
  }
}

export function OwnershipCard({ data }) {
  if (!data?.found) {
    return (
      <div className="card">
        <h3>Owner not found</h3>
        <p>{data?.message || 'No property matched your request.'}</p>
      </div>
    );
  }

  const ownerName = data.owner_name || data.institutional_owner?.name || 'Unknown owner';
  const ownerPhone = data.owner_phone || data.institutional_owner?.phone || 'N/A';

  return (
    <div className="card">
      <h3>Current Owner</h3>
      <p className="muted">
        {data.unit} • {data.building || 'Unknown building'} • {data.community || 'Unknown community'}
      </p>
      <p>
        <strong>{ownerName}</strong>
      </p>
      <p>{ownerPhone}</p>
      {data.last_price && <p>Last price: AED {Math.round(data.last_price).toLocaleString()}</p>}
      {data.last_transaction_date && <p>Date: {new Date(data.last_transaction_date).toLocaleDateString()}</p>}
    </div>
  );
}

export function HistoryCard({ data }) {
  if (!data?.history?.length) {
    return (
      <div className="card">
        <h3>Transaction History</h3>
        <p>No transaction history found.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>Transaction History</h3>
      <div className="timeline">
        {data.history.map((txn, index) => (
          <div key={`${txn.date}-${index}`} className="timeline-item">
            <div className="timeline-date">{new Date(txn.date).toLocaleDateString()}</div>
            <div>
              <p>
                AED {Math.round(txn.price || 0).toLocaleString()}{' '}
                {txn.price_per_sqft && `( ${Math.round(txn.price_per_sqft)} AED/sqft )`}
              </p>
              <p>Seller: {txn.seller_name || 'N/A'}</p>
              <p>Buyer: {txn.buyer_name || 'N/A'}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function PortfolioCard({ data }) {
  if (!data?.found || !data.portfolio?.length) {
    return (
      <div className="card">
        <h3>Portfolio</h3>
        <p>{data?.message || 'No holdings found for that owner.'}</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>{data.owner_name || 'Owner'} Portfolio</h3>
      <p className="muted">
        {data.total_properties} properties • AED {Math.round(data.total_value || 0).toLocaleString()}
      </p>
      <div className="list">
        {data.portfolio.map((prop, index) => (
          <div key={`${prop.unit}-${index}`} className="list-item">
            <p>
              <strong>{prop.unit || 'Unit'}</strong> {prop.building && `• ${prop.building}`}
            </p>
            <p>{prop.community || 'Unknown community'}</p>
            {prop.last_price && <p>AED {Math.round(prop.last_price).toLocaleString()}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}

export function AnalyticsCard({ data }) {
  if (!data) {
    return (
      <div className="card">
        <h3>Market Insights</h3>
        <p>No analytics available.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>Market Insights</h3>
      <p className="muted">{data.scope}</p>
      <div className="grid">
        <div>
          <p className="muted">Properties indexed</p>
          <p>{data.total_properties?.toLocaleString() || 0}</p>
        </div>
        <div>
          <p className="muted">Avg price/sqft</p>
          <p>AED {Math.round(data.avg_price_per_sqft || 0).toLocaleString()}</p>
        </div>
      </div>
    </div>
  );
}

export function SearchResults({ data }) {
  if (!data?.results?.length) {
    return (
      <div className="card">
        <h3>No results</h3>
        <p>Try a different search or ask about a specific unit.</p>
      </div>
    );
  }

  return (
    <div className="card">
      <h3>Search Results</h3>
      <div className="list">
        {data.results.map((item, index) => (
          <div key={`${item.unit || index}-${index}`} className="list-item">
            <p>
              <strong>{item.unit || item.property_id || 'Unit'}</strong> {item.building && `• ${item.building}`}
            </p>
            <p>{item.community || 'Unknown community'}</p>
            {item.owner_name && <p>Owner: {item.owner_name}</p>}
            {item.price_aed && <p>Last price: AED {Math.round(item.price_aed).toLocaleString()}</p>}
            {item.snippet && <p className="muted">{item.snippet}</p>}
          </div>
        ))}
      </div>
    </div>
  );
}
