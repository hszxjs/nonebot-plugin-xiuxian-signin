export type AdminOk<T> = T & { ok: boolean };

export type PlayerSummary = {
  user_id: string;
  nickname: string;
  realm: string;
  battle_power: number;
  spirit_stones: number;
};

export type DashboardPlayer = PlayerSummary & {
  realm_index: number;
  last_sign_date: string;
  days_since_sign: number | null;
  signed_today: boolean;
  recent_active: boolean;
  inactive_risk: boolean;
};

export type DashboardPayload = AdminOk<{
  mode: "snapshot";
  generated_date: string;
  metrics: {
    total_players: number;
    signed_today: number;
    recent_active: number;
    inactive_risk: number;
    total_spirit_stones: number;
    average_spirit_stones: number;
    average_battle_power: number;
  };
  realm_distribution: Array<{ realm: string; count: number }>;
  top_battle_power: DashboardPlayer[];
  recent_signins: DashboardPlayer[];
  inactive_players: DashboardPlayer[];
  health_flags: {
    has_players: boolean;
    inactive_ratio: number;
    today_signin_ratio: number;
  };
  capabilities: {
    historical_trends: boolean;
    snapshot_dashboard: boolean;
  };
}>;

export type PlayerListPayload = AdminOk<{ players: PlayerSummary[] }>;

export type PlayerDetailPayload = AdminOk<{
  record: Record<string, unknown>;
  meta: PlayerMeta;
}>;

export type PlayerMeta = {
  realms?: Array<{ index: number; name: string }>;
  attributes?: string[];
  attribute_labels?: Record<string, string>;
  tiers?: string[];
  grades?: string[];
  categories?: string[];
  mystic_types?: string[];
  cultivation_routes?: string[];
  realm_quality_titles?: Record<string, string[]>;
  quality_titles?: string[];
  foundation_quality_titles?: string[];
};
export type AdminItem = {
  name: string;
  category?: string;
  tiers?: string[];
  grades?: string[];
  required_realm?: string;
  realm?: string;
  required_attribute?: string;
  usage?: string;
  source?: string;
  story?: string;
  parameter_note?: string;
  icon?: string;
  customized?: boolean;
};

export type ItemPayload = AdminOk<{
  items: AdminItem[];
  meta: {
    categories?: string[];
    tiers?: string[];
    grades?: string[];
    realms?: string[];
    attributes?: string[];
  };
}>;
export type BeastCard = {
  id: string;
  kind: "beast" | "spell";
  name: string;
  realm?: string;
  faction?: string;
  element?: string;
  cost?: number;
  attack?: number;
  defense?: number;
  pool_copies?: number;
  portrait_id?: string;
  icon?: string;
  icon_id?: string;
  effect?: string;
  story?: string;
  rules?: unknown;
  customized?: boolean;
  tier?: number;
  category?: string;
  target?: string;
  source_realm?: string;
  archetype?: string;
};

export type BeastCardPayload = AdminOk<{
  cards: BeastCard[];
  meta: {
    default_pool_copies?: number;
    factions?: string[];
    realms?: Array<{ index: number; name: string }> | string[];
    elements?: string[];
    categories?: string[];
    targets?: string[];
  };
}>;
