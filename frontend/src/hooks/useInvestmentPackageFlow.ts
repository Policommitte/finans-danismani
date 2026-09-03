"use client";

import { useCallback, useRef, useState } from "react";
import {
  CANCEL_FLOW_ID,
  GOAL_KEYWORDS,
  HORIZON_KEYWORDS,
  RESTART_FLOW_ID,
  RISK_KEYWORDS,
  START_INVESTMENT_FLOW_ID,
  getInvestmentFlowCopy,
} from "../components/chat/investmentFlowCopy";
import type { AppLanguage } from "../contexts/LanguageContext";
import type {
  ChatMessage,
  ChatQuickReply,
  InvestmentGoal,
  InvestmentHorizon,
  InvestmentPackageRequest,
  InvestmentRiskProfile,
} from "../models/chat";
import { getInvestmentPackage } from "../services/recommendationService";
import { formatBudget, parseBudgetInput } from "../utils/budgetInput";

export type InvestmentFlowStep = "idle" | "budget" | "horizon" | "risk" | "goal" | "building" | "done";

type FlowState = {
  step: InvestmentFlowStep;
  answers: Partial<InvestmentPackageRequest>;
  /** Assistant message currently showing quick replies; cleared once answered. */
  promptMessageId: string | null;
};

const INITIAL_STATE: FlowState = { step: "idle", answers: {}, promptMessageId: null };

function matchKeyword<T extends string>(text: string, keywords: Record<T, string[]>): T | null {
  const normalized = text.toLocaleLowerCase("tr-TR");
  for (const [value, words] of Object.entries(keywords) as Array<[T, string[]]>) {
    if (words.some((word) => normalized.includes(word))) return value;
  }
  return null;
}

/**
 * Conversation state machine for the "I want to invest" quick flow.
 *
 * Order of questions: budget -> horizon -> risk -> goal. Budget comes first
 * because every later answer is framed around it ("with 50.000 ₺ ..."), and
 * the goal comes last so the user has already anchored on how long and how
 * risky before naming what the money is for. Every message the flow produces
 * is local - nothing is sent to the chat backend; only the final package
 * request hits the API.
 */
