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
  const [useSharding, setUseSharding] = useState(true);
  const [authorityMode, setAuthorityMode] = useState(false);

  const handleSearch = async () => {
    if (!query) return;
    setLoading(true);
    try {
      const res = await api.search(query, 10, useSharding, { authority_mode: authorityMode });
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
        <p className="text-muted-foreground">Inspect raw scores across dense, sparse, RRF, and PageRank stages.</p>
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

      <div className="flex items-center gap-6 p-4 bg-muted/30 rounded-xl border border-dashed">
        <div className="flex items-center gap-4">
          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold uppercase text-muted-foreground">Architecture</span>
            <div className="flex items-center gap-2">
              <Button 
                size="sm" 
                variant={!useSharding ? "default" : "outline"}
                onClick={() => setUseSharding(false)}
                className="text-[10px] h-7"
              >
                Enterprise
              </Button>
              <Button 
                size="sm" 
                variant={useSharding ? "default" : "outline"}
                onClick={() => setUseSharding(true)}
                className="text-[10px] h-7"
              >
                Multi-Tenant
              </Button>
            </div>
          </div>
          
          <div className="w-px h-8 bg-border" />

          <div className="flex flex-col gap-1">
            <span className="text-[10px] font-bold uppercase text-muted-foreground">Ranking Mode</span>
            <div className="flex items-center gap-2">
              <Button 
                size="sm" 
                variant={!authorityMode ? "default" : "outline"}
                onClick={() => setAuthorityMode(false)}
                className="text-[10px] h-7"
              >
                Standard
              </Button>
              <Button 
                size="sm" 
                variant={authorityMode ? "secondary" : "outline"}
                onClick={() => setAuthorityMode(true)}
                className="text-[10px] h-7"
              >
                Authority Boost
              </Button>
            </div>
          </div>
        </div>
        
        <p className="text-[11px] text-muted-foreground italic flex-1">
          {authorityMode 
            ? "Authority mode increases PageRank influence (Alpha 0.6) for high-credibility retrieval." 
            : "Using standard PageRank influence (Alpha 0.3)."}
        </p>
      </div>

      <div className="overflow-x-auto border rounded-xl bg-background shadow-sm">
        <table className="w-full text-sm text-left">
          <thead className="bg-muted/50 text-muted-foreground font-medium border-b text-[11px] uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3">Content Snippet</th>
              <th className="px-4 py-3">Dense</th>
              <th className="px-4 py-3">RRF</th>
              <th className="px-4 py-3">PageRank</th>
              <th className="px-4 py-3">Boosted</th>
              <th className="px-4 py-3">Metadata</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {results.map((res, i) => (
              <tr key={res.id || i} className="hover:bg-muted/30 transition-colors">
                <td className="px-4 py-4 max-w-xs">
                  <p className="line-clamp-2 text-xs italic">"{res.content}"</p>
                </td>
                <td className="px-4 py-4 font-mono text-[10px]">{res.dense_score?.toFixed(4) || "0.0000"}</td>
                <td className="px-4 py-4 font-mono text-[10px]">{res.rrf_score?.toFixed(4) || "0.0000"}</td>
                <td className="px-4 py-4 font-mono text-[10px] text-blue-600 font-semibold">{res.pagerank_score?.toFixed(4) || "0.0000"}</td>
                <td className="px-4 py-4 font-mono text-xs font-bold text-primary">{res.boosted_score?.toFixed(4) || "0.0000"}</td>
                <td className="px-4 py-4 space-x-1">
                  <Badge variant="outline" className="text-[9px]">{res.metadata.filename}</Badge>
                  <Badge variant="outline" className="text-[9px]">P{res.metadata.page}</Badge>
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
