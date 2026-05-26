import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCcw } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { getBatch, retryJob } from "../api/ingest";

export function BatchDetailPage() {
  const { id } = useParams();
  const queryClient = useQueryClient();
  const batch = useQuery({ queryKey: ["batch", id], queryFn: () => getBatch(id!), enabled: Boolean(id), refetchInterval: 3000 });
  const retry = useMutation({ mutationFn: retryJob, onSuccess: () => queryClient.invalidateQueries({ queryKey: ["batch", id] }) });
  const value = batch.data;
  const progress = value && value.total_count ? Math.round(((value.completed_count + value.failed_count) / value.total_count) * 100) : 0;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Batch</h1>
      {value ? (
        <>
          <div className="border bg-white p-4">
            <div className="flex justify-between text-sm">
              <span>{value.status}</span>
              <span>{value.completed_count} completed · {value.failed_count} failed · {value.total_count} total</span>
            </div>
            <div className="mt-3 h-2 bg-zinc-200"><div className="h-2 bg-blue-600" style={{ width: `${progress}%` }} /></div>
          </div>
          <div className="overflow-hidden border bg-white">
            <table className="w-full text-left text-sm">
              <thead className="bg-zinc-100"><tr><th className="p-3">Source</th><th>Status</th><th>Step</th><th>Action</th></tr></thead>
              <tbody>
                {value.jobs.map((job) => (
                  <tr key={job.id} className="border-t">
                    <td className="p-3">{job.video_id ? <Link className="text-blue-700" to={`/videos/${job.video_id}`}>{job.source_url}</Link> : job.source_url}</td>
                    <td>{job.status}</td>
                    <td>{job.error_message || job.current_step}</td>
                    <td>{job.status === "failed" ? <button className="inline-flex items-center gap-1 text-blue-700" onClick={() => retry.mutate(job.id)}><RefreshCcw size={14} /> Retry</button> : null}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : <p>Loading batch...</p>}
    </div>
  );
}
