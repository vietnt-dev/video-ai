"use client";

import { Check, Loader2 } from "lucide-react";
import clsx from "clsx";

const STEPS = [
    { id: 1, label: "Kịch bản", range: [0, 20] },
    { id: 2, label: "Giọng đọc", range: [20, 45] },
    { id: 3, label: "Tư liệu", range: [45, 65] },
    { id: 4, label: "Render", range: [65, 100] },
];

interface StepIndicatorProps {
    progress: number;
    status: string;
}

export default function StepIndicator({ progress, status }: StepIndicatorProps) {
    const getStepStatus = (range: number[]) => {
        if (progress >= range[1]) return "done";
        if (progress >= range[0]) return "active";
        return "waiting";
    };

    return (
        <div className="flex items-center justify-between w-full">
            {STEPS.map((step, idx) => {
                const stepStatus = getStepStatus(step.range);

                return (
                    <div key={step.id} className="flex items-center flex-1">
                        <div className="flex flex-col items-center gap-1.5">
                            <div
                                className={clsx(
                                    "w-10 h-10 rounded-full flex items-center justify-center text-lg transition-all",
                                    stepStatus === "done" && "bg-emerald-400/15 border border-emerald-400/60",
                                    stepStatus === "active" && "bg-sky-400/15 border border-sky-400/60 animate-pulse",
                                    stepStatus === "waiting" && "bg-slate-800 border border-slate-700"
                                )}
                            >
                                {stepStatus === "done" ? (
                                    <Check size={18} className="text-emerald-400" />
                                ) : stepStatus === "active" ? (
                                    <Loader2 size={18} className="text-sky-400 animate-spin" />
                                ) : (
                                    <span className="text-xs font-bold text-slate-500">{step.id}</span>
                                )}
                            </div>
                            <span
                                className={clsx(
                                    "text-[10px] font-medium text-center leading-tight max-w-[60px]",
                                    stepStatus === "done" && "text-emerald-400",
                                    stepStatus === "active" && "text-sky-400",
                                    stepStatus === "waiting" && "text-slate-500"
                                )}
                            >
                                {step.label}
                            </span>
                        </div>

                        {/* Connector line */}
                        {idx < STEPS.length - 1 && (
                            <div className="flex-1 h-0.5 mx-2 mb-5 rounded-full overflow-hidden bg-slate-800">
                                <div
                                    className="h-full bg-emerald-500 transition-all duration-500"
                                    style={{
                                        width: progress >= step.range[1] ? "100%" : "0%",
                                    }}
                                />
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
