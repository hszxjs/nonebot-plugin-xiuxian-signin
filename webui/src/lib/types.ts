export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue }

export type JsonRecord = Record<string, JsonValue>

export type DashboardMetrics = {
  total_players: number
  signed_today: number
  recent_active: number
  inactive_risk: number
  total_spirit_stones: number
  average_spirit_stones: number
  average_battle_power: number
}

export type PlayerSummary = {
  user_id: string
  nickname: string
  realm: string
  realm_index?: number
  battle_power: number
  spirit_stones: number
  last_sign_date?: string
  days_since_sign?: number | null
  signed_today?: boolean
  recent_active?: boolean
  inactive_risk?: boolean
}

export type DashboardPayload = {
  ok: boolean
  mode: string
  generated_date: string
  metrics: DashboardMetrics
  realm_distribution: Array<{ realm: string; count: number }>
  top_battle_power: PlayerSummary[]
  recent_signins: PlayerSummary[]
  inactive_players: PlayerSummary[]
  health_flags: {
    has_players: boolean
    inactive_ratio: number
    today_signin_ratio: number
  }
  capabilities: Record<string, boolean>
}

export type PlayerListPayload = {
  ok: boolean
  players: PlayerSummary[]
}

export type PlayerMeta = {
  realms: Array<{ index: number; name: string }>
  attributes: string[]
  attribute_labels: Record<string, string>
  tiers: string[]
  grades: string[]
  categories: string[]
  mystic_types: string[]
  cultivation_routes: string[]
  foundation_quality_titles: string[]
  realm_quality_titles: Record<string, string[]>
  quality_titles: string[]
}

export type PlayerDetailPayload = {
  ok: boolean
  record: JsonRecord
  meta: PlayerMeta
}

export type ItemEntry = {
  name: string
  category?: string
  tiers?: string[]
  grades?: string[]
  required_realm?: string
  required_attribute?: string
  usage?: string
  source?: string
  story?: string
  customized?: boolean
  icon?: string
}

export type ItemsPayload = {
  ok: boolean
  items: ItemEntry[]
  meta: {
    categories: string[]
    tiers: string[]
    grades: string[]
    realms: string[]
    attributes: string[]
  }
}

export type BeastCard = {
  id: string
  name: string
  kind?: string
  attack?: number
  defense?: number
  health?: number
  speed?: number
  pool_copies?: number
  portrait?: string
  spell_icon?: string
  effect?: string
  story?: string
  rules?: JsonValue
  customized?: boolean
  [key: string]: unknown
}

export type BeastCardsPayload = {
  ok: boolean
  cards: BeastCard[]
  meta: Record<string, JsonValue>
}

export type MysticPayload = {
  ok: boolean
  mystic: MysticConfig
}

export type EquipmentPayload = {
  ok: boolean
  rules: EquipmentRules
  meta: {
    realms: Array<{ index: number; name: string }>
    tiers: string[]
    grades: string[]
    attributes: string[]
    attribute_labels: Record<string, string>
    artifacts: Array<{
      name: string
      realm_index: number
      realm: string
      tier: string
      grade: string
      attribute: string
      attribute_label: string
    }>
  }
}

export type EquipmentRules = {
  realm_tier_unlocks?: Record<string, string[]>
  tier_default_realm?: Record<string, number>
  artifact_drop_pools?: Record<string, unknown>
  artifact_power_base?: Record<string, number>
  artifact_realm_power_base?: Record<string, number>
  artifact_tier_power_ratio?: Record<string, number>
  artifact_grade_ratio?: Record<string, number>
  artifact_immortal_upgrade_rate?: number
  [key: string]: unknown
}

export type MysticConfig = {
  map_size_rules?: MysticMapSizeRule[]
  min_map_size?: number
  max_map_size?: number
  normal_node_weights?: Record<string, number>
  high_risk_node_weights?: Record<string, number>
  normal_branch_density?: number
  high_risk_branch_density?: number
  high_risk_loop_count?: number
  consecutive_combat_limit?: number
  ordinary_monster_hp_multiplier?: number
  boss_hp_multiplier?: number
  reward_multiplier?: number
  damage_growth_per_ten_rounds?: number
  encounter_response_seconds?: number
  battle_prepare_seconds?: number
  player_action_seconds?: number
  boss_vote_seconds?: number
  leader_inactive_seconds?: number
  leader_transfer_vote_seconds?: number
  rescue_wait_seconds?: number
  signin_normal_token_count?: number
  signin_high_risk_token_count?: number
  daily_task_normal_token_count?: number
  daily_task_high_risk_token_count?: number
  themes?: MysticThemeBinding[]
  types?: string[]
  high_risk_types?: string[]
  enabled_types: string[]
  enabled_high_risk_types: string[]
  category_weights: Record<string, number>
  drop_overrides: Record<string, unknown>
  fishing_option_rate: number
  extra_fishing_chance_rate?: number
  categories?: string[]
  tiers?: string[]
  grades?: string[]
  [key: string]: unknown
}

export type MysticMapSizeRule = {
  minimum_boss_realm_index: number
  node_count: 24 | 28 | 32 | 36 | 40 | 44 | 48
}

export type MysticThemeBinding = {
  theme_id: string
  display_name: string
  risk: string
  template_id: string
  background_path: string
  background_exists: boolean
  template_exists: boolean
}

export type AdminConfig = {
  version: number
  equipment_rules: EquipmentRules
  mystic: MysticConfig
  signin: {
    extra_fishing_chance_rate: number
    [key: string]: unknown
  }
  item_overrides: Record<string, unknown>
  beast_realm: {
    card_pool_copies: number
    card_overrides: Record<string, unknown>
    [key: string]: unknown
  }
  [key: string]: unknown
}

export type ConfigPayload = {
  ok: boolean
  config: AdminConfig
}

export type BackupPayload = {
  ok: boolean
  path: string
}
