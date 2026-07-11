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
  object_key: string | null;
  download_status: string;
  sender_role: string;
  status: string;
  customer_id: number | null;
  batch_id: number | null;
  created_at: string;
}

export interface MenuRequirementData {
  head_count: number | null;
  budget: number | null;
  dietary_restrictions: string[];
  taste_preferences: string[];
  dishes: string[];
  event_type: string | null;
  notes: string | null;
  missing_fields: string[];
}

export interface MenuRequirement {
  id: number;
  batch_id: number;
  customer_id: number;
  version: number;
  data: MenuRequirementData;
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
