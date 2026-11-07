import { Injectable } from '@nestjs/common';
import { AccountEvent, AccountEventSender } from './account-events';

/**
 * Entrega un evento por HTTP a un suscriptor, autenticando con X-Service-Token.
 * Cualquier respuesta que no sea 2xx (o un timeout) es un error: el despachador reintenta.
 */
@Injectable()
export class HttpAccountEventSender implements AccountEventSender {
  constructor(
    private readonly serviceToken: string = process.env.SERVICE_TOKEN ?? '',
    private readonly timeoutMs = 5000,
  ) {}

  async send(subscriber: string, event: AccountEvent): Promise<void> {
    const response = await fetch(subscriber, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Service-Token': this.serviceToken },
      body: JSON.stringify(event),
      signal: AbortSignal.timeout(this.timeoutMs),
    });
    if (!response.ok) {
      throw new Error(`respondió ${response.status}`);
    }
  }
}

/** URLs de ACCOUNT_EVENT_WEBHOOKS separadas por coma (vacía = no avisa a nadie). */
export function subscribersFromEnv(raw = process.env.ACCOUNT_EVENT_WEBHOOKS ?? ''): string[] {
  return [
    ...new Set(
      raw
        .split(',')
        .map((url) => url.trim())
        .filter(Boolean),
    ),
  ];
}
