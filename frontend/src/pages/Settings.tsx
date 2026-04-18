import axios from "axios";
import { useState, useEffect } from "react";
import { api } from "../api/client";
import type { SnapshotRecord } from "../api/client";
import { useAppContext } from "../app-context";
import { Button } from "../components/ui/button";
import { getCoreChainReadiness } from "../lib/core-chain-readiness";

interface SnapshotHistoryItem {
  version: number;
  chapter_num: number;
  created_at?: string;
  characters: number;
  world_states: number;
}

const DEFAULT_CONFIG = {
  llm_api_key: "",
  llm_base_url: "https://coding.dashscope.aliyuncs.com/v1",
  default_model: "qwen3.6-plus",
  writer_model: "",
  editor_model: "",
  redteam_model: "",
  navigator_model: "",
  director_model: "",
  review_mode: "strict",
  max_retries: 3,
  pipeline_parallel: false,
};

type ConfigState = typeof DEFAULT_CONFIG;

export function Settings() {
  const { currentBook } = useAppContext();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [config, setConfig] = useState(DEFAULT_CONFIG);
  const [hasSavedModel, setHasSavedModel] = useState<boolean | null>(null);
  const [hasOutline, setHasOutline] = useState<boolean | null>(null);

  // Snapshots
  const [snapshots, setSnapshots] = useState<SnapshotHistoryItem[]>([]);
  const [snapshotError, setSnapshotError] = useState<string | null>(null);
  const [restoring, setRestoring] = useState<number | null>(null);

  useEffect(() => {
    loadConfig();
    loadSnapshots();
    void loadOutlineState();
  }, [currentBook?.id]);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const res = await api.getConfig();
      setConfig({
        llm_api_key: "",
        llm_base_url: res.data.llm_base_url || "https://coding.dashscope.aliyuncs.com/v1",
        default_model: res.data.default_model || "qwen3.6-plus",
        writer_model: res.data.writer_model || "",
        editor_model: res.data.editor_model || "",
        redteam_model: res.data.redteam_model || "",
        navigator_model: res.data.navigator_model || "",
        director_model: res.data.director_model || "",
        review_mode: res.data.review_mode || "strict",
        max_retries: res.data.max_retries || 3,
        pipeline_parallel: res.data.pipeline_parallel || false,
      });
      setHasSavedModel(Boolean(res.data.llm_api_key_masked || res.data.llm_api_key));
    } catch {
      console.error("Failed to load config");
      setHasSavedModel(null);
    } finally {
      setLoading(false);
    }
  };

  const loadSnapshots = async () => {
    try {
      const res = await api.listSnapshots();
      setSnapshots(
        res.data.snapshots.map((snapshot: SnapshotRecord) => ({
          version: snapshot.version,
          chapter_num: snapshot.chapter_num,
          created_at: undefined,
          characters: snapshot.characters.length,
          world_states: snapshot.world_states.length,
        }))
      );
      setSnapshotError(null);
    } catch {
      console.error("Failed to load snapshots");
      setSnapshotError("版本历史加载失败，请稍后重试");
    }
  };

  const loadOutlineState = async () => {
    try {
      const res = await api.getOutline();
      setHasOutline(Boolean(res.data.outline));
    } catch {
      setHasOutline(false);
    }
  };

  const handleRestoreSnapshot = async (version: number) => {
    if (!confirm(`确定要回滚到版本 ${version} 吗？当前状态将被覆盖。`)) return;
    setRestoring(version);
    try {
      await api.restoreSnapshot(version);
      alert("回滚成功");
      loadSnapshots();
    } catch (e: unknown) {
      console.error("Failed to restore snapshot:", e);
      alert("回滚失败");
    } finally {
      setRestoring(null);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setSaved(false);
    try {
      const payload: Partial<ConfigState> = { ...config };
      if (!payload.llm_api_key?.trim()) {
        delete payload.llm_api_key;
      }
      await api.saveConfig(payload);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: unknown) {
      console.error("Failed to save config:", e);
      const detail = axios.isAxiosError(e)
        ? (() => {
            const data = e.response?.data as { detail?: unknown } | undefined;
            if (typeof data?.detail === "string") return data.detail;
            if (Array.isArray(data?.detail)) {
              return data.detail
                .map((item) => (typeof item === "string" ? item : JSON.stringify(item)))
                .join("; ");
            }
            if (data?.detail) return JSON.stringify(data.detail);
            return undefined;
          })()
        : undefined;
      alert("保存失败: " + (detail || (e instanceof Error ? e.message : "未知错误")));
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm("确定要重置当前项目的配置吗？此操作将删除已保存的 API 密钥、模型和流水线设置。")) return;
    setResetting(true);
    try {
      await api.resetConfig();
      await loadConfig();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: unknown) {
      console.error("Failed to reset config:", e);
      alert("重置失败，请重试");
    } finally {
      setResetting(false);
    }
  };

  const update = <K extends keyof ConfigState>(field: K, value: ConfigState[K]) => {
    setConfig((prev) => ({ ...prev, [field]: value }));
  };

  if (loading) {
    return <div className="flex items-center justify-center h-full"><p className="text-gray-400">加载配置中...</p></div>;
  }

  const chainReadiness = getCoreChainReadiness({
    hasProjectSummary: Boolean(currentBook?.summary.trim()),
    hasOutline: Boolean(hasOutline),
    hasRealModel: hasSavedModel,
  });

  return (
    <div className="h-full overflow-auto p-6">
      {/* Toolbar */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-lg font-semibold">当前项目设置</h2>
          <p className="text-sm text-gray-400 mt-1">管理当前项目的模型、流水线和版本快照配置</p>
          <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-gray-500">
            <span className={`rounded-full px-2.5 py-1 ${chainReadiness.badgeClassName}`}>
              链路状态：{chainReadiness.label}
            </span>
            <span>{chainReadiness.description}</span>
            <span>下一步：{chainReadiness.nextAction}</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="text-sm text-green-500">已保存</span>
          )}
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "保存中..." : "保存设置"}
          </Button>
        </div>
      </div>

      <div className="max-w-3xl space-y-6">
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
                用于调用 LLM API 的密钥。章节生成要求这里存在真实模型配置。
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">API Base URL</label>
              <input
                type="text"
                value={config.llm_base_url}
                onChange={(e) => update("llm_base_url", e.target.value)}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="https://coding.dashscope.aliyuncs.com/v1"
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
                placeholder="例如: qwen3.6-plus, claude-sonnet-4-6"
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

        {/* Snapshot Management */}
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">版本历史</h2>
          {snapshotError ? (
            <p className="text-sm text-red-500">{snapshotError}</p>
          ) : snapshots.length === 0 ? (
            <p className="text-sm text-gray-400">暂无快照数据</p>
          ) : (
            <div className="space-y-2">
              {snapshots.map((s) => (
                <div key={s.version} className="flex justify-between items-center p-3 border rounded-lg">
                  <div>
                    <p className="font-medium">版本 {s.version}</p>
                    <p className="text-xs text-gray-400">
                      章节 {s.chapter_num} · {s.characters} 个角色 · {s.world_states} 个世界状态
                    </p>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRestoreSnapshot(s.version)}
                    disabled={restoring === s.version}
                  >
                    {restoring === s.version ? "回滚中..." : "回滚"}
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Danger Zone */}
        <div className="bg-white rounded-xl border border-red-200 p-6">
          <h2 className="font-semibold mb-4 text-red-600">危险操作</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <div>
                <p className="font-medium">重置配置</p>
                <p className="text-sm text-gray-400">删除当前项目保存的 API 密钥、模型和流水线设置</p>
              </div>
              <Button
                variant="outline"
                size="sm"
                className="text-red-600 border-red-200"
                onClick={handleReset}
                disabled={resetting}
              >
                {resetting ? "重置中..." : "重置配置"}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
