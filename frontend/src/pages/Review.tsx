import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/button";
import type { ReviewItem } from "../types";

// Mock data for Phase 2
const MOCK_REVIEWS: ReviewItem[] = [
  {
    id: "1",
    chapter_num: 3,
    editor_score: 75,
    issues: ["角色对话略显生硬", "战斗场景描写可以更详细"],
    redteam_issues: ["战力逻辑轻微不一致"],
    status: "pending",
  },
  {
    id: "2",
    chapter_num: 7,
    editor_score: 62,
    issues: ["时间线存在矛盾", "角色动机不够清晰"],
    redteam_issues: ["情节存在逻辑漏洞"],
    status: "pending",
  },
];

export function Review() {
  const navigate = useNavigate();

  const statusLabel = (status: string) => {
    const map: Record<string, string> = {
      pending: "待审",
      approved: "通过",
      rejected: "退回",
    };
    return map[status] || status;
  };

  const statusColor = (status: string) => {
    const map: Record<string, string> = {
      pending: "bg-yellow-100 text-yellow-700",
      approved: "bg-green-100 text-green-700",
      rejected: "bg-red-100 text-red-700",
    };
    return map[status] || "bg-gray-100 text-gray-500";
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="outline" size="sm" onClick={() => navigate("/")}>
            返回
          </Button>
          <h1 className="text-xl font-bold">审核中心</h1>
          <span className="text-sm text-gray-400">
            {MOCK_REVIEWS.filter((r) => r.status === "pending").length} 项待审
          </span>
        </div>
      </header>

      <div className="max-w-4xl mx-auto p-6">
        {MOCK_REVIEWS.length === 0 ? (
          <div className="bg-white rounded-xl border p-12 text-center">
            <div className="text-5xl mb-4">✅</div>
            <h2 className="text-xl font-semibold mb-2">没有待审内容</h2>
            <p className="text-gray-400">所有章节都已审核通过</p>
          </div>
        ) : (
          <div className="space-y-4">
            {MOCK_REVIEWS.map((item) => (
              <div key={item.id} className="bg-white rounded-xl border p-6">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <h3 className="font-semibold text-lg">
                      第{item.chapter_num}章
                    </h3>
                    <div className="flex gap-2 mt-1">
                      <span className={`text-xs px-2 py-0.5 rounded ${statusColor(item.status)}`}>
                        {statusLabel(item.status)}
                      </span>
                      <span className="text-xs text-gray-400">
                        编辑评分: {item.editor_score}/100
                      </span>
                    </div>
                  </div>
                  {item.status === "pending" && (
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">退回</Button>
                      <Button size="sm">通过</Button>
                    </div>
                  )}
                </div>

                {/* Editor Issues */}
                {item.issues.length > 0 && (
                  <div className="mb-3">
                    <h4 className="text-sm font-medium mb-2 text-gray-600">编辑意见</h4>
                    <ul className="space-y-1">
                      {item.issues.map((issue, i) => (
                        <li key={i} className="text-sm text-gray-500 flex items-start gap-2">
                          <span className="text-yellow-500 mt-0.5">⚠</span>
                          {issue}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* RedTeam Issues */}
                {item.redteam_issues.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2 text-gray-600">红队攻击发现</h4>
                    <ul className="space-y-1">
                      {item.redteam_issues.map((issue, i) => (
                        <li key={i} className="text-sm text-red-600 flex items-start gap-2">
                          <span className="text-red-500 mt-0.5">⚡</span>
                          {issue}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
