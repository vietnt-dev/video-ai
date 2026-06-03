const API_BASE = "/api";

// ─── Video Generation ─────────────────────────────────────────────────────────

export interface GenerateRequest {
    topic: string;
    style?: string;
    language?: "vi" | "en";
    media_source?: string;
    auto_upload_youtube?: boolean;
    youtube_privacy?: "public" | "unlisted" | "private";
}

export interface JobResponse {
    job_id: string;
    status: string;
    message: string;
}

export interface JobStatus {
    job_id: string;
    status: "pending" | "processing" | "completed" | "failed";
    progress: number;
    message: string;
    video_url?: string;
    error?: string;
    youtube_url?: string;
    youtube_video_id?: string;
}

export async function generateVideo(data: GenerateRequest): Promise<JobResponse> {
    const res = await fetch(`${API_BASE}/video/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Lỗi khi tạo video");
    }
    return res.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
    const res = await fetch(`${API_BASE}/video/status/${jobId}`);
    if (!res.ok) throw new Error("Không thể lấy trạng thái job");
    return res.json();
}

export function getVideoStreamUrl(jobId: string): string {
    return `${API_BASE}/video/stream/${jobId}`;
}

export function getVideoDownloadUrl(jobId: string): string {
    return `${API_BASE}/video/download/${jobId}`;
}

// ─── YouTube ──────────────────────────────────────────────────────────────────

export interface YouTubeChannel {
    id: string;
    title: string;
    thumbnail?: string;
    subscriber_count: string;
    video_count: string;
}

export interface YouTubeStatus {
    connected: boolean;
    channel?: YouTubeChannel;
    authorize_url?: string;
}

export interface YouTubeUploadRequest {
    title: string;
    description?: string;
    tags?: string[];
    privacy?: "public" | "unlisted" | "private";
}

export interface YouTubeUploadResponse {
    video_id: string;
    youtube_url: string;
    title: string;
    privacy: string;
}

export async function getYouTubeStatus(): Promise<YouTubeStatus> {
    const res = await fetch(`${API_BASE}/youtube/status`);
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Không thể kiểm tra trạng thái YouTube");
    }
    return res.json();
}

export async function uploadToYouTube(
    jobId: string,
    data: YouTubeUploadRequest
): Promise<YouTubeUploadResponse> {
    const res = await fetch(`${API_BASE}/youtube/upload/${jobId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Upload YouTube thất bại");
    }
    return res.json();
}

export async function disconnectYouTube(): Promise<void> {
    await fetch(`${API_BASE}/youtube/disconnect`, { method: "DELETE" });
}

// ─── SEO ──────────────────────────────────────────────────────────────────────

export interface SEOMetadata {
    title: string;
    description: string;
    tags: string[];
    hashtags: string[];
    ab_test_titles?: string[];
    seo_explanation?: string;
}

export async function getSEOMetadata(jobId: string): Promise<SEOMetadata> {
    const res = await fetch(`${API_BASE}/video/seo/${jobId}`);
    if (!res.ok) throw new Error("SEO data chưa sẵn sàng");
    return res.json();
}
