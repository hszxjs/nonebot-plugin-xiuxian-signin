import { Activity, Boxes, Compass } from "lucide-react";

const tiles = [
  { label: "玩家", value: "--", icon: Activity },
  { label: "物品", value: "--", icon: Boxes },
  { label: "秘境", value: "--", icon: Compass },
];

export default function App() {
  return (
    <main className="min-h-screen bg-background p-6 text-foreground">
      <section className="mx-auto grid max-w-5xl gap-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">修仙签到后台</h1>
            <p className="mt-2 text-sm text-muted-foreground">总览</p>
          </div>
          <div className="inline-flex w-fit items-center rounded-md border border-border bg-card px-3 py-2 text-sm text-card-foreground shadow-sm">
            本地
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          {tiles.map((tile) => {
            const Icon = tile.icon;
            return (
              <section key={tile.label} className="rounded-lg border border-border bg-card p-5 text-card-foreground shadow-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm text-muted-foreground">{tile.label}</span>
                  <Icon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
                </div>
                <div className="mt-4 text-2xl font-semibold tracking-normal">{tile.value}</div>
              </section>
            );
          })}
        </div>
      </section>
    </main>
  );
}