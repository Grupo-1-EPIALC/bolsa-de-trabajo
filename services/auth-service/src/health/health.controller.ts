import { Controller, Get } from '@nestjs/common';
import { ApiTags } from '@nestjs/swagger';

export interface HealthStatus {
  status: 'ok';
  service: string;
  version: string;
}

@ApiTags('health')
@Controller('health')
export class HealthController {
  @Get()
  check(): HealthStatus {
    return { status: 'ok', service: 'auth-service', version: '0.0.1' };
  }
}
