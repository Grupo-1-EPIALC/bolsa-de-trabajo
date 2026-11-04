import { Injectable, UnauthorizedException } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { readFileSync } from 'node:fs';
import { AuthenticatedUser } from './current-user.decorator';
import { UserRole } from '../users/user-role';

function readPublicKey(): string {
  const path = process.env.JWT_PUBLIC_KEY_PATH;
  if (!path) {
    throw new Error('JWT_PUBLIC_KEY_PATH es obligatorio');
  }
  return readFileSync(path, 'utf8');
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  constructor() {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      secretOrKey: readPublicKey(),
      algorithms: ['RS256'],
      issuer: process.env.JWT_ISSUER ?? 'bolsa-auth',
      audience: process.env.JWT_AUDIENCE ?? 'bolsa-api',
    });
  }

  validate(payload: AuthenticatedUser): AuthenticatedUser {
    if (!payload.sub || !Object.values(UserRole).includes(payload.role)) {
      throw new UnauthorizedException('JWT payload inválido');
    }
    return payload;
  }
}
