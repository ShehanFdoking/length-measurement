'use client';

import { useState } from 'react';
import { ChevronDown, HelpCircle, Lightbulb, AlertCircle, CheckCircle2 } from 'lucide-react';

interface ReferenceObject {
  emoji: string;
  name: string;
  typical: string;
  range: { min: number; max: number };
  unit: 'cm';
  why: string;
}

const COMMON_REFERENCE_OBJECTS: ReferenceObject[] = [
  {
    emoji: '🛋️',
    name: 'Sofa (2-3 seater)',
    typical: '1.6m - 2.0m',
    range: { min: 160, max: 200 },
    unit: 'cm',
    why: 'Large, recognizable, consistent sizing across brands'
  },
  {
    emoji: '🚪',
    name: 'Standard Door',
    typical: '2.0m - 2.1m',
    range: { min: 200, max: 210 },
    unit: 'cm',
    why: 'Very consistent - building code standardized'
  },
  {
    emoji: '📺',
    name: '55" TV Screen',
    typical: '122cm wide',
    range: { min: 110, max: 135 },
    unit: 'cm',
    why: 'Modern common reference, predictable size'
  },
  {
    emoji: '🪑',
    name: 'Dining Chair Seat Height',
    typical: '45cm - 50cm',
    range: { min: 45, max: 50 },
    unit: 'cm',
    why: 'Standard furniture measurement'
  },
  {
    emoji: '📄',
    name: 'A4 Paper',
    typical: '21cm',
    range: { min: 21, max: 21 },
    unit: 'cm',
    why: 'Exact and universal - best for precision'
  },
  {
    emoji: '💡',
    name: 'Light Bulb (E27)',
    typical: '10.8cm',
    range: { min: 10.5, max: 11.5 },
    unit: 'cm',
    why: 'Small, precise, easy to identify'
  },
  {
    emoji: '📖',
    name: 'Standard Book',
    typical: '23cm (height)',
    range: { min: 20, max: 25 },
    unit: 'cm',
    why: 'Commonly available, recognizable'
  },
  {
    emoji: '☕',
    name: 'Coffee Mug',
    typical: '10cm',
    range: { min: 8, max: 12 },
    unit: 'cm',
    why: 'Common household item, portable'
  }
];

