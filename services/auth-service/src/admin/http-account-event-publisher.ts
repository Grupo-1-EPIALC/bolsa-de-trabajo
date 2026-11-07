import { Injectable, Logger } from '@nestjs/common';
import { AccountEvent, AccountEventPublisher } from './account-events';

/**
 * Publica cada evento por HTTP a los suscriptores de ACCOUNT_EVENT_WEBHOOKS
 * (URLs separadas por coma), autenticando con X-Service-Token.
 * Es best effort: registra los fallos y sigue con el resto.
 */
@Injectable()
export class HttpAccountEventPublisher implements AccountEventPublisher {
  private readonly logger = new Logger(HttpAccountEventPublisher.name);

  constructor(
    private readonly urls: string[] = (process.env.ACCOUNT_EVENT_WEBHOOKS ?? '')
      .split(',')
      .map((url) => url.trim())
      .filter(Boolean),
    private readonly serviceToken: string = process.env.SERVICE_TOKEN ?? '',
    private readonly timeoutMs = 5000,
  ) {}

  async publish(event: AccountEvent): Promise<void> {
    await Promise.all(this.urls.map((url) => this.send(url, event)));
  }

  private async send(url: string, event: AccountEvent): Promise<void> {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Service-Token': this.serviceToken },
        body: JSON.stringify(event),
        signal: AbortSignal.timeout(this.timeoutMs),
      });
      if (!response.ok) {
        this.logger.warn(`${event.event} → ${url} respondió ${response.status}`);
      }
    } catch (error) {
      this.logger.warn(
        `${event.event} → ${url} falló: ${error instanceof Error ? error.message : String(error)}`,
      );
    }
  }
}
