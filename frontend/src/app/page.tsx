"use client";

import { useState, useEffect, useRef } from "react";
import { Zap, Sparkles, AlertCircle, Youtube, Video, CheckCircle2, ArrowRight, ShieldCheck, WandSparkles, Gauge } from "lucide-react";
import GeneratorForm from "@/components/GeneratorForm";
import VideoPlayer from "@/components/VideoPlayer";
import ProgressBar from "@/components/ProgressBar";
import StepIndicator from "@/components/StepIndicator";
import YouTubePanel from "@/components/YouTubePanel";
import SEOPanel from "@/components/SEOPanel";
import { generateVideo, getJobStatus, type JobStatus, type SEOMetadata } from "@/lib/api";

type AppState = "idle" | "generating" | "completed" | "failed";

const FEATURES = [
    "Script viral theo 10+ phong cách",
    "Giọng đọc Việt tự nhiên (Edge TTS)",
    "Video stock từ Pexels hoặc AI image",
    "Ken Burns effect cho ảnh AI",
    "Phụ đề tự động căn chỉnh",
    "SEO title/tags tối ưu YouTube",
    "Upload YouTube Shorts tự động",
];

export default function Dashboard() {
    const [appState, setAppState] = useState<AppState>("idle");
    const [jobId, setJobId] = useState<string | null>(null);
    const [jobStatus, setJobStatus] = useState<JobStatus | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [autoUploadYT, setAutoUploadYT] = useState(false);
    const [ytPrivacy, setYtPrivacy] = useState<"public" | "unlisted" | "private">("public");
    const [seoData, setSeoData] = useState<SEOMetadata | null>(null);
    const [selectedTitle, setSelectedTitle] = useState("");
    const [scriptMeta, setScriptMeta] = useState<{ title?: string; description?: string; tags?: string[] }>({});
    const pollRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        const params = new URLSearchParams(window.location.search);
        if (params.get("youtube_connected") === "true") window.history.replaceState({}, "", "/");
        if (params.get("youtube_error")) window.history.replaceState({}, "", "/");
    }, []);

    useEffect(() => {
        if (!jobId || appState !== "generating") return;
        const poll = async () => {
            try {
                const status = await getJobStatus(jobId);
                setJobStatus(status);
                if (status.status === "completed") { setAppState("completed"); clearInterval(pollRef.current!); }
                else if (status.status === "failed") { setAppState("failed"); setError(status.error || "Lỗi không xác định"); clearInterval(pollRef.current!); }
            } catch { }
        };
        poll();
        pollRef.current = setInterval(poll, 3000);
        return () => { if (pollRef.current) clearInterval(pollRef.current); };
    }, [jobId, appState]);

    const handleGenerate = async (topic: string, style: string, language: string, mediaSource: string, meta?: { title?: string; description?: string; tags?: string[] }) => {
        setError(null); setJobStatus(null); setJobId(null);
        setScriptMeta(meta || {}); setSeoData(null); setSelectedTitle("");
        setAppState("generating");
        try {
            const res = await generateVideo({ topic, style, language: language as "vi" | "en", media_source: mediaSource, auto_upload_youtube: autoUploadYT, youtube_privacy: ytPrivacy });
            setJobId(res.job_id);
        } catch (err: any) { setAppState("failed"); setError(err.message || "Không thể kết nối server"); }
    };

    const handleReset = () => {
        setAppState("idle"); setJobId(null); setJobStatus(null);
        setError(null); setScriptMeta({}); setSeoData(null); setSelectedTitle("");
        if (pollRef.current) clearInterval(pollRef.current);
    };

    const isCompleted = appState === "completed" && !!jobId;

    return (
        <div className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(14,165,233,0.13),transparent_32rem),linear-gradient(180deg,#020617_0%,#0f172a_52%,#111827_100%)] flex flex-col">

            {/* ── Header ── */}
            <header className="relative border-b border-white/[0.08] bg-slate-950/82 backdrop-blur-xl sticky top-0 z-20">
                <div className="mx-auto flex w-full max-w-[1560px] items-center justify-between px-4 py-3 sm:px-6">
                    {/* Logo */}
                    <div className="flex items-center gap-3">
                        <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-sky-300/30 bg-sky-400/15 glow-sm">
                            <Zap size={16} className="text-sky-200" />
                        </div>
                        <div className="flex items-baseline gap-2">
                            <span className="font-bold text-base text-white tracking-tight">AutoVideo</span>
                            <span className="rounded border border-emerald-400/25 bg-emerald-400/10 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-300">AI</span>
                        </div>
                    </div>

                    {/* Center pills */}
                    <div className="hidden lg:flex items-center gap-1 rounded-full border border-white/[0.08] bg-white/[0.04] px-3 py-1.5">
                        {["Gemini AI", "Edge TTS", "Pexels", "YouTube API"].map((t, i) => (
                            <span key={t} className="flex items-center gap-1.5 text-[11px] text-slate-400">
                                {i > 0 && <span className="w-px h-3 bg-white/10" />}
                                <span>{t}</span>
                            </span>
                        ))}
                    </div>

                    {/* Right */}
                    <div className="flex items-center gap-2">
                        <div className="flex items-center gap-1.5 rounded-full border border-white/[0.08] bg-white/[0.04] px-3 py-1.5 text-xs text-slate-300">
                            <Youtube size={12} className="text-red-500" />
                            <span>YouTube Shorts</span>
                        </div>
                    </div>
                </div>
            </header>

            {/* ── 3-column body ── */}
            <main className="relative mx-auto grid w-full max-w-[1560px] flex-1 grid-cols-1 gap-5 px-4 py-5 lg:grid-cols-[minmax(340px,1.08fr)_minmax(260px,0.72fr)_minmax(340px,1fr)] xl:grid-cols-[minmax(380px,1.05fr)_minmax(300px,0.7fr)_minmax(380px,1fr)] sm:px-6">

                {/* ════ COL 1: Form ════ */}
                <div className="space-y-4">

                    {/* Form card */}
                    <div className="glass-card p-5">
                        <div className="flex items-center justify-between mb-4">
                            <div className="flex items-center gap-2">
                                <div className="flex h-7 w-7 items-center justify-center rounded-lg border border-sky-400/20 bg-sky-400/10">
                                    <Sparkles size={13} className="text-sky-300" />
                                </div>
                                <span className="text-sm font-semibold text-white">Tạo video mới</span>
                            </div>
                            {appState !== "idle" && (
                                <button onClick={handleReset} className="flex items-center gap-1 text-[11px] text-slate-500 transition-colors hover:text-slate-200">
                                    ← Tạo mới
                                </button>
                            )}
                        </div>
                        <GeneratorForm
                            onGenerate={handleGenerate}
                            isLoading={appState === "generating"}
                            autoUploadYT={autoUploadYT}
                            onAutoUploadChange={setAutoUploadYT}
                            ytPrivacy={ytPrivacy}
                            onPrivacyChange={setYtPrivacy}
                        />
                    </div>

                    {/* Progress */}
                    {(appState === "generating" || appState === "completed") && jobStatus && (
                        <div className="glass-card p-5 space-y-4">
                            <p className="section-label">Tiến trình</p>
                            <StepIndicator progress={jobStatus.progress} status={jobStatus.status} />
                            <ProgressBar progress={jobStatus.progress} message={jobStatus.message} status={jobStatus.status} />
                        </div>
                    )}

                    {/* Error */}
                    {appState === "failed" && error && (
                        <div className="rounded-lg p-4 border border-red-500/20 bg-red-500/5">
                            <div className="flex items-start gap-3">
                                <AlertCircle size={16} className="text-red-400 mt-0.5 shrink-0" />
                                <div className="flex-1 min-w-0">
                                    <p className="text-red-400 font-semibold text-sm">Đã xảy ra lỗi</p>
                                    <p className="text-slate-400 text-xs mt-1 break-words leading-relaxed">{error}</p>
                                    <button onClick={handleReset} className="mt-2 text-xs text-sky-300 hover:text-sky-200 transition-colors">← Thử lại</button>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* How it works — idle only */}
                    {appState === "idle" && (
                        <div className="glass-card p-5">
                            <p className="section-label mb-4">Quy trình</p>
                            <div className="space-y-3">
                                {[
                                    { icon: WandSparkles, title: "AI viết kịch bản", desc: "Gemini tạo script theo phong cách đã chọn" },
                                    { icon: Gauge, title: "Sản xuất nội dung", desc: "TTS, stock footage và phụ đề được xử lý tự động" },
                                    { icon: Video, title: "Render 1080×1920", desc: "Xuất MP4 tối ưu cho Shorts, Reels và TikTok" },
                                    { icon: ShieldCheck, title: "Sẵn sàng đăng", desc: "Tạo metadata SEO và upload qua YouTube Data API" },
                                ].map((step, i, arr) => (
                                    <div key={i} className="flex items-start gap-3">
                                        <div className="flex flex-col items-center shrink-0">
                                            <div className="w-7 h-7 rounded-lg bg-white/[0.06] border border-white/[0.08] flex items-center justify-center">
                                                <step.icon size={13} className="text-slate-300" />
                                            </div>
                                            {i < arr.length - 1 && <div className="w-px h-3 bg-white/[0.06] mt-0.5" />}
                                        </div>
                                        <div className="pb-0.5">
                                            <p className="text-xs font-semibold text-slate-200">{step.title}</p>
                                            <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{step.desc}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* ════ COL 2: Video preview ════ */}
                <div className="flex flex-col items-center gap-3 lg:sticky lg:top-[76px] lg:self-start">
                    {/* Status badge */}
                    <div className="w-full flex items-center justify-between">
                        <span className="section-label">Preview</span>
                        {isCompleted && (
                            <span className="flex items-center gap-1 text-[11px] text-emerald-300 font-medium">
                                <CheckCircle2 size={11} /> Sẵn sàng
                            </span>
                        )}
                        {appState === "generating" && (
                            <span className="flex items-center gap-1.5 text-[11px] text-sky-300 font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-sky-300 animate-pulse" /> Đang render
                            </span>
                        )}
                    </div>

                    {/* Video / Placeholder */}
                    {isCompleted ? (
                        <VideoPlayer jobId={jobId} />
                    ) : (
                        <div className="relative flex aspect-[9/16] w-full max-w-[360px] flex-col items-center justify-center gap-3 overflow-hidden rounded-lg border border-white/[0.08] bg-slate-900/72 p-4 text-center shadow-2xl shadow-slate-950/40">
                            {/* Subtle grid pattern */}
                            <div className="absolute inset-0 opacity-[0.03]"
                                style={{ backgroundImage: "linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
                            <div className="relative z-10 flex flex-col items-center gap-3">
                                <div className="w-12 h-12 rounded-lg bg-white/[0.06] border border-white/[0.1] flex items-center justify-center">
                                    <Video size={20} className="text-slate-500" />
                                </div>
                                <div>
                                    <p className="text-gray-500 text-xs font-medium">
                                        {appState === "generating" ? "Đang tạo video..." : "Video sẽ hiển thị tại đây"}
                                    </p>
                                    <p className="text-slate-600 text-[10px] mt-1">1080 × 1920 · MP4</p>
                                </div>
                                {appState === "generating" && (
                                    <div className="flex gap-1">
                                        {[0, 1, 2].map((i) => (
                                            <div key={i} className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* ════ COL 3: Info / Results ════ */}
                <div className="space-y-4">

                    {/* IDLE: stats + features */}
                    {appState === "idle" && (
                        <>
                            {/* Stats */}
                            <div className="glass-card p-5">
                                <p className="section-label mb-4">Thông số</p>
                                <div className="space-y-2.5">
                                    {[
                                        { label: "Thời gian tạo", value: "~1–2 phút" },
                                        { label: "Độ phân giải", value: "1080 × 1920" },
                                        { label: "Định dạng", value: "MP4 H.264" },
                                        { label: "Nền tảng", value: "TikTok · Reels · Shorts" },
                                        { label: "Phụ đề", value: "Tự động (ASS)" },
                                    ].map((s) => (
                                        <div key={s.label} className="flex items-center justify-between py-1.5 border-b border-white/[0.04] last:border-0">
                                            <span className="text-xs text-slate-500">{s.label}</span>
                                            <span className="text-xs font-medium text-slate-200">{s.value}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Features */}
                            <div className="glass-card p-5">
                                <p className="section-label mb-4">Tính năng</p>
                                <div className="space-y-2">
                                    {FEATURES.map((f) => (
                                        <div key={f} className="flex items-start gap-2.5">
                                            <div className="w-4 h-4 rounded-full bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center shrink-0 mt-0.5">
                                                <span className="text-emerald-400 text-[9px] font-bold">✓</span>
                                            </div>
                                            <span className="text-xs text-slate-300 leading-relaxed">{f}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* CTA hint */}
                            <div className="rounded-lg p-4 bg-gradient-to-br from-sky-500/10 via-white/[0.03] to-emerald-500/10 border border-sky-400/20">
                                <p className="text-sm font-semibold text-white mb-1">Bắt đầu ngay</p>
                                <p className="text-xs text-slate-300 leading-relaxed mb-3">Chọn phong cách, nhập chủ đề và nhấn <span className="text-sky-300 font-medium">Tạo Video AI</span>. Video sẽ sẵn sàng trong khoảng 2 phút.</p>
                                <div className="flex items-center gap-1 text-xs text-emerald-300 font-medium">
                                    <ArrowRight size={12} /> Hoàn toàn miễn phí
                                </div>
                            </div>
                        </>
                    )}

                    {/* GENERATING: tips while waiting */}
                    {appState === "generating" && (
                        <div className="glass-card p-5 space-y-3">
                            <p className="section-label">Trong khi chờ...</p>
                            <div className="space-y-2">
                                {[
                                    "AI đang phân tích chủ đề và viết kịch bản viral",
                                    "Edge TTS tổng hợp giọng đọc tự nhiên",
                                    "Tìm kiếm video stock phù hợp từ Pexels",
                                    "Render và ghép video 1080×1920",
                                ].map((tip, i) => (
                                    <div key={i} className="flex items-start gap-2.5">
                                        <div className="w-4 h-4 rounded-full bg-sky-400/15 border border-sky-400/30 flex items-center justify-center shrink-0 mt-0.5">
                                            <span className="text-sky-300 text-[9px] font-bold">{i + 1}</span>
                                        </div>
                                        <span className="text-xs text-slate-400 leading-relaxed">{tip}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* FAILED */}
                    {appState === "failed" && (
                        <div className="glass-card p-5 space-y-3">
                            <p className="section-label">Gợi ý</p>
                            <div className="space-y-2">
                                {["Kiểm tra kết nối internet", "Thử lại với chủ đề khác", "Kiểm tra API key trong .env"].map((tip) => (
                                    <div key={tip} className="flex items-center gap-2 text-xs text-slate-400">
                                        <span className="text-slate-600">→</span> {tip}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* COMPLETED: SEO + YouTube */}
                    {isCompleted && (
                        <>
                            <SEOPanel
                                jobId={jobId!}
                                onTitleSelect={(t) => setSelectedTitle(t)}
                                onMetadataReady={(s) => setSeoData(s)}
                            />
                            <YouTubePanel
                                jobId={jobId}
                                suggestedTitle={selectedTitle || seoData?.title || scriptMeta.title}
                                suggestedDescription={seoData?.description || scriptMeta.description}
                                suggestedTags={seoData?.tags || scriptMeta.tags}
                                youtubeUrl={jobStatus?.youtube_url}
                            />
                        </>
                    )}
                </div>
            </main>

            <footer className="relative border-t border-white/[0.06] py-3 text-center text-slate-600 text-[11px]">
                AutoVideo AI © 2026 · Next.js · FastAPI · YouTube Data API v3
            </footer>
        </div>
    );
}
