const fallbackApiUrl = "http://localhost:8000/api/v1";
const fallbackWsUrl = "ws://localhost:8000/ws";

const resolvedApiUrl = import.meta.env.VITE_API_URL ?? fallbackApiUrl;
const resolvedWsUrl = import.meta.env.VITE_WS_URL ?? fallbackWsUrl;

export const env = {
  apiUrl: resolvedApiUrl,
  websocketUrl: resolvedWsUrl,
  environment: import.meta.env.MODE ?? "development",
};

export type AppEnvironment = typeof env;

