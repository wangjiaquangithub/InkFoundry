import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { api, type ApiStatusResponse } from "../api/client";
import { useAppContext } from "../app-context";
import { Button } from "../components/ui/button";
import { getCoreChainReadiness } from "../lib/core-chain-readiness";
import type { Outline } from "../types";

const DEFAULT_OUTLINE_CHAPTERS = 100;

const getErrorMessage = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    return error.message;
  }
  return error instanceof Error ? error.message : "生成大纲失败";
};

export function Outline() {
  const navigate = useNavigate();
  const { currentBook } = useAppContext();
  const [outline, setOutline] = useState<Outline | null>(null);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [generationMode, setGenerationMode] = useState<"model" | "fallback" | null>(null);
  const [statusSnapshot, setStatusSnapshot] = useState<ApiStatusResponse | null>(null);
  const [outlineAvailability, setOutlineAvailability] = useState<boolean | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const loadOutline = async () => {
      setLoading(true);
      setGenerationMode(null);
      setSuccessMessage(null);
      const [outlineRes, statusRes] = await Promise.allSettled([api.getOutline(), api.status()]);

      if (cancelled) {
        return;
      }

      if (outlineRes.status === "fulfilled") {
        setOutline(outlineRes.value.data.outline);
        setOutlineAvailability(Boolean(outlineRes.value.data.outline));
      } else {
        setOutline(null);
        setOutlineAvailability(null);
        setGenerationMode(null);
      }

      if (statusRes.status === "fulfilled") {
        setStatusSnapshot(statusRes.value.data);
      } else {
        setStatusSnapshot(null);
      }

      setLoading(false);
    };

    void loadOutline();

    return () => {
      cancelled = true;
    };
  }, [currentBook?.id]);

  const handleGenerate = async () => {
    if (!currentBook) {
      setError("请先进入一个项目");
      return;
    }

    if (statusSnapshot?.core_chain_readiness?.project_brief_ready === false) {
      setError("请先回到项目页填写故事简介，再生成大纲");
      return;
    }

    setGenerating(true);
    setError(null);
    setSuccessMessage(null);
    try {
      const res = await api.generateOutline({
        genre: currentBook.genre,
        title: currentBook.title,
        summary: currentBook.summary.trim() ? currentBook.summary : undefined,
        total_chapters: currentBook.targetChapters || DEFAULT_OUTLINE_CHAPTERS,
      });
      setOutline(res.data.outline);
      setOutlineAvailability(true);
      setGenerationMode(res.data.mode);
      let statusFacts = statusSnapshot?.core_chain_readiness ?? null;
      try {
        const statusRes = await api.status();
        setStatusSnapshot(statusRes.data);
        statusFacts = statusRes.data.core_chain_readiness;
      } catch {
        setStatusSnapshot(null);
      }
      setSuccessMessage(
        statusFacts?.real_model_ready === true
          ? "大纲已生成，下一步可以直接进入章节页开始创作。"
          : statusFacts?.real_model_ready === false
            ? "大纲已生成，下一步请先去设置模型，再进入章节页开始创作。"
            : "大纲已生成，下一步可去设置页检查模型状态，或刷新后再继续。"
      );
    } catch (e: unknown) {
      setError(getErrorMessage(e));
    } finally {
      setGenerating(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p className="text-gray-400">加载中...</p></div>;
  }

  const chainReadiness = getCoreChainReadiness({
    hasProjectSummary: statusSnapshot ? Boolean(currentBook?.summary.trim()) : null,
    hasOutline: outline ? true : outlineAvailability,
    hasRealModel: statusSnapshot?.core_chain_readiness?.real_model_ready ?? null,
    facts: statusSnapshot?.core_chain_readiness,
  });
  const backendExplicitlyBlocksOutline = statusSnapshot?.core_chain_readiness?.project_brief_ready === false;
  const canTriggerOutlineGeneration = !backendExplicitlyBlocksOutline && !generating;
  const outlineGenerateBlockReason = generating
    ? "正在生成大纲"
    : backendExplicitlyBlocksOutline
      ? "回到项目页补全简介"
      : chainReadiness.nextAction;

  return (
    <div className="h-full overflow-auto">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mx-6 mt-4">
          {error}
        </div>
      )}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-700 p-4 rounded-lg mx-6 mt-4">
          {successMessage}
        </div>
      )}

      {!outline ? (
        <div className="flex items-center justify-center h-full">
          <div className="bg-white rounded-xl border p-12 text-center max-w-md">
            {generating ? (
              <>
                <div className="text-5xl mb-4 animate-pulse">⚙️</div>
                <h2 className="text-xl font-semibold mb-2">正在生成大纲...</h2>
                <p className="text-gray-400 mb-6">AI 正在根据你的题材和简介生成完整的故事结构</p>
                <div className="text-sm text-blue-500">生成完成后会留在当前页，方便你确认下一步。</div>
              </>
            ) : (
              <>
                <div className="text-5xl mb-4">📝</div>
                <h2 className="text-xl font-semibold mb-2">还没有大纲</h2>
                <div className="mb-3 flex items-center justify-center">
                  <span className={`rounded-full px-2.5 py-1 text-xs ${chainReadiness.badgeClassName}`}>
                    {chainReadiness.label}
                  </span>
                </div>
                <p className="text-gray-400 mb-3">{chainReadiness.description}</p>
                <div className="mb-3 rounded-lg border bg-gray-50 px-4 py-3 text-left text-sm text-gray-600">
                  <div><span className="font-medium">项目：</span>{currentBook?.title ?? "-"}</div>
                  <div><span className="font-medium">目标章数：</span>{currentBook?.targetChapters ?? DEFAULT_OUTLINE_CHAPTERS}</div>
                  <div><span className="font-medium">简介：</span>{currentBook?.summary?.trim() ? currentBook.summary : "未填写"}</div>
                </div>
                <p className="mb-6 text-xs text-gray-500">下一步：{chainReadiness.nextAction}</p>
                <Button
                  onClick={handleGenerate}
                  disabled={!canTriggerOutlineGeneration}
                  title={!canTriggerOutlineGeneration ? outlineGenerateBlockReason : undefined}
                >
                  {generating ? "生成中..." : "生成大纲"}
                </Button>
              </>
            )}
          </div>
        </div>
      ) : (
        <div className="max-w-5xl mx-auto p-6">
          {/* Info Card */}
          <div className="bg-white rounded-xl border p-6 mb-4">
            <h2 className="text-lg font-semibold mb-3">{outline.title}</h2>
            <p className="text-gray-600 mb-4">{outline.summary || "暂无简介"}</p>
            <div className="flex flex-wrap gap-4 text-sm text-gray-500">
              <span>总章数：{outline.total_chapters}</span>
              <span>结构：{outline.arc}</span>
              <span>
                生成模式：
                {generationMode === "model"
                  ? "真实模型"
                  : generationMode === "fallback"
                    ? "模板降级"
                    : "沿用已有大纲"}
              </span>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-500">
              <span className={`rounded-full px-2.5 py-1 ${chainReadiness.badgeClassName}`}>
                链路状态：{chainReadiness.label}
              </span>
              <span>下一步：{chainReadiness.nextAction}</span>
            </div>
            <div className="mt-4 rounded-lg border bg-gray-50 p-4">
              <div className="text-sm font-medium text-gray-900">下一步建议</div>
              <p className="mt-1 text-sm text-gray-600">{chainReadiness.description}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {chainReadiness.primaryAction.route ? (
                  <Button onClick={() => navigate(chainReadiness.primaryAction.route!)}>
                    {chainReadiness.primaryAction.label}
                  </Button>
                ) : null}
                <Button
                  variant="outline"
                  onClick={() => navigate("/chapters")}
                  disabled={!chainReadiness.canGenerateChapter}
                  title={!chainReadiness.canGenerateChapter ? chainReadiness.nextAction : undefined}
                >
                  去章节页
                </Button>
                <Button variant="outline" onClick={() => navigate("/settings")}>去设置模型</Button>
                <Button variant="outline" onClick={() => navigate("/")}>返回项目页</Button>
              </div>
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
            <div className="bg-white rounded-xl border p-6 mb-4">
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
          <div className="bg-white rounded-xl border p-6 mb-4">
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
          <div className="bg-white rounded-xl border p-6 mb-4">
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

          {/* Toolbar */}
          <div className="flex justify-end mt-4">
            <Button
              variant="outline"
              onClick={handleGenerate}
              disabled={!canTriggerOutlineGeneration}
              title={!canTriggerOutlineGeneration ? outlineGenerateBlockReason : undefined}
            >
              {generating ? "生成中..." : "重新生成"}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
