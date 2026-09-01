/** Yarışma ekranı (soru-cevap) aktifken AppShell'e sidebar/footer'ı gizlemesini söyler. */
export function setGameFocus(active: boolean) {
  window.dispatchEvent(new CustomEvent("polifin-game-focus", { detail: active }));
}