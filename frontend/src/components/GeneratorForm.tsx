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
            "Cổ nhân có một lời dạy về tiền bạc mà nhiều người hiểu sai",
            "Sai lầm khi chọn bạn mà người xưa đã cảnh báo từ lâu",
            "Bí quyết sống thọ của người xưa không nằm ở thuốc bổ",
            "Một quy tắc đối nhân xử thế giúp tránh mất lòng người",
            "Người xưa không theo đuổi thành công theo cách bạn nghĩ",
            "Lời cổ nhân về hôn nhân nghe cũ nhưng vẫn đúng hôm nay"
        ]
    },
    {
        value: "tu_vi",
        label: "Tử Vi & Tướng Số",
        description: "Tử vi, tướng số, phong thủy",
        color: "purple",
        example_topics: [
            "Một đặc điểm nhỏ trên bàn tay thường bị nhiều người bỏ qua",
            "Người sinh tháng 3 thường có một điểm tính cách rất lạ",
            "Sai lầm phong thủy phòng ngủ khiến bạn khó nghỉ ngơi",
            "Dấu hiệu trên khuôn mặt tiết lộ cách bạn xử lý áp lực",
            "Vì sao nhiều người chọn số đẹp nhưng vẫn không thấy may mắn",
            "Một thói quen hằng ngày ảnh hưởng vận khí nhiều hơn vật phẩm"
        ]
    },
    {
        value: "su_that",
        label: "Sự Thật Bất Ngờ",
        description: "Kiến thức gây sốc, ít ai biết",
        color: "red",
        example_topics: [
            "Vì sao não bạn nghiện video ngắn nhanh hơn bạn nghĩ",
            "Sự thật về giấc ngủ mà nhiều người trẻ đang bỏ qua",
            "Một thói quen hằng ngày đang âm thầm làm bạn kém tập trung",
            "Bạn tưởng trí nhớ kém do tuổi tác nhưng lý do thật khác hơn",
            "Sự thật về dopamine khiến bạn khó rời điện thoại",
            "Điều trường học ít dạy về cách não học một kỹ năng mới"
        ]
    },
    {
        value: "tam_ly",
        label: "Tâm Lý & Phát Triển",
        description: "Tâm lý học, kỹ năng sống",
        color: "blue",
        example_topics: [
            "Tại sao bạn biết phải làm nhưng vẫn cứ trì hoãn",
            "Hiệu ứng tâm lý khiến bạn tiêu tiền rồi mới hối hận",
            "Cách não tạo thói quen xấu chỉ bằng một phần thưởng nhỏ",
            "Vì sao người thông minh vẫn ra quyết định rất tệ",
            "Một mẹo 5 giây giúp bạn thoát khỏi vòng trì hoãn",
            "Bạn tưởng mình lười nhưng thật ra não đang né đau"
        ]
    },
    {
        value: "lam_giau",
        label: "Tiền Bạc & Làm Giàu",
        description: "Tài chính cá nhân, đầu tư",
        color: "green",
        example_topics: [
            "Sai lầm tiền bạc khiến nhiều người trẻ lương cao vẫn hết tiền",
            "Vì sao quy tắc 50-30-20 không hợp với mọi người Việt",
            "Bạn tưởng tiết kiệm là giàu nhưng thiếu bước này vẫn thua",
            "Một lỗi mua sắm nhỏ đang ăn mất cả tháng lương của bạn",
            "Người giàu không nghĩ về tiền theo cách người mới đi làm nghĩ",
            "Cách bắt đầu đầu tư nhỏ mà không tự biến mình thành con bạc"
        ]
    },
    {
        value: "suc_khoe",
        label: "Sức Khỏe & Thuốc Nam",
        description: "Sức khỏe, bài thuốc dân gian Việt",
        color: "emerald",
        example_topics: [
            "Một thói quen trước khi ngủ đang phá chất lượng giấc ngủ",
            "Bạn tưởng uống nhiều nước luôn tốt nhưng có một lỗi phổ biến",
            "Loại rau quen thuộc trong mâm cơm Việt có lợi hơn bạn nghĩ",
            "Vì sao càng cố ngủ sớm bạn càng khó ngủ hơn",
            "Một sai lầm ăn sáng khiến bạn nhanh đói và mệt hơn",
            "Bài thuốc dân gian nào nên cẩn thận trước khi tin"
        ]
    },
    {
        value: "tinh_cam",
        label: "Tình Cảm & Gia Đình",
        description: "Tình yêu, hôn nhân, gia đình",
        color: "rose",
        example_topics: [
            "Dấu hiệu người đó cần bạn chứ chưa chắc yêu bạn",
            "Tại sao nhiều người Việt ngại nói yêu dù rất quan tâm",
            "Một câu nói của cha mẹ vô tình làm con xa cách hơn",
            "Sai lầm hôn nhân không ồn ào nhưng làm tình cảm cạn dần",
            "Vì sao càng khuyên con nhiều con càng không nghe",
            "Điều các cặp đôi hay né nhưng quyết định mối quan hệ"
        ]
    },
    {
        value: "engaging",
        label: "Hấp Dẫn & Viral",
        description: "Nội dung viral, mọi đối tượng",
        color: "orange",
        example_topics: [
            "Sai lầm lớn nhất khi dùng ChatGPT để học",
            "Vì sao AI không cướp việc của bạn nhưng người biết AI thì có thể",
            "5 giây đầu quyết định video có viral không như thế nào",
            "Một thói quen nhỏ đang phá hủy khả năng tập trung",
            "Vì sao bạn càng xem Shorts càng khó làm việc sâu",
            "Công nghệ đang âm thầm thay đổi cách bạn kiếm tiền"
        ]
    },
    {
        value: "educational",
        label: "Giáo Dục & Kiến Thức",
        description: "Kiến thức bổ ích, dễ hiểu",
        color: "sky",
        example_topics: [
            "Lạm phát đang lấy tiền của bạn theo cách rất khó thấy",
            "Internet hoạt động thế nào trong một ví dụ 60 giây",
            "Tại sao bầu trời màu xanh nhưng hoàng hôn lại đỏ",
            "Vì sao pin điện thoại chai nhanh hơn bạn nghĩ",
            "Một ví dụ đơn giản giúp hiểu AI tạo sinh hoạt động thế nào"
        ]
    },
    {
        value: "funny",
        label: "Hài Hước & Vui Nhộn",
        description: "Nội dung hài, relatable",
        color: "yellow",
        example_topics: [
            "Những kiểu người ở quán cà phê mà ai cũng từng gặp",
            "Khi mẹ hỏi ăn chưa nhưng thật ra muốn hỏi chuyện khác",
            "Sự thật đau lòng về việc học tiếng Anh của nhiều người Việt",
            "Một kiểu họp công ty khiến ai cũng giả vờ tập trung",
            "Vì sao đi cà phê để làm việc nhưng cuối cùng chỉ lướt điện thoại"
        ]
    },
    {
        value: "motion_tech",
        label: "Motion Tech Short",
        description: "AI, công nghệ, giáo dục motion design",
        color: "orange",
        example_topics: [
            "AI tool miễn phí giúp dựng UI trong vài phút",
            "Một command giúp chạy web app ngay trên máy",
            "Cách AI làm bạn học nhanh hơn nhưng dễ hiểu sai hơn",
            "Công cụ local-first không gửi dữ liệu đi đâu",
            "Một workflow giúp biến prompt thành landing page",
            "Sự thật về AI coding mà người mới dễ bỏ qua"
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
                        Ý tưởng video
                    </label>
                    <button
                        type="button"
                        onClick={handleRandomize}
                        disabled={isLoading}
                        className="text-[10px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-semibold transition-colors disabled:opacity-40"
                    >
                        Tạo ý tưởng
                    </button>
                </div>
                <textarea
                    value={topic}
                    onChange={(e) => setTopic(e.target.value)}
                    placeholder={`Nhập một ý tưởng có tò mò, mâu thuẫn hoặc sự thật bất ngờ. Ví dụ: Vì sao não bạn nghiện video ngắn?`}
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
                        <span className="text-[10px] text-slate-500 font-semibold block">Ý tưởng dễ viral:</span>
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
