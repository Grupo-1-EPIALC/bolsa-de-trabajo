import { Injectable, UnauthorizedException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { User } from '../users/user.entity';
import { UserRole } from '../users/user-role';
import { AuthenticatedUser } from './current-user.decorator';

/** Lee la versión vigente de los tokens de una cuenta (null si no existe o está borrada). */
export interface TokenVersionReader {
  current(userId: string): Promise<{ role: UserRole; tokenVersion: number } | null>;
}

@Injectable()
export class UserTokenVersionReader implements TokenVersionReader {
  constructor(@InjectRepository(User) private readonly users: Repository<User>) {}

  async current(userId: string): Promise<{ role: UserRole; tokenVersion: number } | null> {
    // find() excluye las cuentas con borrado lógico.
    const user = await this.users.findOne({
      where: { id: userId },
      select: { id: true, role: true, tokenVersion: true },
    });
    return user ? { role: user.role, tokenVersion: user.tokenVersion } : null;
  }
}

const revoked = () =>
  new UnauthorizedException({
    message: 'La sesión ya no es válida. Iniciá sesión nuevamente.',
    error: 'TOKEN_REVOKED',
  });

/**
 * Además de la firma y los claims (que valida passport-jwt), comprueba contra la base que
 * la cuenta siga activa, con el mismo rol y la misma `token_version`. Así un reset, un
 * borrado o un cambio de clave cortan al instante los access tokens ya emitidos.
 */
export class AccessTokenValidator {
  constructor(private readonly versions: TokenVersionReader) {}

  async validate(payload: AuthenticatedUser): Promise<AuthenticatedUser> {
    if (
      typeof payload.sub !== 'string' ||
      !payload.sub ||
      !Object.values(UserRole).includes(payload.role)
    ) {
      throw new UnauthorizedException('JWT payload inválido');
    }
    const tokenVersion = payload.tv ?? 0;
    if (!Number.isInteger(tokenVersion)) {
      throw new UnauthorizedException('JWT payload inválido');
    }
    const current = await this.versions.current(payload.sub);
    if (!current || current.role !== payload.role || current.tokenVersion !== tokenVersion) {
      throw revoked();
    }
    return { sub: payload.sub, role: payload.role, tv: tokenVersion };
  }
}
