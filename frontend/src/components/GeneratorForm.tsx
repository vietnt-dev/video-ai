"use client";

import { useState, useEffect } from "react";
import { Sparkles, Loader2, ChevronDown, Youtube } from "lucide-react";
import clsx from "clsx";

interface GeneratorFormProps {
    onGenerate: (topic: string, style: string, language: string) => void;
    isLoading: boolean;
    autoUploadYT: boolean;
    onAutoUploadChange: (v: boolean) => void;
    ytPrivacy: "public" | "unlisted" | "private";
    onPrivacyChange: (v: "public" | "unlisted" | "private") => void;
}

interface StyleOption {
    value: string;
    label: string;
    description: string;
    color: string;
    example_topics: string[];
}

const DEFAULT_STYLES: StyleOption[] = [
    { value: "co_nhan", label: "Cổ Nhân Dạy", description: "Triết lý sống, lời dạy cổ nhân", color: "amber", example_topics: ["Cổ nhân dạy về tiền bạc và hạnh phúc", "Lời dạy của người xưa về chọn bạn mà chơi"] },
    { value: "tu_vi", label: "Tử Vi & Tướng Số", description: "Tử vi, tướng số, phong thủy", color: "purple", example_topics: ["Người sinh tháng 3 có vận mệnh đặc biệt", "3 đường chỉ tay của người phú quý"] },
    { value: "su_that", label: "Sự Thật Bất Ngờ", description: "Kiến thức gây sốc, ít ai biết", color: "red", example_topics: ["Sự thật về não người mà trường học không dạy", "Tại sao người Nhật sống thọ nhất thế giới"] },
    { value: "tam_ly", label: "Tâm Lý & Phát Triển", description: "Tâm lý học, kỹ năng sống", color: "blue", example_topics: ["Tại sao bạn trì hoãn và cách dừng lại", "Hiệu ứng tâm lý khiến bạn tiêu tiền không kiểm soát"] },
    { value: "lam_giau", label: "Tiền Bạc & Làm Giàu", description: "Tài chính cá nhân, đầu tư", color: "green", example_topics: ["Quy tắc 50-30-20 quản lý tiền lương", "Cách đầu tư 1 triệu/tháng để có 1 tỷ"] },
    { value: "suc_khoe", label: "Sức Khỏe & Thuốc Nam", description: "Sức khỏe, bài thuốc dân gian Việt", color: "emerald", example_topics: ["Gừng nghệ mật ong - bài thuốc vàng", "5 loại rau Việt Nam tốt hơn thuốc bổ"] },
    { value: "tinh_cam", label: "Tình Cảm & Gia Đình", description: "Tình yêu, hôn nhân, gia đình", color: "rose", example_topics: ["Dấu hiệu người đó yêu bạn thật lòng", "Bí quyết hôn nhân bền vững của các cụ"] },
    { value: "engaging", label: "Hấp Dẫn & Viral", description: "Nội dung viral, mọi đối tượng", color: "orange", example_topics: ["5 sự thật về não người", "Cách kiếm tiền online năm 2025"] },
    { value: "educational", label: "Giáo Dục & Kiến Thức", description: "Kiến thức bổ ích, dễ hiểu", color: "sky", example_topics: ["Lạm phát là gì và ảnh hưởng đến bạn", "Cách internet hoạt động trong 60 giây"] },
    { value: "funny", label: "Hài Hước & Vui Nhộn", description: "Nội dung hài, relatable", color: "yellow", example_topics: ["Những kiểu người Việt hay gặp ở quán cà phê", "Khi mẹ hỏi con ăn chưa lúc 10 giờ đêm"] },
];

// Màu active cho từng style
const ACTIVE_COLORS: Record<string, string> = {
    amber: "border-amber-400/50 bg-amber-400/10 ring-1 ring-amber-400/25",
    purple: "border-violet-400/50 bg-violet-400/10 ring-1 ring-violet-400/25",
    red: "border-red-400/50 bg-red-400/10 ring-1 ring-red-400/25",
    blue: "border-sky-400/50 bg-sky-400/10 ring-1 ring-sky-400/25",
    green: "border-emerald-400/50 bg-emerald-400/10 ring-1 ring-emerald-400/25",
    emerald: "border-emerald-400/50 bg-emerald-400/10 ring-1 ring-emerald-400/25",
    rose: "border-rose-400/50 bg-rose-400/10 ring-1 ring-rose-400/25",
    orange: "border-orange-400/50 bg-orange-400/10 ring-1 ring-orange-400/25",
    sky: "border-sky-400/50 bg-sky-400/10 ring-1 ring-sky-400/25",
    yellow: "border-yellow-400/50 bg-yellow-400/10 ring-1 ring-yellow-400/25",
};

