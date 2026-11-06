import { BadRequestException, ForbiddenException, NotFoundException } from '@nestjs/common';
import { DataSource, EntityManager, Repository } from 'typeorm';
import { AuthService } from '../auth/auth.service';
import { AccountStatus } from '../users/account-status';
import { Company } from '../users/company.entity';
import { User } from '../users/user.entity';
import { UserRole } from '../users/user-role';
import { AccountEventPublisher } from './account-events';
import { AdminUsersService } from './admin-users.service';

const ADMIN_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const USER_ID = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';

function makeUser(overrides: Partial<User> = {}): User {
  return Object.assign(new User(), {
    id: USER_ID,
    email: 'persona@example.test',
    role: UserRole.STUDENT,
    status: AccountStatus.ACTIVE,
    suspendedAt: null,
    suspensionReason: null,
    deletedAt: null,
    emailVerifiedAt: null,
    createdAt: new Date('2026-11-01T00:00:00Z'),
    updatedAt: new Date('2026-11-01T00:00:00Z'),
    ...overrides,
  });
}

function setup(initial: User | null = makeUser()) {
  let current = initial;
  const sessionUpdate = {
    update: jest.fn().mockReturnThis(),
    set: jest.fn().mockReturnThis(),
    where: jest.fn().mockReturnThis(),
    execute: jest.fn().mockResolvedValue({ affected: 2 }),
  };
  const manager = {
    update: jest.fn(async (_entity: unknown, _criteria: unknown, patch: Partial<User>) => {
      if (current && _entity === User) current = Object.assign(makeUser(), current, patch);
      return { affected: 1 };
    }),
    createQueryBuilder: jest.fn(() => sessionUpdate),
  };
  const dataSource = {
    transaction: jest.fn(async (cb: (m: EntityManager) => Promise<unknown>) =>
      cb(manager as unknown as EntityManager),
    ),
  };
  const listQb = {
    leftJoinAndSelect: jest.fn().mockReturnThis(),
    withDeleted: jest.fn().mockReturnThis(),
    andWhere: jest.fn().mockReturnThis(),
    orderBy: jest.fn().mockReturnThis(),
    skip: jest.fn().mockReturnThis(),
    take: jest.fn().mockReturnThis(),
    getManyAndCount: jest.fn(async () => [[makeUser()], 41]),
  };
  const users = {
    findOne: jest.fn(async () => current),
    update: jest.fn(async (_id: string, patch: Partial<User>) => {
      current = Object.assign(makeUser(), current, patch);
      return { affected: 1 };
    }),
    createQueryBuilder: jest.fn(() => listQb),
  };
  const auth = { sendPasswordResetLink: jest.fn().mockResolvedValue(true) };
  const events: AccountEventPublisher = { publish: jest.fn().mockResolvedValue(undefined) };
  const service = new AdminUsersService(
    users as unknown as Repository<User>,
    dataSource as unknown as DataSource,
    auth as unknown as AuthService,
    events,
  );
  return { service, users, manager, sessionUpdate, listQb, auth, events };
}

