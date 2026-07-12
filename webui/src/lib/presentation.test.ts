import { describe, expect, it } from "vitest"

import { configFieldComponents, dataPresentation } from "@/lib/presentation"

describe("xiuxian data presentation contract", () => {
  it("maps primitive data shapes to intent-specific shadcn components", () => {
    expect(dataPresentation.boolean).toBe("Switch")
    expect(dataPresentation.shortEnum).toBe("ToggleGroup")
    expect(dataPresentation.enum).toBe("Select")
    expect(dataPresentation.multiEnum).toBe("CheckboxGroup")
    expect(dataPresentation.boundedRate).toBe("Slider")
    expect(dataPresentation.exactNumber).toBe("Input")
    expect(dataPresentation.searchableEntityList).toBe("ItemGroupWithSearch")
    expect(dataPresentation.repeatedDomainEntry).toBe("ItemGroup")
    expect(dataPresentation.nestedRule).toBe("AdvancedJsonLayer")
  })

  it("documents field-level component choices for high-risk config data", () => {
    expect(configFieldComponents["mystic.fishing_option_rate"]).toBe("Slider")
    expect(configFieldComponents["signin.extra_fishing_chance_rate"]).toBe("Slider")
    expect(configFieldComponents["mystic.enabled_types"]).toBe("CheckboxGroup")
    expect(configFieldComponents["equipment_rules.realm_tier_unlocks"]).toBe("CheckboxMatrix")
    expect(configFieldComponents["beast_realm.card_pool_copies"]).toBe("Slider")
    expect(configFieldComponents["item_overrides"]).toBe("AdvancedJsonLayer")
  })
})
