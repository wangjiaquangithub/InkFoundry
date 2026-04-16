import { useState } from "react";
import { api } from "../api/client";

interface AIIssue {
  type: string;
  severity: number;
  description: string;
}

interface AIDetectResult {
  score: number;
  issue_count: number;
  issues: AIIssue[];
  llm_feedback: string;
  suggestions: string[];
}

const typeLabels: Record<string, string> = {
  ai_cliche: "AI 套话",
  repetitive_structure: "重复结构",
  low_sensory: "感官不足",
  over_adjective: "形容词过多",
};

const typeColors: Record<string, string> = {
  ai_cliche: "bg-purple-100 text-purple-700",
  repetitive_structure: "bg-orange-100 text-orange-700",
  low_sensory: "bg-blue-100 text-blue-700",
  over_adjective: "bg-pink-100 text-pink-700",
};

export function AIDetection() {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AIDetectResult | null>(null);
  const [error, setError] = useState("");

  const handleAnalyze = async () => {
    if (!text.trim()) {
      setError("请输入要分析的文本");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await api.aiDetect(text);
      setResult(res.data);
    } catch {
      setError("分析失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  const scoreColor = (score: number) => {
    if (score > 70) return "text-green-500";
    if (score > 40) return "text-yellow-500";
    return "text-red-500";
  };

  const scoreRing = (score: number) => {
    const radius = 60;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (score / 100) * circumference;
    return { circumference, offset, color: scoreColor(score) };
  };

  const severityLabel = (severity: number) => {
    if (severity >= 0.7) return "高";
    if (severity >= 0.4) return "中";
    return "低";
  };

  const severityColor = (severity: number) => {
    if (severity >= 0.7) return "bg-red-100 text-red-700";
    if (severity >= 0.4) return "bg-yellow-100 text-yellow-700";
    return "bg-green-100 text-green-700";
  };

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-6 py-4 border-b">
        <h1 className="text-xl font-bold">AI 检测 / 去 AI 味</h1>
        <p className="text-sm text-gray-500 mt-1">
          检测文本中的 AI 写作痕迹，提供修改建议
        </p>
      </div>

      <div className="flex-1 overflow-auto">
        <div className="max-w-4xl mx-auto p-6 space-y-6">
          {/* Input */}
          <div className="bg-white rounded-lg border p-4">
            <label className="text-sm font-medium mb-2 block">输入文本</label>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="粘贴要检测的文本..."
              className="w-full h-48 border rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex justify-between items-center mt-2">
              <span className="text-xs text-gray-400">{text.length} 字</span>
              <button
                onClick={handleAnalyze}
                disabled={loading || !text.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
              >
                {loading ? "分析中..." : "开始分析"}
              </button>
            </div>
            {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
          </div>

          {/* Results */}
          {result && (
            <>
              {/* Score */}
              <div className="bg-white rounded-lg border p-6 flex items-center justify-center">
                <div className="text-center">
                  <svg width="160" height="160" className="mx-auto">
                    <circle
                      cx="80" cy="80" r="60"
                      fill="none" stroke="#e5e7eb" strokeWidth="12"
                    />
                    <circle
                      cx="80" cy="80" r="60"
                      fill="none"
                      strokeWidth="12"
                      strokeLinecap="round"
                      strokeDasharray={scoreRing(result.score).circumference}
                      strokeDashoffset={scoreRing(result.score).offset}
                      transform="rotate(-90 80 80)"
                      className={scoreRing(result.score).color.replace("text-", "stroke-")}
                    />
                    <text x="80" y="75" textAnchor="middle" className={`text-4xl font-bold ${scoreRing(result.score).color}`} fontSize="32">
                      {result.score.toFixed(0)}
                    </text>
                    <text x="80" y="100" textAnchor="middle" fill="#9ca3af" fontSize="12">
                      人类指数
                    </text>
                  </svg>
                  <p className="text-sm text-gray-500 mt-2">
                    共发现 <strong>{result.issue_count}</strong> 处 AI 痕迹
                  </p>
                </div>
              </div>

              {/* Issues List */}
              {result.issues.length > 0 && (
                <div className="bg-white rounded-lg border p-4">
                  <h3 className="font-medium mb-3">规则检测结果</h3>
                  <div className="space-y-2">
                    {result.issues.map((issue, idx) => (
                      <div key={idx} className="flex items-start gap-3 p-3 bg-gray-50 rounded">
                        <span className={`text-xs px-2 py-0.5 rounded whitespace-nowrap ${typeColors[issue.type] || "bg-gray-100 text-gray-700"}`}>
                          {typeLabels[issue.type] || issue.type}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded whitespace-nowrap ${severityColor(issue.severity)}`}>
                          {severityLabel(issue.severity)}
                        </span>
                        <span className="text-sm text-gray-700">{issue.description}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* LLM Feedback */}
              {result.llm_feedback && (
                <div className="bg-white rounded-lg border p-4">
                  <h3 className="font-medium mb-2">LLM 深度分析</h3>
                  <p className="text-sm text-gray-600">{result.llm_feedback}</p>
                </div>
              )}

              {/* Suggestions */}
              {result.suggestions.length > 0 && (
                <div className="bg-white rounded-lg border p-4">
                  <h3 className="font-medium mb-3">修改建议</h3>
                  <ul className="space-y-2">
                    {result.suggestions.map((s, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                        <span className="text-blue-500 mt-0.5">•</span>
                        {s}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {result.issues.length === 0 && (
                <div className="text-center py-8 text-green-600">
                  <p className="text-lg">未发现 AI 写作痕迹</p>
                  <p className="text-sm text-gray-500 mt-1">文本风格自然，无需修改</p>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
