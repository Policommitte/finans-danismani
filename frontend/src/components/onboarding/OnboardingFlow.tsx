"use client";

import { ReactNode, useState } from "react";
import type { RiskTier } from "../../models/auth";
import { useAuth } from "../../hooks/useAuth";
import { completeOnboarding } from "../../services/authService";
import { RiskProfileQuiz } from "../profile/RiskProfileQuiz";
import { OnboardingBundleScreen } from "./OnboardingBundleScreen";

type Step = "quiz" | "bundle";

function FullscreenOverlay({ children }: { children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/60 px-4 py-8">
      {children}
    </div>
  );
}

export function OnboardingFlow({ onDone }: { onDone: () => void }) {
  const auth = useAuth();
  const [step, setStep] = useState<Step>("quiz");
  const [tier, setTier] = useState<RiskTier | null>(null);
  const [saving, setSaving] = useState(false);

  if (step === "quiz") {
    return (
      <FullscreenOverlay>
        <div className="w-full max-w-lg">
          <RiskProfileQuiz
            onComplete={(result) => {
              setTier(result);
              setStep("bundle");
            }}
          />
        </div>
      </FullscreenOverlay>
    );
  }

  if (step === "bundle" && tier) {
    return (
      <FullscreenOverlay>
        <OnboardingBundleScreen
          tier={tier}
          onContinue={async () => {
            if (saving) return;
            setSaving(true);
            try {
              await completeOnboarding({ risk_tolerance: tier });
              await auth.refresh();
              // Urun turu (ProductTour) artik burada DEGIL, AppShell'de -
              // `auth.user.has_seen_tour === false` oldugu surece kendi
              // basina otomatik acilir (bkz. AppShell.tsx). Onboarding
              // burada biter.
              onDone();
            } finally {
              setSaving(false);
            }
          }}
        />
      </FullscreenOverlay>
    );
  }

  return null;
}
