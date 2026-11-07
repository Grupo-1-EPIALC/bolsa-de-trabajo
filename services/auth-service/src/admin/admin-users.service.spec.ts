import { BadRequestException, ForbiddenException, NotFoundException } from '@nestjs/common';
import { DataSource, EntityManager, Repository } from 'typeorm';
import { AuthService } from '../auth/auth.service';
import { Company } from '../users/company.entity';
import { User } from '../users/user.entity';
import { UserRole } from '../users/user-role';
import { AccountEventOutbox } from './account-events';
import { AdminUsersService } from './admin-users.service';

const ADMIN_ID = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const USER_ID = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';

function makeUser(overrides: Partial<User> = {}): User {
  return Object.assign(new User(), {
    id: USER_ID,
    email: 'persona@example.test',
    role: UserRole.STUDENT,
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
    findOne: jest.fn(async () => current),
  };
  const log: string[] = [];
  const dataSource = {
    transaction: jest.fn(async (cb: (m: EntityManager) => Promise<unknown>) => {
      log.push('begin');
      const result = await cb(manager as unknown as EntityManager);
      log.push('commit');
      return result;
    }),
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
  const outbox = {
    enqueue: jest.fn(async (m: EntityManager) => {
      log.push(m === (manager as unknown as EntityManager) ? 'enqueue(tx)' : 'enqueue(otro)');
    }),
    afterCommit: jest.fn(() => log.push('afterCommit')),
  };
  const service = new AdminUsersService(
    users as unknown as Repository<User>,
    dataSource as unknown as DataSource,
    auth as unknown as AuthService,
    outbox as unknown as AccountEventOutbox,
  );
  return { service, users, manager, sessionUpdate, listQb, auth, outbox, log };
}

describe('AdminUsersService', () => {
  it('UT-AUTH-ADM-01 lista sin borrados por defecto y pagina', async () => {
    const { service, listQb } = setup();
    const result = await service.list({ role: UserRole.STUDENT, page: 2, size: 20 });
    expect(listQb.withDeleted).not.toHaveBeenCalled();
    expect(listQb.skip).toHaveBeenCalledWith(20);
    expect(result).toMatchObject({ total: 41, page: 2, size: 20, pages: 3 });
    expect(result.items[0]).toMatchObject({ id: USER_ID, deleted: false });
  });

  it('UT-AUTH-ADM-02 include_deleted muestra también las cuentas borradas', async () => {
    const { service, listQb } = setup();
    await service.list({ include_deleted: true, page: 1, size: 20 });
    expect(listQb.withDeleted).toHaveBeenCalled();
  });

  it('UT-AUTH-ADM-03 no permite borrar la propia cuenta', async () => {
    const { service } = setup();
    await expect(service.softDelete(ADMIN_ID, ADMIN_ID)).rejects.toBeInstanceOf(ForbiddenException);
  });

  it('UT-AUTH-ADM-04 el borrado lógico marca usuario y empresa, revoca sesiones y avisa', async () => {
    const company = Object.assign(new Company(), {
      userId: USER_ID,
      legalName: 'Empresa Ficticia',
      cuit: '30712345671',
      activity: 'Software',
    });
    const { service, manager, sessionUpdate, outbox } = setup(
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
    expect(outbox.enqueue).toHaveBeenCalledWith(
      manager,
      expect.objectContaining({
        event: 'account.deleted',
        deleted: true,
        role: UserRole.COMPANY,
        event_id: expect.stringMatching(/^[0-9a-f-]{36}$/),
      }),
    );
  });

  it('UT-AUTH-ADM-05 el reset invalida la clave, cierra sesiones y manda el link', async () => {
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

  it('UT-AUTH-ADM-06 cambia el email directamente y lo normaliza', async () => {
    const { service, manager, outbox } = setup();
    const view = await service.update(ADMIN_ID, USER_ID, { email: '  Nuevo@Example.TEST ' });
    expect(manager.update).toHaveBeenCalledWith(
      User,
      USER_ID,
      expect.objectContaining({ email: 'nuevo@example.test', pendingEmail: null }),
    );
    expect(view.email).toBe('nuevo@example.test');
    expect(outbox.enqueue).toHaveBeenCalledWith(
      manager,
      expect.objectContaining({ event: 'account.updated', email: 'nuevo@example.test' }),
    );
    expect(outbox.afterCommit).toHaveBeenCalled();
  });

  it('UT-AUTH-ADM-07 valida los datos de empresa', async () => {
    const { service } = setup();
    await expect(
      service.update(ADMIN_ID, USER_ID, { company: { legal_name: 'X' } }),
    ).rejects.toBeInstanceOf(BadRequestException);
    const company = setup(makeUser({ role: UserRole.COMPANY }));
    await expect(
      company.service.update(ADMIN_ID, USER_ID, { company: { cuit: '30712345670' } }),
    ).rejects.toThrow('El CUIT de la empresa no es válido');
  });

  it('UT-AUTH-ADM-08 una cuenta inexistente o borrada da 404', async () => {
    const { service } = setup(null);
    await expect(service.softDelete(ADMIN_ID, USER_ID)).rejects.toBeInstanceOf(NotFoundException);
  });

  it('UT-AUTH-ADM-09 el aviso de borrado se guarda en la misma transacción y se envía después del commit', async () => {
    const { service, log } = setup();
    await service.softDelete(ADMIN_ID, USER_ID);
    expect(log).toEqual(['begin', 'enqueue(tx)', 'commit', 'afterCommit']);
  });

  it('si no se puede guardar el aviso, el borrado no se confirma', async () => {
    const { service, outbox, log } = setup();
    outbox.enqueue.mockRejectedValueOnce(new Error('outbox no disponible'));
    await expect(service.softDelete(ADMIN_ID, USER_ID)).rejects.toThrow('outbox no disponible');
    expect(log).toEqual(['begin']);
    expect(outbox.afterCommit).not.toHaveBeenCalled();
  });

  it('UT-AUTH-ADM-10 reset y borrado suben token_version (cortan los access tokens vigentes)', async () => {
    const bump = expect.objectContaining({ tokenVersion: expect.any(Function) });
    const reset = setup();
    await reset.service.resetPassword(USER_ID);
    expect(reset.manager.update).toHaveBeenCalledWith(User, USER_ID, bump);

    const deleted = setup();
    await deleted.service.softDelete(ADMIN_ID, USER_ID);
    expect(deleted.manager.update).toHaveBeenCalledWith(User, USER_ID, bump);
    const patch = deleted.manager.update.mock.calls.find(([entity]) => entity === User)?.[2] as
      { tokenVersion: () => string } | undefined;
    expect(patch?.tokenVersion()).toBe('token_version + 1');
  });
});
