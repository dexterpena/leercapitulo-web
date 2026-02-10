import { useState, useEffect, useCallback } from "react";
import { imageProxyUrl } from "../lib/api";

interface Props {
  images: string[];
  onPageChange?: (page: number) => void;
}

export default function ReaderViewer({ images, onPageChange }: Props) {
  const [currentPage, setCurrentPage] = useState(0);

  const goTo = useCallback(
    (page: number) => {
      const clamped = Math.max(0, Math.min(page, images.length - 1));
      setCurrentPage(clamped);
      onPageChange?.(clamped);
    },
    [images.length, onPageChange]
  );

  const prev = useCallback(() => goTo(currentPage - 1), [currentPage, goTo]);
  const next = useCallback(() => goTo(currentPage + 1), [currentPage, goTo]);

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "ArrowLeft") prev();
      else if (e.key === "ArrowRight" || e.key === " ") next();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [prev, next]);

  if (!images.length) {
    return <div className="reader-empty">No pages found for this chapter.</div>;
  }

  return (
    <div className="reader-viewer">
      <div className="reader-image-container" onClick={next}>
        <img
          src={imageProxyUrl(images[currentPage])}
          alt={`Page ${currentPage + 1}`}
          className="reader-image"
        />
      </div>
      <div className="reader-controls">
        <button onClick={prev} disabled={currentPage === 0}>
          Prev
        </button>
        <select
          className="reader-page-select"
          value={currentPage}
          onChange={(e) => goTo(Number(e.target.value))}
        >
          {images.map((_, i) => (
            <option key={i} value={i}>
              Page {i + 1}
            </option>
          ))}
        </select>
        <span className="reader-page-info">
          {currentPage + 1} / {images.length}
        </span>
        <button onClick={next} disabled={currentPage === images.length - 1}>
          Next
        </button>
      </div>
    </div>
  );
}
