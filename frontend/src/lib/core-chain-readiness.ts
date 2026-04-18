import type { CoreChainReadinessFacts } from "../types";

export type CoreChainReadinessStage =
  | "needs_project_info"
  | "ready_for_outline"
  | "needs_model_for_chapter"
  | "ready_for_chapter"
  | "readiness_unknown";

interface CoreChainReadinessInput {
  hasProjectSummary: boolean | null;
  hasOutline: boolean | null;
  hasRealModel: boolean | null;
  facts?: CoreChainReadinessFacts | null;
}

export interface CoreChainReadinessAction {
  label: string;
  kind: "navigate" | "refresh";
  route: string | null;
}

export interface CoreChainReadiness {
  stage: CoreChainReadinessStage;
  label: string;
  description: string;
  nextAction: string;
  primaryAction: CoreChainReadinessAction;
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
  facts,
}: CoreChainReadinessInput): CoreChainReadiness {
  const resolvedHasProjectSummary = facts?.project_brief_ready ?? hasProjectSummary;
  const resolvedHasOutline = facts?.outline_ready ?? hasOutline;
  const resolvedHasRealModel = facts?.real_model_ready ?? hasRealModel;
  const projectBriefMissing = resolvedHasProjectSummary === false;
  const projectBriefReady = resolvedHasProjectSummary === true;
  const canRetryOutline = resolvedHasProjectSummary !== false;

  if (facts?.chapter_ready) {
    return {
      stage: "ready_for_chapter",
      label: "可生成章节",
      description: "大纲和真实模型都已就绪，可以生成下一章。",
      nextAction: "进入章节页生成下一章",
      primaryAction: {
        label: "前往章节页",
        kind: "navigate",
        route: "/chapters",
      },
      canGenerateOutline: true,
      canGenerateChapter: true,
      badgeClassName: BADGE_CLASS_BY_STAGE.ready_for_chapter,
    };
  }

  if (projectBriefMissing) {
    return {
      stage: "needs_project_info",
      label: "待补项目信息",
      description: "当前项目还缺少可用故事简介，先补全简介，再生成大纲或继续章节创作。",
      nextAction: "回到项目页补全简介",
      primaryAction: {
        label: "回到项目页",
        kind: "navigate",
        route: "/",
      },
      canGenerateOutline: false,
      canGenerateChapter: false,
      badgeClassName: BADGE_CLASS_BY_STAGE.needs_project_info,
    };
  }

  if (resolvedHasOutline === null) {
    return {
      stage: "readiness_unknown",
      label: "状态待确认",
      description: projectBriefReady
        ? "当前无法确认大纲状态，但项目简介已就绪，可以直接重试生成大纲。"
        : "当前无法确认项目简介和大纲状态，但你仍可在大纲页重试生成。",
      nextAction: "前往大纲页重试生成",
      primaryAction: {
        label: "去大纲页重试",
        kind: "navigate",
        route: "/outline",
      },
      canGenerateOutline: canRetryOutline,
      canGenerateChapter: false,
      badgeClassName: BADGE_CLASS_BY_STAGE.readiness_unknown,
    };
  }

  if (!resolvedHasOutline) {
    if (!projectBriefReady) {
      return {
        stage: "readiness_unknown",
        label: "状态待确认",
        description: "当前尚未生成大纲，且项目简介状态未完全确认，你仍可直接尝试生成大纲。",
        nextAction: "前往大纲页生成",
        primaryAction: {
          label: "前往大纲页",
          kind: "navigate",
          route: "/outline",
        },
        canGenerateOutline: canRetryOutline,
        canGenerateChapter: false,
        badgeClassName: BADGE_CLASS_BY_STAGE.readiness_unknown,
      };
    }

    return {
      stage: "ready_for_outline",
      label: "可生成大纲",
      description: "项目简介已就绪，可以先生成大纲，再进入章节创作。",
      nextAction: "先生成大纲",
      primaryAction: {
        label: "前往大纲页",
        kind: "navigate",
        route: "/outline",
      },
      canGenerateOutline: true,
      canGenerateChapter: false,
      badgeClassName: BADGE_CLASS_BY_STAGE.ready_for_outline,
    };
  }

  if (resolvedHasRealModel === null) {
    return {
      stage: "readiness_unknown",
      label: "状态待确认",
      description: "大纲已就绪，但当前无法确认模型配置状态。",
      nextAction: "刷新页面或重新检查设置",
      primaryAction: {
        label: "去设置页检查模型",
        kind: "navigate",
        route: "/settings",
      },
      canGenerateOutline: canRetryOutline,
      canGenerateChapter: false,
      badgeClassName: BADGE_CLASS_BY_STAGE.readiness_unknown,
    };
  }

  if (!resolvedHasRealModel) {
    return {
      stage: "needs_model_for_chapter",
      label: "待配置写作模型",
      description: "大纲已就绪，但章节生成仍缺少真实模型配置。",
      nextAction: "去设置页配置真实模型",
      primaryAction: {
        label: "前往设置页",
        kind: "navigate",
        route: "/settings",
      },
      canGenerateOutline: canRetryOutline,
      canGenerateChapter: false,
      badgeClassName: BADGE_CLASS_BY_STAGE.needs_model_for_chapter,
    };
  }

  return {
    stage: "ready_for_chapter",
    label: "可生成章节",
    description: "大纲和真实模型都已就绪，可以生成下一章。",
    nextAction: "进入章节页生成下一章",
    primaryAction: {
      label: "前往章节页",
      kind: "navigate",
      route: "/chapters",
    },
    canGenerateOutline: true,
    canGenerateChapter: true,
    badgeClassName: BADGE_CLASS_BY_STAGE.ready_for_chapter,
  };
}
