import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";

export function Projects() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto py-16 px-4">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-3">InkFoundry</h1>
          <p className="text-gray-500 text-lg">AI 长篇小说创作系统</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Create New Project Card */}
          <div
            className="bg-white rounded-xl border-2 border-dashed border-gray-300 p-8 flex flex-col items-center justify-center cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition"
            onClick={() => navigate("/create")}
          >
            <div className="text-5xl mb-4 text-gray-300">+</div>
            <h2 className="text-xl font-semibold mb-2">创建新项目</h2>
            <p className="text-gray-400 text-sm text-center">
              选择题材、填写信息，开始你的创作之旅
            </p>
            <Button className="mt-4" onClick={() => navigate("/create")}>
              开始创作
            </Button>
          </div>

          {/* Quick Start Card */}
          <div
            className="bg-white rounded-xl border p-8 flex flex-col items-center justify-center cursor-pointer hover:shadow-lg transition"
            onClick={() => navigate("/workspace")}
          >
            <div className="text-5xl mb-4">📖</div>
            <h2 className="text-xl font-semibold mb-2">进入工作区</h2>
            <p className="text-gray-400 text-sm text-center">
              直接进入最近的创作项目
            </p>
            <Button variant="outline" className="mt-4" onClick={() => navigate("/workspace")}>
              打开工作区
            </Button>
          </div>
        </div>

        {/* Features */}
        <div className="mt-16 grid grid-cols-3 gap-6 text-center">
          <div>
            <div className="text-2xl mb-2">🤖</div>
            <h3 className="font-medium mb-1">AI 驱动</h3>
            <p className="text-sm text-gray-400">全自动章节生成</p>
          </div>
          <div>
            <div className="text-2xl mb-2">📊</div>
            <h3 className="font-medium mb-1">张力曲线</h3>
            <p className="text-sm text-gray-400">智能节奏控制</p>
          </div>
          <div>
            <div className="text-2xl mb-2">🔒</div>
            <h3 className="font-medium mb-1">逻辑一致性</h3>
            <p className="text-sm text-gray-400">StateDB 单一真相源</p>
          </div>
        </div>
      </div>
    </div>
  );
}
