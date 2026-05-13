"use client";

interface ProgressBarProps {
    progress: number;
    message: string;
    status: string;
}

const statusColors: Record<string, string> = {
    pending: "bg-amber-400",
    processing: "bg-sky-400",
    completed: "bg-emerald-400",
    failed: "bg-red-400",
};

export default function ProgressBar({ progress, message, status }: ProgressBarProps) {
    const barColor = statusColors[status] || "bg-sky-500";

    return (
        <div className="w-full space-y-2">
            <div className="flex justify-between items-center text-sm">
                <span className="text-slate-300">{message}</span>
                <span className="text-slate-400 font-mono">{progress}%</span>
            </div>
            <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                <div
                    className={`h-full rounded-full transition-all duration-500 ease-out ${barColor} ${status === "processing" ? "animate-pulse" : ""
                        }`}
                    style={{ width: `${progress}%` }}
                />
            </div>
        </div>
    );
}
