import { api } from "./client";

export type SearchResult = {
  video_id: string;
  youtube_video_id: string;
  title: string;
  channel_title?: string | null;
  thumbnail_url?: string | null;
  start_ms: number;
  end_ms: number;
  youtube_timestamp_url: string;
  snippet: string;
  score: number;
  match_type: string;
  why: string;
};

export async function searchTranscripts(query: string, searchType: string) {
  const { data } = await api.post("/search/", { query, search_type: searchType, limit: 20, filters: {} });
  return data.results as SearchResult[];
}
