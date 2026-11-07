import { EntityManager } from 'typeorm';
import { UserRole } from '../users/user-role';
import { AccountEvent, AccountEventSender, DeliveryStore, PendingDelivery } from './account-events';
import {
  AccountEventDispatcher,
  DispatcherOptions,
  retryDelayMs,
} from './account-event-dispatcher';
import { subscribersFromEnv } from './http-account-event-sender';
import { TypeOrmAccountEventOutbox } from './typeorm-account-event-outbox';

const PROFILE = 'http://profile-service:8000/api/v1/profiles/internal/account-events';
const JOBS = 'http://jobs-service:8000/api/v1/jobs/internal/account-events';
const USER_ID = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';

const OPTIONS: DispatcherOptions = {
  intervalMs: 1000,
  batchSize: 10,
  leaseMs: 60_000,
  baseDelayMs: 5_000,
  maxDelayMs: 60_000,
};

function event(type: AccountEvent['event'], id: string, userId = USER_ID): AccountEvent {
  return {
    event_id: id,
    event: type,
    user_id: userId,
    role: UserRole.COMPANY,
    deleted: type === 'account.deleted',
    email: 'empresa@example.test',
    actor_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
    occurred_at: '2026-11-07T12:00:00.000Z',
  };
}

interface Row extends PendingDelivery {
  nextAttemptAt: number;
  deliveredAt?: number;
  lastError?: string;
}

/** Mismas reglas que TypeOrmDeliveryStore: vencidas, la más vieja por (suscriptor, usuario). */
class InMemoryDeliveryStore implements DeliveryStore {
  rows: Row[] = [];
  private seq = 0;

  constructor(private readonly clock: { now: number }) {}

  add(subscriber: string, payload: AccountEvent): void {
    this.seq += 1;
    this.rows.push({
      id: String(this.seq),
      subscriber,
      payload,
      attempts: 0,
      nextAttemptAt: this.clock.now,
    });
  }

  async claimDue(limit: number, leaseMs: number): Promise<PendingDelivery[]> {
    const pending = this.rows.filter((r) => r.deliveredAt === undefined);
    const heads = pending.filter(
      (r) =>
        r.nextAttemptAt <= this.clock.now &&
        !pending.some(
          (p) =>
            p.subscriber === r.subscriber &&
            p.payload.user_id === r.payload.user_id &&
            Number(p.id) < Number(r.id),
        ),
    );
    const claimed = heads.slice(0, limit);
    for (const row of claimed) row.nextAttemptAt = this.clock.now + leaseMs;
    return claimed.map(({ id, subscriber, payload, attempts }) => ({
      id,
      subscriber,
      payload,
      attempts,
    }));
  }

  async markDelivered(id: string): Promise<void> {
    const row = this.find(id);
    row.attempts += 1;
    row.deliveredAt = this.clock.now;
  }

  async markFailed(id: string, error: string, nextAttemptAt: Date): Promise<void> {
    const row = this.find(id);
    row.attempts += 1;
    row.lastError = error;
    row.nextAttemptAt = nextAttemptAt.getTime();
  }

  pending(subscriber?: string): Row[] {
    return this.rows.filter(
      (r) => r.deliveredAt === undefined && (!subscriber || r.subscriber === subscriber),
    );
  }

  private find(id: string): Row {
    const row = this.rows.find((r) => r.id === id);
    if (!row) throw new Error(`no existe ${id}`);
    return row;
  }
}

/** Suscriptores que se pueden "caer" y "levantar"; registra lo que recibió cada uno. */
class FakeSubscribers implements AccountEventSender {
  down = new Set<string>();
  received: Array<{ subscriber: string; event: string; event_id: string }> = [];

  async send(subscriber: string, payload: AccountEvent): Promise<void> {
    if (this.down.has(subscriber)) throw new Error('fetch failed (ECONNREFUSED)');
    this.received.push({ subscriber, event: payload.event, event_id: payload.event_id });
  }
}

function setup() {
  const clock = { now: Date.parse('2026-11-07T12:00:00Z') };
  const store = new InMemoryDeliveryStore(clock);
  const subscribers = new FakeSubscribers();
  const dispatcher = new AccountEventDispatcher(
    store,
    subscribers,
    OPTIONS,
    () => new Date(clock.now),
  );
  const advance = (ms: number) => {
    clock.now += ms;
  };
  return { clock, store, subscribers, dispatcher, advance };
}

