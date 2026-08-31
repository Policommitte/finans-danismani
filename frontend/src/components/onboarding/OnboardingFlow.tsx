"use client";

import { ReactNode, useState } from "react";
import type { RiskTier } from "../../models/auth";
import { useAuth } from "../../hooks/useAuth";
import { completeOnboarding } from "../../services/authService";
import { RiskProfileQuiz } from "../profile/RiskProfileQuiz";
import { OnboardingBundleScreen } from "./OnboardingBundleScreen";
import { OnboardingTour } from "./OnboardingTour";

type Step = "quiz" | "bundle" | "tour";

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
              setStep("tour");
            } finally {
              setSaving(false);
            }
          }}
        />
      </FullscreenOverlay>
    );
  }

  if (step === "tour") {
    // Kasitli olarak FullscreenOverlay YOK: driver.js'in gercek Sidebar/
    // Dashboard DOM'unu hedefleyebilmesi icin altta gercek sayfa gorunmeli.
    //
    // NOT: `auth.refresh()` (bir onceki adimda) sunucu bayragini true yaptigi
    // icin AppShell'in KENDI gate mantigi bu noktada zaten "tamamlandi"
    // diyebilir - bu yuzden turun gorunur kalmasi `onDone` ile AppShell'e
    // devredilen AYRI bir yerel state'e bagli, canli `onboarding_completed`
    // degerine degil (bkz. AppShell.tsx `onboardingActive`).
    return <OnboardingTour onFinish={onDone} />;
  }

  return null;
}
