import { Injectable } from '@nestjs/common';
import { PassportStrategy } from '@nestjs/passport';
import { ExtractJwt, Strategy } from 'passport-jwt';
import { readFileSync } from 'node:fs';
import { AccessTokenValidator, UserTokenVersionReader } from './access-token-validator';
import { AuthenticatedUser } from './current-user.decorator';

function readPublicKey(): string {
  const path = process.env.JWT_PUBLIC_KEY_PATH;
  if (!path) {
    throw new Error('JWT_PUBLIC_KEY_PATH es obligatorio');
  }
  return readFileSync(path, 'utf8');
}

@Injectable()
export class JwtStrategy extends PassportStrategy(Strategy) {
  private readonly validator: AccessTokenValidator;

  constructor(versions: UserTokenVersionReader) {
    super({
      jwtFromRequest: ExtractJwt.fromAuthHeaderAsBearerToken(),
      secretOrKey: readPublicKey(),
      algorithms: ['RS256'],
      issuer: process.env.JWT_ISSUER ?? 'bolsa-auth',
      audience: process.env.JWT_AUDIENCE ?? 'bolsa-api',
    });
    this.validator = new AccessTokenValidator(versions);
  }

  validate(payload: AuthenticatedUser): Promise<AuthenticatedUser> {
    return this.validator.validate(payload);
  }
}
