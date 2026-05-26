import { useMutation } from "@tanstack/react-query";
import { Search } from "lucide-react";
import { useState } from "react";
import { searchTranscripts } from "../api/search";
import { SearchResults } from "../components/SearchResults";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [searchType, setSearchType] = useState("hybrid");
  const mutation = useMutation({ mutationFn: () => searchTranscripts(query, searchType) });
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Search transcripts</h1>
      <div className="border bg-white p-4">
        <div className="flex flex-col gap-3 md:flex-row">
          <input className="min-w-0 flex-1 border p-2" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Which video mentioned topic X?" />
          <select className="border p-2" value={searchType} onChange={(event) => setSearchType(event.target.value)}>
            <option value="hybrid">Hybrid</option>
            <option value="keyword">Keyword</option>
            <option value="semantic">Semantic</option>
          </select>
          <button className="inline-flex items-center justify-center gap-2 bg-zinc-950 px-4 py-2 text-white" onClick={() => mutation.mutate()} disabled={!query || mutation.isPending}>
            <Search size={16} /> Search
          </button>
        </div>
      </div>
      {mutation.data ? <SearchResults results={mutation.data} /> : null}
    </div>
  );
}