interface ReferenceObjectGuideProps {
  onSelectReference?: (name: string, value: number) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

export function ReferenceObjectGuide({ onSelectReference, isOpen = true, onClose }: ReferenceObjectGuideProps) {
  const [selectedObject, setSelectedObject] = useState<ReferenceObject | null>(null);
  const [estimationMode, setEstimationMode] = useState(false);

  if (!isOpen) {
    return null;
  }

  return (
    <div className="space-y-4 rounded-[1.75rem] border border-amber-200 bg-gradient-to-br from-amber-50 to-orange-50 p-5 shadow-sm">
      <div className="flex items-start gap-3">
        <Lightbulb className="h-5 w-5 flex-shrink-0 text-amber-600 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-semibold text-ink">📏 Possible reference objects in your image</h3>
          <p className="mt-1 text-sm text-ink/65">
            Select a common object to see typical dimensions. This helps you calibrate measurements accurately.
          </p>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        {COMMON_REFERENCE_OBJECTS.map((obj) => (
          <button
            key={obj.name}
            onClick={() => {
              setSelectedObject(selectedObject?.name === obj.name ? null : obj);
              setEstimationMode(false);
            }}
            className={`text-left p-3 rounded-lg border transition ${
              selectedObject?.name === obj.name
                ? 'border-amber-400 bg-white shadow-sm'
                : 'border-amber-200 hover:border-amber-300 hover:bg-white/60'
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-xl">{obj.emoji}</span>
              <div className="flex-1">
                <p className="text-xs font-semibold text-ink/80">{obj.name}</p>
                <p className="text-xs text-ink/55">{obj.typical}</p>
              </div>
              <ChevronDown
                className={`h-4 w-4 text-ink/40 transition ${
                  selectedObject?.name === obj.name ? 'rotate-180' : ''
                }`}
              />
            </div>
          </button>
        ))}
      </div>

      {selectedObject && (
        <div className="space-y-3 rounded-lg bg-white p-4 border border-amber-200">
          <div className="space-y-2">
            <p className="text-sm font-semibold text-ink">
              {selectedObject.emoji} {selectedObject.name}
            </p>
            <p className="text-xs text-ink/65">{selectedObject.why}</p>
          </div>

          <div className="space-y-2 border-t border-amber-100 pt-3">
            <p className="text-xs font-semibold text-ink/60">Typical size range:</p>
            <div className="rounded bg-amber-50 px-3 py-2 text-center">
              <p className="text-lg font-bold text-amber-700">
                {selectedObject.range.min} - {selectedObject.range.max} cm
              </p>
              <p className="text-xs text-amber-600/80">
                ({(selectedObject.range.min / 100).toFixed(2)}m - {(selectedObject.range.max / 100).toFixed(2)}m)
              </p>
            </div>
          </div>

          <div className="space-y-2 border-t border-amber-100 pt-3">
            <button
              onClick={() => setEstimationMode(!estimationMode)}
              className="w-full flex items-center justify-between text-xs font-semibold text-amber-700 hover:text-amber-900 transition"
            >
              <span>How to use this for estimation</span>
              <ChevronDown className={`h-3 w-3 transition ${estimationMode ? 'rotate-180' : ''}`} />
            </button>

            {estimationMode && (
              <div className="space-y-2 rounded bg-amber-50 p-3 text-xs text-ink/70 leading-relaxed">
                <p>
                  <span className="font-semibold">1. Locate</span> the {selectedObject.name.toLowerCase()} in your image
                </p>
                <p>
                  <span className="font-semibold">2. Compare</span> your target object to this reference
                </p>
                <p>
                  <span className="font-semibold">3. Estimate ratio</span> (e.g., {`"tree is 1.5× sofa height"`})
                </p>
                <p>
                  <span className="font-semibold">4. Calculate</span> estimated dimension
                </p>
                <p className="mt-2 rounded bg-white px-2 py-1">
                  <span className="text-amber-700 font-semibold">⚠️ Accuracy note:</span> Camera angle, distance, and lens distortion can cause ±20-30cm errors or more. For precise measurements, place a ruler or known-size object in the image.
                </p>
              </div>
            )}
          </div>

          {onSelectReference && (
            <button
              onClick={() => {
                onSelectReference(selectedObject.name, selectedObject.range.min);
                setSelectedObject(null);
              }}
              className="w-full flex items-center justify-center gap-2 mt-2 px-3 py-2 rounded-lg bg-amber-600 text-white text-sm font-semibold hover:bg-amber-700 transition"
            >
              <CheckCircle2 className="h-4 w-4" />
              Use {selectedObject.range.min}cm as reference
            </button>
          )}
        </div>
      )}

      <div className="flex gap-2 rounded-lg bg-blue-50 border border-blue-200 p-3">
        <AlertCircle className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-xs text-blue-700">
          <p className="font-semibold mb-1">✅ For best accuracy:</p>
          <ul className="space-y-0.5 text-blue-700/80">
            <li>• Place a ruler, tape measure, or credit card in the image</li>
            <li>• Or tell us the exact dimension of any visible object</li>
            <li>• Position reference object perpendicular to camera</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export function EstimationHelper({
  referenceName,
  referenceValue
}: {
  referenceName?: string;
  referenceValue?: number;
}) {
  if (!referenceName || !referenceValue) return null;

  return (
    <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-xs space-y-2">
      <p className="font-semibold text-blue-900">
        📐 Using: {referenceName} (~{referenceValue}cm)
      </p>
      <p className="text-blue-700/80">
        {`The app will now use this as a scale reference. Objects in your image will be measured relative to this dimension. You can refine this value if it doesn't match your actual reference object.`}
      </p>
    </div>
  );
}
