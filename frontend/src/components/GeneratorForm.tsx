"use client";

import { useState, useEffect } from "react";
import { Sparkles, Loader2, ChevronDown, Youtube } from "lucide-react";
import clsx from "clsx";

interface GeneratorFormProps {
    onGenerate: (topic: string, style: string, language: string, mediaSource: string) => void;
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
    {
        value: "co_nhan",
        label: "Cổ Nhân Dạy",
        description: "Triết lý sống, lời dạy cổ nhân",
        color: "amber",
        example_topics: [
            "Cổ nhân dạy về tiền bạc và hạnh phúc",
            "Lời dạy của người xưa về chọn bạn mà chơi",
            "Bí quyết sống thọ của cổ nhân Việt",
            "Cổ nhân dạy cách đối nhân xử thế",
            "Triết lý sống của người xưa về thành công",
            "Lời cổ nhân về hôn nhân và gia đình"
        ]
    },
    {
        value: "tu_vi",
        label: "Tử Vi & Tướng Số",
        description: "Tử vi, tướng số, phong thủy",
        color: "purple",
        example_topics: [
            "Người sinh tháng 3 có vận mệnh đặc biệt",
            "3 dấu hiệu trên bàn tay cho thấy bạn sẽ giàu có",
            "Phong thủy phòng ngủ thu hút tài lộc",
            "Tử vi 12 con giáp năm 2025",
            "Dấu hiệu trên khuôn mặt tiết lộ tính cách",
            "Số điện thoại hợp mệnh mang lại may mắn"
        ]
    },
    {
        value: "su_that",
        label: "Sự Thật Bất Ngờ",
        description: "Kiến thức gây sốc, ít ai biết",
        color: "red",
        example_topics: [
            "Sự thật về não người mà trường học không dạy",
            "Tại sao người Nhật sống thọ nhất thế giới",
            "Sự thật về giấc ngủ mà 99% người không biết",
            "Những điều bạn làm hàng ngày đang hại sức khỏe",
            "Sự thật về tiền bạc mà người giàu biết còn người nghèo không"
        ]
    },
    {
        value: "tam_ly",
        label: "Tâm Lý & Phát Triển",
        description: "Tâm lý học, kỹ năng sống",
        color: "blue",
        example_topics: [
            "Tại sao bạn trì hoãn và cách dừng lại",
            "Hiệu ứng tâm lý khiến bạn tiêu tiền không kiểm soát",
            "Cách não bộ tạo thói quen và cách thay đổi",
            "Tại sao người thông minh thường cô đơn hơn",
            "Kỹ thuật 5 giây thay đổi cuộc đời của Mel Robbins"
        ]
    },
    {
        value: "lam_giau",
        label: "Tiền Bạc & Làm Giàu",
        description: "Tài chính cá nhân, đầu tư",
        color: "green",
        example_topics: [
            "Quy tắc 50-30-20 quản lý tiền lương",
            "Cách đầu tư 1 triệu/tháng để có 1 tỷ",
            "Sai lầm tài chính của người Việt ở độ tuổi 20-30",
            "Cách người giàu nghĩ về tiền khác người nghèo",
            "5 nguồn thu nhập thụ động phù hợp người Việt"
        ]
    },
    {
        value: "suc_khoe",
        label: "Sức Khỏe & Thuốc Nam",
        description: "Sức khỏe, bài thuốc dân gian Việt",
        color: "emerald",
        example_topics: [
            "Gừng nghệ mật ong - bài thuốc vàng",
            "5 loại rau Việt Nam tốt hơn thuốc bổ",
            "Tại sao người Việt xưa ít bị ung thư hơn bây giờ",
            "Bài thuốc dân gian trị mất ngủ không cần thuốc",
            "Thói quen ăn uống của người Việt thọ 100 tuổi"
        ]
    },
    {
        value: "tinh_cam",
        label: "Tình Cảm & Gia Đình",
        description: "Tình yêu, hôn nhân, gia đình",
        color: "rose",
        example_topics: [
            "Dấu hiệu người đó yêu bạn thật lòng",
            "Tại sao đàn ông Việt ngại nói yêu",
            "Cách nói chuyện với cha mẹ về chuyện hôn nhân",
            "Bí quyết hôn nhân bền vững của các cụ",
            "Sai lầm nuôi dạy con mà cha mẹ Việt hay mắc"
        ]
    },
    {
        value: "engaging",
        label: "Hấp Dẫn & Viral",
        description: "Nội dung viral, mọi đối tượng",
        color: "orange",
        example_topics: [
            "5 sự thật về não người",
            "Cách kiếm tiền online năm 2025",
            "Bí quyết ngủ ngon trong 5 phút",
            "Tại sao người giàu không làm việc chăm chỉ hơn"
        ]
    },
    {
        value: "educational",
        label: "Giáo Dục & Kiến Thức",
        description: "Kiến thức bổ ích, dễ hiểu",
        color: "sky",
        example_topics: [
            "Lạm phát là gì và ảnh hưởng đến bạn",
            "Cách internet hoạt động trong 60 giây",
            "Tại sao bầu trời màu xanh - giải thích đơn giản"
        ]
    },
    {
        value: "funny",
        label: "Hài Hước & Vui Nhộn",
        description: "Nội dung hài, relatable",
        color: "yellow",
        example_topics: [
            "Những kiểu người Việt hay gặp ở quán cà phê",
            "Khi mẹ hỏi con ăn chưa lúc 10 giờ đêm",
            "Sự thật về việc học tiếng Anh của người Việt"
        ]
    }
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
    const [style, setStyle] = useState("engaging");
    const [language, setLanguage] = useState("vi");
    const [mediaSource, setMediaSource] = useState("hybrid");
    const [styles, setStyles] = useState<StyleOption[]>(DEFAULT_STYLES);
    const [suggestions, setSuggestions] = useState<string[]>([]);

