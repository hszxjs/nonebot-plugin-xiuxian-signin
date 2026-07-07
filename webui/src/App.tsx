import { Activity, ShieldCheck } from "lucide-react";

export default function App() {
  return (
    <main className="min-h-screen bg-background p-6 text-foreground">
      <section className="mx-auto grid max-w-5xl gap-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-normal">修仙签到后台</h1>
            <p className="mt-2 text-sm text-muted-foreground">React admin shell is ready.</p>
          </div>
          <div className="inline-flex w-fit items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm text-card-foreground shadow-sm">
            <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            <span>Static bundle ready</span>
          </div>
        </div>

        <div className="rounded-lg border border-border bg-card p-5 text-card-foreground shadow-sm">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-md bg-muted">
              <Activity className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-base font-medium">Admin WebUI Skeleton</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Task 4 provides the Vite, React, and Tailwind foundation for later pages.
              </p>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
