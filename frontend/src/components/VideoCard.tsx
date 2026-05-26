import { Link } from "react-router-dom";
import type { Video } from "../api/videos";
import { Trash2 } from "lucide-react";

export function VideoCard({ video, onDelete }: { video: Video; onDelete: (video: Video) => void }) {
  return (
    <article className="flex items-start gap-4 border bg-white p-3 hover:border-blue-500">
      <Link to={`/videos/${video.id}`} className="flex min-w-0 flex-1 gap-4">
        {video.thumbnail_url ? <img className="h-24 w-36 flex-none object-cover" src={video.thumbnail_url} alt="" /> : null}
        <div className="min-w-0">
          <h3 className="font-medium">{video.title}</h3>
          <p className="mt-1 text-sm text-zinc-600">{video.channel_title || "Unknown channel"}</p>
          {video.summary?.short_summary ? <p className="mt-2 line-clamp-2 text-sm">{video.summary.short_summary}</p> : null}
        </div>
      </Link>
      <button
        className="inline-flex h-9 w-9 flex-none items-center justify-center border text-red-700 hover:bg-red-50"
        title="Delete video"
        aria-label={`Delete ${video.title}`}
        onClick={() => onDelete(video)}
      >
        <Trash2 size={16} />
      </button>
    </article>
  );
}