describe('AccountEventDispatcher (outbox con reintentos)', () => {
  it('UT-AUTH-ADM-11 un receptor caído recibe el borrado cuando se recupera', async () => {
    const { store, subscribers, dispatcher, advance } = setup();
    subscribers.down.add(PROFILE);
    const deleted = event('account.deleted', 'evt-1');
    store.add(PROFILE, deleted);
    store.add(JOBS, deleted);

    // Primer intento: jobs recibe; profile está caído y queda pendiente con su error.
    await expect(dispatcher.run()).resolves.toEqual({ delivered: 1, failed: 1 });
    expect(subscribers.received).toEqual([
      { subscriber: JOBS, event: 'account.deleted', event_id: 'evt-1' },
    ]);
    expect(store.pending(PROFILE)).toHaveLength(1);
    expect(store.pending(PROFILE)[0]).toMatchObject({
      attempts: 1,
      lastError: expect.stringContaining('ECONNREFUSED'),
    });

    // Antes del backoff no reintenta; sigue caído en el segundo intento.
    advance(1_000);
    await expect(dispatcher.run()).resolves.toEqual({ delivered: 0, failed: 0 });
    advance(5_000);
    await expect(dispatcher.run()).resolves.toEqual({ delivered: 0, failed: 1 });

    // profile-service se recupera: llega el mismo evento (mismo event_id) y no hay duplicados.
    subscribers.down.delete(PROFILE);
    advance(10_000);
    await expect(dispatcher.run()).resolves.toEqual({ delivered: 1, failed: 0 });
    expect(subscribers.received).toEqual([
      { subscriber: JOBS, event: 'account.deleted', event_id: 'evt-1' },
      { subscriber: PROFILE, event: 'account.deleted', event_id: 'evt-1' },
    ]);
    expect(store.pending()).toHaveLength(0);
    expect(store.rows.find((r) => r.subscriber === PROFILE)?.attempts).toBe(3);
  });

  it('UT-AUTH-ADM-12 respeta el orden por cuenta: un updated viejo no llega después del deleted', async () => {
    const { store, subscribers, dispatcher, advance } = setup();
    subscribers.down.add(PROFILE);
    store.add(PROFILE, event('account.updated', 'evt-1'));
    store.add(PROFILE, event('account.deleted', 'evt-2'));
    store.add(PROFILE, event('account.updated', 'evt-3', 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'));

    await dispatcher.run();
    // Sólo se intentaron las cabezas de cada cuenta: evt-1 y evt-3 (otra cuenta).
    expect(store.rows.map((r) => r.attempts)).toEqual([1, 0, 1]);

    subscribers.down.delete(PROFILE);
    advance(5_000);
    await dispatcher.run();
    expect(subscribers.received.map((r) => r.event_id)).toEqual(['evt-1', 'evt-3', 'evt-2']);
    expect(store.pending()).toHaveLength(0);
  });

  it('un suscriptor caído no frena a los demás ni a otras cuentas', async () => {
    const { store, subscribers, dispatcher } = setup();
    subscribers.down.add(JOBS);
    store.add(JOBS, event('account.deleted', 'evt-1'));
    store.add(PROFILE, event('account.deleted', 'evt-1'));
    store.add(PROFILE, event('account.updated', 'evt-2'));

    await dispatcher.run();
    expect(subscribers.received.map((r) => `${r.subscriber}|${r.event_id}`)).toEqual([
      `${PROFILE}|evt-1`,
      `${PROFILE}|evt-2`,
    ]);
    expect(store.pending()).toEqual([expect.objectContaining({ subscriber: JOBS })]);
  });

  it('el backoff es exponencial con tope', () => {
    expect([1, 2, 3, 4, 5, 6, 50].map((n) => retryDelayMs(n, OPTIONS))).toEqual([
      5_000, 10_000, 20_000, 40_000, 60_000, 60_000, 60_000,
    ]);
  });

  it('un trigger durante una corrida no se pierde: vuelve a correr al terminar', async () => {
    const { store, subscribers, dispatcher } = setup();
    let release!: () => void;
    const gate = new Promise<void>((resolve) => (release = resolve));
    const send = subscribers.send.bind(subscribers);
    jest.spyOn(subscribers, 'send').mockImplementationOnce(async (s, p) => {
      await gate;
      return send(s, p);
    });
    store.add(PROFILE, event('account.updated', 'evt-1'));
    const first = dispatcher.run();
    // Llega un evento nuevo de otra cuenta mientras la primera corrida espera.
    store.add(PROFILE, event('account.deleted', 'evt-2', 'cccccccc-cccc-4ccc-8ccc-cccccccccccc'));
    dispatcher.trigger();
    release();
    await first;
    await new Promise((resolve) => setImmediate(resolve));
    await new Promise((resolve) => setImmediate(resolve));
    expect(subscribers.received.map((r) => r.event_id).sort()).toEqual(['evt-1', 'evt-2']);
  });
});

describe('TypeOrmAccountEventOutbox', () => {
  it('UT-AUTH-ADM-13 guarda una entrega por suscriptor en la transacción del caso de uso', async () => {
    const onCommitted = jest.fn();
    const outbox = new TypeOrmAccountEventOutbox([PROFILE, JOBS], onCommitted);
    const manager = { query: jest.fn().mockResolvedValue([]) };
    const deleted = event('account.deleted', '11111111-1111-4111-8111-111111111111');

    await outbox.enqueue(manager as unknown as EntityManager, deleted);

    expect(manager.query).toHaveBeenCalledTimes(2);
    for (const [index, subscriber] of [PROFILE, JOBS].entries()) {
      const [sql, params] = manager.query.mock.calls[index] as [string, unknown[]];
      expect(sql).toContain('INSERT INTO auth.account_event_deliveries');
      expect(params).toEqual([
        deleted.event_id,
        'account.deleted',
        USER_ID,
        subscriber,
        JSON.stringify(deleted),
      ]);
    }
    expect(onCommitted).not.toHaveBeenCalled();
    outbox.afterCommit();
    expect(onCommitted).toHaveBeenCalledTimes(1);
  });

  it('sin suscriptores no guarda nada ni dispara entregas', async () => {
    const onCommitted = jest.fn();
    const outbox = new TypeOrmAccountEventOutbox(subscribersFromEnv(' , '), onCommitted);
    const manager = { query: jest.fn() };
    await outbox.enqueue(manager as unknown as EntityManager, event('account.updated', 'e'));
    outbox.afterCommit();
    expect(manager.query).not.toHaveBeenCalled();
    expect(onCommitted).not.toHaveBeenCalled();
  });

  it('ACCOUNT_EVENT_WEBHOOKS se separa por coma, sin vacíos ni repetidos', () => {
    expect(subscribersFromEnv(` ${PROFILE},,${JOBS} ,${PROFILE}`)).toEqual([PROFILE, JOBS]);
  });
});
