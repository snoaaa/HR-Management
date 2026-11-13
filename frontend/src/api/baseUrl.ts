/**
 * Address of the API.
 * - `npm run dev`: VITE_API_URL (frontend/.env) or the Django development server;
 * - production build: "/api/", because the backend serves the application and
 *   the API from the same address (single container on port 8000). Set
 *   VITE_PROD_API_URL at build time only if the API lives on another host.
 */
const url: string = import.meta.env.DEV
  ? import.meta.env.VITE_API_URL || "http://localhost:8000/api/"
  : import.meta.env.VITE_PROD_API_URL || import.meta.env.VITE_API_URL || "/api/";

export const API_URL = url.replace(/\/?$/, "/");
