"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { SearchResult } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, Loader2, Info } from "lucide-react";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!query) return;
    setLoading(true);
    try {
      const res = await api.search(query);
      setResults(res.results);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto p-8 space-y-8">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">Retrieval Debugger</h1>
        <p className="text-muted-foreground">Inspect raw scores across dense, sparse, and RRF stages.</p>
      </div>

      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Enter search query..." 
            className="pl-10"
          />
        </div>
        <Button onClick={handleSearch} disabled={loading}>
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : "Run Retrieval"}
        </Button>
      </div>

      <div className="overflow-x-auto border rounded-xl bg-background shadow-sm">
        <table className="w-full text-sm text-left">
          <thead className="bg-muted/50 text-muted-foreground font-medium border-b">
            <tr>
              <th className="px-4 py-3">Content Snippet</th>
              <th className="px-4 py-3">Dense Score</th>
              <th className="px-4 py-3">BM25 Score</th>
              <th className="px-4 py-3">RRF Score</th>
              <th className="px-4 py-3">Metadata</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {results.map((res, i) => (
              <tr key={res.id || i} className="hover:bg-muted/30 transition-colors">
                <td className="px-4 py-4 max-w-md">
                  <p className="line-clamp-2 text-xs italic">"{res.content}"</p>
                </td>
                <td className="px-4 py-4 font-mono text-xs">{res.dense_score?.toFixed(4) || "0.0000"}</td>
                <td className="px-4 py-4 font-mono text-xs">{res.bm25_score?.toFixed(4) || "0.0000"}</td>
                <td className="px-4 py-4 font-mono text-xs font-bold text-primary">{res.rrf_score?.toFixed(4) || "0.0000"}</td>
                <td className="px-4 py-4 space-x-1">
                  <Badge variant="outline" className="text-[10px]">{res.metadata.filename}</Badge>
                  <Badge variant="outline" className="text-[10px]">P{res.metadata.page}</Badge>
                </td>
              </tr>
            ))}
            {results.length === 0 && !loading && (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-muted-foreground">
                  <Info className="w-8 h-8 mx-auto mb-2 opacity-20" />
                  No results yet. Try a query.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
