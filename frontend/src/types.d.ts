declare interface ApiMeta {
  request_id?: string;
  provider?: string;
  latency_ms?: number;
}

declare interface SearchResultItem {
  unit?: string;
  building?: string;
  community?: string;
  owner_name?: string;
  price_aed?: number;
  snippet?: string;
}

declare interface AliasMapResponse {
  request_id?: string;
  communities: Record<string, string>;
  buildings: Record<string, string>;
}

declare interface Alert {
  id: string;
  query: string;
  community?: string;
  building?: string;
  notify_phone?: string;
  notify_email?: string;
  created_at: string;
}
