import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Button } from "../components/ui/button";
import type { Outline } from "../types";

export function Outline() {
  const navigate = useNavigate();
  const [outline, setOutline] = useState<Outline | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadOutline();
  }, []);

  const loadOutline = async () => {
    setLoading(true);
    try {
      const res = await api.getOutline();
      setOutline(res.data.outline);
    } catch {
      setOutline(null);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    setError(null);
    try {
      const pending = JSON.parse(localStorage.getItem("pendingProject") || "{}");
      const res = await api.generateOutline({
        genre: pending.genre || "xuanhuan",
        title: pending.title || "Untitled",
        summary: pending.summary || "",
        total_chapters: pending.totalChapters || 100,
      });
      setOutline(res.data.outline);
    } catch (e: any) {
      setError(e.message || "生成大纲失败");
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">加载中...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate("/")}>
            返回
          </Button>
          <h1 className="text-xl font-bold">小说大纲</h1>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleGenerate} disabled={generating}>
            {generating ? "生成中..." : "重新生成"}
          </Button>
          {outline && (
            <Button onClick={() => navigate("/workspace")}>
              进入工作区
            </Button>
          )}
        </div>
      </header>

      <div className="max-w-5xl mx-auto p-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-4">
            {error}
          </div>
        )}

        {!outline ? (
          <div className="bg-white rounded-xl border p-12 text-center">
            <div className="text-5xl mb-4">📝</div>
            <h2 className="text-xl font-semibold mb-2">还没有大纲</h2>
            <p className="text-gray-400 mb-6">
              先生成你的小说大纲，AI 会根据题材和简介生成完整的故事结构
            </p>
            <Button onClick={handleGenerate} disabled={generating}>
              {generating ? "生成中..." : "生成大纲"}
            </Button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Info Card */}
            <div className="bg-white rounded-xl border p-6">
              <h2 className="text-lg font-semibold mb-3">{outline.title}</h2>
              <p className="text-gray-600 mb-4">{outline.summary || "暂无简介"}</p>
              <div className="flex gap-4 text-sm text-gray-500">
                <span>总章数: {outline.total_chapters}</span>
                <span>结构: {outline.arc}</span>
              </div>
              {outline.genre_rules.length > 0 && (
                <div className="mt-4">
                  <h3 className="text-sm font-medium mb-2">题材规则</h3>
                  <div className="flex flex-wrap gap-2">
                    {outline.genre_rules.map((rule, i) => (
                      <span key={i} className="bg-blue-50 text-blue-700 px-2 py-1 rounded text-xs">
                        {rule}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Volume Plans */}
            {outline.volume_plans.length > 0 && (
              <div className="bg-white rounded-xl border p-6">
                <h3 className="font-semibold mb-4">分卷计划</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {outline.volume_plans.map((vol) => (
                    <div key={vol.volume} className="border rounded-lg p-4">
                      <h4 className="font-medium">{vol.name}</h4>
                      <p className="text-sm text-gray-500 mt-1">章节: {vol.chapters}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Chapter Summaries */}
            <div className="bg-white rounded-xl border p-6">
              <h3 className="font-semibold mb-4">章节概要</h3>
              <div className="max-h-96 overflow-y-auto space-y-2">
                {outline.chapter_summaries.map((ch) => (
                  <div key={ch.chapter_num} className="flex items-start gap-3 p-3 border rounded-lg">
                    <span className="text-sm font-medium text-blue-600 whitespace-nowrap">
                      第{ch.chapter_num}章
                    </span>
                    <p className="text-sm text-gray-600 flex-1">{ch.summary}</p>
                    <span className="text-xs text-gray-400 whitespace-nowrap">
                      张力: {ch.tension}/10
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Tension Curve */}
            <div className="bg-white rounded-xl border p-6">
              <h3 className="font-semibold mb-4">张力曲线</h3>
              <div className="flex items-end gap-0.5 h-24">
                {outline.tension_curve.map((t, i) => (
                  <div
                    key={i}
                    className="flex-1 bg-blue-400 rounded-t"
                    style={{ height: `${(t / 10) * 100}%`, minHeight: "2px" }}
                    title={`第${i + 1}章: ${t}`}
                  />
                ))}
              </div>
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>第1章</span>
                <span>第{outline.tension_curve.length}章</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
