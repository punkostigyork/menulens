import type { MenuItem } from "./menu";
export interface SearchIntent {
  ingredients: string[];
  tags: string[];
  name: string | null;
  min_price: string | null;
  max_price: string | null;
  min_price_inclusive: boolean;
  max_price_inclusive: boolean;
  currency: string | null;
  unsupported: string[];
}
export interface SearchMatch {
  item: MenuItem;
  menu_id: string;
  menu_title: string;
  section_name: string;
  matched_inferred_tags: string[];
}
export interface SearchResponse {
  intent: SearchIntent;
  results: SearchMatch[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
  clarification: string | null;
}
export interface SearchRequest {
  query?: string;
  filters?: Partial<SearchIntent>;
  limit?: number;
  offset?: number;
  menu_id?: string;
}
