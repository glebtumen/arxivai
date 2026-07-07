import Link from "next/link";
import { notFound } from "next/navigation";
import { fetchItem, mediaUrl } from "@/lib/api";

export default async function ItemPage({
  params,
}: {
  params: { id: string };
}) {
  const item = await fetchItem(params.id).catch(() => null);
  if (!item) {
    notFound();
  }

  return (
    <div>
      <Link href="/" className="mb-4 inline-block text-sm text-blue-600">
        ← Back to library
      </Link>

      <div className="rounded-lg border bg-white p-6 shadow-sm">
        <h2 className="mb-2 text-2xl font-bold">
          {item.title || "Untitled"}
        </h2>

        <div className="mb-4 flex flex-wrap gap-2">
          {(item.tags || []).map((tag) => (
            <span
              key={tag}
              className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600"
            >
              {tag}
            </span>
          ))}
        </div>

        <p className="mb-6 whitespace-pre-line text-slate-700">
          {item.summary || "No summary available."}
        </p>

        {item.frame_paths && item.frame_paths.length > 0 && (
          <div className="mb-6">
            <h3 className="mb-2 text-sm font-semibold text-slate-500">
              Key frames
            </h3>
            <div className="grid grid-cols-3 gap-3">
              {item.frame_paths.map((path) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={path}
                  src={mediaUrl(path)}
                  alt="frame"
                  className="w-full rounded object-cover"
                />
              ))}
            </div>
          </div>
        )}

        {item.transcript && (
          <details className="mb-6 rounded border bg-slate-50 p-4">
            <summary className="cursor-pointer text-sm font-semibold text-slate-500">
              Transcript
            </summary>
            <p className="mt-2 whitespace-pre-line text-sm text-slate-700">
              {item.transcript}
            </p>
          </details>
        )}

        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          Open original
        </a>
      </div>
    </div>
  );
}
