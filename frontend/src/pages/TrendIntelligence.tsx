import { useState } from "react";
import { api } from "../api/client";

interface Topic {
  name: string;
  heat: number;
  trend: "up" | "stable" | "down";
}

interface GenreTrends {
  genre: string;
  top_tags: string[];
  emerging_tags: string[];
  declining_tags: string[];
}

interface TrendResult {
  topics: Topic[];
  market_insights: string[];
  recommendations: string[];
  genre_trends: GenreTrends;
}

const GENRES = [
  "玄幻", "都市", "仙侠", "历史", "科幻", "悬疑", "游戏", "体育",
  "武侠", "奇幻", "轻小说", "现实题材",
];

export function TrendIntelligence() {
  const [genre, setGenre] = useState("");
  const [keywords, setKeywords] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TrendResult | null>(null);
  const [error, setError] = useState("");

  const handleAnalyze = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.analyzeTrends({
        genre: genre || undefined,
        keywords: keywords
          ? keywords.split(/[,，\s]+/).filter(Boolean)
          : undefined,
      });
      setResult(res.data);
    } catch {
      setError("分析失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-6 py-4 border-b">
        <h1 className="text-xl font-bold">趋势洞察</h1>
        <p className="text-sm text-gray-500 mt-1">
          基于网文市场趋势，为创作提供数据参考
        </p>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto p-6 space-y-6">
          {/* Filters */}
          <div className="bg-white rounded-lg border p-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">题材选择</label>
                <select
                  value={genre}
                  onChange={(e) => setGenre(e.target.value)}
                  className="w-full border rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">全部题材</option>
                  {GENRES.map((g) => (
                    <option key={g} value={g}>{g}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">关键词（可选）</label>
                <input
                  type="text"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="多个关键词用逗号分隔..."
                  className="w-full border rounded-lg p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex justify-end mt-3">
              <button
                onClick={handleAnalyze}
                disabled={loading}
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
              >
                {loading ? "分析中..." : "开始分析"}
              </button>
            </div>
            {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
          </div>

          {/* Loading */}
          {loading && (
            <div className="text-center py-16">
              <div className="inline-block animate-spin rounded-full h-10 w-10 border-4 border-blue-200 border-t-blue-600 mb-4" />
              <p className="text-gray-500">正在分析市场趋势...</p>
            </div>
          )}

          {/* Results */}
          {result && !loading && (
            <>
              {/* Hot Topics */}
              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-medium mb-4">热门话题</h3>
                <div className="space-y-3">
                  {result.topics.map((topic) => (
                    <div key={topic.name} className="flex items-center gap-4">
                      <span className="text-sm font-medium w-20">{topic.name}</span>
                      <div className="flex-1 bg-gray-100 rounded-full h-4 overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            topic.trend === "up"
                              ? "bg-green-500"
                              : topic.trend === "down"
                              ? "bg-red-400"
                              : "bg-yellow-400"
                          }`}
                          style={{ width: `${topic.heat}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-500 w-12 text-right">{topic.heat}</span>
                      <span className="text-lg w-6">
                        {topic.trend === "up" ? "📈" : topic.trend === "down" ? "📉" : "➡️"}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Genre Trends */}
              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-medium mb-4">
                  题材趋势: {result.genre_trends.genre}
                </h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-sm text-green-600 font-medium mb-2">热门标签</div>
                    <div className="flex flex-wrap gap-2">
                      {result.genre_trends.top_tags.map((tag) => (
                        <span key={tag} className="px-2 py-1 bg-green-50 text-green-700 rounded text-xs">{tag}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-blue-600 font-medium mb-2">新兴标签</div>
                    <div className="flex flex-wrap gap-2">
                      {result.genre_trends.emerging_tags.map((tag) => (
                        <span key={tag} className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs">{tag}</span>
                      ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-red-600 font-medium mb-2">衰退标签</div>
                    <div className="flex flex-wrap gap-2">
                      {result.genre_trends.declining_tags.map((tag) => (
                        <span key={tag} className="px-2 py-1 bg-red-50 text-red-700 rounded text-xs">{tag}</span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Market Insights */}
              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-medium mb-3">市场洞察</h3>
                <ul className="space-y-2">
                  {result.market_insights.map((insight, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="text-blue-500 mt-0.5">•</span>
                      {insight}
                    </li>
                  ))}
                </ul>
              </div>

              {/* Recommendations */}
              <div className="bg-white rounded-lg border p-4">
                <h3 className="font-medium mb-3">创作建议</h3>
                <ul className="space-y-2">
                  {result.recommendations.map((rec, idx) => (
                    <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="text-green-500 mt-0.5">✓</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            </>
          )}

          {/* Empty State */}
          {!result && !loading && (
            <div className="text-center py-20 text-gray-400">
              <div className="text-5xl mb-4">📊</div>
              <p className="text-lg font-medium">选择题材并点击分析</p>
              <p className="text-sm mt-1">AI 将为您生成最新的市场趋势报告</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
