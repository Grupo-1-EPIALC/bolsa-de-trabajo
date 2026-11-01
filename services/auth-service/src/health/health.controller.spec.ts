import { HealthController } from './health.controller';

describe('HealthController', () => {
  it('devuelve status ok', () => {
    expect(new HealthController().check().status).toBe('ok');
  });
});
