import { useState, useEffect } from "react";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import { api, type ApiStatusResponse } from "../api/client";
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
  const navigate = useNavigate();
  const { currentBook } = useAppContext();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Chapter | null>(null);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [generating, setGenerating] = useState(false);
  const [outline, setOutline] = useState<Outline | null>(null);
  const [statusSnapshot, setStatusSnapshot] = useState<ApiStatusResponse | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [pageError, setPageError] = useState<string | null>(null);
  const [pageNotice, setPageNotice] = useState<string | null>(null);
  const [loadingReadiness, setLoadingReadiness] = useState(true);
  const [deleteTarget, setDeleteTarget] = useState<Chapter | null>(null);
  const [exportFormat, setExportFormat] = useState<"txt" | "md" | "html">("txt");
  const [showExportModal, setShowExportModal] = useState(false);
  const [hasOutline, setHasOutline] = useState<boolean | null>(null);

  const resetSelectedChapter = () => {
    setSelected(null);
    setEditing(false);
    setEditContent("");
    setDeleteTarget(null);
  };

  useEffect(() => {
    if (!selected) {
      return;
    }
    if (chapters.some((chapter) => chapter.chapter_num === selected.chapter_num)) {
      return;
    }
    resetSelectedChapter();
  }, [chapters, selected]);

  useEffect(() => {
    let cancelled = false;

    const loadPageState = async () => {
      setLoading(true);
      setLoadingReadiness(true);
      const [chaptersRes, outlineRes, configRes] = await Promise.allSettled([
        api.getChapters(),
        api.getOutline(),
        api.status(),
      ]);

      if (cancelled) {
        return;
      }

      if (chaptersRes.status === "fulfilled") {
        setChapters(chaptersRes.value.data.chapters || []);
      } else {
        setChapters([]);
        resetSelectedChapter();
      }

      if (outlineRes.status === "fulfilled") {
        setOutline(outlineRes.value.data.outline);
        setHasOutline(Boolean(outlineRes.value.data.outline));
      } else {
        setOutline(null);
        setHasOutline(null);
      }

      if (configRes.status === "fulfilled") {
        setStatusSnapshot(configRes.value.data);
        setStatusError(null);
      } else {
        setStatusSnapshot(null);
        setStatusError(getErrorMessage(configRes.reason));
      }

      setLoading(false);
      setLoadingReadiness(false);
    };

    void loadPageState();

    return () => {
      cancelled = true;
    };
  }, [currentBook?.id]);

  const refreshGeneratedState = async () => {
    setLoading(true);
    setLoadingReadiness(true);
    const [chaptersRes, outlineRes, configRes] = await Promise.allSettled([
      api.getChapters(),
      api.getOutline(),
      api.status(),
    ]);
    let refreshError: string | null = null;

    if (chaptersRes.status === "fulfilled") {
      setChapters(chaptersRes.value.data.chapters || []);
    } else {
      setChapters([]);
      resetSelectedChapter();
      refreshError = "章节列表刷新失败，请手动刷新后确认最新状态。";
    }

    if (outlineRes.status === "fulfilled") {
      setOutline(outlineRes.value.data.outline);
      setHasOutline(Boolean(outlineRes.value.data.outline));
    } else {
      setOutline(null);
      setHasOutline(null);
    }

    if (configRes.status === "fulfilled") {
      setStatusSnapshot(configRes.value.data);
      setStatusError(null);
    } else {
      setStatusSnapshot(null);
      setStatusError(getErrorMessage(configRes.reason));
    }

    setLoading(false);
    setLoadingReadiness(false);

    if (refreshError) {
      throw new Error(refreshError);
    }
  };

  const handleSelect = async (num: number) => {
    try {
      const res = await api.getChapter(num);
      setSelected(res.data);
      setEditContent(res.data.content || "");
      setEditing(false);
    } catch (e: unknown) {
      resetSelectedChapter();
      setPageError(`加载第${num}章失败：${getErrorMessage(e)}`);
    }
  };

  const handleSave = async () => {
    if (!selected) return;
    try {
      await api.updateChapter(selected.chapter_num, {
        content: editContent,
      });
      setEditing(false);
      setSelected({
        ...selected,
        content: editContent,
      });
      setChapters((items) =>
        items.map((chapter) =>
          chapter.chapter_num === selected.chapter_num
            ? {
                ...chapter,
                content: editContent,
              }
            : chapter
        )
      );
      setPageNotice(`第${selected.chapter_num}章已保存。`);
    } catch (e: unknown) {
      setPageError(getErrorMessage(e));
    }
  };

  const handleDelete = async (chapter: Chapter) => {
    try {
      await api.deleteChapter(chapter.chapter_num);
      setChapters((items) => items.filter((item) => item.chapter_num !== chapter.chapter_num));
      if (selected?.chapter_num === chapter.chapter_num) {
        setSelected(null);
      }
      setDeleteTarget(null);
      setPageNotice(`第${chapter.chapter_num}章已删除。`);
    } catch (e: unknown) {
      setPageError(getErrorMessage(e));
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
    setPageNotice(null);
    try {
      await api.runChapter(nextNum);
      await refreshGeneratedState();
      setPageNotice(`第${nextNum}章已生成。`);
    } catch (e: unknown) {
      setPageError(getErrorMessage(e));
    } finally {
      setGenerating(false);
    }
  };

  const handleExport = async () => {
    try {
      const res = await api.exportNovel(exportFormat);
      const { content, filename } = res.data;
      const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
      setShowExportModal(false);
      setPageNotice(`已导出 ${filename}。`);
    } catch (e: unknown) {
      setPageError(`导出失败: ${getErrorMessage(e)}`);
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
    hasOutline: outline ? true : hasOutline,
    hasRealModel: statusSnapshot?.core_chain_readiness?.real_model_ready ?? null,
    facts: statusSnapshot?.core_chain_readiness,
  });
  const canGenerate = chainReadiness.canGenerateChapter && !generating;

  return (
    <div className="flex h-full">
      {pageError && (
        <div className="absolute left-1/2 top-4 z-10 w-[min(720px,calc(100%-2rem))] -translate-x-1/2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <div className="flex items-start justify-between gap-3">
            <span>{pageError}</span>
            <button className="text-xs font-medium text-red-700" onClick={() => setPageError(null)}>
              关闭
            </button>
          </div>
        </div>
      )}
      {pageNotice && (
        <div className="absolute left-1/2 top-20 z-10 w-[min(720px,calc(100%-2rem))] -translate-x-1/2 rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          <div className="flex items-start justify-between gap-3">
            <span>{pageNotice}</span>
            <button className="text-xs font-medium text-green-700" onClick={() => setPageNotice(null)}>
              关闭
            </button>
          </div>
        </div>
      )}
      {deleteTarget && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-black bg-opacity-40">
          <div className="mx-4 w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900">删除章节</h3>
            <p className="mt-2 text-sm text-gray-600">
              确定删除第{deleteTarget.chapter_num}章吗？已生成内容将无法恢复。
            </p>
            <div className="mt-6 flex gap-2">
              <Button className="flex-1" variant="outline" onClick={() => setDeleteTarget(null)}>
                取消
              </Button>
              <Button className="flex-1" variant="destructive" onClick={() => void handleDelete(deleteTarget)}>
                确认删除
              </Button>
            </div>
          </div>
        </div>
      )}
      {showExportModal && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-black bg-opacity-40">
          <div className="mx-4 w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
            <h3 className="text-lg font-bold text-gray-900">导出小说</h3>
            <p className="mt-2 text-sm text-gray-600">选择导出格式后立即下载当前项目内容。</p>
            <div className="mt-4 space-y-2">
              {(["txt", "md", "html"] as const).map((format) => (
                <label key={format} className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm text-gray-700">
                  <input
                    type="radio"
                    name="export-format"
                    checked={exportFormat === format}
                    onChange={() => setExportFormat(format)}
                  />
                  <span>{format.toUpperCase()}</span>
                </label>
              ))}
            </div>
            <div className="mt-6 flex gap-2">
              <Button className="flex-1" variant="outline" onClick={() => setShowExportModal(false)}>
                取消
              </Button>
              <Button className="flex-1" onClick={() => void handleExport()}>
                开始导出
              </Button>
            </div>
          </div>
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
              <span>
                模式：
                {loadingReadiness
                  ? "检查中"
                  : statusSnapshot?.core_chain_readiness?.real_model_ready === true
                    ? "真实模型"
                    : statusSnapshot?.core_chain_readiness?.real_model_ready === false
                      ? "未配置模型"
                      : "状态待确认"}
              </span>
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
              onClick={() => setShowExportModal(true)}
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
                    onClick={() => setDeleteTarget(selected)}
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
                  {hasOutline === null
                    ? "当前无法确认大纲状态，请稍后重试或重新检查设置。"
                    : outlineSummary && chainReadiness.canGenerateChapter
                      ? `下一章将基于概要：${outlineSummary}`
                      : `下一步：${chainReadiness.nextAction}`}
                </p>
                <div className="flex flex-wrap items-center justify-center gap-2">
                  <Button size="lg" onClick={handleGenerate} disabled={!canGenerate}>
                    {generating ? "生成中..." : "生成第一章"}
                  </Button>
                  {!chainReadiness.canGenerateChapter && chainReadiness.primaryAction.route ? (
                    <Button
                      size="lg"
                      variant="outline"
                      onClick={() => navigate(chainReadiness.primaryAction.route!)}
                    >
                      {chainReadiness.primaryAction.label}
                    </Button>
                  ) : null}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
