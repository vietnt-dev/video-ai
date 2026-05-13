"use client";

import { useState, useEffect } from "react";
import {
    Search,
    Copy,
    Check,
    ChevronDown,
    ChevronUp,
    Tag,
    Hash,
    FileText,
    Lightbulb,
    RefreshCw,
} from "lucide-react";
import clsx from "clsx";
import { getSEOMetadata, type SEOMetadata } from "@/lib/api";

interface SEOPanelProps {
    jobId: string;
    onTitleSelect?: (title: string) => void;
    onMetadataReady?: (seo: SEOMetadata) => void;
}

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg hover:bg-white/10 text-gray-500 hover:text-gray-300 transition-colors shrink-0"
            title="Copy"
        >
            {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
        </button>
    );
}

function ScoreBar({ label, score }: { label: string; score: number }) {
    const color =
        score >= 80 ? "bg-emerald-500" : score >= 60 ? "bg-yellow-500" : "bg-red-500";
    return (
        <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500 w-20 shrink-0">{label}</span>
            <div className="flex-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                <div
                    className={`h-full rounded-full transition-all duration-700 ${color}`}
                    style={{ width: `${score}%` }}
                />
            </div>
            <span className="text-xs font-mono text-gray-400 w-8 text-right">{score}</span>
        </div>
    );
}

