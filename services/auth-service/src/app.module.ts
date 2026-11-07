import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AdminModule } from './admin/admin.module';
import { AuthModule } from './auth/auth.module';
import { InitialAuthSchema1710000000000 } from './database/migrations/1710000000000-InitialAuthSchema';
import { SoftDelete1793900000000 } from './database/migrations/1793900000000-SoftDelete';
import { AccountEventOutbox1794000000000 } from './database/migrations/1794000000000-AccountEventOutbox';
import { TokenVersion1794000000001 } from './database/migrations/1794000000001-TokenVersion';
import { HealthController } from './health/health.controller';

function databaseOptions() {
  const rawUrl = process.env.DATABASE_URL;
  if (!rawUrl) {
    throw new Error('DATABASE_URL es obligatorio');
  }

  const databaseUrl = new URL(rawUrl);
  databaseUrl.searchParams.delete('schema');

  return {
    type: 'postgres' as const,
    url: databaseUrl.toString(),
    schema: 'auth',
    autoLoadEntities: true,
    synchronize: false,
    migrationsRun: true,
    migrations: [
      InitialAuthSchema1710000000000,
      SoftDelete1793900000000,
      AccountEventOutbox1794000000000,
      TokenVersion1794000000001,
    ],
  };
}

@Module({
  imports: [TypeOrmModule.forRoot(databaseOptions()), AuthModule, AdminModule],
  controllers: [HealthController],
})
export class AppModule {}
