export const dataPresentation = {
  metric: "Card",
  rankedList: "ItemGroup",
  searchableEntityList: "ItemGroupWithSearch",
  boolean: "Switch",
  enum: "Select",
  shortEnum: "ToggleGroup",
  multiEnum: "CheckboxGroup",
  boundedRate: "Slider",
  exactNumber: "Input",
  longText: "Textarea",
  repeatedDomainEntry: "ItemGroup",
  nestedRule: "AdvancedJsonLayer",
} as const

export const configFieldComponents = {
  "mystic.enabled_types": "CheckboxGroup",
  "mystic.enabled_high_risk_types": "CheckboxGroup",
  "mystic.category_weights": "SliderGroup",
  "mystic.drop_overrides": "AdvancedJsonLayer",
  "mystic.fishing_option_rate": "Slider",
  "signin.extra_fishing_chance_rate": "Slider",
  "equipment_rules.realm_tier_unlocks": "CheckboxMatrix",
  "equipment_rules.tier_default_realm": "SelectGroup",
  "equipment_rules.artifact_drop_pools": "AdvancedJsonLayer",
  "equipment_rules.artifact_power_base": "NumberFieldGroup",
  "equipment_rules.artifact_realm_power_base": "NumberFieldGroup",
  "equipment_rules.artifact_tier_power_ratio": "SliderGroup",
  "equipment_rules.artifact_grade_ratio": "SliderGroup",
  "equipment_rules.artifact_immortal_upgrade_rate": "Slider",
  item_overrides: "AdvancedJsonLayer",
  "beast_realm.card_pool_copies": "Slider",
  "beast_realm.card_overrides": "AdvancedJsonLayer",
} as const

export type DataPresentationKind =
  (typeof dataPresentation)[keyof typeof dataPresentation]

export type ConfigFieldPath = keyof typeof configFieldComponents
