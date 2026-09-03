import { describe, expect, it } from "vitest";
import { guvenliUrl } from "./SourceList";

/**
 * `kaynak_url` ingestion hattindan gelir; bu yuzden `href`'e yazilmadan once
 * SUZULUR. Buradaki asil koruma `javascript:` satiridir - kaynak kartina
 * tiklayan kullanicida kod calistirabilirdi.
 */
describe("guvenliUrl", () => {
  it("http ve https adresleri gecirir", () => {
    expect(guvenliUrl("https://www.aa.com.tr/tr/ekonomi/haber")).toBe(
      "https://www.aa.com.tr/tr/ekonomi/haber",
    );
    expect(guvenliUrl("http://bigpara.hurriyet.com.tr/doviz")).toBe(
      "http://bigpara.hurriyet.com.tr/doviz",
    );
  });

  it("javascript: semasini REDDEDER (XSS)", () => {
    expect(guvenliUrl("javascript:alert(document.cookie)")).toBeNull();
    // Buyuk/kucuk harf ve bosluklu varyant da gecmemeli: `new URL()` semayi
    // kucuk harfe indirir ve bastaki bosluklari atar, yani ikisi de ayni
    // sekilde yakalanir.
    expect(guvenliUrl("  JavaScript:alert(1)")).toBeNull();
  });

  it("diger tehlikeli/desteklenmeyen semalari reddeder", () => {
    expect(guvenliUrl("data:text/html;base64,PHNjcmlwdD4=")).toBeNull();
    expect(guvenliUrl("vbscript:msgbox(1)")).toBeNull();
    expect(guvenliUrl("file:///C:/Windows/System32")).toBeNull();
  });

  it("bos ve cozulemeyen degerlerde null doner", () => {
    expect(guvenliUrl(null)).toBeNull();
    expect(guvenliUrl(undefined)).toBeNull();
    expect(guvenliUrl("")).toBeNull();
    // Goreli adres: `new URL()` taban olmadan cozemez -> link uretilmez.
    expect(guvenliUrl("/tr/ekonomi/haber")).toBeNull();
    expect(guvenliUrl("bozuk adres")).toBeNull();
  });
});
