import { useMemo } from "react";

interface Relationship {
  from_character: string;
  to_character: string;
  relationship_type: string;
  description: string;
  strength: number;
}

interface CharacterRelationsProps {
  relationships: Relationship[];
  characterNames?: string[];
}

const RELATIONSHIP_LABELS: Record<string, string> = {
  mentor: "师徒",
  love_interest: "感情",
  friend: "朋友",
  rival: "对手",
  enemy: "敌人",
  family: "家人",
  supporting: "同伴",
  antagonist: "对立",
};

export function CharacterRelations({ relationships, characterNames = [] }: CharacterRelationsProps) {
  const nodes = useMemo(() => {
    const names = new Set<string>();
    relationships.forEach((r) => {
      names.add(r.from_character);
      names.add(r.to_character);
    });
    characterNames.forEach((n) => names.add(n));
    return Array.from(names);
  }, [relationships, characterNames]);

  const edges = useMemo(() => {
    return relationships.map((r) => ({
      ...r,
      label: RELATIONSHIP_LABELS[r.relationship_type] || r.relationship_type,
    }));
  }, [relationships]);

  if (nodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-gray-400 text-sm">
        暂无角色关系数据
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Node List */}
      <div>
        <h3 className="text-sm font-medium mb-2">角色节点</h3>
        <div className="flex flex-wrap gap-2">
          {nodes.map((name) => (
            <span
              key={name}
              className="px-2 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium"
            >
              {name}
            </span>
          ))}
        </div>
      </div>

      {/* Edge List */}
      {edges.length > 0 && (
        <div>
          <h3 className="text-sm font-medium mb-2">关系连线</h3>
          <div className="space-y-1">
            {edges.map((edge, i) => (
              <div key={i} className="flex items-center gap-2 text-sm">
                <span className="font-medium">{edge.from_character}</span>
                <span className="text-gray-400">→</span>
                <span className={`px-1.5 py-0.5 rounded text-xs ${
                  edge.strength > 0.7 ? "bg-green-100 text-green-700" :
                  edge.strength > 0.4 ? "bg-yellow-100 text-yellow-700" :
                  "bg-red-100 text-red-700"
                }`}>
                  {edge.label}
                </span>
                <span className="text-gray-400">→</span>
                <span className="font-medium">{edge.to_character}</span>
                <span className="text-xs text-gray-400 ml-auto">
                  强度: {Math.round(edge.strength * 100)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Simple Visual Graph */}
      <div className="border rounded-lg p-4 min-h-[120px] bg-gray-50">
        <div className="flex flex-wrap items-center justify-center gap-4">
          {nodes.map((name) => (
            <div key={name} className="flex flex-col items-center">
              <div
                className="w-10 h-10 rounded-full bg-blue-400 text-white flex items-center justify-center text-sm font-bold"
              >
                {name.charAt(0)}
              </div>
              <span className="text-xs mt-1 text-gray-600">{name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
