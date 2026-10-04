import type { Menu, Explanation, ExplanationLanguage } from "@/types/menu";

export async function getUploadLimit(): Promise<number> {
  const response = await fetch("/api/menus/upload-config");
  if (!response.ok) throw new Error("Uploads are unavailable right now. Please try again.");
  const config = await response.json();
  if (!Number.isSafeInteger(config.max_upload_bytes) || config.max_upload_bytes <= 0) throw new Error("Uploads are unavailable right now. Please try again.");
  return config.max_upload_bytes;
}

export function uploadMenu(file: File, onProgress: (progress: number) => void): Promise<Menu> {
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("POST", "/api/menus");
    request.timeout = 120_000;
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round(event.loaded / event.total * 100));
    };
    request.onload = () => {
      try {
        const data = JSON.parse(request.responseText);
        if (request.status >= 200 && request.status < 300) resolve(data as Menu);
        else reject(new Error(typeof data.detail === "string" ? data.detail : "We couldn't upload this menu. Please check the file and try again."));
      } catch {
        reject(new Error("The upload service is unavailable. Please try again."));
      }
    };
    request.onerror = () => reject(new Error("Connection lost. Check your connection and try again."));
    request.ontimeout = () => reject(new Error("The upload timed out. Please try again."));
    const form = new FormData();
    form.append("file", file);
    request.send(form);
  });
}


export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

async function menuRequest(path: string, method = "GET", signal?: AbortSignal): Promise<Menu> {
  const response = await fetch(path, { method, signal, cache: "no-store" });
  let data;
  try { data = await response.json(); }
  catch { throw new Error("Menu understanding is unavailable right now. Please try again."); }
  if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "We couldn't load your menu. Please try again.", response.status);
  return data as Menu;
}

export function getMenu(id: string, signal?: AbortSignal): Promise<Menu> {
  return menuRequest(`/api/menus/${encodeURIComponent(id)}`, "GET", signal);
}

export function processMenu(id: string): Promise<Menu> {
  return menuRequest(`/api/menus/${encodeURIComponent(id)}/process`, "POST");
}


async function explanationRequest(id: string, language: ExplanationLanguage, method: "GET" | "POST", signal?: AbortSignal): Promise<Explanation> {
  const response = await fetch(`/api/menu-items/${encodeURIComponent(id)}/explanation${method === "GET" ? `?language=${language}` : ""}`, {
    method, signal, cache: "no-store",
    ...(method === "POST" ? { headers: { "Content-Type": "application/json" }, body: JSON.stringify({ language }) } : {}),
  });
  let data;
  try { data = await response.json(); }
  catch { throw new Error("Explanations are unavailable right now. Please try again."); }
  if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "We couldn't create the explanation. Please try again.", response.status);
  return data as Explanation;
}
export const requestExplanation = (id: string, language: ExplanationLanguage) => explanationRequest(id, language, "POST");
export const getExplanation = (id: string, language: ExplanationLanguage, signal?: AbortSignal) => explanationRequest(id, language, "GET", signal);


export async function searchDishes(request: import("@/types/search").SearchRequest, signal?: AbortSignal): Promise<import("@/types/search").SearchResponse> {
  const response = await fetch("/api/search", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(request), signal, cache:"no-store"});
  let data;
  try { data = await response.json(); }
  catch { throw new Error("Search is unavailable right now. Please try again."); }
  if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "Check your search filters and try again.", response.status);
  return data;
}


export async function dishImage(id: string, method: "GET" | "POST", signal?: AbortSignal): Promise<import("@/types/menu").GeneratedImage> {
  const response = await fetch(`/api/menu-items/${encodeURIComponent(id)}/image`, {method, signal, cache:"no-store"});
  let data;
  try { data = await response.json(); }
  catch { throw new Error("Food illustrations are unavailable. Please try again."); }
  if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "We couldn't load the illustration.", response.status);
  return data;
}

async function placesRequest<T>(path: string, signal?: AbortSignal): Promise<T> {
  let response;
  try { response = await fetch(path, {signal, cache:"no-store"}); }
  catch (error) { if (signal?.aborted) throw error; throw new Error("Check your connection and try again."); }
  let data;
  try { data = await response.json(); }
  catch { throw new Error("Nearby places are unavailable. Please try again."); }
  if (!response.ok) throw new ApiError(typeof data.detail === "string" ? data.detail : "Check your location and search distance.", response.status);
  return data as T;
}
export function nearbyPlaces(center: import("@/types/places").Coordinates, type: import("@/types/places").PlaceType, radius: number, signal?: AbortSignal) {
  const params = new URLSearchParams({latitude:String(center.latitude), longitude:String(center.longitude), place_type:type, radius:String(radius)});
  return placesRequest<import("@/types/places").NearbyResponse>(`/api/places/nearby?${params}`, signal);
}
export const getMapsConfig = (signal?: AbortSignal) => placesRequest<import("@/types/places").MapsConfig>("/api/places/config", signal);
