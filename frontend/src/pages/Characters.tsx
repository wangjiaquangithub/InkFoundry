import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Button } from "../components/ui/button";
import type { CharacterState } from "../types";

export function Characters() {
  const navigate = useNavigate();
  const [characters, setCharacters] = useState<CharacterState[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newRole, setNewRole] = useState("supporting");
  const [newStatus, setNewStatus] = useState("active");

  useEffect(() => {
    loadCharacters();
  }, []);

  const loadCharacters = async () => {
    setLoading(true);
    try {
      const res = await api.getCharacters();
      setCharacters(res.data.characters || []);
    } catch {
      setCharacters([]);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      await api.createCharacter({ name: newName, role: newRole, status: newStatus });
      setNewName("");
      setShowCreate(false);
      loadCharacters();
    } catch (e: any) {
      console.error("Failed to create character:", e);
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`确定删除角色「${name}」？`)) return;
    try {
      await api.deleteCharacter(name);
      loadCharacters();
    } catch (e: any) {
      console.error("Failed to delete character:", e);
    }
  };

  const roleLabel = (role: string) => {
    const map: Record<string, string> = {
      protagonist: "主角",
      antagonist: "反派",
      love_interest: "感情线",
      supporting: "配角",
    };
    return map[role] || role;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">加载角色中...</p>
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
          <h1 className="text-xl font-bold">角色管理</h1>
          <span className="text-sm text-gray-400">共 {characters.length} 个角色</span>
        </div>
        <div className="flex gap-2">
          <Button onClick={() => setShowCreate(true)}>添加角色</Button>
        </div>
      </header>

      <div className="max-w-4xl mx-auto p-6">
        {/* Create Form */}
        {showCreate && (
          <div className="bg-white rounded-xl border p-6 mb-6">
            <h2 className="font-semibold mb-4">新角色</h2>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">名称</label>
                <input
                  type="text"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="角色名称"
                  className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">定位</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="protagonist">主角</option>
                  <option value="antagonist">反派</option>
                  <option value="love_interest">感情线</option>
                  <option value="supporting">配角</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">状态</label>
                <select
                  value={newStatus}
                  onChange={(e) => setNewStatus(e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="active">活跃</option>
                  <option value="inactive">隐藏</option>
                  <option value="deceased">死亡</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <Button onClick={handleCreate}>创建</Button>
              <Button variant="outline" onClick={() => setShowCreate(false)}>取消</Button>
            </div>
          </div>
        )}

        {/* Character List */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {characters.length === 0 ? (
            <div className="col-span-2 bg-white rounded-xl border p-12 text-center">
              <div className="text-4xl mb-3">👥</div>
              <p className="text-gray-400">暂无角色，点击上方「添加角色」开始</p>
            </div>
          ) : (
            characters.map((ch) => (
              <div key={ch.name} className="bg-white rounded-xl border p-4">
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="font-semibold text-lg">{ch.name}</h3>
                    <p className="text-sm text-gray-500">{roleLabel(ch.role)}</p>
                  </div>
                  <div className="flex gap-2">
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      ch.status === "active" ? "bg-green-100 text-green-700" :
                      ch.status === "inactive" ? "bg-gray-100 text-gray-500" :
                      "bg-red-100 text-red-700"
                    }`}>
                      {ch.status === "active" ? "活跃" :
                       ch.status === "inactive" ? "隐藏" : "死亡"}
                    </span>
                  </div>
                </div>
                <div className="mt-3 flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(ch.name)}
                  >
                    删除
                  </Button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
