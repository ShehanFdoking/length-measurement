'use client';

import { CheckCircle2, AlertCircle, Lightbulb } from 'lucide-react';

interface DetectedReference {
  objectType: string;
  confidence: number;
  standardDimension: number;
  dimension: string;
  reason: string;
}

interface AutoCalibrationSuggestionProps {
  detected?: DetectedReference[];
  suggested?: DetectedReference;
  onSelectSuggestion?: (value: number) => void;
}

const OBJECT_EMOJIS: Record<string, string> = {
  door: '🚪',
  sofa: '🛋️',
  tv: '📺',
  table: '🪑',
};

export function AutoCalibrationSuggestion({
  detected,
  suggested,
  onSelectSuggestion
}: AutoCalibrationSuggestionProps) {
  if (!detected || detected.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3 rounded-lg bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 p-4">
      <div className="flex gap-2">
        <Lightbulb className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-semibold text-ink">🎯 Auto-detected reference objects</h3>
          <p className="mt-1 text-xs text-ink/65">
            The app found {detected.length} object{detected.length !== 1 ? 's' : ''} with standard dimensions in your image.
          </p>
        </div>
      </div>

      <div className="space-y-2">
        {detected.map((ref) => (
          <div
            key={ref.objectType}
            className={`flex items-start gap-3 rounded-lg border p-3 transition cursor-pointer ${
              suggested?.objectType === ref.objectType
                ? 'border-green-400 bg-white shadow-sm'
                : 'border-green-200 hover:border-green-300 bg-white/60'
            }`}
            onClick={() => onSelectSuggestion?.(ref.standardDimension)}
          >
            <div className="flex-shrink-0 text-2xl">
              {OBJECT_EMOJIS[ref.objectType] || '📦'}
            </div>
            <div className="flex-1">
              <p className="text-sm font-semibold text-ink capitalize">{ref.objectType}</p>
              <p className="text-xs text-ink/65">{ref.reason}</p>
              <div className="mt-2 flex items-center gap-2">
                <div className="h-1.5 bg-green-200 rounded-full flex-1" style={{width: '100%'}}>
                  <div
                    className="h-full bg-green-500 rounded-full"
                    style={{ width: `${Math.round(ref.confidence * 100)}%` }}
                  />
                </div>
                <span className="text-xs font-semibold text-green-700">
                  {Math.round(ref.confidence * 100)}%
                </span>
              </div>
            </div>
            <div className="text-right flex-shrink-0">
              <p className="text-sm font-bold text-ink">{ref.dimension}</p>
              <p className="text-xs text-ink/55">standard size</p>
            </div>
          </div>
        ))}
      </div>

      {suggested && (
        <button
          onClick={() => onSelectSuggestion?.(suggested.standardDimension)}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-semibold hover:bg-green-700 transition"
        >
          <CheckCircle2 className="h-4 w-4" />
          Use {suggested.objectType.toUpperCase()} ({suggested.dimension}) as calibration
        </button>
      )}

      <div className="flex gap-2 rounded-lg bg-blue-50 border border-blue-200 p-3">
        <AlertCircle className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-blue-700">
          <span className="font-semibold">Confidence score</span> shows how accurately the detected object matches standard dimensions. Higher is better, but always verify the object is actually present in your image.
        </p>
      </div>
    </div>
  );
}
