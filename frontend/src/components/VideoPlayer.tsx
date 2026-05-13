"use client";

import { Download, Play, Share2 } from "lucide-react";
import { getVideoDownloadUrl, getVideoStreamUrl } from "@/lib/api";

interface VideoPlayerProps {
    jobId: string;
}

export default function VideoPlayer({ jobId }: VideoPlayerProps) {
    const streamUrl = getVideoStreamUrl(jobId);
    const downloadUrl = getVideoDownloadUrl(jobId);

    const handleShare = async () => {
        if (navigator.share) {
            await navigator.share({
                title: "AutoShorts Video",
                text: "Video được tạo bởi AutoShorts AI",
                url: window.location.href,
            });
        } else {
            await navigator.clipboard.writeText(window.location.href);
            alert("Đã copy link!");
        }
    };

    return (
        <div className="flex w-full flex-col items-center gap-4">
            {/* Video container - 9:16 ratio */}
            <div className="relative w-full max-w-[360px] overflow-hidden rounded-lg border border-white/10 shadow-2xl shadow-slate-950/40">
                <div className="aspect-[9/16] bg-black">
                    <video
                        src={streamUrl}
                        controls
                        autoPlay
                        loop
                        playsInline
                        className="w-full h-full object-cover"
                        poster=""
                    >
                        Trình duyệt của bạn không hỗ trợ video.
                    </video>
                </div>

                {/* Platform badges */}
                <div className="absolute top-3 left-3 flex gap-1.5">
                    {["TikTok", "Reels", "Shorts"].map((p) => (
                        <span
                            key={p}
                            className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-sm text-white border border-white/20"
                        >
                            {p}
                        </span>
                    ))}
                </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-3 w-full max-w-[320px]">
                <a
                    href={downloadUrl}
                    download
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-3 bg-sky-500 hover:bg-sky-400 text-white font-semibold rounded-lg transition-colors"
                >
                    <Download size={18} />
                    Tải xuống
                </a>
                <button
                    onClick={handleShare}
                    className="flex items-center justify-center gap-2 px-4 py-3 bg-white/10 hover:bg-white/20 text-white font-semibold rounded-lg transition-colors border border-white/10"
                >
                    <Share2 size={18} />
                </button>
            </div>

            <p className="text-xs text-slate-500 text-center">
                1080×1920 · MP4 · Sẵn sàng đăng lên TikTok, Reels & Shorts
            </p>
        </div>
    );
}
