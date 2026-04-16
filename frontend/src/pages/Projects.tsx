import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Button } from "../components/ui/button";

interface Project {
  id: string;
  title: string;
  genre: string;
  created_at: string;
  last_modified: string;
  db_path: string;
  status: string;
  total_chapters?: number;
  latest_chapter?: number;
}

const QUICK_ACTIONS = [
  { label: "设置", icon: "⚙️", path: "/settings", desc: "API Key 与模型配置" },
  { label: "Token 用量", icon: "📊", path: "/workspace", desc: "查看全局 Token 消耗" },
];

const GENRE_MAP: Record<string, string> = {
  xuanhuan: "玄幻",
  urban: "都市",
  scifi: "科幻",
  romance: "言情",
  wuxia: "武侠",
  historical: "历史",
  mystery: "悬疑",
};

export function Projects() {
  const navigate = useNavigate();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newGenre, setNewGenre] = useState("xuanhuan");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const [projRes, chapRes] = await Promise.all([
        api.listProjects(),
        api.getChapters().catch(() => ({ data: { chapters: [] } })),
      ]);
      const list = projRes.data.projects || [];
      const chapters = chapRes.data.chapters || [];

      // Enrich projects with chapter stats
      const enriched = list.map((p: Project) => ({
        ...p,
        total_chapters: chapters.length,
        latest_chapter: chapters.length > 0 ? Math.max(...chapters.map((c: any) => c.chapter_num)) : 0,
      }));
      setProjects(enriched);
    } catch {
      console.error("Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      await api.createProject({ title: newTitle, genre: newGenre });
      setShowCreate(false);
      setNewTitle("");
      await loadProjects();
    } catch (e: any) {
      console.error("Failed to create project:", e);
      alert("创建失败，请重试");
    } finally {
      setCreating(false);
    }
  };

  const handleActivate = async (id: string) => {
    try {
      await api.activateProject(id);
      navigate("/workspace");
    } catch (e: any) {
      console.error("Failed to activate project:", e);
      alert("切换项目失败");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除此项目吗？数据将无法恢复。")) return;
    try {
      await api.deleteProject(id);
      await loadProjects();
    } catch (e: any) {
      console.error("Failed to delete project:", e);
      alert("删除失败，请重试");
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">加载项目中...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Global Header */}
      <header className="bg-white border-b px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold">InkFoundry</h1>
          <nav className="flex gap-1">
            {QUICK_ACTIONS.map((a) => (
              <button
                key={a.path}
                onClick={() => a.path === "#projects" ? window.scrollTo({ top: 0, behavior: "smooth" }) : navigate(a.path)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm text-gray-600 hover:bg-gray-100 transition"
              >
                <span>{a.icon}</span>
                <span>{a.label}</span>
              </button>
            ))}
          </nav>
        </div>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          + 创建项目
        </Button>
      </header>

      <div className="max-w-5xl mx-auto py-8 px-4">
        {/* Hero */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">AI 小说创作工坊</h1>
          <p className="text-gray-500">智能驱动，从大纲到完稿</p>
        </div>

        {/* Project List */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">我的项目</h2>
          <span className="text-sm text-gray-400">{projects.length} 个项目</span>
        </div>

        {projects.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl border">
            <div className="text-5xl mb-4">📝</div>
            <p className="text-gray-500 mb-1">还没有项目</p>
            <p className="text-sm text-gray-400 mb-4">创建你的第一部小说开始创作</p>
            <Button onClick={() => setShowCreate(true)}>创建第一个项目</Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map((p) => (
              <div
                key={p.id}
                className="bg-white rounded-xl border p-5 hover:shadow-md transition"
              >
                <h3 className="font-semibold text-lg mb-1">{p.title}</h3>
                <p className="text-xs text-gray-400 mb-3">
                  {GENRE_MAP[p.genre] || p.genre}
                  {p.total_chapters ? ` · ${p.total_chapters}章` : ""}
                  {p.latest_chapter ? ` · 最新: 第${p.latest_chapter}章` : ""}
                </p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    className="flex-1"
                    onClick={() => handleActivate(p.id)}
                  >
                    进入创作
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-red-600"
                    onClick={() => handleDelete(p.id)}
                  >
                    删除
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Project Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl p-6 max-w-sm w-full mx-4">
            <h3 className="text-lg font-bold mb-4">创建新项目</h3>
            <div className="space-y-4 mb-4">
              <div>
                <label className="block text-sm font-medium mb-1">小说标题</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2"
                  placeholder="输入小说标题"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">题材类型</label>
                <select
                  value={newGenre}
                  onChange={(e) => setNewGenre(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2"
                >
                  <option value="xuanhuan">玄幻</option>
                  <option value="urban">都市</option>
                  <option value="scifi">科幻</option>
                  <option value="romance">言情</option>
                  <option value="wuxia">武侠</option>
                  <option value="historical">历史</option>
                  <option value="mystery">悬疑</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2">
              <Button className="flex-1" onClick={handleCreate} disabled={creating || !newTitle.trim()}>
                {creating ? "创建中..." : "创建"}
              </Button>
              <Button variant="outline" onClick={() => { setShowCreate(false); setNewTitle(""); }}>
                取消
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
