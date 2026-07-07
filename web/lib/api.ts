const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export interface Item {
  id: number;
  url: string;
  status: string;
  error_message?: string | null;
  title?: string | null;
  summary?: string | null;
  transcript?: string | null;
  tags: string[];
  frame_paths: string[];
  video_path?: string | null;
  created_at: string;
}

export function mediaUrl(relativePath: string): string {
  return `${API_BASE_URL}/media/${relativePath}`;
}

export async function fetchItems(): Promise<Item[]> {
  const res = await fetch(`${API_BASE_URL}/items`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch items");
  return res.json();
}

export async function fetchItem(id: string): Promise<Item> {
  const res = await fetch(`${API_BASE_URL}/items/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch item");
  return res.json();
}
