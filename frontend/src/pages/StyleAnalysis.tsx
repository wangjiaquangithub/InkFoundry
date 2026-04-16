import { useState } from "react";
import { api } from "../api/client";

interface StyleProfile {
  avg_sentence_length: number;
  avg_paragraph_length: number;
  vocabulary_richness: number;
  common_patterns: string[];
  tone: string;
}

interface FingerprintResult {
  fingerprint: string;
  style_profile: StyleProfile;
}

const toneLabels: Record<string, string> = {
  formal: "正式",
  casual: "日常",
  poetic: "诗意",
  direct: "直接",
};

type Tab = "fingerprint" | "imitation";

export function StyleAnalysis() {
  const [activeTab, setActiveTab] = useState<Tab>("fingerprint");

  return (
    <div className="flex flex-col h-full bg-white">
      <div className="px-6 py-4 border-b">
        <h1 className="text-xl font-bold">风格分析 / 仿写</h1>
        <p className="text-sm text-gray-500 mt-1">
          分析参考文本风格特征，或生成仿写内容
        </p>
      </div>

      {/* Tab Bar */}
      <div className="flex border-b bg-white">
        <button
          onClick={() => setActiveTab("fingerprint")}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition ${
            activeTab === "fingerprint"
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          风格分析
        </button>
        <button
          onClick={() => setActiveTab("imitation")}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition ${
            activeTab === "imitation"
              ? "border-blue-500 text-blue-600"
              : "border-transparent text-gray-500 hover:text-gray-700"
          }`}
        >
          仿写生成
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto">
        {activeTab === "fingerprint" ? <StyleFingerprintTab /> : <ImitationTab />}
      </div>
    </div>
  );
}

function StyleFingerprintTab() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FingerprintResult | null>(null);
  const [error, setError] = useState("");

  const analyze = async () => {
    if (!input.trim()) {
      setError("请输入要分析的文本");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await api.getStyleFingerprint(input);
      setResult(res.data);
    } catch {
      setError("分析失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Input */}
      <div className="bg-white rounded-lg border p-4">
        <label className="text-sm font-medium mb-2 block">参考文本</label>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="粘贴参考文本以分析其写作风格..."
          className="w-full h-40 border rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex gap-2 mt-2">
          <button
            onClick={analyze}
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          >
            {loading ? "分析中..." : "分析风格"}
          </button>
          {result && (
            <button
              onClick={() => { setResult(null); setInput(""); }}
              className="px-4 py-2 border rounded hover:bg-gray-50 text-sm"
            >
              清除
            </button>
          )}
        </div>
        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </div>

      {/* Results */}
      {result && (
        <>
          {/* Fingerprint */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="text-sm text-gray-500 mb-1">风格指纹</div>
            <code className="text-green-600 font-mono text-sm">{result.fingerprint}</code>
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white rounded-lg border p-4">
              <div className="text-sm text-gray-500">平均句长</div>
              <div className="text-2xl font-bold text-blue-600">{result.style_profile.avg_sentence_length.toFixed(1)}</div>
              <div className="text-xs text-gray-400">字/句</div>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="text-sm text-gray-500">词汇丰富度</div>
              <div className="text-2xl font-bold text-purple-600">{result.style_profile.vocabulary_richness.toFixed(2)}</div>
              <div className="text-xs text-gray-400">词汇密度</div>
            </div>
            <div className="bg-white rounded-lg border p-4">
              <div className="text-sm text-gray-500">语调</div>
              <div className="text-2xl font-bold text-yellow-600">{toneLabels[result.style_profile.tone] || result.style_profile.tone}</div>
              <div className="text-xs text-gray-400">写作风格</div>
            </div>
          </div>

          {/* Pattern Tags */}
          {result.style_profile.common_patterns.length > 0 && (
            <div className="bg-white rounded-lg border p-4">
              <div className="text-sm text-gray-500 mb-2">检测到的模式</div>
              <div className="flex flex-wrap gap-2">
                {result.style_profile.common_patterns.map((p) => (
                  <span key={p} className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-xs">{p}</span>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function ImitationTab() {
  const [sampleText, setSampleText] = useState("");
  const [topic, setTopic] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string>("");
  const [error, setError] = useState("");

  const handleGenerate = async () => {
    if (!sampleText.trim() || !topic.trim()) {
      setError("请填写参考文本和主题");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await api.generateImitation({
        sample_text: sampleText,
        topic: topic,
      });
      setResult(res.data.content || "");
    } catch {
      setError("生成失败，请重试");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Input */}
      <div className="bg-white rounded-lg border p-4">
        <label className="text-sm font-medium mb-2 block">参考文本</label>
        <textarea
          value={sampleText}
          onChange={(e) => setSampleText(e.target.value)}
          placeholder="粘贴要模仿的参考文本..."
          className="w-full h-32 border rounded-lg p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <label className="text-sm font-medium mb-2 mt-4 block">仿写主题</label>
        <input
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="输入要仿写的主题..."
          className="w-full border rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />

        <div className="flex gap-2 mt-3">
          <button
            onClick={handleGenerate}
            disabled={loading || !sampleText.trim() || !topic.trim()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          >
            {loading ? "生成中..." : "生成仿写"}
          </button>
          {result && (
            <button
              onClick={() => { setResult(""); setSampleText(""); setTopic(""); }}
              className="px-4 py-2 border rounded hover:bg-gray-50 text-sm"
            >
              清除
            </button>
          )}
        </div>
        {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
      </div>

      {/* Result */}
      {result && (
        <div className="bg-white rounded-lg border p-6">
          <h3 className="font-medium mb-3">仿写结果</h3>
          <div className="whitespace-pre-wrap font-serif text-base leading-relaxed text-gray-800">
            {result}
          </div>
        </div>
      )}
    </div>
  );
}
