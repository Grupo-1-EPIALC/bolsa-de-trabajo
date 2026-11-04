import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { AuthModule } from './auth/auth.module';
import { InitialAuthSchema1710000000000 } from './database/migrations/1710000000000-InitialAuthSchema';
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
    migrations: [InitialAuthSchema1710000000000],
  };
}

@Module({
  imports: [TypeOrmModule.forRoot(databaseOptions()), AuthModule],
  controllers: [HealthController],
})
export class AppModule {}
