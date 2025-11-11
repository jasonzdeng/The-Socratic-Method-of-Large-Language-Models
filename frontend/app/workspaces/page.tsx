import Link from "next/link";

type Workspace = {
  id: string;
  title: string;
  description: string;
  topics: number;
};

const workspaces: Workspace[] = [
  {
    id: "logic",
    title: "Logical Reasoning",
    description: "Curated exercises designed to sharpen deductive reasoning.",
    topics: 5,
  },
  {
    id: "ethics",
    title: "Ethics Lab",
    description: "Explore moral dilemmas through collaborative analysis.",
    topics: 8,
  },
];

export default function WorkspacesPage() {
  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-8 px-6 py-12">
      <header className="space-y-3">
        <h1 className="text-3xl font-bold text-primary-700">Workspaces</h1>
        <p className="text-slate-600">
          Select a workspace to view active topics and schedule new background processing jobs.
        </p>
      </header>
      <div className="grid gap-4 md:grid-cols-2">
        {workspaces.map((workspace) => (
          <Link
            key={workspace.id}
            href={`/workspaces/${workspace.id}`}
            className="rounded-lg border border-slate-200 bg-white p-6 transition hover:shadow-md"
          >
            <h2 className="text-xl font-semibold text-primary-700">{workspace.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{workspace.description}</p>
            <p className="mt-4 text-xs uppercase tracking-wide text-slate-400">
              {workspace.topics} topics
            </p>
          </Link>
        ))}
      </div>
    </main>
  );
}
