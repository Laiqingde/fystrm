import axios from "axios";

export const api = axios.create({ baseURL: "/" });

export interface Library {
  id: number;
  name: string;
  source_path: string;
  target_strm_path: string;
  cd2_mount_prefix: string;
  media_type: string;
  enabled: boolean;
  last_scan_at: string | null;
  // v0.2
  strm_mode: string;
  webdav_base_url: string | null;
  webdav_path_prefix: string | null;
}

export interface ScanTask {
  id: number;
  library_id: number;
  status: string;
  total_files: number;
  processed_files: number;
  success_count: number;
  failed_count: number;
  error: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface MediaItem {
  id: number;
  library_id: number;
  title: string;
  original_title: string | null;
  year: number | null;
  tmdb_id: string | null;
  media_type: string;
  season: number | null;
  episode: number | null;
  episode_title: string | null;
  parent_tmdb_id: string | null;
  source_file_path: string;
  source_file_size: number;
  strm_path: string | null;
  nfo_path: string | null;
  poster_path: string | null;
  fanart_path: string | null;
  subtitle_paths: string[] | null;
  scrape_status: string;
  scrape_error: string | null;
  created_at: string;
}

export interface Settings {
  tmdb_configured: boolean;
  tmdb_language: string;
  emby_configured: boolean;
  emby_url: string | null;
  log_level: string;
  debug: boolean;
}

export const listLibraries = () => api.get<Library[]>("/api/libraries/").then(r => r.data);
export const createLibrary = (data: Partial<Library>) => api.post<Library>("/api/libraries/", data).then(r => r.data);
export const updateLibrary = (id: number, data: Partial<Library>) => api.put<Library>(`/api/libraries/${id}`, data).then(r => r.data);
export const deleteLibrary = (id: number) => api.delete(`/api/libraries/${id}`);
export const startScan = (library_id: number) => api.post<ScanTask>("/api/scan", { library_id }).then(r => r.data);
export const listTasks = (limit = 50) => api.get<ScanTask[]>(`/api/tasks?limit=${limit}`).then(r => r.data);
export const getTask = (id: number) => api.get<ScanTask>(`/api/tasks/${id}`).then(r => r.data);
export const listMedia = (library_id?: number, status?: string) => {
  const params: Record<string, string|number> = {};
  if (library_id !== undefined) params.library_id = library_id;
  if (status) params.status = status;
  return api.get<MediaItem[]>("/api/media/", { params }).then(r => r.data);
};
export const getSettings = () => api.get<Settings>("/api/settings/").then(r => r.data);

export interface DashboardStats {
  media_count: number;
  library_count: number;
  task_count: number;
  total_size: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  trend_7d: { date: string; success: number; failed: number; tasks: number }[];
  recent_tasks: { id: number; library_id: number; status: string; total_files: number; processed_files: number; success_count: number; failed_count: number; started_at: string | null; finished_at: string | null }[];
  recent_media: { id: number; title: string; year: number | null; media_type: string; season: number | null; episode: number | null; episode_title: string | null; tmdb_id: string | null; scrape_status: string; poster_path: string | null }[];
}

export const getDashboardStats = () => api.get<DashboardStats>("/api/dashboard/stats").then(r => r.data);