describe('AdminUsersService', () => {
  it('UT-AUTH-ADM-01 lista sin borrados por defecto y pagina', async () => {
    const { service, listQb } = setup();
    const result = await service.list({ role: UserRole.STUDENT, page: 2, size: 20 });
    expect(listQb.withDeleted).not.toHaveBeenCalled();
    expect(listQb.skip).toHaveBeenCalledWith(20);
    expect(result).toMatchObject({ total: 41, page: 2, size: 20, pages: 3 });
    expect(result.items[0]).toMatchObject({ id: USER_ID, status: 'active', deleted: false });
  });

  it('UT-AUTH-ADM-02 include_deleted muestra también las cuentas borradas', async () => {
    const { service, listQb } = setup();
    await service.list({ include_deleted: true, page: 1, size: 20 });
    expect(listQb.withDeleted).toHaveBeenCalled();
  });

  it('UT-AUTH-ADM-03 suspender cierra las sesiones y avisa a los servicios', async () => {
    const { service, sessionUpdate, events } = setup();
    const view = await service.suspend(ADMIN_ID, USER_ID, { reason: 'Uso indebido' });
    expect(view.status).toBe(AccountStatus.SUSPENDED);
    expect(view.suspension_reason).toBe('Uso indebido');
    expect(sessionUpdate.execute).toHaveBeenCalled();
    expect(events.publish).toHaveBeenCalledWith(
      expect.objectContaining({ event: 'account.suspended', user_id: USER_ID, actor_id: ADMIN_ID }),
    );
  });

  it('UT-AUTH-ADM-04 no permite suspender ni borrar la propia cuenta', async () => {
    const { service } = setup();
    await expect(service.suspend(ADMIN_ID, ADMIN_ID, {})).rejects.toBeInstanceOf(
      ForbiddenException,
    );
    await expect(service.softDelete(ADMIN_ID, ADMIN_ID)).rejects.toBeInstanceOf(ForbiddenException);
  });

  it('UT-AUTH-ADM-05 reactivar limpia la suspensión', async () => {
    const { service, events } = setup(
      makeUser({ status: AccountStatus.SUSPENDED, suspensionReason: 'x', suspendedAt: new Date() }),
    );
    const view = await service.reactivate(ADMIN_ID, USER_ID);
    expect(view).toMatchObject({ status: 'active', suspension_reason: null, suspended_at: null });
    expect(events.publish).toHaveBeenCalledWith(
      expect.objectContaining({ event: 'account.reactivated' }),
    );
  });

  it('UT-AUTH-ADM-06 el borrado lógico marca usuario y empresa, revoca sesiones y avisa', async () => {
    const company = Object.assign(new Company(), {
      userId: USER_ID,
      legalName: 'Empresa Ficticia',
      cuit: '30712345671',
      activity: 'Software',
    });
    const { service, manager, sessionUpdate, events } = setup(
      makeUser({ role: UserRole.COMPANY, company }),
    );
    await service.softDelete(ADMIN_ID, USER_ID);
    expect(manager.update).toHaveBeenCalledWith(
      User,
      USER_ID,
      expect.objectContaining({ deletedAt: expect.any(Date) }),
    );
    expect(manager.update).toHaveBeenCalledWith(
      Company,
      USER_ID,
      expect.objectContaining({ deletedAt: expect.any(Date) }),
    );
    expect(sessionUpdate.execute).toHaveBeenCalled();
    expect(events.publish).toHaveBeenCalledWith(
      expect.objectContaining({ event: 'account.deleted', deleted: true, role: UserRole.COMPANY }),
    );
  });

  it('UT-AUTH-ADM-07 el reset invalida la clave, cierra sesiones y manda el link', async () => {
    const { service, manager, sessionUpdate, auth } = setup();
    const result = await service.resetPassword(USER_ID);
    expect(manager.update).toHaveBeenCalledWith(
      User,
      USER_ID,
      expect.objectContaining({ passwordHash: expect.stringMatching(/^\$argon2id\$/) }),
    );
    expect(sessionUpdate.execute).toHaveBeenCalled();
    expect(auth.sendPasswordResetLink).toHaveBeenCalledWith(USER_ID, 'persona@example.test');
    expect(result.email_sent).toBe(true);
  });

  it('UT-AUTH-ADM-08 cambia el email directamente y lo normaliza', async () => {
    const { service, manager, events } = setup();
    const view = await service.update(ADMIN_ID, USER_ID, { email: '  Nuevo@Example.TEST ' });
    expect(manager.update).toHaveBeenCalledWith(
      User,
      USER_ID,
      expect.objectContaining({ email: 'nuevo@example.test', pendingEmail: null }),
    );
    expect(view.email).toBe('nuevo@example.test');
    expect(events.publish).toHaveBeenCalledWith(
      expect.objectContaining({ event: 'account.updated' }),
    );
  });

  it('UT-AUTH-ADM-09 valida los datos de empresa', async () => {
    const { service } = setup();
    await expect(
      service.update(ADMIN_ID, USER_ID, { company: { legal_name: 'X' } }),
    ).rejects.toBeInstanceOf(BadRequestException);
    const company = setup(makeUser({ role: UserRole.COMPANY }));
    await expect(
      company.service.update(ADMIN_ID, USER_ID, { company: { cuit: '30712345670' } }),
    ).rejects.toThrow('El CUIT de la empresa no es válido');
  });

  it('UT-AUTH-ADM-10 una cuenta inexistente o borrada da 404', async () => {
    const { service } = setup(null);
    await expect(service.suspend(ADMIN_ID, USER_ID, {})).rejects.toBeInstanceOf(NotFoundException);
  });
});