const PILL_COLORS: Record<string, string> = {
    amber: "border-amber-500/40 bg-amber-500/10 text-amber-400",
    purple: "border-purple-500/40 bg-purple-500/10 text-purple-400",
    red: "border-red-500/40 bg-red-500/10 text-red-400",
    blue: "border-blue-500/40 bg-blue-500/10 text-blue-400",
    green: "border-green-500/40 bg-green-500/10 text-green-400",
    emerald: "border-emerald-500/40 bg-emerald-500/10 text-emerald-400",
    rose: "border-rose-500/40 bg-rose-500/10 text-rose-400",
    orange: "border-orange-500/40 bg-orange-500/10 text-orange-400",
    sky: "border-sky-500/40 bg-sky-500/10 text-sky-400",
    yellow: "border-yellow-500/40 bg-yellow-500/10 text-yellow-400",
};

export default function GeneratorForm({ onGenerate, isLoading, autoUploadYT, onAutoUploadChange, ytPrivacy, onPrivacyChange }: GeneratorFormProps) {
    const [topic, setTopic] = useState("");
    const [style, setStyle] = useState("co_nhan");
    const [language, setLanguage] = useState("vi");
    const [styles, setStyles] = useState<StyleOption[]>(DEFAULT_STYLES);
    const [showAllStyles, setShowAllStyles] = useState(false);

    useEffect(() => {
        fetch("/api/video/styles")
            .then((r) => r.json())
            .then((d) => { if (d.styles?.length) setStyles(d.styles); })
            .catch(() => { });
    }, []);

    const selectedStyle = styles.find((s) => s.value === style) || styles[0];
    const visibleStyles = showAllStyles ? styles : styles.slice(0, 6);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!topic.trim() || isLoading) return;
        onGenerate(topic.trim(), style, language);
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">

            {/* ── Style Picker ── */}
            <div className="space-y-2">
                <label className="text-[11px] font-bold uppercase tracking-widest text-gray-600">
                    Phong cách nội dung
                </label>
                <div className="grid grid-cols-2 gap-1.5">
                    {visibleStyles.map((opt) => {
                        const isActive = style === opt.value;
                        return (
                            <button
                                key={opt.value}
                                type="button"
                                onClick={() => {
                                    setStyle(opt.value);
                                    if (!topic && opt.example_topics?.[0]) setTopic(opt.example_topics[0]);
                                }}
                                disabled={isLoading}
                                className={clsx(
                                    "flex min-h-[70px] flex-col items-start gap-1 rounded-lg border px-3 py-2.5 text-left transition-all duration-150",
                                    isActive
                                        ? ACTIVE_COLORS[opt.color] || "border-sky-400/50 bg-sky-400/10 ring-1 ring-sky-400/25"
                                        : "border-white/[0.08] bg-white/[0.03] hover:bg-white/[0.06] hover:border-white/[0.14]",
                                    "disabled:opacity-40"
                                )}
                            >
                                <span className="text-xs font-semibold text-white leading-tight">{opt.label}</span>
                                <span className="text-[10px] text-slate-500 leading-tight">{opt.description}</span>
                            </button>
                        );
                    })}
                </div>
                <button
                    type="button"
                    onClick={() => setShowAllStyles(!showAllStyles)}
                    className="text-[11px] text-slate-500 hover:text-slate-300 flex items-center gap-1 transition-colors"
                >
                    <ChevronDown size={11} className={clsx("transition-transform", showAllStyles && "rotate-180")} />
                    {showAllStyles ? "Ẩn bớt" : `Xem thêm ${styles.length - 6} phong cách`}
                </button>
            </div>

            {/* ── Topic Input ── */}
            <div className="space-y-2">
                <label className="text-[11px] font-bold uppercase tracking-widest text-gray-600">
                    Chủ đề video
                </label>
                <textarea
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder={`Nhập chủ đề cho video ${selectedStyle?.label || ""}...`}
                    rows={3}
                    disabled={isLoading}
                    className={clsx(
                        "w-full px-3.5 py-3 rounded-lg text-sm text-white placeholder-slate-600 resize-none transition-all",
                        "bg-white/[0.04] border border-white/[0.08]",
                        "focus:outline-none focus:ring-2 focus:ring-sky-400/30 focus:border-sky-400/50",
                        "hover:border-white/[0.14]",
                        isLoading && "opacity-40 cursor-not-allowed"
                    )}
                />
                {selectedStyle?.example_topics?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                        {selectedStyle.example_topics.slice(0, 2).map((ex) => (
                            <button
                                key={ex}
                                type="button"
                                onClick={() => setTopic(ex)}
                                disabled={isLoading}
                                className={clsx(
                                    "text-[10px] px-2.5 py-1 rounded-full border transition-colors disabled:opacity-40",
                                    PILL_COLORS[selectedStyle.color] || "border-white/10 bg-white/5 text-gray-400"
                                )}
                            >
                                {ex}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* ── Language ── */}
            <div className="space-y-2">
                <label className="text-[11px] font-bold uppercase tracking-widest text-gray-600">Ngôn ngữ</label>
                <div className="flex gap-2">
                    {[{ value: "vi", label: "🇻🇳 Tiếng Việt" }, { value: "en", label: "🇺🇸 English" }].map((lang) => (
                        <button
                            key={lang.value}
                            type="button"
                            onClick={() => setLanguage(lang.value)}
                            disabled={isLoading}
                            className={clsx(
                                "flex-1 py-2 rounded-lg border text-xs font-semibold transition-all",
                                language === lang.value
                                    ? "border-sky-400/60 bg-sky-400/10 text-sky-200 ring-1 ring-sky-400/25"
                                    : "border-white/[0.08] bg-white/[0.03] text-slate-500 hover:border-white/[0.14] hover:text-slate-300",
                                "disabled:opacity-40"
                            )}
                        >
                            {lang.label}
                        </button>
                    ))}
                </div>
            </div>

            {/* ── YouTube toggle ── */}
            <div className="pt-3 border-t border-white/[0.06] space-y-2">
                <label className="flex items-center justify-between cursor-pointer">
                    <div className="flex items-center gap-2">
                        <Youtube size={13} className="text-red-500" />
                        <span className="text-xs text-slate-400">Tự động đăng YouTube sau khi xong</span>
                    </div>
                    <button
                        type="button"
                        onClick={() => onAutoUploadChange(!autoUploadYT)}
                        disabled={isLoading}
                        className={clsx(
                            "relative w-9 h-5 rounded-full transition-colors shrink-0",
                            autoUploadYT ? "bg-red-600" : "bg-white/10"
                        )}
                    >
                        <span className={clsx(
                            "absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform",
                            autoUploadYT ? "translate-x-4" : "translate-x-0.5"
                        )} />
                    </button>
                </label>
                {autoUploadYT && (
                    <select
                        value={ytPrivacy}
                        onChange={(e) => onPrivacyChange(e.target.value as any)}
                        disabled={isLoading}
                        className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-white/[0.08] text-white text-xs focus:outline-none focus:ring-1 focus:ring-red-500/50 disabled:opacity-40"
                    >
                        <option value="public">🌐 Công khai</option>
                        <option value="unlisted">👁️ Không công khai (có link)</option>
                        <option value="private">🔒 Riêng tư</option>
                    </select>
                )}
            </div>

            {/* ── Submit ── */}
            <button
                type="submit"
                disabled={!topic.trim() || isLoading}
                className={clsx(
                    "w-full flex items-center justify-center gap-2 px-6 py-3.5 rounded-lg font-bold text-sm transition-all",
                    "bg-sky-500 text-white",
                    "hover:bg-sky-400 hover:shadow-lg hover:shadow-sky-500/20",
                    "disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:shadow-none",
                    "active:scale-[0.98]"
                )}
            >
                {isLoading ? (
                    <><Loader2 size={17} className="animate-spin" /> Đang tạo video...</>
                ) : (
                    <><Sparkles size={17} /> Tạo Video AI</>
                )}
            </button>
        </form>
    );
}
