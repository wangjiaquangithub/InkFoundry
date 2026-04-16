import { useEffect, useState } from "react";
import { api } from "../api/client";

interface TensionPoint {
  chapter_num: number;
  tension_level: string | number;
}

interface TensionGraphProps {
  chapters?: TensionPoint[];
}

export function TensionGraph({ chapters }: TensionGraphProps) {
  const [loading, setLoading] = useState(!chapters);
  const [data, setData] = useState<TensionPoint[]>(chapters || []);

  useEffect(() => {
    if (chapters) {
      setData(chapters);
      setLoading(false);
      return;
    }
    api.getChapters().then((res) => {
      const points = (res.data.chapters || []).map((ch: any) => ({
        chapter_num: ch.chapter_num,
        tension_level: ch.tension_level || 5,
      }));
      setData(points);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [chapters]);

  if (loading) return <div className="text-center py-8 text-gray-400">Loading tension data...</div>;
  if (data.length === 0) return <div className="text-center py-8 text-gray-400">No chapter data available</div>;

  const maxChapter = Math.max(...data.map(d => typeof d.chapter_num === 'number' ? d.chapter_num : 0), 1);
  const maxHeight = 200;

  const points = data.map((d) => {
    const x = (d.chapter_num / maxChapter) * 600 + 20;
    const tension = typeof d.tension_level === 'number' ? d.tension_level : parseInt(d.tension_level) || 5;
    const y = maxHeight - (Math.min(Math.max(tension, 1), 10) / 10) * maxHeight + 10;
    return { x, y, ...d };
  });

  const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
  const areaD = pathD + ` L ${points[points.length - 1]?.x || 0} ${maxHeight + 10} L ${points[0]?.x || 20} ${maxHeight + 10} Z`;

  const tensionLabels = { 10: "最高潮", 8: "高潮", 6: "紧张", 4: "平缓", 2: "放松" };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold text-white mb-2">Tension Curve</h3>
      <svg viewBox="0 0 640 230" className="w-full h-48">
        {/* Grid lines */}
        {[2, 4, 6, 8, 10].map(v => (
          <g key={v}>
            <line x1="20" y1={maxHeight - (v / 10) * maxHeight + 10} x2="620" y2={maxHeight - (v / 10) * maxHeight + 10} stroke="#374151" strokeDasharray="4" />
            <text x="5" y={maxHeight - (v / 10) * maxHeight + 14} fill="#9CA3AF" fontSize="10">{v}</text>
          </g>
        ))}
        {/* Area fill */}
        <path d={areaD} fill="rgba(59,130,246,0.15)" />
        {/* Line */}
        <path d={pathD} fill="none" stroke="#3B82F6" strokeWidth="2" />
        {/* Points */}
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r="4" fill="#3B82F6" />
            <text x={p.x} y={maxHeight + 25} fill="#9CA3AF" fontSize="9" textAnchor="middle">{p.chapter_num}</text>
          </g>
        ))}
        {/* Y axis label */}
        <text x="5" y={maxHeight / 2} fill="#9CA3AF" fontSize="10" transform="rotate(-90, 5, 100)">Tension</text>
      </svg>
      {/* Legend */}
      <div className="flex gap-3 text-xs text-gray-400 mt-1">
        {Object.entries(tensionLabels).map(([level, label]) => (
          <span key={level}>{label}: {level}</span>
        ))}
      </div>
    </div>
  );
}
