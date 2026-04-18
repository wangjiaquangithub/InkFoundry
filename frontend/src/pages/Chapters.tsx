import { useState, useEffect } from "react";
import axios from "axios";
import { api } from "../api/client";
import { Button } from "../components/ui/button";
import { useAppContext } from "../app-context";
import { getCoreChainReadiness } from "../lib/core-chain-readiness";
import type { Chapter, Outline } from "../types";

const getErrorMessage = (error: unknown) => {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") {
      return detail;
    }
    const errorField = error.response?.data?.error;
    if (typeof errorField === "string") {
      return errorField;
    }
    return error.message;
  }
  return error instanceof Error ? error.message : "未知错误";
};

export function Chapters() {
  const { currentBook } = useAppContext();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Chapter | null>(null);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [generating, setGenerating] = useState(false);
  const [outline, setOutline] = useState<Outline | null>(null);
  const [statusMode, setStatusMode] = useState<"model" | "fallback" | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [loadingReadiness, setLoadingReadiness] = useState(true);

  useEffect(() => {
    void loadChapters();
    void loadReadiness();
  }, [currentBook?.id]);

  const loadChapters = async () => {
    setLoading(true);
    try {
      const res = await api.getChapters();
      setChapters(res.data.chapters || []);
    } catch {
      setChapters([]);
    } finally {
      setLoading(false);
    }
  };

  const loadReadiness = async () => {
    setLoadingReadiness(true);
    const [outlineRes, configRes] = await Promise.allSettled([api.getOutline(), api.getConfig()]);

    if (outlineRes.status === "fulfilled") {
      setOutline(outlineRes.value.data.outline);
    } else {
      setOutline(null);
    }

    if (configRes.status === "fulfilled") {
      const hasModel = Boolean(configRes.value.data.llm_api_key_masked || configRes.value.data.llm_api_key);
      setStatusMode(hasModel ? "model" : "fallback");
      setStatusError(null);
    } else {
      setStatusMode(null);
      setStatusError(getErrorMessage(configRes.reason));
    }

    setLoadingReadiness(false);
  };

  const handleSelect = async (num: number) => {
    try {
      const res = await api.getChapter(num);
      setSelected(res.data);
      setEditContent(res.data.content || "");
      setEditing(false);
    } catch {
      setSelected(null);
    }
  };

  const handleSave = async () => {
    if (!selected) return;
    try {
      await api.updateChapter(selected.chapter_num, {
        content: editContent,
      });
      setEditing(false);
      loadChapters();
    } catch (e: unknown) {
      console.error("Failed to save chapter:", e);
    }
  };

  const handleDelete = async (num: number) => {
    if (!confirm(`确定删除第${num}章？`)) return;
    try {
      await api.deleteChapter(num);
      loadChapters();
      if (selected?.chapter_num === num) setSelected(null);
    } catch (e: unknown) {
      console.error("Failed to delete chapter:", e);
    }
  };

  const handleGenerate = async () => {
    const nextNum = chapters.length > 0
      ? Math.max(...chapters.map((c) => c.chapter_num)) + 1
      : 1;

    if (!chainReadiness.canGenerateChapter) {
      setPageError(chainReadiness.description);
      return;
    }

    setGenerating(true);
    setPageError(null);
    try {
      await api.runChapter(nextNum);
      await loadChapters();
      await loadReadiness();
    } catch (e: unknown) {
      console.error("Failed to generate chapter:", e);
      setPageError(getErrorMessage(e));
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async () => {
    const format = prompt("选择导出格式 (txt/md/html):", "txt");
    if (!format || !["txt", "md", "html"].includes(format)) return;
    try {
      const res = await api.exportNovel(format);
      const { content, filename } = res.data;
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: unknown) {
      alert("导出失败: " + (e instanceof Error ? e.message : "未知错误"));
    }
  };

  const statusLabel = (status: string) => {
    const map: Record<string, string> = {
      final: "完成",
      reviewed: "已审",
      draft: "草稿",
      pending: "待写",
    };
    return map[status] || status;
  };

  const statusColor = (status: string) => {
    const map: Record<string, string> = {
      final: "bg-green-100 text-green-700",
      reviewed: "bg-blue-100 text-blue-700",
      draft: "bg-yellow-100 text-yellow-700",
      pending: "bg-gray-100 text-gray-500",
    };
    return map[status] || "bg-gray-100 text-gray-500";
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p className="text-gray-400">加载章节中...</p></div>;
  }

  const nextChapterNum = chapters.length > 0 ? Math.max(...chapters.map((c) => c.chapter_num)) + 1 : 1;
  const outlineSummary = outline?.chapter_summaries?.find((ch) => ch.chapter_num === nextChapterNum)?.summary ?? "";
  const chainReadiness = getCoreChainReadiness({
    hasProjectSummary: Boolean(currentBook?.summary.trim()),
    hasOutline: Boolean(outline),
    hasRealModel: statusMode === null ? null : statusMode === "model",
  });
  const canGenerate = chainReadiness.canGenerateChapter && !generating;

  return (
    <div className="flex h-full">
      {pageError && (
        <div className="absolute left-1/2 top-4 z-10 w-[min(720px,calc(100%-2rem))] -translate-x-1/2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {pageError}
        </div>
      )}
      {/* Chapter List */}
      <aside className="w-72 border-r bg-white overflow-y-auto flex flex-col">
        <div className="p-3 border-b flex justify-between items-center">
          <h2 className="font-semibold">章节列表</h2>
          <span className="text-xs text-gray-400">{chapters.length} 章</span>
        </div>
        <div className="p-2 flex-1 overflow-y-auto">
          {chapters.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <div className="text-3xl mb-2">📭</div>
              <p className="text-sm">暂无章节</p>
              <p className="text-xs mb-3">点击右上方「生成下一章」开始</p>
            </div>
          ) : (
            chapters.map((ch) => (
              <button
                key={ch.chapter_num}
                onClick={() => handleSelect(ch.chapter_num)}
                className={`w-full text-left p-3 rounded-lg mb-1 transition ${
                  selected?.chapter_num === ch.chapter_num
                    ? "bg-blue-50 border border-blue-200"
                    : "hover:bg-gray-50"
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="font-medium text-sm">
                    第{ch.chapter_num}章 {ch.title || ""}
                  </span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${statusColor(ch.status)}`}>
                    {statusLabel(ch.status)}
                  </span>
                </div>
                <div className="text-xs text-gray-400 mt-1 truncate">
                  {ch.content?.substring(0, 60) || "暂无内容"}
                </div>
              </button>
            ))
          )}
        </div>
      </aside>

      {/* Chapter Content */}
      <main className="flex-1 overflow-hidden flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b bg-white">
          <div>
            <span className="text-sm text-gray-500">
              {selected ? `第${selected.chapter_num}章 · ${selected.title || ""}` : "选择左侧章节"}
            </span>
            <div className="mt-1 flex flex-wrap gap-3 text-xs text-gray-500">
              <span className={`rounded-full px-2.5 py-1 ${chainReadiness.badgeClassName}`}>
                链路状态：{chainReadiness.label}
              </span>
              <span>模式：{loadingReadiness ? "检查中" : statusMode === "model" ? "真实模型" : statusMode === "fallback" ? "未配置模型" : "状态待确认"}</span>
              <span>大纲：{outline ? `已加载（目标 ${outline.total_chapters} 章）` : "缺失"}</span>
              <span>下一步：{chainReadiness.nextAction}</span>
              {outlineSummary ? <span>下一章概要：{outlineSummary}</span> : null}
              {statusError ? <span className="text-red-600">状态检查失败：{statusError}</span> : null}
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={chapters.length === 0}
            >
              导出
            </Button>
            <Button
              size="sm"
              onClick={handleGenerate}
              disabled={!canGenerate}
              title={!canGenerate ? chainReadiness.nextAction : undefined}
            >
              {generating ? "生成中..." : "生成下一章"}
            </Button>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-y-auto">
          {selected ? (
            <div className="max-w-3xl mx-auto p-8">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">
                  第{selected.chapter_num}章 {selected.title || ""}
                </h2>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setEditing(!editing)}>
                    {editing ? "取消" : "编辑"}
                  </Button>
                  {editing && (
                    <Button size="sm" onClick={handleSave}>保存</Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(selected.chapter_num)}
                  >
                    删除
                  </Button>
                </div>
              </div>
              {editing ? (
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full border rounded-lg p-4 min-h-[500px] font-serif text-base leading-relaxed focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              ) : (
                <div className="bg-white rounded-lg border p-6 min-h-[500px] whitespace-pre-wrap font-serif text-base leading-relaxed">
                  {selected.content || (
                    <div className="text-center text-gray-400 py-12">
                      <p className="text-lg mb-2">暂无内容</p>
                      <p className="text-sm">点击上方「生成下一章」AI 创作</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              <div className="text-center">
                <div className="text-6xl mb-4">✍️</div>
                <h2 className="text-2xl font-bold mb-2">开始创作</h2>
                <p className="text-gray-500 mb-2">先有大纲，再在真实模型模式下生成章节。</p>
                <div className="mb-2 flex items-center justify-center">
                  <span className={`rounded-full px-2.5 py-1 text-xs ${chainReadiness.badgeClassName}`}>
                    {chainReadiness.label}
                  </span>
                </div>
                <p className="text-sm text-gray-400 mb-2">{chainReadiness.description}</p>
                <p className="text-sm text-gray-400 mb-4">
                  {outlineSummary && chainReadiness.canGenerateChapter
                    ? `下一章将基于概要：${outlineSummary}`
                    : `下一步：${chainReadiness.nextAction}`}
                </p>
                <Button size="lg" onClick={handleGenerate} disabled={!canGenerate}>
                  {generating ? "生成中..." : "生成第一章"}
                </Button>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
