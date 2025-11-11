import Link from "next/link";

const features = [
  {
    title: "Workspace Insights",
    description: "Dive into curated topics backed by Socratic dialogue prompts.",
  },
  {
    title: "Collaborative Tasks",
    description: "Queue long-running analysis jobs without blocking the experience.",
  },
  {
    title: "Unified Knowledge",
    description: "Share models and schemas across services via the common package.",
  },
];

export default function HomePage() {
  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-12 px-6 py-16">
      <section className="space-y-6 text-center">
        <h1 className="text-4xl font-bold text-primary-700">Socratic Workspace</h1>
        <p className="text-lg text-slate-600">
          A unified environment for orchestrating backend knowledge services and frontend
          exploration interfaces.
        </p>
        <div className="flex justify-center gap-4">
          <Link
            href="/workspaces"
            className="rounded bg-primary-500 px-5 py-3 font-semibold text-white shadow"
          >
            View Workspaces
          </Link>
          <a
            href="https://fastapi.tiangolo.com/"
            className="rounded border border-primary-500 px-5 py-3 font-semibold text-primary-500"
          >
            API Documentation
          </a>
        </div>
      </section>
      <section className="grid gap-6 md:grid-cols-3">
        {features.map((feature) => (
          <div key={feature.title} className="rounded-lg border border-slate-200 bg-white p-6">
            <h2 className="text-xl font-semibold text-primary-700">{feature.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{feature.description}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
