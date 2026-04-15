import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Button } from "../components/ui/button";

export function Settings() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [config, setConfig] = useState({
    llm_api_key: "",
    llm_base_url: "https://api.openai.com/v1",
    default_model: "qwen-plus",
    writer_model: "",
    editor_model: "",
    redteam_model: "",
    navigator_model: "",
    director_model: "",
    review_mode: "strict",
    max_retries: 3,
    pipeline_parallel: false,
  });

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const res = await api.getConfig();
      setConfig({
        llm_api_key: res.data.llm_api_key || "",
        llm_base_url: res.data.llm_base_url || "https://api.openai.com/v1",
        default_model: res.data.default_model || "qwen-plus",
        writer_model: res.data.writer_model || "",
        editor_model: res.data.editor_model || "",
        redteam_model: res.data.redteam_model || "",
        navigator_model: res.data.navigator_model || "",
        director_model: res.data.director_model || "",
        review_mode: res.data.review_mode || "strict",
        max_retries: res.data.max_retries || 3,
        pipeline_parallel: res.data.pipeline_parallel || false,
      });
    } catch {
      console.error("Failed to load config");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      await api.saveConfig(config);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: any) {
      console.error("Failed to save config:", e);
    } finally {
      setSaving(false);
    }
  };

  const update = (field: string, value: any) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">加载配置中...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate("/workspace")}>
            返回工作区
          </Button>
          <h1 className="text-xl font-bold">设置</h1>
        </div>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="text-sm text-green-500">已保存</span>
          )}
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "保存中..." : "保存设置"}
          </Button>
        </div>
      </header>

      <div className="max-w-3xl mx-auto p-6 space-y-6">
        {/* API Configuration */}
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">API 配置</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">LLM API Key</label>
              <input
                type="password"
                value={config.llm_api_key}
                onChange={(e) => update("llm_api_key", e.target.value)}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="sk-..."
              />
              <p className="text-xs text-gray-400 mt-1">
                用于调用 LLM API 的密钥
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">API Base URL</label>
              <input
                type="text"
                value={config.llm_base_url}
                onChange={(e) => update("llm_base_url", e.target.value)}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://api.openai.com/v1"
              />
              <p className="text-xs text-gray-400 mt-1">
                兼容 OpenAI 格式的 API 地址
              </p>
            </div>
          </div>
        </div>

        {/* Model Configuration */}
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">模型配置</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">默认模型</label>
              <input
                type="text"
                value={config.default_model}
                onChange={(e) => update("default_model", e.target.value)}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="例如: qwen-plus, claude-sonnet-4-6"
              />
              <p className="text-xs text-gray-400 mt-1">
                用于大多数章节生成的默认模型
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Writer 模型</label>
                <input
                  type="text"
                  value={config.writer_model}
                  onChange={(e) => update("writer_model", e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="留空则使用默认模型"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Editor 模型</label>
                <input
                  type="text"
                  value={config.editor_model}
                  onChange={(e) => update("editor_model", e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="留空则使用默认模型"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">RedTeam 模型</label>
                <input
                  type="text"
                  value={config.redteam_model}
                  onChange={(e) => update("redteam_model", e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="留空则使用默认模型"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Navigator 模型</label>
                <input
                  type="text"
                  value={config.navigator_model}
                  onChange={(e) => update("navigator_model", e.target.value)}
                  className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="留空则使用默认模型"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Pipeline Settings */}
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">流水线设置</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">审核模式</label>
              <select
                value={config.review_mode}
                onChange={(e) => update("review_mode", e.target.value)}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="strict">严格模式 - 每章需用户审批</option>
                <option value="milestone">里程碑模式 - 关键节点审批</option>
                <option value="headless">无人值守 - 全自动生成</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">最大重试次数</label>
              <input
                type="number"
                value={config.max_retries}
                onChange={(e) => update("max_retries", Number(e.target.value))}
                min={1}
                max={10}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <p className="text-xs text-gray-400 mt-1">
                生成失败后的最大重试次数
              </p>
            </div>
          </div>
        </div>

        {/* Danger Zone */}
        <div className="bg-white rounded-xl border border-red-200 p-6">
          <h2 className="font-semibold mb-4 text-red-600">危险操作</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <p className="font-medium">重置所有数据</p>
                <p className="text-sm text-gray-400">删除所有章节、角色和设置</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="text-red-600 border-red-200"
                onClick={() => {
                  if (confirm("确定要重置所有数据吗？此操作不可撤销。")) {
                    // TODO: Implement reset API
                    alert("此功能尚未实现");
                  }
                }}
              >
                重置
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
