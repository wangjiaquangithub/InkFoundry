import { useEffect, useState } from "react";
import { api } from "../api/client";

interface TokenStats {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  cost_usd?: number;
}

interface TokenRecord {
  id: number;
  task: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  timestamp: string;
}

interface TokenChartProps {
  stats?: TokenStats;
  records?: TokenRecord[];
}

export function TokenChart({ stats: initialStats, records: initialRecords }: TokenChartProps) {
  const [loading, setLoading] = useState(!initialStats);
  const [data, setData] = useState<{ stats: TokenStats | null; records: TokenRecord[] }>({
    stats: initialStats || null,
    records: initialRecords || [],
  });

  useEffect(() => {
    if (initialStats && initialRecords) {
      setData({ stats: initialStats, records: initialRecords });
      setLoading(false);
      return;
    }
    Promise.all([api.getTokenStats(), api.getTokenRecords()])
      .then(([statsRes, recordsRes]) => {
        setData({
          stats: statsRes.data || null,
          records: recordsRes.data?.records || [],
        });
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [initialStats, initialRecords]);

  if (loading) return <div className="text-center py-8 text-gray-400">Loading token data...</div>;
  if (!data.stats) return <div className="text-center py-8 text-gray-400">No token data available</div>;

  const s = data.stats;
  const promptPct = s.total_tokens > 0 ? (s.total_prompt_tokens / s.total_tokens) * 100 : 0;
  const completionPct = s.total_tokens > 0 ? (s.total_completion_tokens / s.total_tokens) * 100 : 0;

  const taskUsage: Record<string, number> = {};
  data.records.forEach(r => {
    taskUsage[r.task] = (taskUsage[r.task] || 0) + r.total_tokens;
  });
  const topTasks = Object.entries(taskUsage)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  const formatNum = (n: number) => n >= 1000 ? `${(n / 1000).toFixed(1)}k` : `${n}`;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold text-white mb-4">Token Usage</h3>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-700 rounded p-3">
          <div className="text-sm text-gray-400">Prompt</div>
          <div className="text-xl font-bold text-blue-400">{formatNum(s.total_prompt_tokens)}</div>
        </div>
        <div className="bg-gray-700 rounded p-3">
          <div className="text-sm text-gray-400">Completion</div>
          <div className="text-xl font-bold text-green-400">{formatNum(s.total_completion_tokens)}</div>
        </div>
        <div className="bg-gray-700 rounded p-3">
          <div className="text-sm text-gray-400">Total</div>
          <div className="text-xl font-bold text-yellow-400">{formatNum(s.total_tokens)}</div>
        </div>
      </div>

      {/* Bar chart */}
      <div className="space-y-2">
        <div className="text-sm text-gray-400 mb-1">Token Distribution</div>
        <div className="flex h-6 rounded overflow-hidden">
          <div className="bg-blue-500 transition-all" style={{ width: `${promptPct}%` }} />
          <div className="bg-green-500 transition-all" style={{ width: `${completionPct}%` }} />
        </div>
        <div className="flex gap-4 text-xs text-gray-400">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500"></span>Prompt ({promptPct.toFixed(1)}%)</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span>Completion ({completionPct.toFixed(1)}%)</span>
        </div>
      </div>

      {/* Top tasks */}
      {topTasks.length > 0 && (
        <div className="mt-6">
          <div className="text-sm text-gray-400 mb-2">Top Tasks by Token Usage</div>
          <div className="space-y-2">
            {topTasks.map(([task, tokens]) => (
              <div key={task} className="flex items-center gap-3">
                <span className="text-xs text-gray-300 w-24 truncate" title={task}>{task}</span>
                <div className="flex-1 h-3 bg-gray-700 rounded overflow-hidden">
                  <div
                    className="h-full bg-purple-500 rounded"
                    style={{ width: `${Math.min((tokens / s.total_tokens) * 100, 100)}%` }}
                  />
                </div>
                <span className="text-xs text-gray-400 w-12 text-right">{formatNum(tokens)}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
