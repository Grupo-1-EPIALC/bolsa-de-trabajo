import { Controller, Get } from '@nestjs/common';

export interface HealthStatus {
  status: 'ok';
  service: string;
  version: string;
}

@Controller('health')
export class HealthController {
  @Get()
  check(): HealthStatus {
    return { status: 'ok', service: 'auth-service', version: '0.0.1' };
  }
}
