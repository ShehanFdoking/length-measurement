"use client";

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { useSession } from 'next-auth/react';
import { Check, ImagePlus, Loader2, Save, Shield } from 'lucide-react';

import { AppShell } from '@/components/AppShell';
import { BlueprintView } from '@/components/BlueprintView';
import { ReferenceObjectGuide, EstimationHelper } from '@/components/ReferenceObjectGuide';
import { AutoCalibrationSuggestion } from '@/components/AutoCalibrationSuggestion';
import type { ImageMeasurement, MeasureResponse, MeasurementObject } from '@/lib/api';
import { measureImages, saveProject } from '@/lib/api';

type PreviewFile = {
  file: File;
  previewUrl: string;
};

type ScaleUnit = 'mm' | 'cm' | 'm';

function toCentimeters(value: number, unit: ScaleUnit): number {
  if (unit === 'mm') return value / 10;
  if (unit === 'm') return value * 100;
  return value;
}

function formatMetricTriplet(valueCm: number) {
  return {
    mm: `${(valueCm * 10).toFixed(1)} mm`,
    cm: `${valueCm.toFixed(2)} cm`,
    m: `${(valueCm / 100).toFixed(3)} m`
  };
}

export default function MeasurePage() {
  const { data: session, status } = useSession();
  const [projectName, setProjectName] = useState('');
  const [referenceScaleValue, setReferenceScaleValue] = useState<string>('');
  const [referenceScaleUnit, setReferenceScaleUnit] = useState<ScaleUnit>('cm');
  const [files, setFiles] = useState<File[]>([]);
  const [measurement, setMeasurement] = useState<MeasureResponse | null>(null);
  const [selectedObjectIds, setSelectedObjectIds] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [isMeasuring, setIsMeasuring] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [savedProjectId, setSavedProjectId] = useState('');
  const [previewFiles, setPreviewFiles] = useState<PreviewFile[]>([]);
  const [showBlueprintView, setShowBlueprintView] = useState(true);
  const [selectedReferenceObject, setSelectedReferenceObject] = useState<{ name: string; value: number } | null>(null);
  const [showReferenceGuide, setShowReferenceGuide] = useState(true);

  useEffect(() => {
    const nextPreviewFiles = files.map((file) => ({ file, previewUrl: URL.createObjectURL(file) }));
    setPreviewFiles(nextPreviewFiles);

    return () => {
      nextPreviewFiles.forEach(({ previewUrl }) => URL.revokeObjectURL(previewUrl));
    };
  }, [files]);

  const totalObjects = useMemo(() => measurement?.images.reduce((count, image) => count + image.objects.length, 0) ?? 0, [measurement]);

  if (status === 'loading') {
    return <LoadingState />;
  }

  if (!session) {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <div className="max-w-md rounded-[2rem] border border-line bg-white p-8 text-center shadow-glow">
          <Shield className="mx-auto h-10 w-10 text-moss" />
          <h1 className="mt-4 font-[family-name:var(--font-space-grotesk)] text-3xl text-ink">Login required</h1>
          <p className="mt-3 text-ink/65">Return to the home page and sign in with Google before uploading images.</p>
          <Link href="/" className="mt-6 inline-flex rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper">
            Back to home
          </Link>
        </div>
      </main>
    );
  }

  async function handleMeasure() {
    if (files.length === 0) {
      setError('Please upload at least one image.');
      return;
    }

    const numericScaleValue = Number(referenceScaleValue);
    if (!referenceScaleValue || !Number.isFinite(numericScaleValue) || numericScaleValue <= 0) {
      setError('Enter one known real-world length from the image, drawing, or plan before measuring.');
      return;
    }

    setError('');
    setIsMeasuring(true);

    try {
      const userId = session?.user?.id;

      const result = await measureImages({
        projectName: projectName || 'Untitled project',
        files,
        userId,
        referenceWidthCm: toCentimeters(numericScaleValue, referenceScaleUnit)
      });

      setMeasurement(result);
      setSelectedObjectIds(result.images.flatMap((image) => image.objects.map((object) => object.id)));
      setSavedProjectId('');
    } catch (measureError) {
      setError(measureError instanceof Error ? measureError.message : 'Measurement failed.');
    } finally {
      setIsMeasuring(false);
    }
  }

  async function handleSaveProject() {
    if (!measurement) {
      setError('Run a measurement before saving the project.');
      return;
    }

    if (!projectName.trim()) {
      setError('Enter a project name before saving.');
      return;
    }

    setError('');
    setIsSaving(true);

    try {
      const savedProject = await saveProject({
        name: projectName.trim(),
        measurement,
        selectedObjectIds
      });

      setSavedProjectId(savedProject.id);
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Could not save the project.');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <AppShell>
      <section className="rounded-[2rem] border border-line bg-white p-6 shadow-sm sm:p-8">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-moss">Measurement studio</p>
            <h1 className="mt-2 font-[family-name:var(--font-space-grotesk)] text-4xl text-ink sm:text-5xl">Upload images and generate measurements.</h1>
            <p className="mt-3 max-w-2xl text-ink/65">Add up to three images or plan sheets, run the measurement step, review isolated object cards and the background summary, then save the selection as a project.</p>
            <p className="mt-3 max-w-2xl rounded-2xl border border-sand bg-sand/30 px-4 py-3 text-sm text-ink/70">
              Length, width, and height are shown in mm, cm, and m. Use a known real-world dimension in the image or drawing to calibrate the scale. Height is still estimated from 2D geometry; true 3D height needs depth data or multi-view capture.
            </p>
          </div>
          <div className="rounded-2xl border border-line bg-sand/30 px-4 py-3 text-sm text-ink/70">
            Selected objects: <span className="font-semibold text-ink">{selectedObjectIds.length}</span> · Total objects: <span className="font-semibold text-ink">{totalObjects}</span>
          </div>
        </div>

        <div className="mt-8 grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
          <div className="space-y-6 rounded-[1.75rem] border border-line bg-paper/55 p-5">
            <div>
              <label className="text-sm font-semibold text-ink" htmlFor="project-name">Project name</label>
              <input
                id="project-name"
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
                placeholder="Example: Shelf scan June"
                className="mt-2 w-full rounded-2xl border border-line bg-white px-4 py-3 text-sm outline-none ring-0 placeholder:text-ink/35 focus:border-moss"
              />
            </div>

            <div>
              <label className="text-sm font-semibold text-ink" htmlFor="reference-value">Known scale length</label>
              {selectedReferenceObject && (
                <EstimationHelper
                  referenceName={selectedReferenceObject.name}
                  referenceValue={selectedReferenceObject.value}
                />
              )}
              <div className="mt-3 grid grid-cols-[1fr_96px] gap-3">
                <input
                  id="reference-value"
                  type="number"
                  min={0.1}
                  step="0.1"
                  placeholder="Enter one real length"
                  value={referenceScaleValue}
                  onChange={(event) => setReferenceScaleValue(event.target.value)}
                  className="w-full rounded-2xl border border-line bg-white px-4 py-3 text-sm outline-none ring-0 placeholder:text-ink/35 focus:border-moss"
                />
                <select
                  value={referenceScaleUnit}
                  onChange={(event) => setReferenceScaleUnit(event.target.value as ScaleUnit)}
                  className="w-full rounded-2xl border border-line bg-white px-4 py-3 text-sm outline-none ring-0 focus:border-moss"
                >
                  <option value="mm">mm</option>
                  <option value="cm">cm</option>
                  <option value="m">m</option>
                </select>
              </div>
              <p className="mt-2 text-xs text-ink/55">You must enter one real dimension from the image, drawing, or plan. Without that scale, the app cannot produce real-world measurements.</p>
            </div>

            {showReferenceGuide && (
              <div className="space-y-3">
                <button
                  onClick={() => setShowReferenceGuide(false)}
                  className="text-xs text-ink/50 hover:text-ink/70 transition underline"
                >
                  Hide reference guide
                </button>
                <ReferenceObjectGuide
                  isOpen={showReferenceGuide}
                  onSelectReference={(name, value) => {
                    setReferenceScaleValue(value.toString());
                    setSelectedReferenceObject({ name, value });
                    setShowReferenceGuide(false);
                  }}
                  onClose={() => setShowReferenceGuide(false)}
                />
              </div>
            )}
            {!showReferenceGuide && (
              <button
                onClick={() => setShowReferenceGuide(true)}
                className="text-xs text-moss hover:text-moss/80 transition underline font-semibold"
              >
                📏 Show reference objects guide
              </button>
            )}

            <div>
              <label className="flex cursor-pointer flex-col items-center justify-center rounded-[1.5rem] border-2 border-dashed border-line bg-white px-6 py-8 text-center transition hover:border-moss" htmlFor="image-upload">
                <ImagePlus className="h-8 w-8 text-moss" />
                <span className="mt-3 text-base font-semibold text-ink">Add up to 3 images</span>
                <span className="mt-1 text-sm text-ink/55">Choose object photos before measuring.</span>
              </label>
              <input
                id="image-upload"
                type="file"
                accept="image/*"
                multiple
                className="sr-only"
                onChange={(event) => {
                  const nextFiles = Array.from(event.target.files ?? []).slice(0, 3);
                  setFiles(nextFiles);
                  setMeasurement(null);
                  setSavedProjectId('');
                  setSelectedObjectIds([]);
                  setError('');
                }}
              />
            </div>

            {previewFiles.length > 0 && (
              <div className="grid gap-3 sm:grid-cols-3">
                {previewFiles.map(({ file, previewUrl }) => (
                  <div key={file.name} className="overflow-hidden rounded-2xl border border-line bg-white">
                    <Image src={previewUrl} alt={file.name} width={320} height={224} unoptimized className="h-28 w-full object-cover" />
                    <div className="px-3 py-2 text-xs text-ink/65">{file.name}</div>
                  </div>
                ))}
              </div>
            )}

            <button
              type="button"
              onClick={handleMeasure}
              disabled={isMeasuring || files.length === 0}
              className="inline-flex w-full items-center justify-center gap-2 rounded-full bg-ink px-5 py-3 text-sm font-semibold text-paper transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-ink/30"
            >
              {isMeasuring ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              Measure length
            </button>

            {error ? <p className="rounded-2xl border border-coral/30 bg-coral/10 px-4 py-3 text-sm text-coral">{error}</p> : null}
            {savedProjectId ? (
              <p className="rounded-2xl border border-moss/30 bg-moss/10 px-4 py-3 text-sm text-moss">
                Project saved successfully. Open it here: <Link href={`/projects/${savedProjectId}`} className="font-semibold underline">{savedProjectId}</Link>
              </p>
            ) : null}
          </div>

          <div className="space-y-6">
            {!measurement ? (
              <EmptyResults />
            ) : (
              <>
                {measurement.images.map((image) => (
                  <MeasurementPanel
                    key={`${image.imageName}-${image.imageIndex}`}
                    image={image}
                    selectedObjectIds={selectedObjectIds}
                    showBlueprintView={showBlueprintView}
                    onToggleBlueprintView={() => setShowBlueprintView(!showBlueprintView)}
                    onToggleObject={(objectId) => {
                      setSelectedObjectIds((current) =>
                        current.includes(objectId) ? current.filter((item) => item !== objectId) : [...current, objectId]
                      );
                    }}
                  />
                ))}

                <div className="rounded-[1.75rem] border border-line bg-white p-6 shadow-sm">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="text-sm font-semibold uppercase tracking-[0.3em] text-moss">Save project</p>
                      <h2 className="mt-2 font-[family-name:var(--font-space-grotesk)] text-2xl text-ink">Name and store the selected measurements.</h2>
                    </div>
                    <Check className="h-5 w-5 text-moss" />
                  </div>
                  <p className="mt-3 text-sm leading-6 text-ink/65">The project will keep the full measurement response plus the selected object identifiers.</p>
                  <button
                    type="button"
                    onClick={handleSaveProject}
                    disabled={isSaving || !measurement}
                    className="mt-5 inline-flex items-center gap-2 rounded-full bg-moss px-5 py-3 text-sm font-semibold text-paper transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:bg-moss/35"
                  >
                    {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Save as project
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </section>
    </AppShell>
  );
}

function MeasurementPanel({
  image,
  selectedObjectIds,
  showBlueprintView,
  onToggleBlueprintView,
  onToggleObject
}: {
  image: ImageMeasurement;
  selectedObjectIds: string[];
  showBlueprintView: boolean;
  onToggleBlueprintView: () => void;
  onToggleObject: (objectId: string) => void;
}) {
  return (
    <section className="rounded-[1.75rem] border border-line bg-white p-5 shadow-sm">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-moss">Image {image.imageIndex + 1}</p>
          <h2 className="mt-2 text-xl font-semibold text-ink">{image.imageName}</h2>
        </div>
        <div className="flex flex-col items-end gap-3 sm:flex-row sm:items-center">
          <div className="rounded-full bg-sand/50 px-4 py-2 text-sm text-ink/65">White-background object previews and background-only view</div>
          <button
            onClick={onToggleBlueprintView}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              showBlueprintView
                ? 'bg-cyan-500 text-white shadow-sm'
                : 'border border-cyan-300 text-cyan-700 hover:bg-cyan-50'
            }`}
          >
            {showBlueprintView ? '📐 Blueprint' : 'Cards'}
          </button>
        </div>
      </div>

      <p className="mt-3 text-xs uppercase tracking-[0.2em] text-ink/45">
        Calibration: {image.calibrationSource} · {image.pixelsPerCm.toFixed(2)} px/cm
      </p>

      {image.suggestedCalibration && (
        <div className="mt-5">
          <AutoCalibrationSuggestion
            detected={image.detectedReferenceObjects}
            suggested={image.suggestedCalibration}
            onSelectSuggestion={() => {}}
          />
        </div>
      )}

      {showBlueprintView ? (
        <div className="mt-5">
          {image.background.previewDataUrl && (
            <BlueprintView
              imageSrc={image.background.previewDataUrl}
              measurements={[image.background, ...image.objects]}
              pixelsPerCm={image.pixelsPerCm}
              title={`Blueprint: ${image.imageName}`}
            />
          )}
          <div className="mt-5 space-y-2">
            {image.objects.map((object) => (
              <label key={object.id} className="flex cursor-pointer items-center gap-3 rounded-lg border border-line bg-paper/35 p-3 transition hover:border-moss/45">
                <input type="checkbox" checked={selectedObjectIds.includes(object.id)} onChange={() => onToggleObject(object.id)} className="h-4 w-4 rounded border-line text-moss" />
                <span className="text-sm font-medium text-ink">{object.name}</span>
                <span className="ml-auto text-xs text-ink/65">{Math.round(object.confidence * 100)}%</span>
              </label>
            ))}
          </div>
        </div>
      ) : (
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <div className="rounded-3xl border border-line bg-paper/40 p-4">
            <p className="text-sm font-semibold text-ink">Background measurement</p>
            <MeasurementTile measurement={image.background} />
          </div>
          <div className="grid gap-3">
            {image.objects.map((object) => (
              <ObjectMeasurementCard
                key={object.id}
                object={object}
                checked={selectedObjectIds.includes(object.id)}
                onToggle={() => onToggleObject(object.id)}
              />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function ObjectMeasurementCard({
  object,
  checked,
  onToggle
}: {
  object: MeasurementObject;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <label className="flex cursor-pointer items-start gap-4 rounded-3xl border border-line bg-paper/35 p-4 transition hover:border-moss/45">
      <input type="checkbox" checked={checked} onChange={onToggle} className="mt-1 h-4 w-4 rounded border-line text-moss focus:ring-moss" />
      <div className="flex-1">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="font-semibold text-ink">{object.name}</p>
            <p className="text-xs uppercase tracking-[0.25em] text-ink/45">{object.previewLabel}</p>
          </div>
          <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-ink/65">{Math.round(object.confidence * 100)}%</span>
        </div>
        {object.previewDataUrl ? (
          <div className="mt-3 overflow-hidden rounded-2xl border border-line bg-white">
            <Image src={object.previewDataUrl} alt={`${object.name} preview`} width={420} height={260} unoptimized className="h-28 w-full object-contain" />
          </div>
        ) : null}
        <div className="mt-3 grid gap-3 text-sm md:grid-cols-3">
          <MeasurementStat label="Length" metric={object.length} />
          <MeasurementStat label="Width" metric={object.width} />
          <MeasurementStat label="Height" metric={object.height} />
        </div>
      </div>
    </label>
  );
}

function MeasurementTile({ measurement }: { measurement: MeasurementObject }) {
  return (
    <div className="mt-3 rounded-[1.5rem] border border-white/70 bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="font-semibold text-ink">{measurement.name}</p>
          <p className="text-xs uppercase tracking-[0.25em] text-ink/45">{measurement.previewLabel}</p>
        </div>
        <span className="rounded-full bg-sand px-3 py-1 text-xs font-semibold text-ink/60">Background</span>
      </div>
      {measurement.previewDataUrl ? (
        <div className="mt-3 overflow-hidden rounded-2xl border border-line bg-white">
          <Image src={measurement.previewDataUrl} alt="Background preview" width={420} height={260} unoptimized className="h-28 w-full object-cover" />
        </div>
      ) : null}
      <div className="mt-4 grid gap-3 text-sm md:grid-cols-3">
        <MeasurementStat label="Length" metric={measurement.length} />
        <MeasurementStat label="Width" metric={measurement.width} />
        <MeasurementStat label="Height" metric={measurement.height} />
      </div>
    </div>
  );
}

function MeasurementStat({ label, metric }: { label: string; metric: number }) {
  const formatted = formatMetricTriplet(metric);

  return (
    <div className="rounded-2xl bg-white px-3 py-2">
      <p className="text-[11px] uppercase tracking-[0.22em] text-ink/45">{label}</p>
      <div className="mt-1 space-y-0.5 font-semibold text-ink">
        <p>{formatted.mm}</p>
        <p className="text-ink/65">{formatted.cm}</p>
        <p className="text-ink/55">{formatted.m}</p>
      </div>
    </div>
  );
}

function EmptyResults() {
  return (
    <div className="rounded-[1.75rem] border border-dashed border-line bg-white/70 p-8 text-center">
      <ImagePlus className="mx-auto h-10 w-10 text-moss" />
      <h2 className="mt-4 font-[family-name:var(--font-space-grotesk)] text-2xl text-ink">Upload images to see measurements.</h2>
      <p className="mt-2 text-sm text-ink/60">After measurement runs, object cards and background summaries appear here for selection and saving.</p>
    </div>
  );
}

function LoadingState() {
  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="animate-pulse rounded-[2rem] border border-line bg-white px-8 py-6 text-ink/60 shadow-sm">Loading measurement workspace...</div>
    </main>
  );
}
