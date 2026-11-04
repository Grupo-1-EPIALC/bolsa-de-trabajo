import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { TypeOrmModule } from '@nestjs/typeorm';
import { readFileSync } from 'node:fs';
import { SignOptions } from 'jsonwebtoken';
import { Company } from '../users/company.entity';
import { User } from '../users/user.entity';
import { ActionToken } from './action-token.entity';
import { AuthController } from './auth.controller';
import { AuthService } from './auth.service';
import { EMAIL_NOTIFIER } from './email-notifier';
import { RefreshSession } from './refresh-session.entity';
import { JwtAuthGuard } from './jwt-auth.guard';
import { JwtStrategy } from './jwt.strategy';
import { SmtpEmailNotifier } from './smtp-email-notifier';

function readPrivateKey(): string {
  const path = process.env.JWT_PRIVATE_KEY_PATH;
  if (!path) {
    throw new Error('JWT_PRIVATE_KEY_PATH es obligatorio');
  }
  return readFileSync(path, 'utf8');
}

function readPublicKey(): string {
  const path = process.env.JWT_PUBLIC_KEY_PATH;
  if (!path) {
    throw new Error('JWT_PUBLIC_KEY_PATH es obligatorio');
  }
  return readFileSync(path, 'utf8');
}

@Module({
  imports: [
    TypeOrmModule.forFeature([User, Company, RefreshSession, ActionToken]),
    PassportModule.register({ defaultStrategy: 'jwt' }),
    JwtModule.registerAsync({
      useFactory: () => ({
        privateKey: readPrivateKey(),
        publicKey: readPublicKey(),
        signOptions: {
          algorithm: 'RS256',
          issuer: process.env.JWT_ISSUER ?? 'bolsa-auth',
          audience: process.env.JWT_AUDIENCE ?? 'bolsa-api',
          expiresIn: (process.env.JWT_ACCESS_TTL ?? '15m') as SignOptions['expiresIn'],
        },
      }),
    }),
  ],
  controllers: [AuthController],
  providers: [
    AuthService,
    JwtStrategy,
    JwtAuthGuard,
    SmtpEmailNotifier,
    { provide: EMAIL_NOTIFIER, useExisting: SmtpEmailNotifier },
  ],
})
export class AuthModule {}
