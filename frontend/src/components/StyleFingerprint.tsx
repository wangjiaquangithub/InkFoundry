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

export function StyleFingerprint() {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FingerprintResult | null>(null);
  const [error, setError] = useState("");

  const analyze = async () => {
    if (!input.trim()) {
      setError("Please enter some text to analyze");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const res = await api.extractStyle(input);
      setResult(res.data);
    } catch {
      setError("Failed to analyze style");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h3 className="text-lg font-semibold text-white mb-4">Style Fingerprint</h3>

      {/* Input */}
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Paste sample text here to analyze its writing style..."
        className="w-full h-32 bg-gray-700 text-white rounded p-3 text-sm resize-none"
      />
      <div className="flex gap-2 mt-2">
        <button
          onClick={analyze}
          disabled={loading || !input.trim()}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Analyzing..." : "Analyze Style"}
        </button>
        {result && (
          <button
            onClick={() => { setResult(null); setInput(""); }}
            className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Clear
          </button>
        )}
      </div>
      {error && <p className="text-red-400 text-sm mt-2">{error}</p>}

      {/* Results */}
      {result && (
        <div className="mt-4 space-y-4">
          {/* Fingerprint hash */}
          <div className="bg-gray-700 rounded p-3">
            <div className="text-sm text-gray-400 mb-1">Fingerprint</div>
            <code className="text-green-400 font-mono text-sm">{result.fingerprint}</code>
          </div>

          {/* Metrics */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-gray-700 rounded p-3">
              <div className="text-sm text-gray-400">Avg Sentence Length</div>
              <div className="text-xl font-bold text-blue-400">{result.style_profile.avg_sentence_length.toFixed(1)}</div>
            </div>
            <div className="bg-gray-700 rounded p-3">
              <div className="text-sm text-gray-400">Vocabulary Richness</div>
              <div className="text-xl font-bold text-purple-400">{result.style_profile.vocabulary_richness.toFixed(2)}</div>
            </div>
            <div className="bg-gray-700 rounded p-3">
              <div className="text-sm text-gray-400">Tone</div>
              <div className="text-xl font-bold text-yellow-400">{toneLabels[result.style_profile.tone] || result.style_profile.tone}</div>
            </div>
          </div>

          {/* Pattern tags */}
          {result.style_profile.common_patterns.length > 0 && (
            <div>
              <div className="text-sm text-gray-400 mb-2">Detected Patterns</div>
              <div className="flex flex-wrap gap-2">
                {result.style_profile.common_patterns.map((p) => (
                  <span key={p} className="px-2 py-1 bg-gray-600 text-gray-200 rounded text-xs">{p}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
