const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const TOKEN_KEY = "access_token";

type RequestOptions = RequestInit & {
  auth?: boolean;
  /** Istegin toplam ust siniri (ms). `0` = sinirsiz. Verilmezse GET icin
   *  `DEFAULT_GET_TIMEOUT_MS`, digerleri icin sinirsiz. */
  timeoutMs?: number;
};

const GET_RETRY_DELAYS_MS = [300, 900];

// Okuma istekleri icin varsayilan ust sinir. Eskiden HICBIR istekte timeout
// yoktu: backend takilinca (Supabase havuzu dolu, Pexels 6 sn'lik dis cagri
// zinciri...) `useAsyncData.loading` hic bitmiyor ve gecis perdesi asili
// kaliyordu. 20 sn, en agir mesru istegin (soguk dashboard ozeti) bile
// ustunde; yalnizca gercekten takilmis istekleri keser. Yazma istekleri
// (POST/PUT/DELETE) BILINCLI OLARAK kapsam disi: yarim kalmis bir emir ya
// da onay istegini istemci tarafinda kesmek, sonucu belirsiz birakir.
const DEFAULT_GET_TIMEOUT_MS = 20_000;

export function getAccessToken(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearAccessToken(): void {
  window.localStorage.removeItem(TOKEN_KEY);
}

export function getApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`;
}

async function fetchWithNetworkRetry(url: string, options: RequestInit): Promise<Response> {
  const method = (options.method ?? "GET").toUpperCase();
  const retryDelays = method === "GET" ? GET_RETRY_DELAYS_MS : [];

  for (let attempt = 0; ; attempt += 1) {
    try {
      return await fetch(url, options);
    } catch (error) {
      if (options.signal?.aborted || attempt >= retryDelays.length) {
        throw error;
      }

      await new Promise<void>((resolve) => {
        window.setTimeout(resolve, retryDelays[attempt]);
      });
    }
  }
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = getAccessToken();
  const headers = new Headers(options.headers);

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (options.auth !== false && token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const method = (options.method ?? "GET").toUpperCase();
  const timeoutMs = options.timeoutMs ?? (method === "GET" ? DEFAULT_GET_TIMEOUT_MS : 0);
  // Cagiran kendi sinyalini verdiyse ona dokunulmaz; timeout yalnizca sinyalsiz
  // isteklerde bizim tarafimizdan kurulur.
  const controller = timeoutMs > 0 && !options.signal ? new AbortController() : null;
  const timeoutTimer =
    controller !== null ? window.setTimeout(() => controller.abort(), timeoutMs) : null;
  const { timeoutMs: _ignored, ...fetchOptions } = options;

  let response: Response;
  try {
    response = await fetchWithNetworkRetry(getApiUrl(path), {
      ...fetchOptions,
      headers,
      signal: controller?.signal ?? options.signal,
    });
  } catch (error) {
    if (controller?.signal.aborted) {
      throw new Error(`Sunucu ${Math.round(timeoutMs / 1000)} saniye icinde yanit vermedi.`);
    }
    throw error;
  } finally {
    if (timeoutTimer !== null) {
      window.clearTimeout(timeoutTimer);
    }
  }

  if (!response.ok) {
    let message = "API istegi basarisiz oldu.";
    try {
      const body = await response.json();
      message = body?.error?.message ?? body?.detail ?? message;
    } catch {
      // Keep the default message if the body is not JSON.
    }
    throw new Error(message);
  }

  // 204 No Content (ör. POST /api/contest/agreement, /reset) hicbir govde
  // getirmez - `response.json()` bunda "Unexpected end of JSON input" ile
  // patlardi. Bos govdeyi `undefined` (T=void icin gecerli) olarak donuyoruz.
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
