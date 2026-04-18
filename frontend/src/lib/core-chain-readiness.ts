export type CoreChainReadinessStage =
  | "needs_project_info"
  | "ready_for_outline"
  | "needs_model_for_chapter"
  | "ready_for_chapter"
  | "readiness_unknown";

interface CoreChainReadinessInput {
  hasProjectSummary: boolean;
  hasOutline: boolean;
  hasRealModel: boolean | null;
}

export interface CoreChainReadiness {
  stage: CoreChainReadinessStage;
  label: string;
  description: string;
  nextAction: string;
  canGenerateOutline: boolean;
  canGenerateChapter: boolean;
  badgeClassName: string;
}

const BADGE_CLASS_BY_STAGE: Record<CoreChainReadinessStage, string> = {
  needs_project_info: "bg-amber-100 text-amber-700",
  ready_for_outline: "bg-blue-100 text-blue-700",
  needs_model_for_chapter: "bg-amber-100 text-amber-700",
  ready_for_chapter: "bg-green-100 text-green-700",
  readiness_unknown: "bg-gray-100 text-gray-600",
};

export function getCoreChainReadiness({
  hasProjectSummary,
  hasOutline,
  hasRealModel,
}: CoreChainReadinessInput): CoreChainReadiness {
  if (!hasOutline) {
    if (!hasProjectSummary) {
      return {
        stage: "needs_project_info",
        label: "待补项目信息",
        description: "当前项目还缺少可用故事简介，先补全简介，再生成大纲。",
        nextAction: "回到项目页补全简介",
        canGenerateOutline: false,
        canGenerateChapter: false,
        badgeClassName: BADGE_CLASS_BY_STAGE.needs_project_info,
      };
    }

    return {
      stage: "ready_for_outline",
      label: "可生成大纲",
      description: "项目简介已就绪，可以先生成大纲，再进入章节创作。",
      nextAction: "先生成大纲",
      canGenerateOutline: true,
      canGenerateChapter: false,
      badgeClassName: BADGE_CLASS_BY_STAGE.ready_for_outline,
    };
  }

  if (hasRealModel === null) {
    return {
      stage: "readiness_unknown",
      label: "状态待确认",
      description: "大纲已就绪，但当前无法确认模型配置状态。",
      nextAction: "刷新页面或重新检查设置",
      canGenerateOutline: hasProjectSummary,
      canGenerateChapter: false,
      badgeClassName: BADGE_CLASS_BY_STAGE.readiness_unknown,
    };
  }

  if (!hasRealModel) {
    return {
      stage: "needs_model_for_chapter",
      label: "待配置写作模型",
      description: "大纲已就绪，但章节生成仍缺少真实模型配置。",
      nextAction: "去设置页配置真实模型",
      canGenerateOutline: hasProjectSummary,
      canGenerateChapter: false,
      badgeClassName: BADGE_CLASS_BY_STAGE.needs_model_for_chapter,
    };
  }

  return {
    stage: "ready_for_chapter",
    label: "可生成章节",
    description: "大纲和真实模型都已就绪，可以生成下一章。",
    nextAction: "进入章节页生成下一章",
    canGenerateOutline: hasProjectSummary,
    canGenerateChapter: true,
    badgeClassName: BADGE_CLASS_BY_STAGE.ready_for_chapter,
  };
}
