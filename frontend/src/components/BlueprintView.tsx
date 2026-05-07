'use client';

import { useEffect, useRef } from 'react';
import type { MeasurementObject } from '@/lib/api';

interface BlueprintViewProps {
  imageSrc: string;
  measurements: MeasurementObject[];
  pixelsPerCm: number;
  title?: string;
}

function formatMeasurement(valueCm: number): string {
  return `${valueCm.toFixed(1)} cm`;
}

export function BlueprintView({
  imageSrc,
  measurements,
  pixelsPerCm,
  title = 'Measurement Blueprint'
}: BlueprintViewProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const displayMeasurements = measurements.slice(0, 5);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const img = new Image();
    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;

      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      // Draw the image
      ctx.drawImage(img, 0, 0);

      // Apply blueprint styling
      ctx.globalAlpha = 0.95;
      ctx.fillStyle = 'rgba(230, 245, 255, 0.08)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.globalAlpha = 1;

      // Draw dimension annotations for each measurement
      displayMeasurements.forEach((measurement, index) => {
        drawMeasurementAnnotations(ctx, measurement, pixelsPerCm, index);
      });

      // Draw grid
      drawBlueprintGrid(ctx, canvas.width, canvas.height, pixelsPerCm);
    };

    img.crossOrigin = 'anonymous';
    img.src = imageSrc;
  }, [imageSrc, displayMeasurements, pixelsPerCm]);

  return (
    <div ref={containerRef} className="relative w-full overflow-auto rounded-2xl border-2 border-slate-300 bg-slate-50">
      <div className="absolute right-4 top-4 z-10 rounded-lg bg-slate-900/80 px-3 py-2 text-xs font-mono text-cyan-300 backdrop-blur-sm">
        {title}
      </div>
      <canvas
        ref={canvasRef}
        className="w-full border-b border-slate-300"
        style={{ maxHeight: '600px', objectFit: 'contain' }}
      />
      <div className="space-y-2 border-t border-slate-300 bg-slate-100 p-4 text-xs font-mono">
        {displayMeasurements.map((measurement, idx) => (
          <div key={idx} className="flex items-center justify-between gap-4 text-slate-700">
            <span className="text-slate-600">
              {measurement.name}:
            </span>
            <div className="flex gap-6">
              <span>L: <span className="font-semibold text-slate-900">{formatMeasurement(measurement.length)}</span></span>
              <span>W: <span className="font-semibold text-slate-900">{formatMeasurement(measurement.width)}</span></span>
              <span>H: <span className="font-semibold text-slate-900">{formatMeasurement(measurement.height)}</span></span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function drawBlueprintGrid(ctx: CanvasRenderingContext2D, width: number, height: number, pixelsPerCm: number) {
  const gridSize = pixelsPerCm * 5; // 5cm grid
  ctx.strokeStyle = 'rgba(100, 150, 200, 0.1)';
  ctx.lineWidth = 1;

  // Vertical lines
  for (let x = 0; x < width; x += gridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  // Horizontal lines
  for (let y = 0; y < height; y += gridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  // Major grid lines (every 50cm)
  const majorGridSize = pixelsPerCm * 50;
  ctx.strokeStyle = 'rgba(100, 150, 200, 0.15)';
  ctx.lineWidth = 2;

  for (let x = 0; x < width; x += majorGridSize) {
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, height);
    ctx.stroke();
  }

  for (let y = 0; y < height; y += majorGridSize) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
}

function drawMeasurementAnnotations(
  ctx: CanvasRenderingContext2D,
  measurement: MeasurementObject,
  pixelsPerCm: number,
  index: number
) {
  const offsetX = 20;
  const offsetY = 40 + index * 80;
  const boxWidth = 280;
  const boxHeight = 70;

  // Draw semi-transparent background box
  ctx.fillStyle = 'rgba(15, 23, 42, 0.75)';
  ctx.strokeStyle = 'rgba(100, 150, 200, 0.8)';
  ctx.lineWidth = 2;
  ctx.fillRect(offsetX, offsetY, boxWidth, boxHeight);
  ctx.strokeRect(offsetX, offsetY, boxWidth, boxHeight);

  // Draw technical drawing symbols
  drawDimensionLineCorners(ctx, offsetX, offsetY, boxWidth, boxHeight);

  // Title
  ctx.font = 'bold 13px "Courier New", monospace';
  ctx.fillStyle = 'rgba(34, 197, 94, 0.9)';
  ctx.fillText(measurement.name, offsetX + 10, offsetY + 18);

  // Dimensions with labels
  ctx.font = '11px "Courier New", monospace';
  ctx.fillStyle = 'rgba(100, 200, 255, 0.9)';

  const dims = [
    { label: 'Length', value: measurement.length },
    { label: 'Width', value: measurement.width },
    { label: 'Height', value: measurement.height }
  ];

  dims.forEach((dim, i) => {
    const y = offsetY + 35 + i * 13;
    ctx.fillText(`${dim.label}:`, offsetX + 10, y);
    ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
    ctx.fillText(`${dim.value.toFixed(2)} cm`, offsetX + 95, y);
    ctx.fillStyle = 'rgba(100, 200, 255, 0.9)';
  });
}

function drawDimensionLineCorners(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number
) {
  const cornerSize = 8;
  ctx.strokeStyle = 'rgba(100, 150, 200, 0.6)';
  ctx.lineWidth = 1.5;

  // Top-left
  ctx.beginPath();
  ctx.moveTo(x, y + cornerSize);
  ctx.lineTo(x, y);
  ctx.lineTo(x + cornerSize, y);
  ctx.stroke();

  // Top-right
  ctx.beginPath();
  ctx.moveTo(x + w - cornerSize, y);
  ctx.lineTo(x + w, y);
  ctx.lineTo(x + w, y + cornerSize);
  ctx.stroke();

  // Bottom-left
  ctx.beginPath();
  ctx.moveTo(x, y + h - cornerSize);
  ctx.lineTo(x, y + h);
  ctx.lineTo(x + cornerSize, y + h);
  ctx.stroke();

  // Bottom-right
  ctx.beginPath();
  ctx.moveTo(x + w - cornerSize, y + h);
  ctx.lineTo(x + w, y + h);
  ctx.lineTo(x + w, y + h - cornerSize);
  ctx.stroke();
}
