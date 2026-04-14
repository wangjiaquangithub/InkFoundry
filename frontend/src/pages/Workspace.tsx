import { useEffect } from "react";
import { useNovelStore } from "../store/novelStore";
import { Button } from "../components/ui/button";

export function Workspace() {
  const { chapters, characters, selectedChapter, fetchStatus, fetchCharacters, selectChapter } = useNovelStore();

  useEffect(() => {
    fetchStatus();
    fetchCharacters();
  }, []);

  // Sample chapters if empty
  const displayChapters = chapters.length > 0 ? chapters : [
    { number: 1, content: "第一章：启程\n\n故事从这里开始...", status: "final" as const, tension_level: 3 },
    { number: 2, content: "第二章：相遇\n\n命运的齿轮开始转动...", status: "reviewed" as const, tension_level: 5 },
    { number: 3, content: "第三章：冲突\n\n矛盾逐渐显现...", status: "draft" as const, tension_level: 7 },
    { number: 4, content: "", status: "pending" as const, tension_level: 8 },
  ];

  const selected = displayChapters.find((c) => c.number === selectedChapter);

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left: Chapter List */}
      <aside className="w-64 border-r bg-white overflow-y-auto">
        <div className="p-4 border-b">
          <h2 className="font-semibold text-lg">章节列表</h2>
        </div>
        <div className="p-2">
          {displayChapters.map((ch) => (
            <button
              key={ch.number}
              onClick={() => selectChapter(ch.number)}
              className={`w-full text-left p-2 rounded-md mb-1 text-sm ${
                selectedChapter === ch.number
                  ? "bg-blue-50 border border-blue-200"
                  : "hover:bg-gray-50"
              }`}
            >
              <div className="flex justify-between items-center">
                <span className="font-medium">第{ch.number}章</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                  ch.status === "final" ? "bg-green-100 text-green-700" :
                  ch.status === "reviewed" ? "bg-blue-100 text-blue-700" :
                  ch.status === "draft" ? "bg-yellow-100 text-yellow-700" :
                  "bg-gray-100 text-gray-500"
                }`}>
                  {ch.status === "final" ? "完成" :
                   ch.status === "reviewed" ? "已审" :
                   ch.status === "draft" ? "草稿" : "待写"}
                </span>
              </div>
              <div className="flex items-center gap-1 mt-1">
                <span className="text-xs text-gray-400">张力:</span>
                <div className="flex gap-0.5">
                  {Array.from({ length: 10 }).map((_, i) => (
                    <div key={i} className={`w-2 h-1.5 rounded-sm ${
                      i < ch.tension_level ? "bg-red-400" : "bg-gray-200"
                    }`} />
                  ))}
                </div>
              </div>
            </button>
          ))}
        </div>
      </aside>

      {/* Center: Novel Content */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto p-8">
          {selected ? (
            <>
              <div className="flex justify-between items-center mb-6">
                <h1 className="text-2xl font-bold">第{selected.number}章</h1>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm">编辑</Button>
                  <Button size="sm">生成</Button>
                </div>
              </div>
              <div className="bg-white rounded-lg border p-6 min-h-[600px] whitespace-pre-wrap font-serif text-base leading-relaxed">
                {selected.content || "点击「生成」开始创作..."}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full text-gray-400">
              选择左侧章节开始创作
            </div>
          )}
        </div>
      </main>

      {/* Right: Character Panel */}
      <aside className="w-72 border-l bg-white overflow-y-auto">
        <div className="p-4 border-b">
          <h2 className="font-semibold text-lg">角色状态</h2>
        </div>
        <div className="p-3">
          {characters.length > 0 ? characters.map((ch) => (
            <div key={ch.name} className="p-3 border rounded-lg mb-2">
              <div className="flex justify-between items-center">
                <span className="font-medium">{ch.name}</span>
                <span className={`text-xs px-1.5 py-0.5 rounded ${
                  ch.status === "alive" ? "bg-green-100 text-green-700" :
                  ch.status === "inactive" ? "bg-gray-100 text-gray-500" :
                  "bg-red-100 text-red-700"
                }`}>
                  {ch.status}
                </span>
              </div>
              <p className="text-xs text-gray-500 mt-1">{ch.description}</p>
            </div>
          )) : (
            <div className="text-sm text-gray-400 p-3">暂无角色数据</div>
          )}
        </div>
      </aside>
    </div>
  );
}
