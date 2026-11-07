import {
  BadRequestException,
  ConflictException,
  ForbiddenException,
  Inject,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import * as argon2 from 'argon2';
import { randomBytes } from 'node:crypto';
import { Brackets, DataSource, EntityManager, IsNull, Repository } from 'typeorm';
import { ActionToken } from '../auth/action-token.entity';
import { AuthService } from '../auth/auth.service';
import { isValidCuit } from '../auth/cuit';
import { RefreshSession } from '../auth/refresh-session.entity';
import { Company } from '../users/company.entity';
import { User } from '../users/user.entity';
import { UserRole } from '../users/user-role';
import { ACCOUNT_EVENT_PUBLISHER, AccountEventPublisher, AccountEventType } from './account-events';
import { AdminUpdateUserDto, ListUsersQuery } from './admin.dto';

/** Vista de una cuenta para el panel de administración. */
export interface AdminUserView {
  id: string;
  email: string;
  role: UserRole;
  deleted: boolean;
  created_at: string;
  updated_at: string;
  email_verified_at: string | null;
  deleted_at: string | null;
  company?: { legal_name: string; cuit: string; activity: string };
}

export interface AdminUserList {
  items: AdminUserView[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

const iso = (date: Date | null | undefined): string | null => (date ? date.toISOString() : null);

/**
 * Casos de uso del panel de admin sobre cuentas y empresas (auth-service es su dueño).
 * Cada cambio revoca sesiones cuando corresponde y avisa a los demás servicios.
 */
@Injectable()
export class AdminUsersService {
  constructor(
    @InjectRepository(User) private readonly users: Repository<User>,
    private readonly dataSource: DataSource,
    private readonly auth: AuthService,
    @Inject(ACCOUNT_EVENT_PUBLISHER) private readonly events: AccountEventPublisher,
  ) {}

  async list(query: ListUsersQuery): Promise<AdminUserList> {
    const page = query.page ?? 1;
    const size = query.size ?? 20;
    const qb = this.users.createQueryBuilder('user').leftJoinAndSelect('user.company', 'company');
    if (query.include_deleted) qb.withDeleted();
    if (query.role) qb.andWhere('user.role = :role', { role: query.role });
    const term = query.q?.trim().toLowerCase();
    if (term) {
      qb.andWhere(
        new Brackets((w) =>
          w
            .where('lower(user.email) LIKE :term', { term: `%${term}%` })
            .orWhere('lower(company.legal_name) LIKE :term', { term: `%${term}%` })
            .orWhere('company.cuit LIKE :term', { term: `%${term}%` }),
        ),
      );
    }
    const [rows, total] = await qb
      .orderBy('user.createdAt', 'DESC')
      .skip((page - 1) * size)
      .take(size)
      .getManyAndCount();
    return {
      items: rows.map((u) => this.toView(u)),
      total,
      page,
      size,
      pages: Math.ceil(total / size),
    };
  }

  async get(id: string): Promise<AdminUserView> {
    return this.toView(await this.load(id, true));
  }

  async update(actorId: string, id: string, input: AdminUpdateUserDto): Promise<AdminUserView> {
    const user = await this.load(id);
    if (!input.email && !input.company) {
      throw new BadRequestException('No hay cambios para guardar');
    }
    if (input.company && user.role !== UserRole.COMPANY) {
      throw new BadRequestException('Sólo las cuentas de empresa tienen datos de empresa');
    }
    if (input.company?.cuit && !isValidCuit(input.company.cuit)) {
      throw new BadRequestException('El CUIT de la empresa no es válido');
    }

    try {
      await this.dataSource.transaction(async (manager) => {
        if (input.email) {
          const email = input.email.trim().toLowerCase();
          if (email !== user.email) {
            await manager.update(User, user.id, {
              email,
              pendingEmail: null,
              emailVerifiedAt: null,
            });
            await this.consumeTokens(manager, user.id);
          }
        }
        if (input.company && user.company) {
          const patch: Partial<Company> = {};
          if (input.company.legal_name) patch.legalName = input.company.legal_name.trim();
          if (input.company.activity) patch.activity = input.company.activity.trim();
          if (input.company.cuit) patch.cuit = input.company.cuit;
          if (Object.keys(patch).length) await manager.update(Company, user.id, patch);
        }
      });
    } catch (error) {
      if (this.isUniqueViolation(error)) {
        throw new ConflictException('El email o CUIT ya está registrado');
      }
      throw error;
    }

    const updated = await this.load(id);
    await this.publish('account.updated', updated, actorId);
    return this.toView(updated);
  }

  /**
   * Fuerza el cambio de clave: invalida la clave actual, cierra las sesiones y manda
   * el link de recuperación al email de la cuenta.
   */
  async resetPassword(id: string): Promise<{ message: string; email_sent: boolean }> {
    const user = await this.load(id);
    const unusable = await argon2.hash(randomBytes(32).toString('base64url'), {
      type: argon2.argon2id,
    });
    await this.dataSource.transaction(async (manager) => {
      await manager.update(User, user.id, { passwordHash: unusable });
      await this.revokeSessions(manager, user.id);
    });
    const sent = await this.auth.sendPasswordResetLink(user.id, user.email);
    return {
      message: sent
        ? `Se invalidó la clave y se envió el link de recuperación a ${user.email}.`
        : 'Se invalidó la clave, pero no se pudo enviar el mail. Reintentá más tarde.',
      email_sent: sent,
    };
  }

  /**
   * Borrado lógico: la cuenta deja de aparecer y de poder entrar, y el email/CUIT quedan
   * libres para una nueva alta. La fila queda para auditoría (include_deleted=true).
   */
  async softDelete(actorId: string, id: string): Promise<void> {
    this.assertNotSelf(actorId, id, 'borrar');
    const user = await this.load(id);
    const now = new Date();
    await this.dataSource.transaction(async (manager) => {
      await manager.update(User, user.id, { deletedAt: now, pendingEmail: null });
      if (user.company) await manager.update(Company, user.id, { deletedAt: now });
      await this.revokeSessions(manager, user.id);
      await this.consumeTokens(manager, user.id);
    });
    await this.publish('account.deleted', { ...user, deletedAt: now } as User, actorId);
  }

  // ------------------------------------------------------------------ helpers

  private async load(id: string, withDeleted = false): Promise<User> {
    const user = await this.users.findOne({
      where: { id },
      relations: { company: true },
      withDeleted,
    });
    if (!user) {
      throw new NotFoundException('Usuario no encontrado');
    }
    return user;
  }

  private assertNotSelf(actorId: string, id: string, action: string): void {
    if (actorId === id) {
      throw new ForbiddenException(`No podés ${action} tu propia cuenta`);
    }
  }

  private async revokeSessions(manager: EntityManager, userId: string): Promise<void> {
    await manager
      .createQueryBuilder()
      .update(RefreshSession)
      .set({ revokedAt: new Date() })
      .where('user_id = :userId AND revoked_at IS NULL', { userId })
      .execute();
  }

  private async consumeTokens(manager: EntityManager, userId: string): Promise<void> {
    await manager.update(ActionToken, { userId, consumedAt: IsNull() }, { consumedAt: new Date() });
  }

  private async publish(event: AccountEventType, user: User, actorId: string): Promise<void> {
    const view = this.toView(user);
    await this.events.publish({
      event,
      user_id: user.id,
      role: user.role,
      deleted: view.deleted,
      email: user.email,
      ...(view.company ? { company: view.company } : {}),
      actor_id: actorId,
      occurred_at: new Date().toISOString(),
    });
  }

  private toView(user: User): AdminUserView {
    const view: AdminUserView = {
      id: user.id,
      email: user.email,
      role: user.role,
      deleted: !!user.deletedAt,
      created_at: iso(user.createdAt) ?? '',
      updated_at: iso(user.updatedAt) ?? '',
      email_verified_at: iso(user.emailVerifiedAt),
      deleted_at: iso(user.deletedAt),
    };
    if (user.company) {
      view.company = {
        legal_name: user.company.legalName,
        cuit: user.company.cuit,
        activity: user.company.activity,
      };
    }
    return view;
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
