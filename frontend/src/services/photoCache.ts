import { getMarketPhoto } from "./marketService";

/**
 * `/api/market/photo` icin paylasilan onbellek: ayni sorgu tarayicida bir
 * sekme yasadigi surece bir daha backend'e (ve dolayisiyla Pexels'e)
 * gitmez. Ayni sorgu birden fazla kart tarafindan es zamanli istenirse
 * (orn. bulten sayfasindaki tum "Portfoyden" kartlari ayni anda render
 * olur) ayni Promise paylasilir - iki kez istek atilmaz.
 */
const cache = new Map<string, Promise<string | null>>();

export function fetchPhotoUrl(query: string): Promise<string | null> {
  const normalized = query.trim().toLowerCase();
  if (!normalized) {
    return Promise.resolve(null);
  }

  const cached = cache.get(normalized);
  if (cached) {
    return cached;
  }

  const request = getMarketPhoto(normalized)
    .then((response) => response.url)
    .catch(() => null);
  cache.set(normalized, request);
  return request;
}
