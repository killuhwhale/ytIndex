import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { deleteVideo, listVideos, type Video } from "../api/videos";
import { UrlSubmitBox } from "../components/UrlSubmitBox";
import { VideoCard } from "../components/VideoCard";

export function DashboardPage() {
  const queryClient = useQueryClient();
  const videos = useQuery({ queryKey: ["videos"], queryFn: listVideos });
  const deleteMutation = useMutation({
    mutationFn: deleteVideo,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["videos"] })
  });

  function handleDelete(video: Video) {
    const confirmed = window.confirm(`Delete "${video.title}" and its transcript, chunks, summary, and viral moments?`);
    if (confirmed) {
      deleteMutation.mutate(video.id);
    }
  }

  return (
    <div className="space-y-6">
      <UrlSubmitBox />
      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recently indexed</h2>
          <Link to="/search" className="text-sm text-blue-700">Search transcripts</Link>
        </div>
        <div className="space-y-3">
          {videos.data?.map((video) => <VideoCard key={video.id} video={video} onDelete={handleDelete} />)}
          {videos.data?.length === 0 ? <p className="text-sm text-zinc-600">No indexed videos yet.</p> : null}
        </div>
        {deleteMutation.error ? <p className="mt-2 text-sm text-red-700">Could not delete video.</p> : null}
      </section>
    </div>
  );
}
