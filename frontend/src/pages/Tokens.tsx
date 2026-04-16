import { useState, useEffect } from "react";
import { api } from "../api/client";

interface TokenStats {
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_requests: number;
  total_cost_estimate: number;
  by_model: Record<string, number>;
  by_task: Record<string, number>;
}

interface TokenRecord {
  model: string;
  task: string;
  prompt_tokens: number;
  completion_tokens: number;
  timestamp: number;
  total_tokens?: number;
  cost_estimate?: number;
}

export function Tokens() {
  const [tokenStats, setTokenStats] = useState<TokenStats | null>(null);
  const [tokenRecords, setTokenRecords] = useState<TokenRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statsRes, recordsRes] = await Promise.all([
        api.getTokenStats(),
        api.getTokenRecords(),
      ]);
      setTokenStats(statsRes.data);
      setTokenRecords(recordsRes.data.records || []);
    } catch {
      console.error("Failed to load token data");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p className="text-gray-400">加载 Token 数据中...</p></div>;
  }

  if (!tokenStats) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="text-5xl mb-4">📊</div>
          <h2 className="text-xl font-semibold mb-2">暂无 Token 数据</h2>
          <p className="text-gray-400">使用 AI 生成内容后，Token 用量数据会在这里显示</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full overflow-auto p-6">
      <div className="mb-6">
        <h2 className="text-lg font-semibold">当前项目 Token 用量统计</h2>
        <p className="text-sm text-gray-400 mt-1">查看当前项目在创作过程中的 Token 消耗和最近请求记录</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-400 mb-1">总 Token</p>
          <p className="text-xl font-bold">{tokenStats.total_tokens.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-400 mb-1">请求次数</p>
          <p className="text-xl font-bold">{tokenStats.total_requests}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-400 mb-1">Prompt Tokens</p>
          <p className="text-xl font-bold">{tokenStats.total_prompt_tokens.toLocaleString()}</p>
        </div>
        <div className="bg-white rounded-xl border p-4">
          <p className="text-xs text-gray-400 mb-1">预估费用 ($)</p>
          <p className="text-xl font-bold">${tokenStats.total_cost_estimate.toFixed(6)}</p>
        </div>
      </div>

      {/* By Model */}
      {Object.keys(tokenStats.by_model).length > 0 && (
        <div className="bg-white rounded-xl border p-6 mb-6">
          <h3 className="font-semibold mb-4">各模型用量</h3>
          <div className="space-y-2">
            {Object.entries(tokenStats.by_model).map(([model, tokens]) => (
              <div key={model} className="flex justify-between text-sm border-b pb-2 last:border-0">
                <span className="font-medium">{model}</span>
                <span className="text-gray-500">{tokens.toLocaleString()} tokens</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* By Task */}
      {Object.keys(tokenStats.by_task).length > 0 && (
        <div className="bg-white rounded-xl border p-6 mb-6">
          <h3 className="font-semibold mb-4">各任务用量</h3>
          <div className="space-y-2">
            {Object.entries(tokenStats.by_task).map(([task, tokens]) => (
              <div key={task} className="flex justify-between text-sm border-b pb-2 last:border-0">
                <span className="font-medium">{task}</span>
                <span className="text-gray-500">{tokens.toLocaleString()} tokens</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent records */}
      {tokenRecords.length > 0 && (
        <div className="bg-white rounded-xl border p-6">
          <h3 className="font-semibold mb-4">最近记录</h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {tokenRecords.slice(0, 20).map((r, i) => (
              <div key={i} className="flex justify-between items-center text-sm border-b pb-2">
                <div>
                  <span className="font-medium">{r.model}</span>
                  <span className="text-gray-400 ml-2">{r.task}</span>
                </div>
                <div className="text-gray-500">
                  {(r.prompt_tokens + r.completion_tokens).toLocaleString()} tokens
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
