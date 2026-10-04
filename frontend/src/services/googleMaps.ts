// Only the narrow Maps JavaScript surface used by our map. Place data uses our REST API.
export interface LatLng {lat: number; lng: number}
export interface GoogleMap {panTo(point: LatLng): void; fitBounds(bounds: Bounds, padding: number): void; setZoom(zoom: number): void}
interface Bounds {extend(point: LatLng): void}
interface Listener {remove(): void}
export interface Marker {map: GoogleMap | null; addListener(event: string, callback: () => void): Listener}
export interface MapsSdk {
  Map: new (element: HTMLElement, options: {center: LatLng; zoom: number; mapId: string; mapTypeControl: boolean; streetViewControl: boolean; fullscreenControl: boolean; gestureHandling: string}) => GoogleMap;
  LatLngBounds: new () => Bounds;
  marker: {AdvancedMarkerElement: new (options: {map: GoogleMap; position: LatLng; title: string; content?: HTMLElement}) => Marker};
}
declare global { interface Window { google?: {maps: MapsSdk}; menuLensMapReady?: () => void; gm_authFailure?: () => void } }
let sdkPromise: Promise<MapsSdk> | null = null;
export function loadMaps(key: string): Promise<MapsSdk> {
  if (window.google?.maps?.marker) return Promise.resolve(window.google.maps);
  if (sdkPromise) return sdkPromise;
  sdkPromise = new Promise<MapsSdk>((resolve, reject) => {
    const script = document.createElement("script");
    const fail = () => { clearTimeout(timer); script.remove(); sdkPromise = null; reject(new Error("The map couldn't load. You can still browse the list.")); };
    const timer = setTimeout(fail, 20000);
    window.gm_authFailure = () => { fail(); window.dispatchEvent(new Event("menulens-map-error")); };
    window.menuLensMapReady = () => {
      clearTimeout(timer);
      if (window.google?.maps?.marker) resolve(window.google.maps); else fail();
    };
    const params = new URLSearchParams({key, v:"weekly", loading:"async", libraries:"marker", callback:"menuLensMapReady"});
    script.src = `https://maps.googleapis.com/maps/api/js?${params}`;
    script.async = true; script.onerror = fail; document.head.appendChild(script);
  });
  return sdkPromise;
}
