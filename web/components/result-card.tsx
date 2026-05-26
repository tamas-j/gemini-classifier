"use client";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { ClassificationResult } from "@/lib/types";

type ResultCardProps = {
  title: string;
  subtitle: string;
  result?: ClassificationResult | null;
  loading?: boolean;
};

const labelText: Record<string, string> = {
  very_negative: "Very negative",
  negative: "Negative",
  neutral: "Neutral",
  positive: "Positive",
  very_positive: "Very positive",
};

const sentimentVariant: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  very_negative: "outline",
  negative: "outline",
  neutral: "outline",
  positive: "default",
  very_positive: "default",
};

export function ResultCard({ title, subtitle, result, loading }: ResultCardProps) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-56" />
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Skeleton className="h-12 w-full" />
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-16 w-full" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle>{title}</CardTitle>
            <CardDescription>{subtitle}</CardDescription>
          </div>
          {result?.method ? (
            <Badge variant="outline" className="rounded-full font-mono">
              {result.method}
            </Badge>
          ) : null}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {!result ? (
          <p className="text-sm text-muted-foreground">Run a review to see this result.</p>
        ) : result.unavailableReason ? (
          <p className="text-sm text-muted-foreground">{result.unavailableReason}</p>
        ) : (
          <>
            <div className="grid gap-3 sm:grid-cols-3">
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Sentiment
                </p>
                <Badge
                  variant={sentimentVariant[result.primary_label] ?? "secondary"}
                  className="mt-2 rounded-full"
                >
                  {labelText[result.primary_label] ?? result.primary_label}
                </Badge>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Confidence
                </p>
                <p className="mt-1 text-2xl font-semibold">
                  {Math.round(result.confidence * 100)}%
                </p>
              </div>
              <div>
                <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Language
                </p>
                <p className="mt-1 text-2xl font-semibold">{result.language}</p>
              </div>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Product areas mentioned
              </p>
              <div className="mt-2 flex flex-wrap gap-2">
                {result.aspects.map((aspect) => (
                  <Badge key={aspect} variant="secondary" className="rounded-full">
                    {aspect}
                  </Badge>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Improvement signals
              </p>
              {result.improvement_signals.length > 0 ? (
                <ul className="mt-2 flex list-disc flex-col gap-1 pl-5 text-sm leading-6">
                  {result.improvement_signals.map((signal) => (
                    <li key={signal}>{signal}</li>
                  ))}
                </ul>
              ) : (
                <p className="mt-2 text-sm text-muted-foreground">
                  No concrete improvement request found.
                </p>
              )}
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Why
              </p>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">{result.rationale}</p>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
