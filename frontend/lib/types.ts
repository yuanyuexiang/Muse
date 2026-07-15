export interface Customer {
  id: number;
  name: string;
}

export interface InboxMessage {
  id: number;
  msgid: string;
  seq: number;
  channel: string;
  forwarded_by: string | null;
  type: string;
  content: string | null;
  original_content: string | null;
  edited: boolean;
  object_key: string | null;
  download_status: string;
  sender_role: string;
  status: string;
  customer_id: number | null;
  batch_id: number | null;
  created_at: string;
}

export interface InboxPage {
  items: InboxMessage[];
  total: number;
  limit: number;
  offset: number;
}

export interface Dish {
  number: string | null;
  name: string;
  description: string | null;
  price: string | null;
  flags: string[];
  photo_object_key: string | null;
}

export interface MenuCategory {
  name: string;
  dishes: Dish[];
}

export interface SetMeal {
  name: string;
  price: string | null;
  items: string[];
}

export interface ShopInfo {
  name: string | null;
  tagline: string | null;
  phone: string | null;
  address: string | null;
  online_order_url: string | null;
  opening_hours: string[];
  delivery_terms: string[];
  promotions: string[];
  allergen_notice: string | null;
  style_notes: string | null;
  logo_object_key: string | null;
  hero_object_key: string | null;
}

export interface PageSpec {
  preset: string;
  width_mm: number | null;
  height_mm: number | null;
  bleed_mm: number;
}

export interface MenuSpec {
  shop: ShopInfo;
  categories: MenuCategory[];
  set_meals: SetMeal[];
  page: PageSpec;
  theme: string;
  notes: string | null;
  missing_fields: string[];
}

export interface MenuRequirement {
  id: number;
  batch_id: number;
  customer_id: number;
  version: number;
  data: MenuSpec;
  status: string;
  reviewed_by: string | null;
  created_at: string;
}

export interface Batch {
  id: number;
  customer_id: number;
  status: string;
  messages: InboxMessage[];
  requirements: MenuRequirement[];
}
