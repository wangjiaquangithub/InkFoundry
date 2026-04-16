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
}

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
      const res = await api.listProjects();
      setProjects(res.data.projects || []);
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
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">InkFoundry</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          + 创建项目
        </Button>
      </header>

      <div className="max-w-5xl mx-auto py-8 px-4">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold mb-2">我的项目</h1>
          <p className="text-gray-500">管理和切换小说项目</p>
        </div>

        {/* Project List */}
        {projects.length === 0 ? (
          <div className="text-center py-12">
            <div className="text-5xl mb-4">📝</div>
            <p className="text-gray-500 mb-4">还没有项目</p>
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
                  类型: {p.genre} · 创建: {new Date(p.created_at).toLocaleDateString("zh-CN")}
                </p>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    className="flex-1"
                    onClick={() => handleActivate(p.id)}
                  >
                    进入项目
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
