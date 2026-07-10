import { Tabs } from "antd";
import { useState } from "react";
import { EquipmentPage } from "./EquipmentPage";
import { MysticPage } from "./MysticPage";
import { confirmDiscard, type DirtyChangeHandler } from "./pageShared";

type RulesTab = "equipment" | "mystic";

export function RulesPage({ onDirtyChange }: { onDirtyChange?: DirtyChangeHandler }) {
  const [activeTab, setActiveTab] = useState<RulesTab>("equipment");
  const [dirtyTabs, setDirtyTabs] = useState<Partial<Record<RulesTab, boolean>>>({});

  function setTabDirty(tab: RulesTab, dirty: boolean) {
    setDirtyTabs((current) => {
      const next = { ...current, [tab]: dirty };
      onDirtyChange?.(Boolean(next.equipment || next.mystic));
      return next;
    });
  }

  function changeTab(nextTab: string) {
    const typedNextTab = nextTab as RulesTab;
    if (typedNextTab === activeTab) {
      return;
    }
    if (dirtyTabs[activeTab] && !confirmDiscard()) {
      return;
    }
    setActiveTab(typedNextTab);
  }

  return (
    <Tabs
      activeKey={activeTab}
      items={[
        {
          key: "equipment",
          label: dirtyTabs.equipment ? "灵器掉落 *" : "灵器掉落",
          children: <EquipmentPage onDirtyChange={(dirty) => setTabDirty("equipment", dirty)} />,
        },
        {
          key: "mystic",
          label: dirtyTabs.mystic ? "秘境掉落 *" : "秘境掉落",
          children: <MysticPage onDirtyChange={(dirty) => setTabDirty("mystic", dirty)} />,
        },
      ]}
      onChange={changeTab}
    />
  );
}
