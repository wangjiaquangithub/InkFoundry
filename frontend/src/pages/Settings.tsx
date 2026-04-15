import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";

export function Settings() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate("/")}>
            返回
          </Button>
          <h1 className="text-xl font-bold">设置</h1>
        </div>
      </header>

      <div className="max-w-3xl mx-auto p-6 space-y-6">
        {/* Model Configuration */}
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">模型配置</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">默认模型</label>
              <input
                type="text"
                defaultValue="qwen-plus"
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="例如: qwen-plus, claude-sonnet-4-6"
              />
              <p className="text-xs text-gray-400 mt-1">
                用于大多数章节生成的默认模型
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">高优先级模型</label>
              <input
                type="text"
                defaultValue=""
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="用于关键章节的高质量模型"
              />
              <p className="text-xs text-gray-400 mt-1">
                用于高潮章节、结局等重要部分的模型
              </p>
            </div>
          </div>
        </div>

        {/* Pipeline Settings */}
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">流水线设置</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">审核模式</label>
              <select className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="strict">严格模式 - 每章需用户审批</option>
                <option value="milestone">里程碑模式 - 关键节点审批</option>
                <option value="headless">无人值守 - 全自动生成</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">最大重试次数</label>
              <input
                type="number"
                defaultValue={3}
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

        {/* API Keys */}
        <div className="bg-white rounded-xl border p-6">
          <h2 className="font-semibold mb-4">API 密钥</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">OpenAI API Key</label>
              <input
                type="password"
                defaultValue=""
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="sk-..."
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">通义千问 API Key</label>
              <input
                type="password"
                defaultValue=""
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="sk-..."
              />
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
              <Button variant="outline" size="sm" className="text-red-600 border-red-200">
                重置
              </Button>
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <Button>保存设置</Button>
        </div>
      </div>
    </div>
  );
}
