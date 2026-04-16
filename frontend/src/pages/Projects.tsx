import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAppContext } from "../app-context";
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
  const { currentBook, setCurrentBook, isRestoringBook } = useAppContext();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newGenre, setNewGenre] = useState("xuanhuan");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    void loadProjects();
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    try {
      const projRes = await api.listProjects();
      const list = projRes.data.projects || [];

      // Each project's chapter count is stored in its own state.db
      // The listProjects endpoint already returns total_chapters if available
      setProjects(list);
    } catch {
      console.error("Failed to load projects");
    } finally {
      setLoading(false);
    }
  };

  const activateProject = async (project: Pick<Project, "id" | "title" | "genre">) => {
    if (isRestoringBook) {
      return;
    }

    await api.activateProject(project.id);
    setCurrentBook({ id: project.id, title: project.title, genre: project.genre });
  };

  const handleCreate = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const createRes = await api.createProject({ title: newTitle, genre: newGenre });
      const project = createRes.data.project as Pick<Project, "id" | "title" | "genre">;
      await activateProject(project);
      setShowCreate(false);
      setNewTitle("");
      setNewGenre("xuanhuan");
      navigate("/outline");
    } catch (e: unknown) {
      console.error("Failed to create project:", e);
      alert("创建失败，请重试");
    } finally {
      setCreating(false);
    }
  };

  const handleActivate = async (id: string) => {
    try {
      const project = projects.find((p) => p.id === id);
      if (!project) {
        throw new Error("Project not found");
      }
      await activateProject(project);
      navigate("/outline");
    } catch (e: unknown) {
      console.error("Failed to activate project:", e);
      alert("切换项目失败");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("确定要删除此项目吗？数据将无法恢复。")) return;
    try {
      await api.deleteProject(id);
      if (currentBook?.id === id) {
        setCurrentBook(null);
        navigate("/");
      }
      await loadProjects();
    } catch (e: unknown) {
      console.error("Failed to delete project:", e);
      alert("删除失败，请重试");
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p className="text-gray-400">加载项目中...</p></div>;
  }

  return (
    <div className="h-full overflow-auto p-6">
      {/* Page header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-xl font-bold">书籍管理</h2>
          <p className="text-sm text-gray-400 mt-1">管理你的 AI 小说创作项目</p>
        </div>
        <Button onClick={() => setShowCreate(true)} disabled={isRestoringBook}>+ 创建项目</Button>
      </div>

      {projects.length === 0 ? (
        <div className="bg-white rounded-xl border p-12 text-center max-w-md mx-auto">
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
                  disabled={isRestoringBook}
                >
                  {isRestoringBook ? "恢复中..." : "进入创作"}
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

      {/* Create Modal */}
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
