export type PlaceType = "restaurant" | "cafe" | "bar";
export interface Coordinates { latitude: number; longitude: number }
export interface Place extends Coordinates {
  id: string; name: string; address: string; category: PlaceType;
  rating: number | null; price_level: number | null; provider: "google";
  attributions: {name: string; url: string | null}[];
}
export interface NearbyResponse { places: Place[]; limit: number }
export interface MapsConfig { maps_api_key: string; maps_map_id: string }
