import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { benchmarkReport } from "@/lib/benchmark-report";

function pct(value: number) {
  return `${Math.round(value * 100)}%`;
}

function plainScore(value: number) {
  return Math.round(value * 100);
}

export function BenchmarkBanner() {
  const { gemini, baseline } = benchmarkReport.pipelines;

  return (
    <section className="flex flex-col gap-6 border-b border-border pb-10">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center gap-2">
          <Badge>Real public reviews</Badge>
          <Badge variant="secondary">{benchmarkReport.n} checked examples</Badge>
          <Badge variant="outline">Bootstrap labels</Badge>
        </div>
        <h1 className="max-w-5xl text-[40px] font-medium leading-[1.1] md:text-[60px] md:leading-none">
          LLM-based vs traditional NLP classifier
        </h1>
        <p className="max-w-3xl text-base leading-[1.6] text-muted-foreground">
          Paste a finance app review and compare an LLM classifier with a simpler
          keyword-based baseline. The demo extracts sentiment, product areas, and
          concrete improvement signals.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-2xl bg-card p-4 shadow-[var(--shadow-fire-card)]">
          <p className="text-sm text-muted-foreground">Sentiment calls matched</p>
          <div className="mt-3 flex items-end justify-between gap-4">
            <span className="text-[40px] font-medium leading-none">{pct(gemini.sentimentAccuracy)}</span>
            <Badge>LLM</Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Baseline: {pct(baseline.sentimentAccuracy)}
          </p>
        </div>
        <div className="rounded-2xl bg-card p-4 shadow-[var(--shadow-fire-card)]">
          <p className="text-sm text-muted-foreground">Topic extraction score</p>
          <div className="mt-3 flex items-end justify-between gap-4">
            <span className="text-[40px] font-medium leading-none">{plainScore(gemini.aspectF1)}</span>
            <Badge>LLM</Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            Baseline: {plainScore(baseline.aspectF1)} out of 100
          </p>
        </div>
        <div className="rounded-2xl bg-card p-4 shadow-[var(--shadow-fire-card)]">
          <p className="text-sm text-muted-foreground">Dataset in this demo</p>
          <div className="mt-3 flex items-end justify-between gap-4">
            <span className="text-[40px] font-medium leading-none">1,350</span>
            <Badge variant="secondary">reviews</Badge>
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            100 examples are used for the current benchmark view.
          </p>
        </div>
      </div>

      <Alert>
        <AlertTitle>What these numbers mean</AlertTitle>
        <AlertDescription>
          Matched means the classifier agreed with the current review labels.
          Topic score summarizes how well it found areas like fees, login,
          transfers, support, or security. These labels are bootstrap labels from
          the archived pipeline, so they are useful for the demo flow but should be
          human-reviewed before making final accuracy claims.
        </AlertDescription>
      </Alert>
    </section>
  );
}
