import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useNovelStore } from "../store/novelStore";
import { usePipelineStore } from "../stores/pipelineStore";
import { api } from "../api/client";
import { Button } from "../components/ui/button";
import { ChapterEditor } from "../components/ChapterEditor";
import { PipelineStatusBar } from "../components/PipelineStatusBar";
import type { Outline } from "../types";

const NAV_ITEMS = [
  { label: "工作台", path: "/workspace", icon: "📝" },
  { label: "大纲", path: "/outline", icon: "📋" },
  { label: "章节", path: "/chapters", icon: "📚" },
  { label: "角色", path: "/characters", icon: "👥" },
  { label: "世界观", path: "/world", icon: "🌍" },
  { label: "审核", path: "/review", icon: "✅" },
  { label: "设置", path: "/settings", icon: "⚙️" },
];

export function Workspace() {
  const navigate = useNavigate();
  const {
    chapters, characters, selectedChapter,
    fetchStatus, fetchCharacters, fetchChapters,
    selectChapter,
  } = useNovelStore();

  const {
    running, paused, currentChapter, totalChapters, progress, error,
    runChapter, runBatch, pause, resume, stop, fetchStatus: fetchPipelineStatus,
  } = usePipelineStore();

  const [generating, setGenerating] = useState(false);
  const [batchFrom, setBatchFrom] = useState(1);
  const [batchTo, setBatchTo] = useState(10);
  const [showBatchModal, setShowBatchModal] = useState(false);
  const [outline, setOutline] = useState<Outline | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    fetchStatus();
    fetchCharacters();
    fetchChapters();
    fetchPipelineStatus();
    loadOutline();
  }, []);

  const loadOutline = async () => {
    try {
      const res = await api.getOutline();
      setOutline(res.data.outline);
    } catch {
      setOutline(null);
    }
  };

  // Refresh chapters periodically when pipeline is running
  useEffect(() => {
    if (!running) return;
    const interval = setInterval(() => {
      fetchChapters();
      fetchPipelineStatus();
    }, 2000);
    return () => clearInterval(interval);
  }, [running]);

  // Cleanup batch poll interval on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const hasChapters = chapters.length > 0;
  const selected = chapters.find((c) => c.chapter_num === selectedChapter);

  // Determine next chapter to generate
  const nextChapterNum = hasChapters
    ? (chapters.find((c) => c.status === "pending")?.chapter_num ?? Math.max(...chapters.map((c) => c.chapter_num)) + 1)
    : 1;

  const handleGenerateChapter = useCallback(async (num: number) => {
    setGenerating(true);
    try {
      await runChapter(num);
      // Refresh after generation
      await fetchChapters();
      selectChapter(num);
    } catch (e: any) {
      console.error("Failed to generate chapter:", e);
    } finally {
      setGenerating(false);
    }
  }, [runChapter, fetchChapters, selectChapter]);

  const handleQuickStart = useCallback(async () => {
    // Generate first chapter quickly
    await handleGenerateChapter(1);
  }, [handleGenerateChapter]);

  const handleSaveChapter = useCallback(async (data: { title?: string; content?: string }) => {
    if (!selected) return;
    try {
      await api.updateChapter(selected.chapter_num, data);
      await fetchChapters();
    } catch (e: any) {
      console.error("Failed to save chapter:", e);
    }
  }, [selected, fetchChapters]);

  const handleBatchRun = useCallback(async () => {
    if (batchFrom < 1 || batchTo < batchFrom) return;
    try {
      await runBatch(batchFrom, batchTo);
      setShowBatchModal(false);
      // Poll for completion
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = setInterval(async () => {
        await fetchPipelineStatus();
        await fetchChapters();
        const status = usePipelineStore.getState();
        if (!status.running) {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
        }
      }, 2000);
    } catch (e: any) {
      console.error("Failed to run batch:", e);
    }
  }, [batchFrom, batchTo, runBatch, fetchPipelineStatus, fetchChapters]);

  const statusLabel = (s: string) => {
    const map: Record<string, string> = {
      final: "完成",
      reviewed: "已审",
      draft: "草稿",
      pending: "待写",
    };
    return map[s] || s;
  };

  const statusColor = (s: string) => {
    const map: Record<string, string> = {
      final: "bg-green-100 text-green-700",
      reviewed: "bg-blue-100 text-blue-700",
      draft: "bg-yellow-100 text-yellow-700",
      pending: "bg-gray-100 text-gray-500",
    };
    return map[s] || "bg-gray-100 text-gray-500";
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Top Navigation Bar */}
      <header className="flex items-center justify-between border-b bg-white px-4 py-2">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold">InkFoundry</h1>
          <span className="text-gray-300">|</span>
          {/* Nav Items */}
          <nav className="flex gap-1">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm transition ${
                  item.path === "/workspace"
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-600 hover:bg-gray-100"
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        </div>
        <div className="flex items-center gap-2">
          {/* Batch Run Button */}
          <Button variant="outline" size="sm" onClick={() => setShowBatchModal(true)} disabled={!hasChapters && !outline}>
            批量生成
          </Button>
          {running ? (
            paused ? (
              <Button size="sm" onClick={resume}>继续</Button>
            ) : (
              <Button variant="outline" size="sm" onClick={pause}>暂停</Button>
            )
          ) : (
            <Button
              size="sm"
              onClick={() => handleGenerateChapter(nextChapterNum)}
              disabled={generating}
            >
              {generating ? "生成中..." : hasChapters ? "生成下一章" : "开始写作"}
            </Button>
          )}
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left: Chapter List */}
        <aside className="w-64 border-r bg-white overflow-y-auto flex flex-col">
          <div className="p-3 border-b flex justify-between items-center">
            <h2 className="font-semibold">章节列表</h2>
            {hasChapters && (
              <span className="text-xs text-gray-400">
                {chapters.filter((c) => c.status !== "pending").length}/{chapters.length}
              </span>
            )}
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {!hasChapters ? (
              <div className="flex flex-col items-center justify-center h-full text-center text-gray-400 px-4">
                <div className="text-3xl mb-2">📭</div>
                <p className="text-sm mb-1">暂无章节</p>
                <p className="text-xs mb-3">点击上方「开始写作」生成第一章</p>
                {outline && (
                  <p className="text-xs text-blue-500">
                    大纲已就绪：共 {outline.total_chapters} 章
                  </p>
                )}
              </div>
            ) : chapters.map((ch) => (
              <button
                key={ch.chapter_num}
                onClick={() => selectChapter(ch.chapter_num)}
                className={`w-full text-left p-2 rounded-md mb-1 text-sm transition ${
                  selectedChapter === ch.chapter_num
                    ? "bg-blue-50 border border-blue-200"
                    : "hover:bg-gray-50"
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="font-medium">第{ch.chapter_num}章</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${statusColor(ch.status)}`}>
                    {statusLabel(ch.status)}
                  </span>
                </div>
                {ch.title && (
                  <div className="text-xs text-gray-500 mt-0.5 truncate">{ch.title}</div>
                )}
                <div className="flex items-center gap-1 mt-1">
                  <span className="text-xs text-gray-400">张力:</span>
                  <div className="flex gap-0.5">
                    {Array.from({ length: 10 }).map((_, i) => (
                      <div key={i} className={`w-2 h-1.5 rounded-sm ${
                        i < ch.tension_level ? "bg-red-400" : "bg-gray-200"
                      }`} />
                    ))}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </aside>

        {/* Center: Chapter Editor */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-hidden">
            {!hasChapters ? (
              <div className="flex flex-col items-center justify-center h-full text-center px-6">
                <div className="text-6xl mb-4">✍️</div>
                <h2 className="text-2xl font-bold mb-2">准备好开始创作了吗？</h2>
                <p className="text-gray-500 mb-6 max-w-md">
                  {outline
                    ? `大纲已就绪（共 ${outline.total_chapters} 章）。点击下方按钮，AI 将根据大纲生成第一章内容。`
                    : "还没有大纲？先去生成小说大纲吧。"}
                </p>
                <div className="flex gap-3">
                  <Button size="lg" onClick={handleQuickStart} disabled={generating || !outline}>
                    {generating ? "生成中..." : "生成第一章"}
                  </Button>
                  <Button variant="outline" onClick={() => navigate("/outline")}>
                    查看大纲
                  </Button>
                </div>
              </div>
            ) : (
              <ChapterEditor
                chapterNum={selected?.chapter_num ?? 1}
                title={selected?.title ?? ""}
                content={selected?.content ?? ""}
                status={selected?.status ?? "pending"}
                onSave={handleSaveChapter}
                onGenerate={handleGenerateChapter}
                generating={generating || running}
              />
            )}
          </div>

          {/* Pipeline Status Bar */}
          <PipelineStatusBar
            running={running}
            paused={paused}
            currentChapter={currentChapter}
            totalChapters={totalChapters}
            progress={progress}
            error={error}
            onPause={pause}
            onResume={resume}
            onStop={stop}
          />
        </main>

        {/* Right: Character Panel */}
        <aside className="w-72 border-l bg-white overflow-y-auto">
          <div className="p-3 border-b flex justify-between items-center">
            <h2 className="font-semibold">角色状态</h2>
            <button
              onClick={() => navigate("/characters")}
              className="text-xs text-blue-500 hover:text-blue-700"
            >
              管理 →
            </button>
          </div>
          <div className="p-3">
            {characters.length > 0 ? characters.map((ch) => (
              <div key={ch.name} className="p-3 border rounded-lg mb-2">
                <div className="flex justify-between items-center">
                  <span className="font-medium">{ch.name}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    ch.status === "active" ? "bg-green-100 text-green-700" :
                    ch.status === "inactive" ? "bg-gray-100 text-gray-500" :
                    "bg-red-100 text-red-700"
                  }`}>
                    {ch.role}
                  </span>
                </div>
                <p className="text-xs text-gray-500 mt-1">状态: {ch.status}</p>
              </div>
            )) : (
              <div className="text-sm text-gray-400 p-3">
                暂无角色数据
                <br />
                <button
                  onClick={() => navigate("/characters")}
                  className="text-blue-500 mt-1"
                >
                  去添加 →
                </button>
              </div>
            )}
          </div>
        </aside>
      </div>

      {/* Batch Run Modal */}
      {showBatchModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-bold mb-4">批量生成章节</h3>
            <div className="flex gap-4 mb-4">
              <div className="flex-1">
                <label className="block text-sm font-medium mb-1">从第几章</label>
                <input
                  type="number"
                  value={batchFrom}
                  onChange={(e) => setBatchFrom(Number(e.target.value))}
                  min={1}
                  className="w-full border rounded-lg px-3 py-2"
                />
              </div>
              <div className="flex-1">
                <label className="block text-sm font-medium mb-1">到第几章</label>
                <input
                  type="number"
                  value={batchTo}
                  onChange={(e) => setBatchTo(Number(e.target.value))}
                  min={batchFrom}
                  className="w-full border rounded-lg px-3 py-2"
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button className="flex-1" onClick={handleBatchRun} disabled={running}>
                {running ? "生成中..." : "开始生成"}
              </Button>
              <Button variant="outline" onClick={() => setShowBatchModal(false)}>
                取消
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
