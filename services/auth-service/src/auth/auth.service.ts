import {
  BadRequestException,
  ConflictException,
  Inject,
  Injectable,
  Logger,
  NotFoundException,
  ServiceUnavailableException,
  UnauthorizedException,
} from '@nestjs/common';
import { JwtService } from '@nestjs/jwt';
import { InjectRepository } from '@nestjs/typeorm';
import * as argon2 from 'argon2';
import { createHash, createPublicKey, randomBytes } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { DataSource, IsNull, MoreThan, Repository } from 'typeorm';
import { Company } from '../users/company.entity';
import { User } from '../users/user.entity';
import { UserRole } from '../users/user-role';
import { ActionToken, ActionTokenPurpose } from './action-token.entity';
import {
  ChangeEmailDto,
  ChangePasswordDto,
  LoginDto,
  PasswordResetConfirmDto,
  PasswordResetRequestDto,
  RegisterDto,
} from './auth.dto';
import { EMAIL_NOTIFIER, EmailNotifier } from './email-notifier';
import { RefreshSession } from './refresh-session.entity';
import { isValidCuit } from './cuit';

interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
  expires_in: string;
}

interface PublicUser {
  id: string;
  email: string;
  role: UserRole;
  company?: {
    legal_name: string;
    cuit: string;
    activity: string;
  };
}

const GENERIC_RESET_RESPONSE = {
  message: 'Si el email está registrado, recibirás instrucciones para restablecer la contraseña.',
};

function hashToken(token: string): string {
  return createHash('sha256').update(token).digest('hex');
}

function durationMilliseconds(value: string): number {
  const match = /^(\d+)(s|m|h|d)$/.exec(value);
  if (!match) {
    throw new Error(`Duración inválida: ${value}`);
  }
  const amount = Number(match[1]);
  const unit = { s: 1000, m: 60_000, h: 3_600_000, d: 86_400_000 }[
    match[2] as 's' | 'm' | 'h' | 'd'
  ];
  return amount * unit;
}

@Injectable()
export class AuthService {
  private readonly logger = new Logger(AuthService.name);
  private readonly refreshTtl = process.env.JWT_REFRESH_TTL ?? '7d';
  private readonly accessTtl = process.env.JWT_ACCESS_TTL ?? '15m';
  private readonly resetTtl = process.env.PASSWORD_RESET_TTL ?? '1h';
  private readonly keyId = process.env.JWT_KEY_ID ?? 'bolsa-auth-1';
  private readonly frontendUrl = (process.env.FRONTEND_URL ?? 'http://localhost:8080').replace(
    /\/$/,
    '',
  );

  constructor(
    @InjectRepository(User) private readonly users: Repository<User>,
    @InjectRepository(Company) private readonly companies: Repository<Company>,
    @InjectRepository(RefreshSession)
    private readonly refreshSessions: Repository<RefreshSession>,
    private readonly dataSource: DataSource,
    private readonly jwt: JwtService,
    @Inject(EMAIL_NOTIFIER) private readonly emailNotifier: EmailNotifier,
  ) {}

  async register(input: RegisterDto): Promise<{ user: PublicUser } & TokenPair> {
    const email = this.normalizeEmail(input.email);
    if (input.role === UserRole.COMPANY) {
      if (!input.company || !isValidCuit(input.company.cuit)) {
        throw new BadRequestException('El CUIT de la empresa no es válido');
      }
      // Sólo cuentan las empresas no borradas: un CUIT borrado puede volver a registrarse.
      const companyExists = await this.companies.exists({
        where: { cuit: input.company.cuit, deletedAt: IsNull() },
      });
      if (companyExists) {
        throw new ConflictException('El CUIT ya está registrado');
      }
    }

    const user = this.users.create({
      email,
      passwordHash: await argon2.hash(input.password, { type: argon2.argon2id }),
      role: input.role,
    });

    try {
      await this.dataSource.transaction(async (manager) => {
        await manager.save(User, user);
        if (input.role === UserRole.COMPANY && input.company) {
          user.company = this.companies.create({
            userId: user.id,
            legalName: input.company.legal_name.trim(),
            cuit: input.company.cuit,
            activity: input.company.activity.trim(),
          });
          await manager.save(Company, user.company);
        }
      });
    } catch (error) {
      if (this.isUniqueViolation(error)) {
        throw new ConflictException('El email o CUIT ya está registrado');
      }
      throw error;
    }

    return { user: this.toPublicUser(user), ...(await this.issueTokens(user)) };
  }

