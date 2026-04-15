import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Button } from "../components/ui/button";
import type { WorldBuilding } from "../types";

export function WorldBuilder() {
  const navigate = useNavigate();
  const [world, setWorld] = useState<WorldBuilding | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState<Partial<WorldBuilding>>({});

  useEffect(() => {
    loadWorld();
  }, []);

  const loadWorld = async () => {
    setLoading(true);
    try {
      const res = await api.getWorldBuilding();
      setWorld(res.data.world_building);
    } catch {
      setWorld(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      await api.createWorldBuilding({
        name: formData.name || world?.name || "默认世界",
        era: formData.era ?? world?.era ?? "",
        geography: formData.geography ?? world?.geography ?? "",
        social_structure: formData.social_structure ?? world?.social_structure ?? "",
        technology_level: formData.technology_level ?? world?.technology_level ?? "",
      });
      setEditing(false);
      loadWorld();
    } catch (e: any) {
      console.error("Failed to save world building:", e);
    }
  };

  const updateField = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">加载世界观中...</p>
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
          <h1 className="text-xl font-bold">世界观</h1>
        </div>
        <div className="flex gap-2">
          {world && !editing && (
            <Button onClick={() => setEditing(true)}>编辑</Button>
          )}
        </div>
      </header>

      <div className="max-w-4xl mx-auto p-6">
        {!world && !editing ? (
          <div className="bg-white rounded-xl border p-12 text-center">
            <div className="text-5xl mb-4">🌍</div>
            <h2 className="text-xl font-semibold mb-2">还没有世界观设置</h2>
            <p className="text-gray-400 mb-6">创建你的小说世界观，包括时代、地理、社会结构等</p>
            <Button onClick={() => setEditing(true)}>创建世界观</Button>
          </div>
        ) : (
          <div className="bg-white rounded-xl border p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">世界名称</label>
              <input
                type="text"
                value={editing ? (formData.name ?? "") : (world?.name || "")}
                onChange={(e) => updateField("name", e.target.value)}
                disabled={!editing}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">时代背景</label>
              <textarea
                value={editing ? (formData.era ?? "") : (world?.era || "")}
                onChange={(e) => updateField("era", e.target.value)}
                disabled={!editing}
                rows={2}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">地理环境</label>
              <textarea
                value={editing ? (formData.geography ?? "") : (world?.geography || "")}
                onChange={(e) => updateField("geography", e.target.value)}
                disabled={!editing}
                rows={3}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">社会结构</label>
              <textarea
                value={editing ? (formData.social_structure ?? "") : (world?.social_structure || "")}
                onChange={(e) => updateField("social_structure", e.target.value)}
                disabled={!editing}
                rows={3}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">科技水平</label>
              <input
                type="text"
                value={editing ? (formData.technology_level ?? "") : (world?.technology_level || "")}
                onChange={(e) => updateField("technology_level", e.target.value)}
                disabled={!editing}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-50"
              />
            </div>
            {editing && (
              <div className="flex gap-2 pt-2">
                <Button onClick={handleSave}>保存</Button>
                <Button variant="outline" onClick={() => { setEditing(false); setFormData({}); }}>
                  取消
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
