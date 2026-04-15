import { useState, useEffect } from "react";
import { Button } from "./ui/button";

interface ChapterEditorProps {
  chapterNum: number;
  title?: string;
  content?: string;
  status?: string;
  onSave?: (data: { title?: string; content?: string }) => void;
  onGenerate?: (chapterNum: number) => void;
  generating?: boolean;
}

export function ChapterEditor({
  chapterNum,
  title = "",
  content = "",
  status = "pending",
  onSave,
  onGenerate,
  generating = false,
}: ChapterEditorProps) {
  const [editTitle, setEditTitle] = useState(title);
  const [editContent, setEditContent] = useState(content);
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    setEditTitle(title);
    setEditContent(content);
  }, [title, content, chapterNum]);

  const handleSave = () => {
    onSave?.({ title: editTitle, content: editContent });
    setIsEditing(false);
  };

  const statusLabel = (s: string) => {
    const map: Record<string, string> = {
      final: "完成",
      reviewed: "已审",
      draft: "草稿",
      pending: "待写",
    };
    return map[s] || s;
  };

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="border-b bg-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-bold">
            第{chapterNum}章 {isEditing ? (
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                className="border rounded px-2 py-0.5 text-base font-bold"
              />
            ) : (
              editTitle
            )}
          </h2>
          <span className={`text-xs px-2 py-0.5 rounded ${
            status === "final" ? "bg-green-100 text-green-700" :
            status === "reviewed" ? "bg-blue-100 text-blue-700" :
            status === "draft" ? "bg-yellow-100 text-yellow-700" :
            "bg-gray-100 text-gray-500"
          }`}>
            {statusLabel(status)}
          </span>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onGenerate?.(chapterNum)}
            disabled={generating}
          >
            {generating ? "生成中..." : "生成"}
          </Button>
          {isEditing ? (
            <>
              <Button size="sm" onClick={handleSave}>保存</Button>
              <Button variant="outline" size="sm" onClick={() => {
                setEditTitle(title);
                setEditContent(content);
                setIsEditing(false);
              }}>
                取消
              </Button>
            </>
          ) : (
            <Button variant="outline" size="sm" onClick={() => setIsEditing(true)}>
              编辑
            </Button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {isEditing ? (
          <textarea
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            className="w-full h-full min-h-[400px] border rounded-lg p-4 font-serif text-base leading-relaxed focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            placeholder="在此编辑章节内容..."
          />
        ) : editContent ? (
          <div className="max-w-3xl mx-auto whitespace-pre-wrap font-serif text-base leading-relaxed">
            {editContent}
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-400">
            点击「生成」开始创作，或点击「编辑」手动输入内容
          </div>
        )}
      </div>
    </div>
  );
}
