/**
 * Document upload component — file selector with document type dropdown.
 * After selecting a file, reads it as base64 and notifies the parent.
 */

import { useState, useCallback, useRef } from "react";
import { cn } from "@/lib/utils";
import { Upload, X, FileCheck } from "lucide-react";
import type { UploadedDocument } from "@/types";

const DOCUMENT_TYPES = [
  { value: "drivers_license", label: "Driver's License" },
  { value: "w2", label: "W-2 Form" },
  { value: "bank_statement", label: "Bank Statement" },
  { value: "pay_stub", label: "Pay Stub" },
  { value: "investment_statement", label: "Investment Statement" },
] as const;

interface DocumentUploadProps {
  onUpload: (doc: UploadedDocument) => void;
  disabled?: boolean;
}

export function DocumentUpload({ onUpload, disabled = false }: DocumentUploadProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedType, setSelectedType] = useState<string>("drivers_license");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, []);

  const handleUpload = useCallback(async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    try {
      const base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          // Strip "data:...;base64," prefix
          const b64 = result.includes(",") ? result.split(",")[1] : result;
          resolve(b64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(selectedFile);
      });

      const doc: UploadedDocument = {
        documentId: crypto.randomUUID(),
        documentType: selectedType,
        fileName: selectedFile.name,
        fileSize: selectedFile.size,
        base64Content: base64,
      };

      onUpload(doc);
      setSelectedFile(null);
      setIsOpen(false);
    } finally {
      setIsProcessing(false);
    }
  }, [selectedFile, selectedType, onUpload]);

  const handleCancel = useCallback(() => {
    setSelectedFile(null);
    setIsOpen(false);
  }, []);

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        disabled={disabled}
        className={cn(
          "flex items-center gap-1.5",
          "h-8 px-3 rounded-lg",
          "text-xs font-medium text-foreground/50",
          "border border-foreground/[0.08]",
          "hover:text-foreground/70 hover:bg-foreground/[0.03]",
          "hover:border-foreground/[0.12]",
          "active:scale-[0.97]",
          "transition-all duration-200",
          disabled && "opacity-50 cursor-not-allowed"
        )}
        aria-label="Upload document"
      >
        <Upload className="h-3.5 w-3.5" strokeWidth={1.5} />
        <span className="hidden sm:inline">Upload Doc</span>
      </button>
    );
  }

  return (
    <div
      className={cn(
        "fixed inset-0 z-50 flex items-center justify-center",
        "bg-black/40 backdrop-blur-sm",
        "animate-fade-in opacity-0"
      )}
      onClick={(e) => {
        if (e.target === e.currentTarget) handleCancel();
      }}
    >
      <div
        className={cn(
          "bg-background border border-foreground/[0.08] rounded-2xl",
          "shadow-[0_8px_30px_rgba(0,0,0,0.15)]",
          "w-full max-w-md mx-4 p-6",
          "animate-fade-in-up opacity-0"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-foreground">Upload Document</h2>
          <button
            onClick={handleCancel}
            className="text-foreground/40 hover:text-foreground/60 transition-colors"
            aria-label="Close"
          >
            <X className="h-5 w-5" strokeWidth={1.5} />
          </button>
        </div>

        {/* Document type selector */}
        <label className="block mb-4">
          <span className="text-sm font-medium text-foreground/60 mb-1.5 block">
            Document Type
          </span>
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className={cn(
              "w-full h-10 px-3 rounded-lg",
              "bg-foreground/[0.03] border border-foreground/[0.08]",
              "text-sm text-foreground",
              "focus:outline-none focus:border-primary/30",
              "transition-colors"
            )}
          >
            {DOCUMENT_TYPES.map((dt) => (
              <option key={dt.value} value={dt.value}>
                {dt.label}
              </option>
            ))}
          </select>
        </label>

        {/* File input area */}
        <div className="mb-5">
          {selectedFile ? (
            <div
              className={cn(
                "flex items-center gap-3 p-4 rounded-xl",
                "bg-primary/[0.04] border border-primary/15"
              )}
            >
              <FileCheck className="h-5 w-5 text-primary flex-shrink-0" strokeWidth={1.5} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {selectedFile.name}
                </p>
                <p className="text-xs text-foreground/40">
                  {(selectedFile.size / 1024).toFixed(1)} KB
                </p>
              </div>
              <button
                onClick={() => setSelectedFile(null)}
                className="text-foreground/30 hover:text-foreground/60 transition-colors"
              >
                <X className="h-4 w-4" strokeWidth={1.5} />
              </button>
            </div>
          ) : (
            <label
              className={cn(
                "flex flex-col items-center gap-2 p-8 rounded-xl cursor-pointer",
                "border-2 border-dashed border-foreground/[0.08]",
                "hover:border-primary/20 hover:bg-primary/[0.01]",
                "transition-all duration-200"
              )}
            >
              <Upload className="h-8 w-8 text-foreground/20" strokeWidth={1.5} />
              <span className="text-sm text-foreground/40">
                Click to select or drag & drop
              </span>
              <span className="text-xs text-foreground/25">
                PDF, JPG, PNG, TIFF (max 10 MB)
              </span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.jpg,.jpeg,.png,.tiff,.bmp"
                onChange={handleFileSelect}
                className="hidden"
              />
            </label>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <button
            onClick={handleCancel}
            className={cn(
              "flex-1 h-10 rounded-xl",
              "text-sm font-medium text-foreground/50",
              "border border-foreground/[0.08]",
              "hover:bg-foreground/[0.03]",
              "transition-all duration-200"
            )}
          >
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!selectedFile || isProcessing}
            className={cn(
              "flex-1 h-10 rounded-xl",
              "text-sm font-medium",
              "transition-all duration-200",
              selectedFile && !isProcessing
                ? "bg-primary text-primary-foreground hover:bg-primary/90 active:scale-[0.98]"
                : "bg-foreground/[0.06] text-foreground/20 cursor-not-allowed"
            )}
          >
            {isProcessing ? "Processing…" : "Upload & Attach"}
          </button>
        </div>
      </div>
    </div>
  );
}