  async login(input: LoginDto): Promise<{ user: PublicUser } & TokenPair> {
    const user = await this.users
      .createQueryBuilder('user')
      .addSelect('user.passwordHash')
      .leftJoinAndSelect('user.company', 'company')
      .where('lower(user.email) = :email', { email: this.normalizeEmail(input.email) })
      .getOne();

    if (!user || !(await argon2.verify(user.passwordHash, input.password))) {
      throw new UnauthorizedException('Email o contraseña incorrectos');
    }
    // Las cuentas borradas no aparecen (borrado lógico): para login es como si no existieran.

    return { user: this.toPublicUser(user), ...(await this.issueTokens(user)) };
  }

  async refresh(rawToken: string): Promise<TokenPair> {
    const tokenHash = hashToken(rawToken);
    const result = await this.dataSource.transaction(async (manager) => {
      const session = await manager.findOne(RefreshSession, {
        where: {
          tokenHash,
          revokedAt: IsNull(),
          expiresAt: MoreThan(new Date()),
        },
      });
      if (!session) {
        throw new UnauthorizedException('Refresh token inválido o expirado');
      }

      const revoked = await manager.update(
        RefreshSession,
        { id: session.id, revokedAt: IsNull() },
        { revokedAt: new Date() },
      );
      if (revoked.affected !== 1) {
        throw new UnauthorizedException('Refresh token inválido o expirado');
      }

      const user = await manager.findOne(User, { where: { id: session.userId } });
      if (!user) {
        throw new UnauthorizedException('Refresh token inválido o expirado');
      }
      return user;
    });
    return this.issueTokens(result);
  }

  async getProfile(userId: string): Promise<PublicUser> {
    const user = await this.users.findOne({
      where: { id: userId },
      relations: { company: true },
    });
    if (!user) {
      throw new NotFoundException('Usuario no encontrado');
    }
    return this.toPublicUser(user);
  }

  async changePassword(userId: string, input: ChangePasswordDto): Promise<{ message: string }> {
    const user = await this.users
      .createQueryBuilder('user')
      .addSelect('user.passwordHash')
      .where('user.id = :userId', { userId })
      .getOne();
    if (!user || !(await argon2.verify(user.passwordHash, input.current_password))) {
      throw new UnauthorizedException('La contraseña actual es incorrecta');
    }
    if (input.current_password === input.new_password) {
      throw new BadRequestException('La nueva contraseña debe ser diferente');
    }

    await this.dataSource.transaction(async (manager) => {
      await manager.update(User, userId, {
        passwordHash: await argon2.hash(input.new_password, { type: argon2.argon2id }),
        tokenVersion: () => 'token_version + 1',
      });
      await manager
        .createQueryBuilder()
        .update(RefreshSession)
        .set({ revokedAt: new Date() })
        .where('user_id = :userId AND revoked_at IS NULL', { userId })
        .execute();
      await manager.update(
        ActionToken,
        {
          userId,
          purpose: ActionTokenPurpose.PASSWORD_RESET,
          consumedAt: IsNull(),
        },
        { consumedAt: new Date() },
      );
    });
    return { message: 'Contraseña actualizada. Iniciá sesión nuevamente.' };
  }

  async requestPasswordReset(
    input: PasswordResetRequestDto,
  ): Promise<typeof GENERIC_RESET_RESPONSE> {
    const user = await this.users.findOne({
      where: { email: this.normalizeEmail(input.email) },
    });
    if (!user) {
      return GENERIC_RESET_RESPONSE;
    }

    await this.sendPasswordResetLink(user.id, user.email);
    return GENERIC_RESET_RESPONSE;
  }

