import { api } from "./client";

export type IngestBatch = {
  id: string;
  status: string;
  total_count: number;
  completed_count: number;
  failed_count: number;
  jobs: IngestJob[];
  created_at: string;
};

export type IngestJob = {
  id: string;
  video_id?: string;
  source_url: string;
  status: string;
  current_step: string;
  error_message?: string | null;
};

export async function createIngest(input: string, manualTranscript?: string, ownedContent = false) {
  const { data } = await api.post("/ingest/", {
    input,
    input_type: "auto",
    manual_transcript: manualTranscript || undefined,
    owned_content: ownedContent
  });
  return data as { batch_id: string; job_ids: string[] };
}

export async function getBatch(id: string) {
  const { data } = await api.get(`/ingest/batches/${id}/`);
  return data as IngestBatch;
}

export async function retryJob(id: string) {
  const { data } = await api.post(`/ingest/jobs/${id}/retry/`);
  return data as IngestJob;
}
