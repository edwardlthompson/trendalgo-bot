import {
  fetchOhlcvWarmupActive,
  startOhlcvWarmup,
  type OhlcvWarmupJob,
} from "../api/client";
import { createOhlcvWarmupDialog } from "./ohlcvWarmupDialog";

const POLL_MS = 450;

let activePoll: ReturnType<typeof setInterval> | null = null;

function stopPoll(): void {
  if (activePoll != null) {
    clearInterval(activePoll);
    activePoll = null;
  }
}

function pollWarmup(
  onUpdate: (job: OhlcvWarmupJob) => void,
  onDone?: () => void,
): void {
  stopPoll();
  activePoll = setInterval(() => {
    void fetchOhlcvWarmupActive().then((next) => {
      onUpdate(next);
      if (next.status === "complete" || next.status === "error" || next.status === "idle") {
        stopPoll();
        onDone?.();
      }
    });
  }, POLL_MS);
}

/** Start bot-scoped OHLCV warmup and show a verbose progress dialog while downloading. */
export async function runOhlcvWarmupWithUi(opts?: { silentIfCached?: boolean }): Promise<void> {
  stopPoll();

  let job: OhlcvWarmupJob;
  try {
    job = await startOhlcvWarmup();
  } catch {
    return;
  }

  if (opts?.silentIfCached && job.status === "complete" && (job.bars_downloaded ?? 0) === 0) {
    return;
  }

  if (job.status === "idle") {
    const existing = await fetchOhlcvWarmupActive();
    if (existing.status === "idle") return;
    job = existing;
  }

  if (opts?.silentIfCached) {
    if (job.status === "complete" || job.status === "error") {
      return;
    }
    pollWarmup(() => undefined);
    return;
  }

  const dialog = createOhlcvWarmupDialog();
  dialog.update(job);

  if (job.status === "complete" || job.status === "error") {
    dialog.close();
    return;
  }

  pollWarmup(
    (next) => dialog.update(next),
    () => {
      void fetchOhlcvWarmupActive().then((next) => {
        dialog.update(next);
        if (next.status === "complete" || next.status === "error") {
          dialog.close();
        }
      });
    },
  );
}

export function stopOhlcvWarmupPoll(): void {
  stopPoll();
}
