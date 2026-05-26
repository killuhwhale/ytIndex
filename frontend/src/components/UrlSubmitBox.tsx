import { useMutation } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createIngest } from "../api/ingest";

export function UrlSubmitBox() {
  const [input, setInput] = useState("");
  const [manualTranscript, setManualTranscript] = useState("");
  const [ownedContent, setOwnedContent] = useState(false);
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: () => createIngest(input, manualTranscript, ownedContent),
    onSuccess: (data) => navigate(`/batches/${data.batch_id}`)
  });

  return (
    <section className="border bg-white p-4">
      <h1 className="mb-3 text-2xl font-semibold">Ingest videos</h1>
      <textarea className="h-28 w-full border p-3" value={input} onChange={(event) => setInput(event.target.value)} placeholder="Paste a YouTube video URL, or one URL per line" />
      <textarea className="mt-3 h-24 w-full border p-3" value={manualTranscript} onChange={(event) => setManualTranscript(event.target.value)} placeholder="Optional manual transcript for permitted content" />
      <label className="mt-3 flex items-start gap-2 text-sm text-zinc-700">
        <input className="mt-1" type="checkbox" checked={ownedContent} onChange={(event) => setOwnedContent(event.target.checked)} />
        I own this media or have rights to download audio for transcription if subtitles are unavailable.
      </label>
      <button className="mt-3 inline-flex items-center gap-2 bg-zinc-950 px-4 py-2 text-white disabled:opacity-50" disabled={!input || mutation.isPending} onClick={() => mutation.mutate()}>
        <Send size={16} /> Start ingest
      </button>
      {mutation.error ? <p className="mt-2 text-sm text-red-700">Ingest failed to start.</p> : null}
    </section>
  );
}
