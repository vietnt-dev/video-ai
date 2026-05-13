"use client";

import { useState, useEffect } from "react";
import {
    Youtube,
    CheckCircle2,
    ExternalLink,
    Upload,
    LogOut,
    Loader2,
    AlertCircle,
    Users,
    Video,
    Lock,
    Globe,
    Eye,
} from "lucide-react";
import clsx from "clsx";
import {
    getYouTubeStatus,
    uploadToYouTube,
    disconnectYouTube,
    type YouTubeStatus,
    type YouTubeUploadRequest,
} from "@/lib/api";

interface YouTubePanelProps {
    jobId: string | null;          // job đã completed
    suggestedTitle?: string;       // từ SEO service
    suggestedDescription?: string;
    suggestedTags?: string[];
    youtubeUrl?: string;           // nếu đã upload (auto-upload)
}

const PRIVACY_OPTIONS = [
    { value: "public", label: "Công khai", icon: Globe, desc: "Mọi người đều xem được" },
    { value: "unlisted", label: "Không công khai", icon: Eye, desc: "Chỉ người có link" },
    { value: "private", label: "Riêng tư", icon: Lock, desc: "Chỉ mình bạn xem" },
];

export default function YouTubePanel({
    jobId,
    suggestedTitle = "",
    suggestedDescription = "",
    suggestedTags = [],
    youtubeUrl,
}: YouTubePanelProps) {
    const [ytStatus, setYtStatus] = useState<YouTubeStatus | null>(null);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [uploadResult, setUploadResult] = useState<{ url: string; title: string } | null>(null);
    const [error, setError] = useState<string | null>(null);

    // Form state
    const [title, setTitle] = useState(suggestedTitle);
    const [description, setDescription] = useState(suggestedDescription);
    const [privacy, setPrivacy] = useState<"public" | "unlisted" | "private">("public");

    // Nếu đã auto-upload thành công
    useEffect(() => {
        if (youtubeUrl) {
            setUploadResult({ url: youtubeUrl, title: suggestedTitle });
        }
    }, [youtubeUrl]);

    // Update form khi có suggested values mới
    useEffect(() => {
        if (suggestedTitle) setTitle(suggestedTitle);
        if (suggestedDescription) setDescription(suggestedDescription);
    }, [suggestedTitle, suggestedDescription]);

    // Load YouTube status
    useEffect(() => {
        loadStatus();
    }, []);

    const loadStatus = async () => {
        setLoading(true);
        setError(null);
        try {
            const status = await getYouTubeStatus();
            setYtStatus(status);
        } catch (e: any) {
            setError(e.message);
        } finally {
            setLoading(false);
        }
    };

    const handleConnect = () => {
        window.location.href = "/api/youtube/oauth/authorize";
    };

    const handleDisconnect = async () => {
        await disconnectYouTube();
        setYtStatus({ connected: false });
        setUploadResult(null);
    };

    const handleUpload = async () => {
        if (!jobId || !title.trim()) return;
        setUploading(true);
        setError(null);

        try {
            const payload: YouTubeUploadRequest = {
                title: title.trim(),
                description: description.trim(),
                tags: suggestedTags,
                privacy,
            };
            const result = await uploadToYouTube(jobId, payload);
            setUploadResult({ url: result.youtube_url, title: result.title });
        } catch (e: any) {
            setError(e.message);
        } finally {
            setUploading(false);
        }
    };

    // ── Render ────────────────────────────────────────────────────────

    if (loading) {
        return (
            <div className="glass-card p-5 flex items-center gap-3 text-gray-400">
                <Loader2 size={18} className="animate-spin" />
                <span className="text-sm">Đang kiểm tra kết nối YouTube...</span>
            </div>
        );
    }

    // Đã upload thành công
    if (uploadResult) {
        return (
            <div className="glass-card p-5 space-y-3 border-red-500/20 bg-red-500/5">
                <div className="flex items-center gap-2 text-red-400 font-semibold">
                    <Youtube size={20} />
                    Đã đăng lên YouTube Shorts!
                </div>
                <p className="text-sm text-gray-300 truncate">{uploadResult.title}</p>
                <a
                    href={uploadResult.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 px-4 py-2.5 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold rounded-lg transition-colors w-fit"
                >
                    <ExternalLink size={15} />
                    Xem trên YouTube
                </a>
            </div>
        );
    }

    // Lỗi cấu hình (chưa set CLIENT_ID)
    if (error && error.includes("cấu hình")) {
        return (
            <div className="glass-card p-5 border-yellow-500/20 bg-yellow-500/5">
                <div className="flex items-start gap-3">
                    <AlertCircle size={18} className="text-yellow-400 mt-0.5 shrink-0" />
                    <div>
                        <p className="text-yellow-400 font-medium text-sm">YouTube chưa được cấu hình</p>
                        <p className="text-gray-500 text-xs mt-1">
                            Thêm YOUTUBE_CLIENT_ID và YOUTUBE_CLIENT_SECRET vào file .env
                        </p>
                        <a
                            href="/YOUTUBE_SETUP.md"
                            className="text-xs text-sky-400 hover:underline mt-1 block"
                        >
                            Xem hướng dẫn setup →
                        </a>
                    </div>
                </div>
            </div>
        );
    }

    // Chưa kết nối
    if (!ytStatus?.connected) {
        return (
            <div className="glass-card p-5 space-y-4">
                <div className="flex items-center gap-2">
                    <Youtube size={20} className="text-red-500" />
                    <span className="font-semibold text-white">Đăng lên YouTube Shorts</span>
                </div>
                <p className="text-sm text-gray-400">
                    Kết nối tài khoản YouTube để tự động đăng video sau khi render xong.
                </p>
                <button
                    onClick={handleConnect}
                    className="flex items-center gap-2 px-4 py-2.5 bg-red-600 hover:bg-red-500 text-white text-sm font-semibold rounded-lg transition-colors"
                >
                    <Youtube size={16} />
                    Kết nối YouTube
                </button>
            </div>
        );
    }

    // Đã kết nối — hiện form upload
    const channel = ytStatus.channel;

    return (
        <div className="glass-card p-5 space-y-4">
            {/* Header: channel info */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                    {channel?.thumbnail ? (
                        <img
                            src={channel.thumbnail}
                            alt={channel.title}
                            className="w-8 h-8 rounded-full"
                        />
                    ) : (
                        <div className="w-8 h-8 rounded-full bg-red-600 flex items-center justify-center">
                            <Youtube size={14} className="text-white" />
                        </div>
                    )}
                    <div>
                        <p className="text-sm font-semibold text-white leading-tight">
                            {channel?.title || "YouTube Channel"}
                        </p>
                        <div className="flex items-center gap-2 text-xs text-gray-500">
                            <span className="flex items-center gap-1">
                                <Users size={10} />
                                {Number(channel?.subscriber_count || 0).toLocaleString()}
                            </span>
                            <span className="flex items-center gap-1">
                                <Video size={10} />
                                {channel?.video_count} videos
                            </span>
                        </div>
                    </div>
                </div>
                <div className="flex items-center gap-1.5">
                    <CheckCircle2 size={14} className="text-emerald-400" />
                    <button
                        onClick={handleDisconnect}
                        className="text-xs text-gray-500 hover:text-gray-300 flex items-center gap-1"
                    >
                        <LogOut size={12} />
                        Ngắt
                    </button>
                </div>
            </div>

            {/* Upload form — chỉ hiện khi có video */}
            {jobId ? (
                <div className="space-y-3 pt-1 border-t border-white/5">
                    {/* Title */}
                    <div>
                        <label className="text-xs font-medium text-gray-400 mb-1 block">
                            Tiêu đề video
                        </label>
                        <input
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="Tiêu đề YouTube Shorts..."
                            maxLength={100}
                            className="w-full px-3 py-2 rounded-lg bg-gray-900 border border-gray-700 text-white text-sm placeholder-gray-600 focus:outline-none focus:ring-1 focus:ring-red-500"
                        />
                        <p className="text-xs text-gray-600 mt-0.5 text-right">{title.length}/100</p>
                    </div>

                    {/* Privacy */}
                    <div>
                        <label className="text-xs font-medium text-gray-400 mb-1.5 block">
                            Quyền riêng tư
                        </label>
                        <div className="grid grid-cols-3 gap-2">
                            {PRIVACY_OPTIONS.map((opt) => {
                                const Icon = opt.icon;
                                return (
                                    <button
                                        key={opt.value}
                                        onClick={() => setPrivacy(opt.value as any)}
                                        className={clsx(
                                            "flex flex-col items-center gap-1 p-2 rounded-lg border text-xs transition-all",
                                            privacy === opt.value
                                                ? "border-red-500 bg-red-500/10 text-red-400"
                                                : "border-gray-700 bg-gray-900 text-gray-500 hover:border-gray-600"
                                        )}
                                    >
                                        <Icon size={14} />
                                        <span className="font-medium">{opt.label}</span>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Error */}
                    {error && (
                        <div className="flex items-start gap-2 text-red-400 text-xs bg-red-500/10 rounded-lg p-2.5">
                            <AlertCircle size={14} className="mt-0.5 shrink-0" />
                            {error}
                        </div>
                    )}

                    {/* Upload button */}
                    <button
                        onClick={handleUpload}
                        disabled={uploading || !title.trim()}
                        className={clsx(
                            "w-full flex items-center justify-center gap-2 px-4 py-3 rounded-lg font-semibold text-sm transition-all",
                            "bg-red-600 hover:bg-red-500 text-white",
                            "disabled:opacity-50 disabled:cursor-not-allowed"
                        )}
                    >
                        {uploading ? (
                            <>
                                <Loader2 size={16} className="animate-spin" />
                                Đang upload lên YouTube...
                            </>
                        ) : (
                            <>
                                <Upload size={16} />
                                Đăng lên YouTube Shorts
                            </>
                        )}
                    </button>
                </div>
            ) : (
                <p className="text-xs text-gray-500 text-center py-2">
                    Tạo video xong để đăng lên YouTube
                </p>
            )}
        </div>
    );
}