  /**
   * Genera un token de recuperación y manda el link por mail.
   * Devuelve false si el mail no se pudo enviar (el token queda creado igual).
   */
  async sendPasswordResetLink(userId: string, email: string): Promise<boolean> {
    const token = await this.persistActionToken(userId, ActionTokenPurpose.PASSWORD_RESET);
    const url = `${this.frontendUrl}/auth/password/reset/confirm?token=${encodeURIComponent(token)}`;
    try {
      await this.emailNotifier.sendPasswordReset(email, url);
      return true;
    } catch (error) {
      this.logger.error(
        'Password reset email delivery failed',
        error instanceof Error ? error.stack : String(error),
      );
      return false;
    }
  }

  async confirmPasswordReset(input: PasswordResetConfirmDto): Promise<{ message: string }> {
    const tokenHash = hashToken(input.token);
    await this.dataSource.transaction(async (manager) => {
      const token = await manager.findOne(ActionToken, {
        where: {
          tokenHash,
          purpose: ActionTokenPurpose.PASSWORD_RESET,
          consumedAt: IsNull(),
          expiresAt: MoreThan(new Date()),
        },
      });
      if (!token) {
        throw new BadRequestException('El token de recuperación es inválido o expiró');
      }

      const consumed = await manager.update(
        ActionToken,
        { id: token.id, consumedAt: IsNull() },
        { consumedAt: new Date() },
      );
      if (consumed.affected !== 1) {
        throw new BadRequestException('El token de recuperación ya fue utilizado');
      }

      await manager.update(User, token.userId, {
        passwordHash: await argon2.hash(input.new_password, { type: argon2.argon2id }),
        tokenVersion: () => 'token_version + 1',
      });
      await manager.update(
        ActionToken,
        {
          userId: token.userId,
          purpose: ActionTokenPurpose.PASSWORD_RESET,
          consumedAt: IsNull(),
        },
        { consumedAt: new Date() },
      );
      await manager
        .createQueryBuilder()
        .update(RefreshSession)
        .set({ revokedAt: new Date() })
        .where('user_id = :userId AND revoked_at IS NULL', { userId: token.userId })
        .execute();
    });
    return { message: 'Contraseña restablecida. Iniciá sesión nuevamente.' };
  }

  async requestEmailChange(userId: string, input: ChangeEmailDto): Promise<{ message: string }> {
    const user = await this.users
      .createQueryBuilder('user')
      .addSelect('user.passwordHash')
      .where('user.id = :userId', { userId })
      .getOne();
    if (!user || !(await argon2.verify(user.passwordHash, input.current_password))) {
      throw new UnauthorizedException('La contraseña actual es incorrecta');
    }

    const pendingEmail = this.normalizeEmail(input.email);
    if (pendingEmail === user.email) {
      throw new BadRequestException('El nuevo email debe ser diferente');
    }
    const emailExists = await this.users
      .createQueryBuilder('user')
      .where('lower(user.email) = :email', { email: pendingEmail })
      .orWhere('lower(user.pendingEmail) = :email', { email: pendingEmail })
      .getOne();
    if (emailExists) {
      throw new ConflictException('El email ya está registrado o pendiente de confirmación');
    }

    user.pendingEmail = pendingEmail;
    await this.users.save(user);
    const token = await this.persistActionToken(
      user.id,
      ActionTokenPurpose.EMAIL_CHANGE,
      pendingEmail,
    );
    const url = `${this.frontendUrl}/auth/email/confirm?token=${encodeURIComponent(token)}`;
    try {
      await this.emailNotifier.sendEmailChange(pendingEmail, url);
    } catch (error) {
      await this.dataSource.transaction(async (manager) => {
        await manager.update(User, { id: user.id, pendingEmail }, { pendingEmail: null });
        await manager.update(
          ActionToken,
          { userId: user.id, purpose: ActionTokenPurpose.EMAIL_CHANGE, consumedAt: IsNull() },
          { consumedAt: new Date() },
        );
      });
      this.logger.error(
        'Email change confirmation delivery failed',
        error instanceof Error ? error.stack : String(error),
      );
      throw new ServiceUnavailableException('No se pudo enviar el email de confirmación');
    }
    return { message: 'Enviamos un enlace de confirmación al nuevo email.' };
  }

