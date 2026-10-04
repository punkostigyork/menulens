export interface GeneratedImage {
  id: string;
  menu_item_id: string;
  status: "processing" | "ready" | "failed";
  image_url: string | null;
  error_message: string | null;
  created_at: string;
}
export type ExplanationLanguage = "en" | "hu";
export interface Explanation {
  item_id: string;
  language: ExplanationLanguage;
  status: "processing" | "ready" | "failed";
  description: string | null;
  tags: string[];
  error_message: string | null;
  created_at: string;
}
export interface MenuItem {
  id: string;
  section_id: string;
  display_order: number;
  name: string;
  original_description: string | null;
  generated_description: string | null;
  price: string | null;
  currency: string | null;
  language: string | null;
  cuisine: string | null;
  ingredients: string[];
  tags: string[];
  dietary_info: unknown[];
  explanations: Explanation[];
  generated_image?: GeneratedImage | null;
}
export interface MenuSectionData {
  id: string;
  name: string;
  display_order: number;
  items: MenuItem[];
}
export interface Menu {
  is_demo?: boolean;
  id: string;
  original_filename: string;
  stored_filename: string;
  content_type: string;
  status: "uploaded" | "processing" | "processed" | "failed";
  created_at: string;
  processed_at?: string | null;
  currency?: string | null;
  language?: string | null;
  restaurant_name?: string | null;
  processing_error?: string | null;
  sections?: MenuSectionData[];
}
