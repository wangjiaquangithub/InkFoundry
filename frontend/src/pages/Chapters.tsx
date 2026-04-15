import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Button } from "../components/ui/button";
import type { Chapter } from "../types";

export function Chapters() {
  const navigate = useNavigate();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Chapter | null>(null);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");

  useEffect(() => {
    loadChapters();
  }, []);

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
    } catch (e: any) {
      console.error("Failed to save chapter:", e);
    }
  };

  const handleDelete = async (num: number) => {
    if (!confirm(`确定删除第${num}章？`)) return;
    try {
      await api.deleteChapter(num);
      loadChapters();
      if (selected?.chapter_num === num) {
        setSelected(null);
      }
    } catch (e: any) {
      console.error("Failed to delete chapter:", e);
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
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">加载章节中...</p>
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
          <h1 className="text-xl font-bold">章节管理</h1>
          <span className="text-sm text-gray-400">共 {chapters.length} 章</span>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => navigate("/workspace")}>进入工作区</Button>
        </div>
      </header>

      <div className="flex h-[calc(100vh-64px)]">
        {/* Chapter List */}
        <aside className="w-80 border-r bg-white overflow-y-auto">
          <div className="p-3 space-y-1">
            {chapters.length === 0 ? (
              <p className="text-sm text-gray-400 p-4 text-center">暂无章节</p>
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
                    {ch.content?.substring(0, 50) || "暂无内容"}
                  </div>
                </button>
              ))
            )}
          </div>
        </aside>

        {/* Chapter Content */}
        <main className="flex-1 overflow-y-auto">
          {selected ? (
            <div className="max-w-3xl mx-auto p-8">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-2xl font-bold">
                  第{selected.chapter_num}章 {selected.title || ""}
                </h2>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setEditing(!editing)}>
                    {editing ? "取消编辑" : "编辑"}
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
                  {selected.content || "暂无内容"}
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              选择左侧章节查看内容
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
