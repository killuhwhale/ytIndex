import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { generateViralMoments, getTranscript, getViralMoments, getVideo } from "../api/videos";

export function VideoDetailPage() {
  const { id } = useParams();
  const [tab, setTab] = useState("summary");
  const client = useQueryClient();
  const video = useQuery({ queryKey: ["video", id], queryFn: () => getVideo(id!), enabled: Boolean(id) });
  const transcript = useQuery({ queryKey: ["transcript", id], queryFn: () => getTranscript(id!), enabled: Boolean(id) && tab === "transcript" });
  const moments = useQuery({ queryKey: ["viral", id], queryFn: () => getViralMoments(id!), enabled: Boolean(id) && tab === "viral" });
  const generate = useMutation({ mutationFn: () => generateViralMoments(id!), onSuccess: () => client.invalidateQueries({ queryKey: ["viral", id] }) });
  const item = video.data;

  if (!item) return <p>Loading video...</p>;

  return (
    <div className="space-y-4">
      <section className="flex flex-col gap-4 border bg-white p-4 md:flex-row">
        {item.thumbnail_url ? <img className="h-44 w-full object-cover md:w-72" src={item.thumbnail_url} alt="" /> : null}
        <div>
          <h1 className="text-2xl font-semibold">{item.title}</h1>
          <p className="mt-1 text-sm text-zinc-600">{item.channel_title || "Unknown channel"}</p>
          <a className="mt-3 inline-block text-blue-700" href={item.canonical_url} target="_blank" rel="noreferrer">Open on YouTube</a>
        </div>
      </section>
      <div className="flex gap-2 border-b">
        {["summary", "transcript", "viral"].map((name) => (
          <button key={name} className={`px-3 py-2 ${tab === name ? "border-b-2 border-blue-600" : ""}`} onClick={() => setTab(name)}>{name}</button>
        ))}
      </div>
      {tab === "summary" ? (
        <section className="space-y-5 border bg-white p-4">
          <div>
            <h2 className="mb-2 text-lg font-semibold">Summary</h2>
            <p className="whitespace-pre-line text-sm leading-6">{item.summary?.detailed_summary || item.summary?.short_summary || "No summary yet."}</p>
          </div>
          {item.summary?.key_points?.length ? (
            <div>
              <h3 className="mb-2 font-medium">Key points</h3>
              <ul className="list-disc space-y-1 pl-5 text-sm">{item.summary.key_points.map((point) => <li key={point}>{point}</li>)}</ul>
            </div>
          ) : null}
        </section>
      ) : null}
      {tab === "transcript" ? (
        <section className="space-y-2">
          {transcript.data?.map((segment) => (
            <p key={segment.id} className="border bg-white p-3 text-sm">
              <a className="mr-3 text-blue-700" href={segment.youtube_timestamp_url} target="_blank" rel="noreferrer">{Math.floor(segment.start_ms / 1000)}s</a>
              {segment.text}
            </p>
          ))}
        </section>
      ) : null}
      {tab === "viral" ? (
        <section className="space-y-3">
          <button className="inline-flex items-center gap-2 bg-zinc-950 px-4 py-2 text-white" onClick={() => generate.mutate()}><Sparkles size={16} /> Generate moments</button>
          {moments.data?.map((moment) => (
            <article key={moment.id} className="border bg-white p-4">
              <h3 className="font-medium">{moment.hook}</h3>
              <p className="mt-2 text-sm">{moment.quote}</p>
              <p className="mt-2 text-sm text-zinc-600">{moment.reason}</p>
              <a className="mt-2 inline-block text-sm text-blue-700" href={moment.youtube_timestamp_url} target="_blank" rel="noreferrer">Open timestamp · {moment.score}</a>
            </article>
          ))}
        </section>
      ) : null}
    </div>
  );
}
