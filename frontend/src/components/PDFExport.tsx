"use client";

import { useCallback, useState } from "react";

interface PDFExportProps {
  /** CSS selector for the element to print/export */
  targetSelector?: string;
  /** Custom filename for the exported PDF */
  filename?: string;
}

/**
 * Client-side PDF export via browser print-to-PDF.
 *
 * For a true server-side PDF, the backend would use WeasyPrint or ReportLab.
 * This component uses the browser's native print functionality with optimized
 * print CSS for a polished PDF output.
 */
export default function PDFExport({
  targetSelector = "#report-content",
  filename = "LabSafe_Report.pdf",
}: PDFExportProps) {
  const [exporting, setExporting] = useState(false);

  const handleExport = useCallback(() => {
    setExporting(true);

    // Set the document title for PDF filename
    const originalTitle = document.title;
    document.title = filename.replace(".pdf", "");

    // Trigger print (user can save as PDF in print dialog)
    window.print();

    // Restore title after print dialog opens
    setTimeout(() => {
      document.title = originalTitle;
      setExporting(false);
    }, 500);
  }, [filename]);

  return (
    <button
      onClick={handleExport}
      disabled={exporting}
      className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
      aria-label={exporting ? "准备打印..." : "打印或导出PDF报告"}
    >
      {exporting ? "⏳ 准备中..." : "🖨 打印报告"}
    </button>
  );
}
