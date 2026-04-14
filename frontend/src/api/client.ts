import axios from "axios";

const API_BASE = "/api";

const client = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

export const api = {
  // Health & Status
  health: () => client.get("/health"),
  status: () => client.get("/status"),

  // Characters
  getCharacters: () => client.get("/api/characters"),
  createCharacter: (data: { name: string; status: string; traits: string[]; description: string }) =>
    client.post("/api/characters", data),
  getCharacter: (name: string) => client.get(`/api/characters/${name}`),
  updateCharacter: (name: string, data: Partial<{ name: string; status: string; traits: string[]; description: string }>) =>
    client.put(`/api/characters/${name}`, data),
  deleteCharacter: (name: string) => client.delete(`/api/characters/${name}`),

  // State
  getStateSnapshot: () => client.get("/api/state/snapshot"),
};

export default api;
