import { api } from "./client";

export type Video = {
  id: string;
  youtube_video_id: string;
  canonical_url: string;
  title: string;
  channel_title?: string | null;
  thumbnail_url?: string | null;
  summary?: VideoSummary;
};

export type VideoSummary = {
  short_summary: string;
  detailed_summary: string;
  key_points: string[];
  topics: Array<{ name: string; summary: string; start_ms?: number; end_ms?: number }>;
  important_quotes: Array<{ quote: string; start_ms?: number; end_ms?: number; reason?: string }>;
};

export type TranscriptSegment = {
  id: string;
  start_ms: number;
  end_ms: number;
  text: string;
  youtube_timestamp_url: string;
};

export type ViralMoment = {
  id: string;
  start_ms: number;
  end_ms: number;
  hook: string;
  quote: string;
  reason: string;
  score: number;
  suggested_title?: string;
  suggested_caption?: string;
  tags: string[];
  youtube_timestamp_url: string;
};

export async function listVideos() {
  const { data } = await api.get("/videos/");
  return data as Video[];
}

export async function getVideo(id: string) {
  const { data } = await api.get(`/videos/${id}/`);
  return data as Video;
}

export async function deleteVideo(id: string) {
  await api.delete(`/videos/${id}/`);
}

export async function getTranscript(id: string) {
  const { data } = await api.get(`/videos/${id}/transcript/`);
  return data.segments as TranscriptSegment[];
}

export async function getViralMoments(id: string) {
  const { data } = await api.get(`/videos/${id}/viral-moments/`);
  return data.results as ViralMoment[];
}

export async function generateViralMoments(id: string) {
  await api.post(`/videos/${id}/viral-moments/`);
}
