"use client";

import { ExternalLinkIcon, FileUpIcon, InfoIcon, KeyRoundIcon, Loader2Icon, PlayIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";

import { BenchmarkBanner } from "@/components/benchmark-banner";
import { ResultCard } from "@/components/result-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { sampleReviews } from "@/lib/samples";
import type { ClassificationResult } from "@/lib/types";

const BULK_LIMIT = 10;

async function postJson(path: string, payload: unknown) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data?.error ?? "Request failed");
  }
  return data;
}

export default function Home() {
  const [selectedId, setSelectedId] = useState(sampleReviews[2].id);
  const selected = useMemo(
    () => sampleReviews.find((sample) => sample.id === selectedId) ?? sampleReviews[0],
    [selectedId]
  );
  const [text, setText] = useState(selected.text);
  const [gemini, setGemini] = useState<ClassificationResult | null>(null);
  const [baseline, setBaseline] = useState<ClassificationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [error, setError] = useState("");
  const [apiKey, setApiKey] = useState(() =>
    typeof window === "undefined" ? "" : window.localStorage.getItem("gemini-api-key") ?? ""
  );
  const [bulkText, setBulkText] = useState("");
  const [bulkFileName, setBulkFileName] = useState("");
  const [bulkResults, setBulkResults] = useState<Array<{ text: string; result: ClassificationResult }>>([]);

  function pickSample(value: string | null) {
    if (!value) return;
    const sample = sampleReviews.find((item) => item.id === value);
    if (!sample) return;
    setSelectedId(value);
    setText(sample.text);
    setGemini(null);
    setBaseline(null);
    setError("");
  }

  async function classify() {
    setLoading(true);
    setError("");
    const matchingSample = sampleReviews.find((sample) => sample.text === text);
    const payload = { id: matchingSample?.id, text, apiKey: apiKey || undefined };
    try {
      const [geminiResult, baselineResult] = await Promise.all([
        postJson("/api/classify", payload),
        postJson("/api/baseline", payload),
      ]);
      setGemini(geminiResult);
      setBaseline(baselineResult);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Classification failed");
    } finally {
      setLoading(false);
    }
  }

  function bulkRows() {
    return bulkText
      .split(/\r?\n/)
      .map((line) => line.trim())
      .filter(Boolean);
  }

  async function processBulk() {
    const rows = bulkRows();
    if (rows.length === 0) {
      toast.warning("Add at least one review");
      return;
    }
    if (rows.length > BULK_LIMIT) {
      toast.error(`This demo processes up to ${BULK_LIMIT} reviews at a time. Your file has ${rows.length}.`);
      return;
    }
    setBulkLoading(true);
    const toastId = toast.loading(`Processing ${rows.length} reviews with the LLM`);
    try {
      const processed: Array<{ text: string; result: ClassificationResult }> = [];
      for (const [index, review] of rows.entries()) {
        const result = await postJson("/api/classify", {
          id: `bulk-${index + 1}`,
          text: review,
          apiKey: apiKey || undefined,
        });
        processed.push({ text: review, result });
      }
      setBulkResults(processed);
      toast.success("Bulk run complete", { id: toastId });
    } catch (requestError) {
      toast.error(requestError instanceof Error ? requestError.message : "Bulk processing failed", {
        id: toastId,
      });
    } finally {
      setBulkLoading(false);
    }
  }

  async function loadFile(file: File | null) {
    if (!file) return;
    const textFromFile = await file.text();
    setBulkText(textFromFile);
    setBulkFileName(file.name);
    const count = textFromFile.split(/\r?\n/).map((line) => line.trim()).filter(Boolean).length;
    if (count > BULK_LIMIT) {
      toast.warning(`Loaded ${count} reviews. Trim to ${BULK_LIMIT} before processing.`);
    } else {
      toast.info(`Loaded ${count} reviews`);
    }
  }

  const bulkCount = bulkRows().length;

  return (
    <main className="min-h-screen bg-background">
      <div className="mx-auto flex w-full max-w-[1200px] flex-col gap-10 px-5 py-6 md:px-8 md:py-8">
        <header className="sticky top-0 z-20 -mx-5 flex flex-wrap items-center justify-between gap-4 border-b border-border/70 bg-background/90 px-5 py-3 backdrop-blur md:-mx-8 md:px-8">
          <div className="flex items-center gap-3">
            <span className="inline-flex size-3 rounded-full bg-primary" />
            <span className="text-lg font-medium">review classifier</span>
          </div>
          <div className="flex flex-wrap gap-2">
            <Dialog>
              <DialogTrigger render={<Button variant="outline" />}>
                <InfoIcon data-icon="inline-start" />
                How this works
              </DialogTrigger>
              <DialogContent className="sm:max-w-xl">
                <DialogHeader>
                  <DialogTitle>What the demo is doing</DialogTitle>
                  <DialogDescription>
                    It compares two ways of reading app-store reviews.
                  </DialogDescription>
                </DialogHeader>
                <div className="flex flex-col gap-4 text-sm leading-6 text-muted-foreground">
                  <p>
                    The LLM reads the review and returns structured JSON: sentiment,
                    product areas mentioned, improvement signals, confidence, and a
                    short rationale.
                  </p>
                  <p>
                    The baseline is simpler: a traditional sentiment model plus
                    keyword rules for topics like support, fees, login, transfers,
                    and security.
                  </p>
                  <p>
                    The numbers at the top show how each method performs against the
                    current labelled sample. The sample is built from public app-store
                    reviews, but its labels still need human review before being used
                    as final accuracy claims.
                  </p>
                </div>
              </DialogContent>
            </Dialog>
            <Dialog>
              <DialogTrigger render={<Button variant="outline" />}>
                <KeyRoundIcon data-icon="inline-start" />
                Gemini key
              </DialogTrigger>
              <DialogContent className="sm:max-w-xl">
                <DialogHeader>
                  <DialogTitle>Use your own Gemini key</DialogTitle>
                  <DialogDescription>
                    Optional for local testing. The key is saved in this browser and sent only with classification requests.
                  </DialogDescription>
                </DialogHeader>
                <div className="flex flex-col gap-3">
                  <label className="text-sm font-medium" htmlFor="gemini-key">
                    API key
                  </label>
                  <Input
                    id="gemini-key"
                    value={apiKey}
                    onChange={(event) => setApiKey(event.target.value)}
                    type="password"
                    placeholder="Paste a Gemini API key"
                  />
                  <div className="flex flex-wrap gap-2">
                    <Button
                      onClick={() => {
                        window.localStorage.setItem("gemini-api-key", apiKey.trim());
                      }}
                    >
                      Save key
                    </Button>
                    <Button
                      variant="outline"
                      onClick={() => {
                        window.localStorage.removeItem("gemini-api-key");
                        setApiKey("");
                      }}
                    >
                      Clear
                    </Button>
                  </div>
                  <p className="text-sm leading-6 text-muted-foreground">
                    For deployed demos, prefer a server-side `GEMINI_API_KEY` environment variable so visitors do not need to provide their own key.
                  </p>
                </div>
              </DialogContent>
            </Dialog>
          </div>
        </header>

        <BenchmarkBanner />

        <section className="grid gap-8 lg:grid-cols-[minmax(320px,420px)_minmax(0,1fr)]">
          <div className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium" htmlFor="sample-review">
                Try a real review
              </label>
              <Select value={selectedId} onValueChange={pickSample}>
                <SelectTrigger id="sample-review" className="w-full">
                  <SelectValue>{selected.label}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    {sampleReviews.map((sample) => (
                      <SelectItem key={sample.id} value={sample.id}>
                        {sample.label}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-2">
              <label className="text-sm font-medium" htmlFor="review-text">
                Review text
              </label>
              <Textarea
                id="review-text"
                value={text}
                onChange={(event) => setText(event.target.value)}
                className="min-h-56 resize-none"
              />
            </div>

            {error ? <p className="text-sm text-destructive">{error}</p> : null}

            <Button onClick={classify} disabled={loading || !text.trim()} className="w-full">
              {loading ? (
                <Loader2Icon data-icon="inline-start" className="animate-spin" />
              ) : (
                <PlayIcon data-icon="inline-start" />
              )}
              {loading ? "Classifying" : "Classify review"}
            </Button>
          </div>

          <div className="grid gap-4 xl:grid-cols-2">
            <ResultCard
              title="LLM"
              subtitle="Structured app-review analysis"
              result={gemini}
              loading={loading}
            />
            <ResultCard
              title="Baseline"
              subtitle="Traditional sentiment plus topic rules"
              result={baseline}
              loading={loading}
            />
          </div>
        </section>

        <section className="flex flex-col gap-4 border-t pt-8">
          <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 className="text-2xl font-semibold">Bulk review processing</h2>
              <p className="mt-1 max-w-3xl text-sm leading-6 text-muted-foreground">
                Paste one review per line or upload a text/CSV file. This demo runs the LLM path for
                up to {BULK_LIMIT} reviews at a time. The traditional Python baseline still runs from
                `baseline.py`, not in the browser.
              </p>
            </div>
            <Badge variant="outline" className="w-fit rounded-full">
              LLM only in web demo
            </Badge>
          </div>
          <div className="grid gap-4 lg:grid-cols-[minmax(320px,420px)_minmax(0,1fr)]">
            <div className="flex flex-col gap-3">
              <Input
                type="file"
                accept=".txt,.csv,.jsonl"
                onChange={(event) => loadFile(event.target.files?.[0] ?? null)}
              />
              <div className="rounded-2xl bg-card p-4 shadow-[var(--shadow-fire-card)]">
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium">
                        {bulkFileName || "Paste reviews below"}
                      </p>
                      <p className="text-sm text-muted-foreground">
                        {bulkCount} review{bulkCount === 1 ? "" : "s"} loaded. Limit: {BULK_LIMIT}.
                      </p>
                    </div>
                    <Dialog>
                      <DialogTrigger render={<Button variant="outline" disabled={!bulkText} />}>
                        Preview content
                      </DialogTrigger>
                      <DialogContent className="sm:max-w-3xl">
                        <DialogHeader>
                          <DialogTitle>Bulk input preview</DialogTitle>
                          <DialogDescription>
                            One non-empty line is treated as one review.
                          </DialogDescription>
                        </DialogHeader>
                        <div className="max-h-[60vh] overflow-auto rounded-lg border bg-background p-3 font-mono text-xs leading-5">
                          {bulkText || "No content loaded."}
                        </div>
                        <DialogFooter showCloseButton />
                      </DialogContent>
                    </Dialog>
                  </div>
                  {bulkCount > BULK_LIMIT ? (
                    <p className="rounded-lg border border-primary/40 bg-accent px-3 py-2 text-sm">
                      Too many reviews for the web demo. Keep the first {BULK_LIMIT}, split the file, or run
                      the Python pipeline for larger batches.
                    </p>
                  ) : null}
                </div>
              </div>
              <Textarea
                value={bulkText}
                onChange={(event) => {
                  setBulkText(event.target.value);
                  setBulkFileName("");
                }}
                placeholder="Paste one review per line"
                className="max-h-48 min-h-32 resize-y overflow-auto"
              />
              <Button onClick={processBulk} disabled={bulkLoading || bulkCount === 0 || bulkCount > BULK_LIMIT}>
                {bulkLoading ? (
                  <Loader2Icon data-icon="inline-start" className="animate-spin" />
                ) : (
                  <FileUpIcon data-icon="inline-start" />
                )}
                Process {bulkCount > BULK_LIMIT ? `up to ${BULK_LIMIT}` : bulkCount || ""} reviews
              </Button>
            </div>
            <div className="rounded-2xl bg-card p-3 shadow-[var(--shadow-fire-card)]">
              {bulkResults.length === 0 ? (
                <p className="p-3 text-sm text-muted-foreground">
                  Bulk results will appear here after processing.
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Review</TableHead>
                      <TableHead>Sentiment</TableHead>
                      <TableHead>Areas</TableHead>
                      <TableHead>Confidence</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {bulkResults.map(({ text: review, result }, index) => (
                      <TableRow key={`${review}-${index}`}>
                        <TableCell className="max-w-80 whitespace-normal leading-6">
                          {review}
                        </TableCell>
                        <TableCell>
                          <Badge className="rounded-full">{result.primary_label}</Badge>
                        </TableCell>
                        <TableCell className="max-w-56 whitespace-normal">
                          <div className="flex flex-wrap gap-1">
                            {result.aspects.map((aspect) => (
                              <Badge key={aspect} variant="secondary" className="rounded-full">
                                {aspect}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>{Math.round(result.confidence * 100)}%</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </div>
          </div>
        </section>

        <footer className="flex flex-col gap-2 border-t py-5 text-sm text-muted-foreground md:flex-row md:items-center md:justify-between">
          <span>Open demo repository for the app-review classifier.</span>
          <a
            href="https://github.com/tamas-j/llm-classifier"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 font-medium text-foreground"
          >
            <ExternalLinkIcon data-icon="inline-start" />
            GitHub
          </a>
        </footer>
      </div>
    </main>
  );
}
