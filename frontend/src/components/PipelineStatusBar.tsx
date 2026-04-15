import { Button } from "./ui/button";

interface PipelineStatusBarProps {
  running: boolean;
  paused: boolean;
  currentChapter: number;
  totalChapters: number;
  currentStep?: string;
  currentAgent?: string;
  progress?: number;
  error?: string | null;
  onPause?: () => void;
  onResume?: () => void;
  onStop?: () => void;
}

const STEP_LABELS: Record<string, string> = {
  starting: "启动中",
  navigator: "导航器规划",
  writer: "写作中",
  editor: "编辑审核",
  redteam: "红队检查",
  saving: "保存中",
  complete: "完成",
  pause: "已暂停",
  stop: "已停止",
};

export function PipelineStatusBar({
  running,
  paused,
  currentChapter,
  totalChapters,
  currentStep = "",
  currentAgent = "",
  progress = 0,
  error = null,
  onPause,
  onResume,
  onStop,
}: PipelineStatusBarProps) {
  if (!running && !error) {
    return (
      <div className="border-t bg-white px-4 py-2 flex items-center justify-between text-sm text-gray-400">
        <span>流水线空闲</span>
        <span>共 {totalChapters} 章</span>
      </div>
    );
  }

  return (
    <div className={`border-t bg-white px-4 py-2 ${error ? "bg-red-50" : ""}`}>
      <div className="flex items-center justify-between">
        {/* Left: Status */}
        <div className="flex items-center gap-3 text-sm">
          {running && !paused && (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-green-700">
                {STEP_LABELS[currentStep] || currentStep || "运行中"}
              </span>
            </span>
          )}
          {paused && (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-yellow-500" />
              <span className="text-yellow-700">已暂停</span>
            </span>
          )}
          {error && (
            <span className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-red-700">{error}</span>
            </span>
          )}
          {currentAgent && (
            <span className="text-gray-500">
              代理: {currentAgent}
            </span>
          )}
        </div>

        {/* Center: Progress */}
        <div className="flex items-center gap-2 text-sm">
          <span>第 {currentChapter}/{totalChapters} 章</span>
          {running && (
            <div className="w-32 h-1.5 bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-1.5 bg-blue-500 rounded-full transition-all"
                style={{ width: `${progress * 100}%` }}
              />
            </div>
          )}
          {running && <span className="text-xs text-gray-400">{Math.round(progress * 100)}%</span>}
        </div>

        {/* Right: Controls */}
        <div className="flex gap-2">
          {running && !paused && onPause && (
            <Button variant="outline" size="sm" onClick={onPause}>
              暂停
            </Button>
          )}
          {paused && onResume && (
            <Button variant="outline" size="sm" onClick={onResume}>
              继续
            </Button>
          )}
          {running && onStop && (
            <Button variant="outline" size="sm" onClick={onStop} className="text-red-600">
              停止
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
