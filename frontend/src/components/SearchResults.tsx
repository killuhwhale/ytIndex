import type { SearchResult } from "../api/search";

export function SearchResults({ results }: { results: SearchResult[] }) {
  return (
    <div className="space-y-3">
      {results.map((result) => (
        <article key={`${result.video_id}-${result.start_ms}`} className="border bg-white p-4">
          <div className="flex gap-3">
            {result.thumbnail_url ? <img className="h-20 w-32 object-cover" src={result.thumbnail_url} alt="" /> : null}
            <div>
              <h3 className="font-medium">{result.title}</h3>
              <p className="text-sm text-zinc-600">{result.channel_title}</p>
              <p className="mt-2 text-sm">{result.snippet}</p>
              <div className="mt-2 flex items-center gap-3 text-sm">
                <a className="text-blue-700" href={result.youtube_timestamp_url} target="_blank" rel="noreferrer">Open timestamp</a>
                <span>{result.match_type} · {result.score}</span>
              </div>
              <p className="mt-1 text-xs text-zinc-500">{result.why}</p>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}
