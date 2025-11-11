import Link from "next/link";
import { notFound } from "next/navigation";

const topics: Record<string, { title: string; description: string; tasksInQueue: number }[]> = {
  logic: [
    {
      title: "Propositional Logic",
      description: "Symbolic reasoning drills covering conjunction, disjunction, and implication.",
      tasksInQueue: 1,
    },
    {
      title: "Predicate Logic",
      description: "Quantifiers and inference on structured predicates.",
      tasksInQueue: 3,
    },
  ],
  ethics: [
    {
      title: "Utilitarian Case Studies",
      description: "Contrast outcomes across stakeholder groups.",
      tasksInQueue: 0,
    },
  ],
};

type WorkspacePageProps = {
  params: {
    id: string;
  };
};

export default function WorkspaceDetailPage({ params }: WorkspacePageProps) {
  const workspaceTopics = topics[params.id];

  if (!workspaceTopics) {
    notFound();
  }

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-8 px-6 py-12">
      <header className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-primary-700">Workspace: {params.id}</h1>
            <p className="text-slate-600">
              Monitor Celery queues and explore available learning topics.
            </p>
          </div>
          <Link href="/workspaces" className="text-sm font-semibold text-primary-500">
            ← Back to workspaces
          </Link>
        </div>
      </header>
      <div className="space-y-4">
        {workspaceTopics.map((topic) => (
          <article key={topic.title} className="rounded-lg border border-slate-200 bg-white p-6">
            <h2 className="text-xl font-semibold text-primary-700">{topic.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{topic.description}</p>
            <p className="mt-4 text-xs uppercase tracking-wide text-slate-400">
              {topic.tasksInQueue} queued tasks
            </p>
          </article>
        ))}
      </div>
    </main>
  );
}
