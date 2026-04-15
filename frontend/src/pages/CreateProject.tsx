import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";

const GENRES = [
  { value: "xuanhuan", label: "玄幻" },
  { value: "xianxia", label: "仙侠" },
  { value: "urban", label: "都市" },
  { value: "scifi", label: "科幻" },
  { value: "wuxia", label: "武侠" },
];

export function CreateProject() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [genre, setGenre] = useState("xuanhuan");
  const [title, setTitle] = useState("");
  const [summary, setSummary] = useState("");
  const [totalChapters, setTotalChapters] = useState(100);

  const handleSubmit = async () => {
    // Save project config and navigate to outline
    localStorage.setItem("pendingProject", JSON.stringify({
      genre, title, summary, totalChapters,
    }));
    navigate("/outline");
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow-lg p-8 max-w-lg w-full">
        {/* Progress indicator */}
        <div className="flex items-center gap-2 mb-6">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex-1 h-2 rounded-full bg-gray-200">
              <div
                className={`h-2 rounded-full transition-all ${
                  s <= step ? "bg-blue-500" : "bg-gray-200"
                }`}
                style={{ width: s <= step ? "100%" : "0%" }}
              />
            </div>
          ))}
        </div>

        <h1 className="text-2xl font-bold mb-6">创建新项目</h1>

        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-lg font-medium">第一步：选择题材</h2>
            <div className="grid grid-cols-2 gap-3">
              {GENRES.map((g) => (
                <button
                  key={g.value}
                  onClick={() => setGenre(g.value)}
                  className={`p-4 rounded-lg border-2 text-center transition ${
                    genre === g.value
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                >
                  <span className="text-lg font-medium">{g.label}</span>
                </button>
              ))}
            </div>
            <Button className="w-full" onClick={() => setStep(2)}>
              下一步
            </Button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-lg font-medium">第二步：填写信息</h2>
            <div>
              <label className="block text-sm font-medium mb-1">标题</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="输入小说标题"
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">简介</label>
              <textarea
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="一句话描述你的故事"
                rows={3}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">目标章数</label>
              <input
                type="number"
                value={totalChapters}
                onChange={(e) => setTotalChapters(Number(e.target.value))}
                min={10}
                max={5000}
                className="w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setStep(1)}>
                上一步
              </Button>
              <Button className="flex-1" onClick={() => setStep(3)}>
                下一步
              </Button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h2 className="text-lg font-medium">第三步：确认</h2>
            <div className="bg-gray-50 p-4 rounded-lg space-y-2">
              <p><span className="font-medium">题材：</span>{GENRES.find((g) => g.value === genre)?.label}</p>
              <p><span className="font-medium">标题：</span>{title || "未命名"}</p>
              <p><span className="font-medium">简介：</span>{summary || "无"}</p>
              <p><span className="font-medium">章数：</span>{totalChapters}</p>
            </div>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setStep(2)}>
                上一步
              </Button>
              <Button className="flex-1" onClick={handleSubmit}>
                开始创作
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