export function useInvestmentPackageFlow({
  language,
  appendLocalMessage,
  updateMessage,
}: {
  language: AppLanguage;
  appendLocalMessage: (message: Omit<ChatMessage, "id" | "local">) => string;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
}) {
  const copy = getInvestmentFlowCopy(language);
  const stateRef = useRef<FlowState>(INITIAL_STATE);
  const [step, setStep] = useState<InvestmentFlowStep>("idle");
  const locale = language === "tr" ? "tr-TR" : "en-US";

  const setState = useCallback((next: Partial<FlowState>) => {
    stateRef.current = { ...stateRef.current, ...next };
    setStep(stateRef.current.step);
  }, []);

  const cancelReply = useCallback(
    (): ChatQuickReply => ({ id: CANCEL_FLOW_ID, label: copy.cancelLabel, message: copy.cancelLabel }),
    [copy.cancelLabel],
  );

  /** Posts an assistant question with tappable answers and remembers it. */
  const ask = useCallback(
    (content: string, quickReplies: ChatQuickReply[], nextStep: InvestmentFlowStep) => {
      const previous = stateRef.current.promptMessageId;
      if (previous) updateMessage(previous, { quickReplies: undefined });
      const id = appendLocalMessage({
        role: "assistant",
        content,
        quickReplies: [...quickReplies, cancelReply()],
      });
      setState({ step: nextStep, promptMessageId: id });
    },
    [appendLocalMessage, cancelReply, setState, updateMessage],
  );

  const clearPrompt = useCallback(() => {
    const previous = stateRef.current.promptMessageId;
    if (previous) updateMessage(previous, { quickReplies: undefined });
    setState({ promptMessageId: null });
  }, [setState, updateMessage]);

  const askBudget = useCallback(() => {
    ask(
      copy.askBudget,
      copy.budgetPresets.map((amount) => ({
        id: `budget-${amount}`,
        label: formatBudget(amount, locale),
        message: formatBudget(amount, locale),
      })),
      "budget",
    );
  }, [ask, copy.askBudget, copy.budgetPresets, locale]);

  const askHorizon = useCallback(
    (amount: number) => {
      ask(
        copy.askHorizon(formatBudget(amount, locale)),
        copy.horizonOptions.map((option) => ({
          id: `horizon-${option.value}`,
          label: option.label,
          hint: option.hint,
          message: `${option.label} (${option.hint})`,
        })),
        "horizon",
      );
    },
    [ask, copy, locale],
  );

  const askRisk = useCallback(() => {
    ask(
      copy.askRisk,
      copy.riskOptions.map((option) => ({
        id: `risk-${option.value}`,
        label: option.label,
        hint: option.hint,
        message: option.label,
      })),
      "risk",
    );
  }, [ask, copy.askRisk, copy.riskOptions]);

  const askGoal = useCallback(() => {
    ask(
      copy.askGoal,
      copy.goalOptions.map((option) => ({
        id: `goal-${option.value}`,
        label: option.label,
        hint: option.hint,
        message: option.label,
      })),
      "goal",
    );
  }, [ask, copy.askGoal, copy.goalOptions]);

  const buildPackage = useCallback(
    async (request: InvestmentPackageRequest) => {
      clearPrompt();
      const buildingId = appendLocalMessage({ role: "assistant", content: copy.building });
      setState({ step: "building" });
      try {
        const investmentPackage = await getInvestmentPackage(request);
        updateMessage(buildingId, {
          content: copy.ready(investmentPackage.title),
          investmentPackage,
          quickReplies: [{ id: RESTART_FLOW_ID, label: copy.restartLabel, message: copy.restartLabel }],
        });
        setState({ step: "done", promptMessageId: buildingId });
      } catch (error) {
        const reason = error instanceof Error ? error.message : "";
        updateMessage(buildingId, {
          content: copy.failed(reason),
          quickReplies: [{ id: RESTART_FLOW_ID, label: copy.restartLabel, message: copy.restartLabel }],
        });
        setState({ step: "done", promptMessageId: buildingId });
      }
    },
    [appendLocalMessage, clearPrompt, copy, setState, updateMessage],
  );

  const start = useCallback(
    (echoUserMessage = true) => {
      clearPrompt();
      if (echoUserMessage) {
        appendLocalMessage({ role: "user", content: copy.suggestions[0].message });
      }
      appendLocalMessage({ role: "assistant", content: copy.startMessage });
      setState({ answers: {} });
      askBudget();
    },
    [appendLocalMessage, askBudget, clearPrompt, copy.startMessage, copy.suggestions, setState],
  );

  const cancel = useCallback(() => {
    clearPrompt();
    appendLocalMessage({ role: "assistant", content: copy.cancelled });
    setState({ step: "idle", answers: {}, promptMessageId: null });
  }, [appendLocalMessage, clearPrompt, copy.cancelled, setState]);

  const advance = useCallback(
    (text: string) => {
      const { step: currentStep, answers } = stateRef.current;
      const normalized = text.toLocaleLowerCase("tr-TR");
      if (copy.cancelKeywords.some((word) => normalized.includes(word))) {
        cancel();
        return;
      }

      if (currentStep === "budget") {
        const amount = parseBudgetInput(text);
        if (amount === null) {
          appendLocalMessage({ role: "assistant", content: copy.budgetNotUnderstood });
          return;
        }
        setState({ answers: { ...answers, amount } });
        askHorizon(amount);
        return;
      }

      if (currentStep === "horizon") {
        const horizon = matchKeyword<InvestmentHorizon>(text, HORIZON_KEYWORDS);
        if (!horizon) {
          appendLocalMessage({ role: "assistant", content: copy.optionNotUnderstood });
          return;
        }
        setState({ answers: { ...answers, horizon } });
        askRisk();
        return;
      }

      if (currentStep === "risk") {
        const risk = matchKeyword<InvestmentRiskProfile>(text, RISK_KEYWORDS);
        if (!risk) {
          appendLocalMessage({ role: "assistant", content: copy.optionNotUnderstood });
          return;
        }
        setState({ answers: { ...answers, risk_profile: risk } });
        askGoal();
        return;
      }

      if (currentStep === "goal") {
        const goal = matchKeyword<InvestmentGoal>(text, GOAL_KEYWORDS);
        if (!goal) {
          appendLocalMessage({ role: "assistant", content: copy.optionNotUnderstood });
          return;
        }
        const request = { ...answers, goal } as InvestmentPackageRequest;
        setState({ answers: request });
        void buildPackage(request);
      }
    },
    [appendLocalMessage, askGoal, askHorizon, askRisk, buildPackage, cancel, copy, setState],
  );

  /**
   * Called by the widget for every outgoing user message. Returns true when
   * the flow consumed it (so it must NOT be sent to the chat backend).
   */
  const handleUserMessage = useCallback(
    (text: string): boolean => {
      const currentStep = stateRef.current.step;
      if (currentStep === "idle" || currentStep === "done" || currentStep === "building") {
        return false;
      }
      appendLocalMessage({ role: "user", content: text });
      advance(text);
      return true;
    },
    [advance, appendLocalMessage],
  );

  /**
   * Quick-reply taps. Returns true when handled locally; false means the
   * reply is a plain question that should go to the chat backend as-is.
   */
  const handleQuickReply = useCallback(
    (reply: ChatQuickReply): boolean => {
      if (reply.id === START_INVESTMENT_FLOW_ID || reply.id === RESTART_FLOW_ID) {
        start(reply.id === START_INVESTMENT_FLOW_ID);
        return true;
      }
      if (reply.id === CANCEL_FLOW_ID) {
        appendLocalMessage({ role: "user", content: reply.message });
        cancel();
        return true;
      }
      const currentStep = stateRef.current.step;
      if (currentStep === "idle" || currentStep === "done" || currentStep === "building") {
        return false;
      }
      appendLocalMessage({ role: "user", content: reply.message });
      // Option ids carry the enum value, so taps never depend on label parsing.
      const [kind, value] = reply.id.split("-", 2);
      const { answers } = stateRef.current;
      if (kind === "budget") {
        const amount = Number(value);
        setState({ answers: { ...answers, amount } });
        askHorizon(amount);
      } else if (kind === "horizon") {
        setState({ answers: { ...answers, horizon: value as InvestmentHorizon } });
        askRisk();
      } else if (kind === "risk") {
        setState({ answers: { ...answers, risk_profile: value as InvestmentRiskProfile } });
        askGoal();
      } else if (kind === "goal") {
        const request = { ...answers, goal: value as InvestmentGoal } as InvestmentPackageRequest;
        setState({ answers: request });
        void buildPackage(request);
      } else {
        advance(reply.message);
      }
      return true;
    },
    [advance, appendLocalMessage, askGoal, askHorizon, askRisk, buildPackage, cancel, setState, start],
  );

  const notifyPurchased = useCallback(
    (orderCount: number) => {
      appendLocalMessage({ role: "assistant", content: copy.purchased(orderCount) });
    },
    [appendLocalMessage, copy],
  );

  const isCollectingAnswers = step === "budget" || step === "horizon" || step === "risk" || step === "goal";

  return {
    step,
    isActive: isCollectingAnswers || step === "building",
    inputPlaceholder: step === "budget" ? copy.budgetPlaceholder : isCollectingAnswers ? copy.inputPlaceholder : null,
    suggestions: copy.suggestions,
    suggestionTitle: copy.suggestionTitle,
    handleUserMessage,
    handleQuickReply,
    notifyPurchased,
  };
}