export default function SEOPanel({ jobId, onTitleSelect, onMetadataReady }: SEOPanelProps) {
    const [seo, setSeo] = useState<SEOMetadata | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [selectedTitle, setSelectedTitle] = useState<string>("");
    const [showAllTags, setShowAllTags] = useState(false);
    const [activeTab, setActiveTab] = useState<"title" | "description" | "tags">("title");

    useEffect(() => {
        loadSEO();
    }, [jobId]);

    const loadSEO = async () => {
        setLoading(true);
        setError(null);
        // Retry vài lần vì SEO data có thể chưa sẵn sàng ngay
        for (let i = 0; i < 5; i++) {
            try {
                const data = await getSEOMetadata(jobId);
                setSeo(data);
                setSelectedTitle(data.title);
                onMetadataReady?.(data);
                setLoading(false);
                return;
            } catch {
                await new Promise((r) => setTimeout(r, 1500));
            }
        }
        setError("Không thể tải SEO data");
        setLoading(false);
    };

    const handleSelectTitle = (title: string) => {
        setSelectedTitle(title);
        onTitleSelect?.(title);
    };

    // Tính SEO score đơn giản
    const calcScores = (s: SEOMetadata) => ({
        title: Math.min(100, 60 + (s.title.length <= 70 ? 20 : 0) + (s.title.match(/\d/) ? 10 : 0) + (s.title.match(/[🔥💡😱✅⚡🎯]/) ? 10 : 0)),
        description: Math.min(100, 50 + (s.description.length >= 200 ? 20 : 0) + (s.description.includes("#Shorts") ? 15 : 0) + (s.description.includes("Follow") || s.description.includes("Comment") ? 15 : 0)),
        tags: Math.min(100, 40 + Math.min(s.tags.length * 4, 40) + (s.tags.length >= 10 ? 20 : 0)),
    });

    if (loading) {
        return (
            <div className="glass-card p-5 space-y-3">
                <div className="flex items-center gap-2 text-gray-400">
                    <Search size={16} className="animate-pulse" />
                    <span className="text-sm">Đang tối ưu SEO với GPT-4o...</span>
                </div>
                <div className="space-y-2">
                    {[80, 60, 90].map((w, i) => (
                        <div key={i} className={`h-3 bg-gray-800 rounded animate-pulse`} style={{ width: `${w}%` }} />
                    ))}
                </div>
            </div>
        );
    }

    if (error || !seo) {
        return (
            <div className="glass-card p-4 flex items-center justify-between">
                <span className="text-sm text-gray-500">Không tải được SEO data</span>
                <button onClick={loadSEO} className="text-xs text-sky-400 flex items-center gap-1 hover:underline">
                    <RefreshCw size={12} /> Thử lại
                </button>
            </div>
        );
    }

    const scores = calcScores(seo);
    const overallScore = Math.round((scores.title + scores.description + scores.tags) / 3);

    return (
        <div className="glass-card overflow-hidden">
            {/* Header */}
            <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                    <Search size={16} className="text-sky-400" />
                    <span className="font-semibold text-white text-sm">YouTube SEO</span>
                </div>
                {/* Overall score badge */}
                <div className={clsx(
                    "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold",
                    overallScore >= 80 ? "bg-emerald-500/20 text-emerald-400" :
                        overallScore >= 60 ? "bg-yellow-500/20 text-yellow-400" :
                            "bg-red-500/20 text-red-400"
                )}>
                    <span>SEO Score</span>
                    <span>{overallScore}/100</span>
                </div>
            </div>

            {/* Score bars */}
            <div className="px-5 py-3 border-b border-white/5 space-y-2">
                <ScoreBar label="Title" score={scores.title} />
                <ScoreBar label="Description" score={scores.description} />
                <ScoreBar label="Tags" score={scores.tags} />
            </div>

            {/* Tabs */}
            <div className="flex border-b border-white/5">
                {(["title", "description", "tags"] as const).map((tab) => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={clsx(
                            "flex-1 py-2.5 text-xs font-medium capitalize transition-colors",
                            activeTab === tab
                                ? "text-sky-400 border-b-2 border-sky-400"
                                : "text-gray-500 hover:text-gray-300"
                        )}
                    >
                        {tab === "title" ? "Title" : tab === "description" ? "Mô tả" : "Tags"}
                    </button>
                ))}
            </div>

            <div className="p-5 space-y-4">

                {/* ── TITLE TAB ── */}
                {activeTab === "title" && (
                    <div className="space-y-3">
                        <p className="text-xs text-gray-500">
                            Chọn title tốt nhất. GPT-4o đã tạo 3 biến thể A/B test:
                        </p>

                        {/* Main title */}
                        <div
                            onClick={() => handleSelectTitle(seo.title)}
                            className={clsx(
                                "p-3 rounded-lg border cursor-pointer transition-all",
                                selectedTitle === seo.title
                                    ? "border-sky-500 bg-sky-500/10"
                                    : "border-gray-700 hover:border-gray-600 bg-gray-900"
                            )}
                        >
                            <div className="flex items-start justify-between gap-2">
                                <div className="flex-1">
                                    <div className="flex items-center gap-1.5 mb-1">
                                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-500/20 text-sky-400 font-medium">
                                            Khuyến nghị
                                        </span>
                                        <span className="text-[10px] text-gray-600">{seo.title.length}/100 ký tự</span>
                                    </div>
                                    <p className="text-sm text-white font-medium">{seo.title}</p>
                                </div>
                                <CopyButton text={seo.title} />
                            </div>
                        </div>

                        {/* A/B test titles */}
                        {seo.ab_test_titles && seo.ab_test_titles.length > 0 && (
                            <div className="space-y-2">
                                <p className="text-[10px] text-gray-600 uppercase tracking-wider">Biến thể A/B</p>
                                {seo.ab_test_titles.map((t, i) => (
                                    <div
                                        key={i}
                                        onClick={() => handleSelectTitle(t)}
                                        className={clsx(
                                            "p-3 rounded-lg border cursor-pointer transition-all",
                                            selectedTitle === t
                                                ? "border-sky-400 bg-sky-400/10"
                                                : "border-gray-700 hover:border-gray-600 bg-gray-900"
                                        )}
                                    >
                                        <div className="flex items-start justify-between gap-2">
                                            <div className="flex-1">
                                                <span className="text-[10px] text-gray-600">Biến thể {i + 1} · {t.length}/100</span>
                                                <p className="text-sm text-gray-300 mt-0.5">{t}</p>
                                            </div>
                                            <CopyButton text={t} />
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}

                        {/* SEO explanation */}
                        {seo.seo_explanation && (
                            <div className="flex items-start gap-2 p-3 rounded-lg bg-yellow-500/5 border border-yellow-500/20">
                                <Lightbulb size={14} className="text-yellow-400 mt-0.5 shrink-0" />
                                <p className="text-xs text-gray-400">{seo.seo_explanation}</p>
                            </div>
                        )}
                    </div>
                )}

                {/* ── DESCRIPTION TAB ── */}
                {activeTab === "description" && (
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <p className="text-xs text-gray-500">{seo.description.length} ký tự</p>
                            <CopyButton text={seo.description} />
                        </div>
                        <div className="p-3 rounded-lg bg-gray-900 border border-gray-700">
                            <pre className="text-xs text-gray-300 whitespace-pre-wrap font-sans leading-relaxed">
                                {seo.description}
                            </pre>
                        </div>

                        {/* Hashtags */}
                        <div>
                            <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1">
                                <Hash size={10} /> Hashtags
                            </p>
                            <div className="flex flex-wrap gap-1.5">
                                {seo.hashtags.map((h) => (
                                    <span
                                        key={h}
                                        className="text-xs px-2 py-1 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20"
                                    >
                                        {h}
                                    </span>
                                ))}
                            </div>
                        </div>
                    </div>
                )}

                {/* ── TAGS TAB ── */}
                {activeTab === "tags" && (
                    <div className="space-y-3">
                        <div className="flex items-center justify-between">
                            <p className="text-xs text-gray-500">
                                {seo.tags.length} tags · {seo.tags.join(", ").length}/500 ký tự
                            </p>
                            <CopyButton text={seo.tags.join(", ")} />
                        </div>

                        <div className="flex flex-wrap gap-1.5">
                            {(showAllTags ? seo.tags : seo.tags.slice(0, 8)).map((tag, i) => {
                                const isBroad = tag.split(" ").length <= 2;
                                return (
                                    <span
                                        key={i}
                                        className={clsx(
                                            "text-xs px-2.5 py-1 rounded-full border",
                                            isBroad
                                                ? "bg-sky-400/10 text-sky-300 border-sky-400/20"
                                                : "bg-gray-800 text-gray-400 border-gray-700"
                                        )}
                                    >
                                        {tag}
                                    </span>
                                );
                            })}
                        </div>

                        {seo.tags.length > 8 && (
                            <button
                                onClick={() => setShowAllTags(!showAllTags)}
                                className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300"
                            >
                                {showAllTags ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                {showAllTags ? "Ẩn bớt" : `Xem thêm ${seo.tags.length - 8} tags`}
                            </button>
                        )}

                        <div className="flex items-start gap-2 p-3 rounded-lg bg-gray-900 border border-gray-700">
                            <Tag size={12} className="text-gray-500 mt-0.5 shrink-0" />
                            <p className="text-[11px] text-gray-500 leading-relaxed">
                                <span className="text-sky-300">Xanh</span> = broad tags (volume cao) ·{" "}
                                <span className="text-gray-400">Xám</span> = niche/long-tail tags (ít cạnh tranh)
                            </p>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
