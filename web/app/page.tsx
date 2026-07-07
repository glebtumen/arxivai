import Link from "next/link";
import { fetchItems, mediaUrl } from "@/lib/api";

export default async function LibraryPage() {
  const items = await fetchItems().catch(() => []);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-700">
          {items.length} saved item{items.length === 1 ? "" : "s"}
        </h2>
      </div>

      {items.length === 0 && (
        <p className="text-slate-500">
          Nothing saved yet. Send a link to the Telegram bot to get started.
        </p>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {items.map((item) => (
          <Link
            key={item.id}
            href={`/item/${item.id}`}
            className="block rounded-lg border bg-white p-4 shadow-sm transition hover:shadow-md"
          >
            {item.frame_paths && item.frame_paths[0] ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={mediaUrl(item.frame_paths[0])}
                alt={item.title || "frame"}
                className="mb-3 h-40 w-full rounded object-cover"
              />
            ) : (
              <div className="mb-3 flex h-40 w-full items-center justify-center rounded bg-slate-100 text-slate-400">
                {item.status === "processing" ? "Processing..." : "No preview"}
              </div>
            )}
            <h3 className="mb-1 truncate font-semibold">
              {item.title || "Untitled"}
            </h3>
            <p className="mb-2 line-clamp-2 text-sm text-slate-600">
              {item.summary || "No summary yet."}
            </p>
            <div className="flex flex-wrap gap-1">
              {(item.tags || []).map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600"
                >
                  {tag}
                </span>
              ))}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