  async confirmEmailChange(rawToken: string): Promise<{ message: string }> {
    const tokenHash = hashToken(rawToken);
    try {
      await this.dataSource.transaction(async (manager) => {
        const token = await manager.findOne(ActionToken, {
          where: {
            tokenHash,
            purpose: ActionTokenPurpose.EMAIL_CHANGE,
            consumedAt: IsNull(),
            expiresAt: MoreThan(new Date()),
          },
        });
        if (!token?.targetEmail) {
          throw new BadRequestException('El token de confirmación es inválido o expiró');
        }

        const consumed = await manager.update(
          ActionToken,
          { id: token.id, consumedAt: IsNull() },
          { consumedAt: new Date() },
        );
        if (consumed.affected !== 1) {
          throw new BadRequestException('El token de confirmación ya fue utilizado');
        }

        const updated = await manager.update(
          User,
          { id: token.userId, pendingEmail: token.targetEmail },
          { email: token.targetEmail, pendingEmail: null, emailVerifiedAt: new Date() },
        );
        if (updated.affected !== 1) {
          throw new BadRequestException('El cambio de email ya no está pendiente');
        }
      });
    } catch (error) {
      if (this.isUniqueViolation(error)) {
        throw new ConflictException('El email ya está registrado');
      }
      throw error;
    }
    return { message: 'Email actualizado correctamente.' };
  }

  async getJwks(): Promise<{ keys: Record<string, string>[] }> {
    const path = process.env.JWT_PUBLIC_KEY_PATH;
    if (!path) {
      throw new Error('JWT_PUBLIC_KEY_PATH es obligatorio');
    }
    const jwk = createPublicKey(readFileSync(path, 'utf8')).export({ format: 'jwk' });
    return {
      keys: [
        {
          ...jwk,
          kid: this.keyId,
          use: 'sig',
          alg: 'RS256',
        } as Record<string, string>,
      ],
    };
  }

  private async persistActionToken(
    userId: string,
    purpose: ActionTokenPurpose,
    targetEmail: string | null = null,
  ): Promise<string> {
    const rawToken = randomBytes(32).toString('base64url');
    const ttl = purpose === ActionTokenPurpose.PASSWORD_RESET ? this.resetTtl : '1h';
    const ttlMs = durationMilliseconds(ttl);
    const expiresAt = new Date(Date.now() + ttlMs);

    await this.dataSource.transaction(async (manager) => {
      await manager.update(
        ActionToken,
        { userId, purpose, consumedAt: IsNull() },
        { consumedAt: new Date() },
      );
      await manager.save(
        ActionToken,
        manager.create(ActionToken, {
          userId,
          tokenHash: hashToken(rawToken),
          purpose,
          targetEmail,
          expiresAt,
        }),
      );
    });
    return rawToken;
  }

  private async issueTokens(user: User): Promise<TokenPair> {
    const refreshToken = randomBytes(48).toString('base64url');
    await this.refreshSessions.save(
      this.refreshSessions.create({
        userId: user.id,
        tokenHash: hashToken(refreshToken),
        expiresAt: new Date(Date.now() + durationMilliseconds(this.refreshTtl)),
      }),
    );
    const accessToken = await this.jwt.signAsync(
      // tv = token_version: JwtStrategy la compara con la de la cuenta en cada request.
      { sub: user.id, role: user.role, tv: user.tokenVersion ?? 0 },
      { header: { alg: 'RS256', kid: this.keyId } },
    );
    return {
      access_token: accessToken,
      refresh_token: refreshToken,
      token_type: 'Bearer',
      expires_in: this.accessTtl,
    };
  }

  private toPublicUser(user: User): PublicUser {
    const result: PublicUser = { id: user.id, email: user.email, role: user.role };
    if (user.company) {
      result.company = {
        legal_name: user.company.legalName,
        cuit: user.company.cuit,
        activity: user.company.activity,
      };
    }
    return result;
  }

  private normalizeEmail(email: string): string {
    return email.trim().toLowerCase();
  }

  private isUniqueViolation(error: unknown): boolean {
    return (
      typeof error === 'object' &&
      error !== null &&
      'driverError' in error &&
      typeof error.driverError === 'object' &&
      error.driverError !== null &&
      'code' in error.driverError &&
      error.driverError.code === '23505'
    );
  }
}
