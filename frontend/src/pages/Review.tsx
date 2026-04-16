import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { Button } from "../components/ui/button";
import type { Chapter } from "../types";

export function Review() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [reviews, setReviews] = useState<Chapter[]>([]);

  useEffect(() => {
    loadReviews();
  }, []);

  const loadReviews = async () => {
    setLoading(true);
    try {
      const res = await api.getChapters();
      const chapters = res.data.chapters || [];
      const reviewed = chapters.filter(
        (ch: Chapter) => ch.review_notes || ch.status === "draft" || ch.status === "reviewed" || ch.status === "final"
      );
      setReviews(reviewed);
    } catch {
      setReviews([]);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (ch: Chapter) => {
    try {
      await api.approveChapter(ch.chapter_num);
      loadReviews();
    } catch (err: any) {
      console.error("Failed to approve:", err);
    }
  };

  const handleReject = async (ch: Chapter) => {
    const note = prompt("请输入拒绝原因（可选）：");
    try {
      await api.rejectChapter(ch.chapter_num, note || "");
      loadReviews();
    } catch (err: any) {
      console.error("Failed to reject:", err);
    }
  };

  const statusLabel = (status: string) => {
    const map: Record<string, string> = {
      pending: "待写",
      draft: "草稿",
      reviewed: "已审",
      final: "完成",
    };
    return map[status] || status;
  };

  const statusColor = (status: string) => {
    const map: Record<string, string> = {
      pending: "bg-gray-100 text-gray-500",
      draft: "bg-yellow-100 text-yellow-700",
      reviewed: "bg-blue-100 text-blue-700",
      final: "bg-green-100 text-green-700",
    };
    return map[status] || "bg-gray-100 text-gray-500";
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-400">加载审核数据中...</p>
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
          <h1 className="text-xl font-bold">审核中心</h1>
          <span className="text-sm text-gray-400">
            {reviews.length} 条记录
          </span>
        </div>
      </header>

      <div className="max-w-4xl mx-auto p-6">
        {reviews.length === 0 ? (
          <div className="bg-white rounded-xl border p-12 text-center">
            <div className="text-5xl mb-4">✅</div>
            <h2 className="text-xl font-semibold mb-2">暂无审核记录</h2>
            <p className="text-gray-400">
              生成章节后，编辑器和红队的审核结果会显示在这里
            </p>
            <Button className="mt-4" onClick={() => navigate("/workspace")}>
              去生成章节
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {reviews.map((item) => {
              // Parse review notes if available
              const notes = item.review_notes || "";
              const scoreMatch = notes.match(/score:\s*(\d+)/);
              const score = scoreMatch ? parseInt(scoreMatch[1], 10) : null;

              return (
                <div key={item.chapter_num} className="bg-white rounded-xl border p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-semibold text-lg">
                        第{item.chapter_num}章 {item.title || ""}
                      </h3>
                      <div className="flex gap-2 mt-1">
                        <span className={`text-xs px-2 py-0.5 rounded ${statusColor(item.status)}`}>
                          {statusLabel(item.status)}
                        </span>
                        {score !== null && (
                          <span className="text-xs text-gray-400">
                            编辑评分: {score}/100
                          </span>
                        )}
                        {item.word_count && (
                          <span className="text-xs text-gray-400">
                            {item.word_count} 字
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2">
                      {item.status !== "final" && (
                        <Button size="sm" onClick={() => handleApprove(item)}>
                          批准
                        </Button>
                      )}
                      {item.status !== "final" && (
                        <Button size="sm" variant="outline" onClick={() => handleReject(item)}>
                          拒绝
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Review Notes */}
                  {notes && (
                    <div>
                      <h4 className="text-sm font-medium mb-2 text-gray-600">审核详情</h4>
                      <p className="text-sm text-gray-500">{notes}</p>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
