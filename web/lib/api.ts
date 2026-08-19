const API_BASE_URL =
  process.env.API_BASE_URL;

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

export function mediaUrl(url: string): string {
  return url;
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