    useEffect(() => {
        fetch("/api/video/styles")
            .then((r) => r.json())
            .then((d) => {
                if (d.styles?.length) {
                    setStyles(d.styles);
                    const all = d.styles.flatMap((s: StyleOption) => s.example_topics || []);
                    const shuffled = [...all].sort(() => 0.5 - Math.random());
                    setSuggestions(shuffled.slice(0, 6));
                }
            })
            .catch(() => {
                const all = DEFAULT_STYLES.flatMap((s) => s.example_topics);
                const shuffled = [...all].sort(() => 0.5 - Math.random());
                setSuggestions(shuffled.slice(0, 6));
            });
    }, []);

    const handleRandomize = () => {
        const all = styles.flatMap((s) => s.example_topics || []);
        if (all.length > 0) {
            const randomTopic = all[Math.floor(Math.random() * all.length)];
            setTopic(randomTopic);
            
            // Refresh suggestions pills
            const shuffled = [...all].sort(() => 0.5 - Math.random());
            setSuggestions(shuffled.slice(0, 6));
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!topic.trim() || isLoading) return;
        onGenerate(topic.trim(), style, language, mediaSource);
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">

            {/* ── Topic Input ── */}
            <div className="space-y-2">
                <div className="flex items-center justify-between">
                    <label className="text-[11px] font-bold uppercase tracking-widest text-gray-600">
                        Chủ đề video
                    </label>
                    <button
                        type="button"
                        onClick={handleRandomize}
                        disabled={isLoading}
                        className="text-[10px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-semibold transition-colors disabled:opacity-40"
                    >
                        🎲 Gợi ý ngẫu nhiên
                    </button>
                </div>
                <textarea
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder={`Nhập chủ đề hoặc click vào các gợi ý bên dưới...`}
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
                {suggestions.length > 0 && (
                    <div className="space-y-1.5">
                        <span className="text-[10px] text-slate-500 font-semibold block">💡 Gợi ý chủ đề hay:</span>
                        <div className="flex flex-wrap gap-1.5">
                            {suggestions.map((ex) => (
                                <button
                                    key={ex}
                                    type="button"
                                    onClick={() => setTopic(ex)}
                                    disabled={isLoading}
                                    className={clsx(
                                        "text-[10px] px-2.5 py-1.5 rounded-full border transition-all duration-150 text-left leading-snug break-words",
                                        topic === ex
                                            ? "border-sky-400/50 bg-sky-400/20 text-sky-300 ring-1 ring-sky-400/25"
                                            : "border-white/10 bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white"
                                    )}
                                >
                                    {ex}
                                </button>
                            ))}
                        </div>
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

            {/* ── Visual Source / Media Source ── */}
            <div className="space-y-2">
                <label className="text-[11px] font-bold uppercase tracking-widest text-gray-600">Dạng hình ảnh</label>
                <div className="flex gap-2">
                    {[
                        { value: "hybrid", label: "🎬 Video & Ảnh AI" },
                        { value: "slide", label: "📊 Slide Trình Chiếu" }
                    ].map((src) => (
                        <button
                            key={src.value}
                            type="button"
                            onClick={() => setMediaSource(src.value)}
                            disabled={isLoading}
                            className={clsx(
                                "flex-1 py-2 rounded-lg border text-xs font-semibold transition-all",
                                mediaSource === src.value
                                    ? "border-sky-400/60 bg-sky-400/10 text-sky-200 ring-1 ring-sky-400/25"
                                    : "border-white/[0.08] bg-white/[0.03] text-slate-500 hover:border-white/[0.14] hover:text-slate-300",
                                "disabled:opacity-40"
                            )}
                        >
                            {src.label}
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
