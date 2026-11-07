import { Logger, OnApplicationBootstrap, OnModuleDestroy } from '@nestjs/common';
import { AccountEventSender, DeliveryStore, PendingDelivery } from './account-events';

export interface DispatcherOptions {
  /** Cada cuánto busca entregas vencidas (también reintenta las que fallaron). */
  intervalMs: number;
  batchSize: number;
  /** Cuánto tiempo queda reservada una entrega mientras se envía. */
  leaseMs: number;
  /** Primer reintento; después se duplica hasta `maxDelayMs`. */
  baseDelayMs: number;
  maxDelayMs: number;
}

export interface DispatchSummary {
  delivered: number;
  failed: number;
}

const positive = (raw: string | undefined, fallback: number): number => {
  const value = Number(raw);
  return Number.isFinite(value) && value > 0 ? value : fallback;
};

export function dispatcherOptionsFromEnv(env = process.env): DispatcherOptions {
  return {
    intervalMs: positive(env.ACCOUNT_EVENT_RETRY_INTERVAL_MS, 5_000),
    batchSize: 50,
    leaseMs: 60_000,
    baseDelayMs: positive(env.ACCOUNT_EVENT_RETRY_BASE_MS, 5_000),
    maxDelayMs: positive(env.ACCOUNT_EVENT_RETRY_MAX_MS, 10 * 60_000),
  };
}

/** Espera antes del intento `attempt` (1 = primer reintento): exponencial con tope. */
export function retryDelayMs(attempt: number, options: DispatcherOptions): number {
  const exponent = Math.min(Math.max(attempt - 1, 0), 30);
  return Math.min(options.baseDelayMs * 2 ** exponent, options.maxDelayMs);
}

/**
 * Entrega los eventos del outbox con semántica "al menos una vez": reintenta sin límite
 * (con backoff) hasta que el suscriptor responde 2xx. Los receptores son idempotentes.
 * Corre después de cada commit (`trigger`) y cada `intervalMs`.
 */
export class AccountEventDispatcher implements OnApplicationBootstrap, OnModuleDestroy {
  private readonly logger = new Logger(AccountEventDispatcher.name);
  private timer?: NodeJS.Timeout;
  private running?: Promise<DispatchSummary>;
  private rerun = false;

  constructor(
    private readonly store: DeliveryStore,
    private readonly sender: AccountEventSender,
    private readonly options: DispatcherOptions,
    private readonly now: () => Date = () => new Date(),
  ) {}

  onApplicationBootstrap(): void {
    this.timer = setInterval(() => this.trigger(), this.options.intervalMs);
    this.timer.unref();
    this.trigger();
  }

  onModuleDestroy(): void {
    if (this.timer) clearInterval(this.timer);
  }

  /** Pide una corrida sin esperarla. Si ya hay una en curso, se repite al terminar. */
  trigger(): void {
    void this.run().catch((error: unknown) =>
      this.logger.error(
        `No se pudo leer el outbox de eventos: ${error instanceof Error ? error.message : String(error)}`,
      ),
    );
  }

  /** Corre hasta vaciar lo vencido. Devuelve cuántas entregas salieron y cuántas fallaron. */
  async run(): Promise<DispatchSummary> {
    if (this.running) {
      this.rerun = true;
      return this.running;
    }
    this.running = this.drain();
    try {
      return await this.running;
    } finally {
      this.running = undefined;
      if (this.rerun) {
        this.rerun = false;
        this.trigger();
      }
    }
  }

  private async drain(): Promise<DispatchSummary> {
    const summary: DispatchSummary = { delivered: 0, failed: 0 };
    for (;;) {
      const batch = await this.store.claimDue(this.options.batchSize, this.options.leaseMs);
      // Cada entrega del lote es de un (suscriptor, usuario) distinto: se pueden mandar juntas.
      const results = await Promise.all(batch.map((delivery) => this.deliver(delivery)));
      for (const ok of results) {
        if (ok) summary.delivered += 1;
        else summary.failed += 1;
      }
      // Sigue si el lote vino lleno o si alguna entrega salió (puede haber habilitado la
      // siguiente del mismo usuario). Las fallidas quedan para más tarde: no se repiten acá.
      if (batch.length < this.options.batchSize && !results.some(Boolean)) return summary;
    }
  }

  private async deliver(delivery: PendingDelivery): Promise<boolean> {
    try {
      await this.sender.send(delivery.subscriber, delivery.payload);
      await this.store.markDelivered(delivery.id);
      if (delivery.attempts > 0) {
        this.logger.log(
          `${delivery.payload.event} ${delivery.payload.event_id} → ${delivery.subscriber} entregado al intento ${delivery.attempts + 1}`,
        );
      }
      return true;
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      const attempt = delivery.attempts + 1;
      const next = new Date(this.now().getTime() + retryDelayMs(attempt, this.options));
      await this.store.markFailed(delivery.id, message, next);
      this.logger.warn(
        `${delivery.payload.event} ${delivery.payload.event_id} → ${delivery.subscriber} falló (intento ${attempt}): ${message}. Reintenta ${next.toISOString()}`,
      );
      return false;
    }
  }
}
